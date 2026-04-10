from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .compatibility import classify_environment, evaluate_environment_against_artifact, normalize_arch, normalize_os
from .models import Action, CheckResult


CLI_VERSION = "0.1.0-dev"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "examples" / "release-manifest-v1.json"
DOCTOR_INTERFACES = {"bootstrap", "full"}


def _run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)


def _detect_os() -> str:
    return normalize_os(platform.system())


def _detect_arch() -> str:
    return normalize_arch(platform.machine())


def _read_os_release() -> str | None:
    path = Path("/etc/os-release")
    if not path.exists():
        return None
    data: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        data[key] = value.strip().strip('"')
    if "VERSION_CODENAME" in data:
        return f"{data.get('ID', 'linux')}-{data['VERSION_CODENAME']}"
    if "VERSION_ID" in data:
        return f"{data.get('ID', 'linux')}-{data['VERSION_ID']}"
    return data.get("ID")


def _find_first(names: list[str]) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def _detect_layouts(gnustep_makefiles: str | None, gnustep_config: str | None) -> list[str]:
    layouts: list[str] = []
    if gnustep_makefiles:
        text = gnustep_makefiles.lower()
        if "/usr/gnustep/" in text:
            layouts.append("gnustep")
        if "/usr/local/" in text:
            layouts.append("fhs")
        if "/usr/share/gnustep" in text or "/usr/lib/gnustep" in text:
            layouts.append("debian")
    if gnustep_config and not layouts:
        if "/usr/bin/" in gnustep_config:
            layouts.append("debian")
    return sorted(set(layouts))


def _compiler_info() -> tuple[str | None, str | None, str | None]:
    clang = _find_first(["clang"])
    gcc = _find_first(["gcc"])
    cc = _find_first(["cc"])
    selected = clang or gcc or cc
    if not selected:
        return None, None, None
    proc = _run_command([selected, "--version"])
    first_line = (proc.stdout or proc.stderr).splitlines()[0] if (proc.stdout or proc.stderr) else ""
    compiler_family = "clang" if "clang" in first_line.lower() or "clang" in Path(selected).name else "gcc"
    version = None
    for token in first_line.replace("(", " ").replace(")", " ").split():
        if token[:1].isdigit():
            version = token
            break
    return compiler_family, version, selected


def _probe_compile_link_run(compiler_path: str | None) -> tuple[bool, bool, bool]:
    if not compiler_path:
        return False, False, False
    with tempfile.TemporaryDirectory(prefix="gnustep-cli-doctor-") as tempdir:
        temp = Path(tempdir)
        source = temp / "probe.m"
        source.write_text("int main(void) { return 0; }\n")
        obj = temp / "probe.o"
        exe = temp / "probe"
        compile_proc = _run_command([compiler_path, "-x", "objective-c", "-c", str(source), "-o", str(obj)])
        can_compile = compile_proc.returncode == 0 and obj.exists()
        if not can_compile:
            return False, False, False
        link_proc = _run_command([compiler_path, str(obj), "-o", str(exe)])
        can_link = link_proc.returncode == 0 and exe.exists()
        if not can_link:
            return True, False, False
        run_proc = _run_command([str(exe)])
        return True, True, run_proc.returncode == 0


def _detect_toolchain(environment: dict[str, Any]) -> dict[str, Any]:
    gnustep_config = _find_first(["gnustep-config"])
    gnustep_makefiles = os.environ.get("GNUSTEP_MAKEFILES")
    compiler_family, compiler_version, compiler_path = _compiler_info()
    can_compile, can_link, can_run = _probe_compile_link_run(compiler_path)

    present = bool(gnustep_config or gnustep_makefiles)
    objc_runtime = "unknown"
    objc_abi = "unknown"
    feature_flags = {
        "objc2_syntax": False,
        "blocks": False,
        "arc": False,
        "nonfragile_abi": False,
        "associated_objects": False,
        "exceptions": True,
    }

    if compiler_family == "clang":
        feature_flags.update(
            {
                "objc2_syntax": True,
                "blocks": True,
                "arc": True,
                "nonfragile_abi": True,
                "associated_objects": True,
            }
        )
        objc_runtime = "libobjc2" if present else "unknown"
        objc_abi = "modern" if present else "unknown"
    elif compiler_family == "gcc":
        objc_runtime = "gcc_libobjc" if present else "unknown"
        objc_abi = "legacy" if present else "unknown"

    return {
        "present": present,
        "compiler_family": compiler_family,
        "compiler_version": compiler_version,
        "toolchain_flavor": compiler_family,
        "objc_runtime": objc_runtime,
        "objc_abi": objc_abi,
        "gnustep_make": bool(gnustep_config or gnustep_makefiles),
        "gnustep_base": False,
        "gnustep_gui": False,
        "can_compile": can_compile,
        "can_link": can_link,
        "can_run": can_run,
        "feature_flags": feature_flags,
        "compiler_path": compiler_path,
        "gnustep_config_path": gnustep_config,
        "gnustep_makefiles": gnustep_makefiles,
        "detected_layouts": _detect_layouts(gnustep_makefiles, gnustep_config),
    }


