from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


def _parse_gnumakefile(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    content = path.read_text()
    if "aggregate.make" in content:
        values["__contains_aggregate_make"] = "true"
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
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


def plan_build(project_dir: str | Path = ".") -> dict[str, Any]:
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


def execute_build(project_dir: str | Path = ".") -> tuple[dict[str, Any], int]:
    payload = plan_build(project_dir)
    if not payload["ok"]:
        return payload, 3
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
    if project["project_type"] == "tool":
        invocation = [_tool_run_path(project)]
        backend = "direct-exec"
    elif project["project_type"] == "app":
        invocation = ["openapp", f"{project['target_name']}.app"]
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


def execute_run(project_dir: str | Path = ".") -> tuple[dict[str, Any], int]:
    payload = plan_run(project_dir)
    if not payload["ok"]:
        return payload, 3
    try:
        proc = subprocess.run(
            payload["invocation"],
            cwd=payload["project"]["project_dir"],
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
    project = payload["project"]
    return "\n".join(
        [
            f"run: {payload['summary']}",
            f"run: backend={payload['backend']}",
            f"run: project_type={project.get('project_type')} target={project.get('target_name')}",
            f"run: invocation={' '.join(payload['invocation'])}",
        ]
    )
