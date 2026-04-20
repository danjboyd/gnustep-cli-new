from __future__ import annotations

import ctypes.util
import json
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .compatibility import (
    classify_environment,
    evaluate_environment_against_artifact,
    normalize_arch,
    normalize_os,
    select_artifact_for_environment,
)
from .models import Action, CheckResult


CLI_VERSION = "0.1.0-dev"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "examples" / "release-manifest-v1.json"
DOCTOR_INTERFACES = {"bootstrap", "full"}
NATIVE_TOOLCHAIN_ASSESSMENTS = {
    "unavailable",
    "broken",
    "preferred",
    "supported",
    "interoperability_only",
    "incompatible",
}


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


def _distribution_id(os_version: str | None) -> str | None:
    if not os_version:
        return None
    return os_version.split("-", 1)[0]


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


def _compile_probe(
    compiler_path: str | None,
    source_text: str,
    *,
    extra_flags: list[str] | None = None,
) -> bool:
    if not compiler_path:
        return False
    with tempfile.TemporaryDirectory(prefix="gnustep-cli-feature-") as tempdir:
        temp = Path(tempdir)
        source = temp / "probe.m"
        output = temp / "probe.o"
        source.write_text(source_text)
        args = [compiler_path, "-x", "objective-c", "-c", str(source), "-o", str(output)]
        if extra_flags:
            args[1:1] = extra_flags
        proc = _run_command(args)
        return proc.returncode == 0 and output.exists()


def _library_has_symbol(library_path: str | None, symbol: str) -> bool:
    if not library_path:
        return False
    nm = _find_first(["nm"])
    if not nm:
        return False
    proc = _run_command([nm, "-D", library_path]) if Path(library_path).exists() else subprocess.CompletedProcess([], 1, "", "")
    if proc.returncode != 0:
        proc = _run_command([nm, "-g", library_path]) if Path(library_path).exists() else subprocess.CompletedProcess([], 1, "", "")
    return proc.returncode == 0 and symbol in proc.stdout


def _find_objc_runtime_library(compiler_family: str | None) -> str | None:
    candidates = []
    found = ctypes.util.find_library("objc")
    if found:
        candidates.append(found)
    for name in ("libobjc.so", "libobjc.so.4", "libobjc.dylib", "objc.dll"):
        path = shutil.which(name)
        if path:
            candidates.append(path)
        for prefix in ("/usr/lib", "/usr/local/lib", "/lib", "/opt/local/lib"):
            candidate = Path(prefix) / name
            if candidate.exists():
                candidates.append(str(candidate))
    if compiler_family == "gcc":
        return candidates[0] if candidates else None
    return candidates[0] if candidates else None


def _detect_objc_runtime_and_abi(compiler_family: str | None, present: bool, *, interface: str) -> tuple[str, str]:
    if not present:
        return "unknown", "unknown"
    if interface == "bootstrap":
        if compiler_family == "clang":
            return "libobjc2", "modern"
        if compiler_family == "gcc":
            return "gcc_libobjc", "legacy"
        return "unknown", "unknown"

    library_path = _find_objc_runtime_library(compiler_family)
    if _library_has_symbol(library_path, "objc_setAssociatedObject"):
        return "libobjc2", "modern"
    if compiler_family == "gcc":
        return "gcc_libobjc", "legacy"
    if compiler_family == "clang":
        return "unknown", "unknown"
    return "unknown", "unknown"


def _detect_feature_flags(
    compiler_path: str | None, compiler_family: str | None, *, interface: str
) -> dict[str, bool]:
    feature_flags = {
        "objc2_syntax": False,
        "blocks": False,
        "arc": False,
        "nonfragile_abi": False,
        "associated_objects": False,
        "exceptions": True,
    }
    if interface == "bootstrap":
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
        return feature_flags

    feature_flags["objc2_syntax"] = _compile_probe(
        compiler_path,
        "@interface Probe @property (assign) int value; @end\n@implementation Probe @end\n",
    )
    feature_flags["blocks"] = _compile_probe(
        compiler_path,
        "int main(void) { int (^block)(void) = ^{ return 0; }; return block(); }\n",
        extra_flags=["-fblocks"],
    )
    feature_flags["arc"] = _compile_probe(
        compiler_path,
        "@interface Probe @end\n@implementation Probe @end\n",
        extra_flags=["-fobjc-arc"],
    )
    feature_flags["nonfragile_abi"] = _compile_probe(
        compiler_path,
        "@interface Probe { int value; } @end\n@implementation Probe @end\n",
        extra_flags=["-fobjc-nonfragile-abi"],
    )
    feature_flags["associated_objects"] = _library_has_symbol(_find_objc_runtime_library(compiler_family), "objc_setAssociatedObject")
    return feature_flags


