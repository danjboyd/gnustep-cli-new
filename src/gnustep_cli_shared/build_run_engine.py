from __future__ import annotations

import os
import json
import subprocess
from pathlib import Path
from typing import Any


def _parse_gnumakefile(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    content = path.read_text()
    if "aggregate.make" in content:
        values["__contains_aggregate_make"] = "true"
    iterator = iter(content.splitlines())
    for line in iterator:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        value = value.strip()
        while value.endswith("\\"):
            value = value[:-1].strip()
            try:
                continuation = next(iterator).strip()
            except StopIteration:
                break
            if continuation.endswith("\\"):
                value = f"{value} {continuation[:-1].strip()} \\"
            else:
                value = f"{value} {continuation}".strip()
        values[key.strip()] = value.strip()
    return values


def detect_project(project_dir: str | Path = ".") -> dict[str, Any]:
    root = Path(project_dir).resolve()
    gnumakefile = root / "GNUmakefile"
    if not gnumakefile.exists():
        return {
            "supported": False,
            "reason": "missing_gnumakefile",
            "project_dir": str(root),
        }

    values = _parse_gnumakefile(gnumakefile)
    project_type = None
    target_name = None
    if "TOOL_NAME" in values:
        project_type = "tool"
        target_name = values["TOOL_NAME"]
    elif "APP_NAME" in values:
        project_type = "app"
        target_name = values["APP_NAME"]
    elif "LIBRARY_NAME" in values:
        project_type = "library"
        target_name = values["LIBRARY_NAME"]

    if not project_type:
        if "SUBPROJECTS" in values or values.get("__contains_aggregate_make") == "true":
            project_type = "aggregate"
        else:
            project_type = "unknown"


    return {
        "supported": True,
        "project_dir": str(root),
        "gnumakefile": str(gnumakefile),
        "project_type": project_type,
        "target_name": target_name,
        "build_system": "gnustep-make",
        "detection_reason": "gnumakefile_marker",
    }


def runnable_projects(project_dir: str | Path = ".") -> list[dict[str, Any]]:
    return _runnable_projects(project_dir, set())


def _runnable_projects(project_dir: str | Path, visited: set[str]) -> list[dict[str, Any]]:
    root = Path(project_dir).resolve()
    root_key = str(root)
    if root_key in visited:
        return []
    visited.add(root_key)

    values = _parse_gnumakefile(root / "GNUmakefile")
    apps: list[dict[str, Any]] = []
    tools: list[dict[str, Any]] = []

    for name in values.get("SUBPROJECTS", "").split():
        directory = (root / name).resolve()
        if not (directory / "GNUmakefile").exists():
            continue
        project = detect_project(directory)
        if not project["supported"]:
            continue
        if project["project_type"] == "app":
            apps.append(project)
        elif project["project_type"] == "tool":
            tools.append(project)
        for nested in _runnable_projects(directory, visited):
            if nested["project_type"] == "app":
                apps.append(nested)
            elif nested["project_type"] == "tool":
                tools.append(nested)

    return apps or tools


def runnable_project(project: dict[str, Any]) -> dict[str, Any] | None:
    if project["project_type"] in {"app", "tool"}:
        return project
    candidates = runnable_projects(project["project_dir"])
    if len(candidates) == 1:
        return candidates[0]
    return None


def plan_build(project_dir: str | Path = ".", clean_first: bool = False) -> dict[str, Any]:
    project = detect_project(project_dir)
    if not project["supported"]:
        return {
            "schema_version": 1,
            "command": "build",
            "ok": False,
            "status": "error",
            "summary": "The current directory is not a supported GNUstep project.",
            "project": project,
            "backend": None,
            "invocation": None,
        }
    if clean_first:
        return {
            "schema_version": 1,
            "command": "build",
            "ok": True,
            "status": "ok",
            "summary": "GNUstep project clean build plan created.",
            "project": project,
            "backend": "gnustep-make",
            "operation": "clean_build",
            "invocation": None,
            "phases": [
                {"name": "clean", "backend": "gnustep-make", "invocation": ["make", "distclean"]},
                {"name": "build", "backend": "gnustep-make", "invocation": ["make"]},
            ],
        }
    return {
        "schema_version": 1,
        "command": "build",
        "ok": True,
        "status": "ok",
        "summary": "GNUstep project build plan created.",
        "project": project,
        "backend": "gnustep-make",
        "invocation": ["make"],
    }


def plan_clean(project_dir: str | Path = ".") -> dict[str, Any]:
    project = detect_project(project_dir)
    if not project["supported"]:
        return {
            "schema_version": 1,
            "command": "clean",
            "ok": False,
            "status": "error",
            "summary": "The current directory is not a supported GNUstep project.",
            "project": project,
            "backend": None,
            "invocation": None,
        }
    return {
        "schema_version": 1,
        "command": "clean",
        "ok": True,
        "status": "ok",
        "summary": "GNUstep project clean plan created.",
        "project": project,
        "backend": "gnustep-make",
        "operation": "clean",
        "invocation": ["make", "distclean"],
    }


def _run_phase(phase: dict[str, Any], project_dir: str) -> dict[str, Any]:
    proc = subprocess.run(
        phase["invocation"],
        cwd=project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    result = dict(phase)
    result["stdout"] = proc.stdout
    result["stderr"] = proc.stderr
    result["exit_status"] = proc.returncode
    result["ok"] = proc.returncode == 0
    result["status"] = "ok" if proc.returncode == 0 else "error"
    return result


def execute_build(project_dir: str | Path = ".", clean_first: bool = False) -> tuple[dict[str, Any], int]:
    payload = plan_build(project_dir, clean_first=clean_first)
    if not payload["ok"]:
        return payload, 3
    if clean_first:
        completed_phases = []
        for phase in payload["phases"]:
            completed = _run_phase(phase, payload["project"]["project_dir"])
            completed_phases.append(completed)
            if not completed["ok"]:
                payload["phases"] = completed_phases
                payload["stdout"] = completed["stdout"]
                payload["stderr"] = completed["stderr"]
                payload["exit_status"] = completed["exit_status"]
                payload["ok"] = False
                payload["status"] = "error"
                payload["summary"] = "GNUstep project clean failed." if phase["name"] == "clean" else "GNUstep project build failed."
                return payload, 1
        payload["phases"] = completed_phases
        payload["stdout"] = completed_phases[-1]["stdout"]
        payload["stderr"] = completed_phases[-1]["stderr"]
        payload["exit_status"] = completed_phases[-1]["exit_status"]
        payload["summary"] = "GNUstep project clean build completed."
        return payload, 0
    proc = subprocess.run(
        payload["invocation"],
        cwd=payload["project"]["project_dir"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    payload["stdout"] = proc.stdout
    payload["stderr"] = proc.stderr
    payload["exit_status"] = proc.returncode
    payload["ok"] = proc.returncode == 0
    payload["status"] = "ok" if proc.returncode == 0 else "error"
    payload["summary"] = "GNUstep project build completed." if proc.returncode == 0 else "GNUstep project build failed."
    return payload, 0 if proc.returncode == 0 else 1


def execute_clean(project_dir: str | Path = ".") -> tuple[dict[str, Any], int]:
    payload = plan_clean(project_dir)
    if not payload["ok"]:
        return payload, 3
    phase = _run_phase(
        {"name": "clean", "backend": payload["backend"], "invocation": payload["invocation"]},
        payload["project"]["project_dir"],
    )
    payload["stdout"] = phase["stdout"]
    payload["stderr"] = phase["stderr"]
    payload["exit_status"] = phase["exit_status"]
    payload["ok"] = phase["ok"]
    payload["status"] = phase["status"]
    payload["summary"] = "GNUstep project clean completed." if phase["ok"] else "GNUstep project clean failed."
    return payload, 0 if phase["ok"] else 1


def render_build_human(payload: dict[str, Any]) -> str:
    if not payload["ok"] and not payload.get("backend"):
        return payload["summary"]
    project = payload["project"]
    lines = [
        f"build: {payload['summary']}",
        f"build: backend={payload.get('backend')}",
        f"build: project_type={project.get('project_type')} target={project.get('target_name')}",
    ]
    if payload.get("invocation"):
        lines.append(f"build: invocation={' '.join(payload['invocation'])}")
    for phase in payload.get("phases", []):
        if "exit_status" in phase:
            lines.append(f"build: phase={phase['name']} invocation={' '.join(phase['invocation'])} exit_status={phase['exit_status']}")
        else:
            lines.append(f"build: phase={phase['name']} invocation={' '.join(phase['invocation'])}")
    return "\n".join(lines)


def render_clean_human(payload: dict[str, Any]) -> str:
    if not payload["ok"] and not payload.get("backend"):
        return payload["summary"]
    project = payload["project"]
    lines = [
        f"clean: {payload['summary']}",
        f"clean: backend={payload.get('backend')}",
        f"clean: project_type={project.get('project_type')} target={project.get('target_name')}",
    ]
    if payload.get("operation"):
        lines.append(f"clean: operation={payload['operation']}")
    if payload.get("invocation"):
        lines.append(f"clean: invocation={' '.join(payload['invocation'])}")
    return "\n".join(lines)


def plan_run(project_dir: str | Path = ".") -> dict[str, Any]:
    project = detect_project(project_dir)
    if not project["supported"]:
        return {
            "schema_version": 1,
            "command": "run",
            "ok": False,
            "status": "error",
            "summary": "The current directory is not a supported GNUstep project.",
            "project": project,
            "backend": None,
            "invocation": None,
        }
    run_project = runnable_project(project)
    if run_project is None:
        candidates = runnable_projects(project["project_dir"])
        summary = (
            "Multiple runnable targets were detected. Run from a specific app or tool directory."
            if len(candidates) > 1
            else "This GNUstep project can be built, but no runnable target was detected."
        )
        return {
            "schema_version": 1,
            "command": "run",
            "ok": False,
            "status": "error",
            "summary": summary,
            "project": project,
            "runnable_targets": candidates,
            "backend": None,
            "invocation": None,
        }
    if run_project["project_type"] == "tool":
        invocation = [_tool_run_path(run_project)]
        backend = "direct-exec"
    elif run_project["project_type"] == "app":
        if os.name == "nt":
            invocation = ["bash.exe", "-lc", _windows_openapp_launch_command(run_project, project["project_dir"])]
            backend = "openapp"
        else:
            invocation = ["openapp", f"{run_project['target_name']}.app"]
            backend = "openapp"
    else:
        return {
            "schema_version": 1,
            "command": "run",
            "ok": False,
            "status": "error",
            "summary": "This GNUstep project can be built, but no runnable target was detected.",
            "project": project,
            "backend": None,
            "invocation": None,
        }
    return {
        "schema_version": 1,
        "command": "run",
        "ok": True,
        "status": "ok",
        "summary": "Run plan created.",
        "project": project,
        "run_project": run_project,
        "backend": backend,
        "invocation": invocation,
    }


def _tool_run_path(project: dict[str, Any]) -> str:
    target_name = project["target_name"]
    project_dir = Path(project["project_dir"])
    extensionless = project_dir / "obj" / target_name
    windows_executable = project_dir / "obj" / f"{target_name}.exe"
    if not extensionless.exists() and windows_executable.exists():
        return f"./obj/{target_name}.exe"
    if os.name == "nt" and not extensionless.exists():
        return f"./obj/{target_name}.exe"
    return f"./obj/{target_name}"


def _windows_runtime_path_entries(project_dir: str | Path) -> list[str]:
    root = Path(project_dir).resolve()
    entries: list[str] = []
    seen: set[str] = set()
    for dll in root.rglob("*.dll"):
        directory = str(dll.parent.resolve())
        if directory not in seen:
            seen.add(directory)
            entries.append(directory)
    return entries


def _windows_shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _windows_openapp_launch_command(run_project: dict[str, Any], project_dir: str | Path) -> str:
    project_dir = str(Path(run_project["project_dir"]).resolve()).replace("\\", "\\\\").replace("'", "'\"'\"'")
    target_name = str(run_project["target_name"]).replace("'", "'\"'\"'")
    runtime_entries = [
        f"$(cygpath -u {_windows_shell_quote(entry)})"
        for entry in _windows_runtime_path_entries(project_dir)
    ]
    runtime_path = ":".join(["/clang64/bin", "/usr/bin", *runtime_entries, "$PATH"])
    return (
        f"cd \"$(cygpath -u '{project_dir}')\""
        " && . /clang64/share/GNUstep/Makefiles/GNUstep.sh"
        f" && export PATH=\"{runtime_path}\""
        f" && /clang64/bin/openapp './{target_name}.app'"
    )


def execute_run(project_dir: str | Path = ".") -> tuple[dict[str, Any], int]:
    payload = plan_run(project_dir)
    if not payload["ok"]:
        return payload, 3
    try:
        if os.name == "nt" and payload["backend"] == "openapp" and payload["run_project"].get("project_type") == "app":
            subprocess.Popen(
                payload["invocation"],
                cwd=payload.get("run_project", payload["project"])["project_dir"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            payload["stdout"] = ""
            payload["stderr"] = ""
            payload["exit_status"] = 0
            payload["ok"] = True
            payload["status"] = "ok"
            payload["summary"] = "Run launched."
            return payload, 0
        proc = subprocess.run(
            payload["invocation"],
            cwd=payload.get("run_project", payload["project"])["project_dir"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        payload["stdout"] = ""
        payload["stderr"] = str(exc)
        payload["exit_status"] = 1
        payload["ok"] = False
        payload["status"] = "error"
        payload["summary"] = "Run target was not found. Build the project before running it."
        return payload, 1
    payload["stdout"] = proc.stdout
    payload["stderr"] = proc.stderr
    payload["exit_status"] = proc.returncode
    payload["ok"] = proc.returncode == 0
    payload["status"] = "ok" if proc.returncode == 0 else "error"
    payload["summary"] = "Run completed." if proc.returncode == 0 else "Run failed."
    return payload, 0 if proc.returncode == 0 else 1


def render_run_human(payload: dict[str, Any]) -> str:
    if not payload["ok"]:
        return payload["summary"]
    project = payload.get("run_project", payload["project"])
    invocation = " ".join(payload["invocation"])
    if os.name == "nt" and payload["backend"] == "openapp" and project.get("project_type") == "app":
        invocation = f"bash -lc openapp ./{project.get('target_name')}.app"
    return "\n".join(
        [
            f"run: {payload['summary']}",
            f"run: backend={payload['backend']}",
            f"run: project_type={project.get('project_type')} target={project.get('target_name')}",
            f"run: selected_project={project.get('project_dir')}",
            f"run: invocation={invocation}",
        ]
    )