def _select_artifact(
    environment: dict[str, Any], manifest_path: Path | None = None, *, kind: str | None = None
) -> dict[str, Any] | None:
    manifest_file = manifest_path or DEFAULT_MANIFEST
    payload = json.loads(manifest_file.read_text())
    for release in payload.get("releases", []):
        for artifact in release.get("artifacts", []):
            if (
                artifact.get("os") == environment["os"]
                and artifact.get("arch") == environment["arch"]
                and (kind is None or artifact.get("kind") == kind)
            ):
                return artifact
    return None


def _full_only_check(check_id: str, title: str, severity: str) -> CheckResult:
    return CheckResult(
        id=check_id,
        title=title,
        status="not_run",
        severity=severity,
        message="This check is available in the full CLI only.",
        interface="full",
        execution_tier="full_only",
        details={"unavailable_in_bootstrap": True},
    )


def build_doctor_payload(manifest_path: Path | None = None, *, interface: str = "full") -> dict[str, Any]:
    if interface not in DOCTOR_INTERFACES:
        raise ValueError(f"unsupported doctor interface: {interface}")

    environment: dict[str, Any] = {
        "os": _detect_os(),
        "os_version": _read_os_release(),
        "arch": _detect_arch(),
        "shell_family": "posix" if os.name == "posix" else "windows",
        "install_scope": "user",
        "toolchain": {},
        "bootstrap_prerequisites": {
            "curl": shutil.which("curl") is not None,
            "wget": shutil.which("wget") is not None,
        },
    }
    environment["toolchain"] = _detect_toolchain(environment)
    environment["detected_layouts"] = environment["toolchain"].get("detected_layouts", [])
    environment["install_prefixes"] = []
    if environment["toolchain"].get("gnustep_makefiles"):
        environment["install_prefixes"].append(environment["toolchain"]["gnustep_makefiles"])

    artifact = _select_artifact(environment, manifest_path, kind="toolchain")
    compatibility = evaluate_environment_against_artifact(environment, artifact)
    environment["compatibility"] = compatibility
    classification = classify_environment(environment)
    status = "ok"
    if classification in {"toolchain_incompatible", "toolchain_broken"}:
        status = "error"
    elif classification == "no_toolchain":
        status = "warning"

    checks = [
        CheckResult(
            id="host.identity",
            title="Determine host identity",
            status="ok",
            severity="info",
            message=f"Detected {environment['os']} on {environment['arch']}.",
            interface="bootstrap" if interface == "bootstrap" else "both",
            execution_tier="bootstrap_required",
        ),
        CheckResult(
            id="bootstrap.downloader",
            title="Check for downloader",
            status="ok" if environment["bootstrap_prerequisites"]["curl"] or environment["bootstrap_prerequisites"]["wget"] else "error",
            severity="error",
            message=(
                "Found curl or wget."
                if environment["bootstrap_prerequisites"]["curl"] or environment["bootstrap_prerequisites"]["wget"]
                else "Neither curl nor wget is available."
            ),
            interface="bootstrap" if interface == "bootstrap" else "both",
            execution_tier="bootstrap_required",
        ),
        CheckResult(
            id="toolchain.detect",
            title="Detect GNUstep toolchain",
            status="ok" if environment["toolchain"]["present"] else "warning",
            severity="error",
            message=(
                f"Detected a {environment['toolchain']['compiler_family'] or 'unknown'}-based GNUstep toolchain."
                if environment["toolchain"]["present"]
                else "No GNUstep toolchain detected."
            ),
            interface="bootstrap" if interface == "bootstrap" else "both",
            execution_tier="bootstrap_optional",
        ),
    ]
    if interface == "full":
        checks.append(
            CheckResult(
                id="toolchain.probe",
                title="Compile/link/run probe",
                status="ok" if environment["toolchain"]["can_compile"] and environment["toolchain"]["can_link"] and environment["toolchain"]["can_run"] else "warning",
                severity="error",
                message=(
                    "The compiler can compile, link, and run a minimal Objective-C probe."
                    if environment["toolchain"]["can_compile"] and environment["toolchain"]["can_link"] and environment["toolchain"]["can_run"]
                    else "A compiler probe did not fully succeed."
                ),
                interface="full",
                execution_tier="full_only",
            )
        )
    else:
        checks.append(_full_only_check("toolchain.probe", "Compile/link/run probe", "error"))
    if artifact is not None:
        checks.append(
            CheckResult(
                id="toolchain.compatibility",
                title="Evaluate managed artifact compatibility",
                status="ok" if compatibility["compatible"] else "error",
                severity="error",
                message=(
                    f"The environment is compatible with artifact {artifact['id']}."
                    if compatibility["compatible"]
                    else f"The environment is not compatible with artifact {artifact['id']}."
                ),
                interface="bootstrap" if interface == "bootstrap" else "both",
                execution_tier="bootstrap_optional",
            )
        )
    else:
        checks.append(
            CheckResult(
                id="toolchain.compatibility",
                title="Evaluate managed artifact compatibility",
                status="warning",
                severity="error",
                message="No matching managed artifact was found for this host.",
                interface="bootstrap" if interface == "bootstrap" else "both",
                execution_tier="bootstrap_optional",
            )
        )

    actions: list[Action] = []
    if not environment["bootstrap_prerequisites"]["curl"] and not environment["bootstrap_prerequisites"]["wget"]:
        actions.append(Action(kind="install_downloader", priority=1, message="Install curl or wget, then rerun setup."))
    if classification == "no_toolchain":
        actions.append(Action(kind="install_managed_toolchain", priority=1, message="Install the supported managed GNUstep toolchain."))
    elif classification == "toolchain_incompatible":
        actions.append(Action(kind="install_managed_toolchain", priority=1, message="Install the supported Clang-based managed toolchain."))
    elif classification == "toolchain_broken":
        actions.append(Action(kind="repair_or_replace_toolchain", priority=1, message="Repair the detected toolchain or install a managed one."))
    else:
        actions.append(Action(kind="use_existing_toolchain", priority=1, message="You can continue with the detected toolchain or install a managed one explicitly."))

    summary_map = {
        "no_toolchain": "No preexisting GNUstep toolchain was detected.",
        "toolchain_compatible": "A compatible GNUstep toolchain was detected.",
        "toolchain_incompatible": "A GNUstep toolchain was detected, but it is incompatible with the selected managed artifacts.",
        "toolchain_broken": "A GNUstep toolchain was detected, but it does not appear to be working correctly.",
    }

    return {
        "schema_version": 1,
        "command": "doctor",
        "cli_version": CLI_VERSION,
        "interface": interface,
        "diagnostic_depth": "installer" if interface == "bootstrap" else "full",
        "ok": status != "error",
        "status": status,
        "environment_classification": classification,
        "summary": summary_map[classification],
        "environment": {
            k: v
            for k, v in environment.items()
            if k != "compatibility"
        },
        "compatibility": compatibility,
        "checks": [check.to_dict() for check in checks],
        "actions": [action.to_dict() for action in actions],
    }


def render_human(payload: dict[str, Any]) -> str:
    lines = [
        f"doctor: {payload['summary']}",
        f"doctor: status={payload['status']} classification={payload['environment_classification']}",
        f"doctor: interface={payload.get('interface', 'full')} depth={payload.get('diagnostic_depth', 'full')}",
    ]
    environment = payload["environment"]
    lines.append(f"doctor: host={environment['os']}/{environment['arch']}")
    toolchain = environment["toolchain"]
    if toolchain["present"]:
        lines.append(
            "doctor: toolchain="
            f"{toolchain['compiler_family'] or 'unknown'} "
            f"runtime={toolchain['objc_runtime']} abi={toolchain['objc_abi']}"
        )
    else:
        lines.append("doctor: toolchain=not detected")
    for action in payload["actions"]:
        lines.append(f"next: {action['message']}")
    return "\n".join(lines)