def _detect_gnustep_components(gnustep_config: str | None, *, interface: str) -> tuple[bool, bool]:
    if not gnustep_config:
        return False, False
    if interface == "bootstrap":
        return False, False
    base_proc = _run_command([gnustep_config, "--base-libs"])
    gui_proc = _run_command([gnustep_config, "--gui-libs"])
    base_present = base_proc.returncode == 0 and "-lgnustep-base" in base_proc.stdout
    gui_present = gui_proc.returncode == 0 and "-lgnustep-gui" in gui_proc.stdout
    return base_present, gui_present


def _detect_toolchain(environment: dict[str, Any], *, interface: str) -> dict[str, Any]:
    gnustep_config = _find_first(["gnustep-config"])
    gnustep_makefiles = os.environ.get("GNUSTEP_MAKEFILES")
    compiler_family, compiler_version, compiler_path = _compiler_info()
    can_compile, can_link, can_run = _probe_compile_link_run(compiler_path)

    present = bool(gnustep_config or gnustep_makefiles)
    objc_runtime, objc_abi = _detect_objc_runtime_and_abi(compiler_family, present, interface=interface)
    feature_flags = _detect_feature_flags(compiler_path, compiler_family, interface=interface)
    gnustep_base, gnustep_gui = _detect_gnustep_components(gnustep_config, interface=interface)

    return {
        "present": present,
        "compiler_family": compiler_family,
        "compiler_version": compiler_version,
        "toolchain_flavor": compiler_family,
        "objc_runtime": objc_runtime,
        "objc_abi": objc_abi,
        "gnustep_make": bool(gnustep_config or gnustep_makefiles),
        "gnustep_base": gnustep_base,
        "gnustep_gui": gnustep_gui,
        "can_compile": can_compile,
        "can_link": can_link,
        "can_run": can_run,
        "feature_flags": feature_flags,
        "compiler_path": compiler_path,
        "gnustep_config_path": gnustep_config,
        "gnustep_makefiles": gnustep_makefiles,
        "detected_layouts": _detect_layouts(gnustep_makefiles, gnustep_config),
        "detection_depth": "installer" if interface == "bootstrap" else "full",
    }


def _select_artifact(
    environment: dict[str, Any], manifest_path: Path | None = None, *, kind: str | None = None
) -> dict[str, Any] | None:
    manifest_file = manifest_path or DEFAULT_MANIFEST
    payload = json.loads(manifest_file.read_text())
    for release in payload.get("releases", []):
        artifacts = release.get("artifacts", [])
        if kind is None:
            for artifact_kind in ("cli", "toolchain"):
                artifact, _ = select_artifact_for_environment(environment, artifacts, kind=artifact_kind)
                if artifact is not None:
                    return artifact
        else:
            artifact, _ = select_artifact_for_environment(environment, artifacts, kind=kind)
            if artifact is not None:
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


def _managed_install_integrity_check(environment: dict[str, Any], *, interface: str, managed_root: Path | None = None) -> CheckResult:
    toolchain = environment["toolchain"]
    if interface == "bootstrap":
        return _full_only_check("managed.install.integrity", "Inspect managed install integrity", "warning")
    root = managed_root or (Path(os.environ.get("GNUSTEP_CLI_MANAGED_ROOT")) if os.environ.get("GNUSTEP_CLI_MANAGED_ROOT") else ROOT)
    state_path = root / "state" / "cli-state.json"
    staging_path = root / ".staging"
    transactions_path = root / ".transactions"
    setup_transaction_path = root / "state" / "setup-transaction.json"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
        except Exception as exc:
            return CheckResult(
                id="managed.install.integrity",
                title="Inspect managed install integrity",
                status="error",
                severity="warning",
                message=f"Managed install state is unreadable: {exc}",
                interface="full",
                execution_tier="full_only",
                details={"state_path": str(state_path)},
            )
        stale_paths = [str(path) for path in (staging_path, transactions_path, setup_transaction_path) if path.exists()]
        if state.get("status") in {"installing", "upgrading", "repairing", "needs_repair"} or stale_paths:
            return CheckResult(
                id="managed.install.integrity",
                title="Inspect managed install integrity",
                status="warning",
                severity="warning",
                message="Managed install state requires repair validation.",
                interface="full",
                execution_tier="full_only",
                details={"state_path": str(state_path), "state_status": state.get("status"), "stale_paths": stale_paths},
            )
        return CheckResult(
            id="managed.install.integrity",
            title="Inspect managed install integrity",
            status="ok",
            severity="warning",
            message=f"Managed install state was found at {state_path}.",
            interface="full",
            execution_tier="full_only",
            details={"state_path": str(state_path), "state_status": state.get("status")},
        )
    if toolchain["present"]:
        return CheckResult(
            id="managed.install.integrity",
            title="Inspect managed install integrity",
            status="not_run",
            severity="warning",
            message="No managed install state was detected on this host.",
            interface="full",
            execution_tier="full_only",
            details={"managed_install_detected": False},
        )
    return CheckResult(
        id="managed.install.integrity",
        title="Inspect managed install integrity",
        status="not_run",
        severity="warning",
        message="Managed install integrity checks were skipped because no GNUstep toolchain is present.",
        interface="full",
        execution_tier="full_only",
        details={"managed_install_detected": False},
    )


def _assess_native_toolchain(environment: dict[str, Any], compatibility: dict[str, Any]) -> dict[str, Any]:
    toolchain = environment["toolchain"]
    distribution_id = environment.get("distribution_id")

    if not toolchain["present"]:
        return {
            "assessment": "unavailable",
            "preference": "managed",
            "message": "No native GNUstep toolchain was detected.",
            "reasons": [{"code": "native_toolchain_missing", "message": "No GNUstep toolchain was detected on the host."}],
        }
    if not toolchain["can_compile"] or not toolchain["can_link"] or not toolchain["can_run"]:
        return {
            "assessment": "broken",
            "preference": "managed",
            "message": "A native GNUstep toolchain was detected, but it does not pass functional validation.",
            "reasons": [{"code": "native_toolchain_broken", "message": "The detected toolchain cannot compile, link, and run correctly."}],
        }

    compiler = toolchain.get("compiler_family")
    runtime = toolchain.get("objc_runtime")
    abi = toolchain.get("objc_abi")
    modern_clang = compiler == "clang" and runtime == "libobjc2" and abi == "modern"

    if environment["os"] == "openbsd" and modern_clang:
        return {
            "assessment": "preferred",
            "preference": "native",
            "message": "The packaged OpenBSD GNUstep environment is a preferred native toolchain candidate.",
            "reasons": [{"code": "openbsd_packaged_candidate", "message": "OpenBSD packaged GNUstep should be preferred when it satisfies the CLI requirements."}],
        }
    if distribution_id == "fedora" and modern_clang:
        return {
            "assessment": "supported",
            "preference": "native",
            "message": "The detected Fedora GNUstep environment is a supported native toolchain candidate.",
            "reasons": [{"code": "fedora_packaged_candidate", "message": "Fedora appears to provide a compatible native GNUstep stack."}],
        }
    if distribution_id == "arch" and modern_clang:
        return {
            "assessment": "supported",
            "preference": "native",
            "message": "The detected Arch GNUstep environment is a supported native toolchain candidate.",
            "reasons": [{"code": "arch_packaged_candidate", "message": "Arch appears to provide a compatible native GNUstep stack."}],
        }
    if distribution_id in {"debian", "arch"} and compiler == "gcc":
        return {
            "assessment": "interoperability_only",
            "preference": "managed",
            "message": "The detected packaged GNUstep environment is suitable for interoperability validation, but it is not the preferred runtime model.",
            "reasons": [{"code": "gcc_interop_only", "message": f"{distribution_id} currently looks like a GCC-oriented packaged GNUstep environment."}],
        }
    if modern_clang and compatibility["compatible"]:
        return {
            "assessment": "supported",
            "preference": "native",
            "message": "The detected native GNUstep environment satisfies the managed runtime expectations.",
            "reasons": [{"code": "native_toolchain_supported", "message": "The detected native toolchain matches the required runtime and capability model."}],
        }
    return {
        "assessment": "incompatible",
        "preference": "managed",
        "message": "A native GNUstep toolchain was detected, but it does not match the preferred runtime model for this workflow.",
        "reasons": [{"code": "native_toolchain_incompatible", "message": "Use the managed toolchain unless a workflow explicitly supports this native environment."}],
    }


def _native_toolchain_check(native_toolchain: dict[str, Any], *, interface: str) -> CheckResult:
    assessment = native_toolchain["assessment"]
    status_map = {
        "preferred": "ok",
        "supported": "ok",
        "interoperability_only": "warning",
        "unavailable": "warning",
        "broken": "error",
        "incompatible": "error",
    }
    return CheckResult(
        id="native-toolchain.assess",
        title="Assess native packaged toolchain path",
        status=status_map[assessment],
        severity="warning" if assessment in {"preferred", "supported", "interoperability_only", "unavailable"} else "error",
        message=native_toolchain["message"],
        interface="bootstrap" if interface == "bootstrap" else "both",
        execution_tier="bootstrap_optional",
        details={"assessment": assessment, "preference": native_toolchain["preference"], "reasons": native_toolchain["reasons"]},
    )


def build_doctor_payload(manifest_path: Path | None = None, *, interface: str = "full", managed_root: Path | None = None) -> dict[str, Any]:
    if interface not in DOCTOR_INTERFACES:
        raise ValueError(f"unsupported doctor interface: {interface}")

    environment: dict[str, Any] = {
        "os": _detect_os(),
        "os_version": _read_os_release(),
        "distribution_id": None,
        "arch": _detect_arch(),
        "shell_family": "posix" if os.name == "posix" else "windows",
        "install_scope": "user",
        "toolchain": {},
        "bootstrap_prerequisites": {
            "curl": shutil.which("curl") is not None,
            "wget": shutil.which("wget") is not None,
        },
    }
    environment["distribution_id"] = _distribution_id(environment["os_version"])
    environment["toolchain"] = _detect_toolchain(environment, interface=interface)
    environment["detected_layouts"] = environment["toolchain"].get("detected_layouts", [])
    environment["install_prefixes"] = []
    if environment["toolchain"].get("gnustep_makefiles"):
        environment["install_prefixes"].append(environment["toolchain"]["gnustep_makefiles"])

    artifact = _select_artifact(environment, manifest_path, kind="toolchain")
    compatibility = evaluate_environment_against_artifact(environment, artifact)
    native_toolchain = _assess_native_toolchain(environment, compatibility)
    environment["native_toolchain"] = native_toolchain
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
            details={"distribution_id": environment["distribution_id"], "os_version": environment["os_version"]},
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
        _native_toolchain_check(native_toolchain, interface=interface),
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
    checks.append(_managed_install_integrity_check(environment, interface=interface, managed_root=managed_root))
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
    if native_toolchain["assessment"] == "preferred":
        actions.append(Action(kind="use_existing_toolchain", priority=1, message="Use the packaged native GNUstep toolchain; it is the preferred path on this host."))
    elif native_toolchain["assessment"] == "supported":
        actions.append(Action(kind="use_existing_toolchain", priority=1, message="Use the detected native GNUstep toolchain or choose a managed install explicitly."))
    elif native_toolchain["assessment"] == "interoperability_only":
        actions.append(Action(kind="use_existing_toolchain", priority=2, message="The detected native GNUstep toolchain is suitable for interoperability validation, but the managed toolchain remains the preferred path."))
        actions.append(Action(kind="install_managed_toolchain", priority=1, message="Install the supported managed GNUstep toolchain for the preferred runtime model."))
    elif classification == "no_toolchain":
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
        "native_toolchain_assessment": native_toolchain["assessment"],
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
