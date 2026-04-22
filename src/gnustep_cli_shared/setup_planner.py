from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from .doctor_engine import CLI_VERSION, DEFAULT_MANIFEST, build_doctor_payload
from .lifecycle import save_cli_state
from .compatibility import select_artifact_for_environment

MANAGED_PREFIX_PLACEHOLDER = "__GNUSTEP_CLI_INSTALL_ROOT__"


def _relocate_managed_toolchain(root: Path) -> None:
    replacement = str(root)
    placeholder_bytes = MANAGED_PREFIX_PLACEHOLDER.encode("utf-8")
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        data = path.read_bytes()
        if placeholder_bytes not in data or b"\0" in data:
            continue
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        path.write_text(content.replace(MANAGED_PREFIX_PLACEHOLDER, replacement), encoding="utf-8")


def _default_user_root(os_name: str) -> str:
    if os_name == "windows":
        return r"%LOCALAPPDATA%\gnustep-cli"
    return "~/.local/share/gnustep-cli"


def _default_system_root(os_name: str) -> str:
    if os_name == "windows":
        return r"%ProgramFiles%\gnustep-cli"
    return "/opt/gnustep-cli"


def _has_system_privileges(os_name: str) -> bool:
    if os_name == "windows":
        return False
    geteuid = getattr(os, "geteuid", None)
    return bool(geteuid and geteuid() == 0)


def _artifact_matches_host(artifact: dict[str, Any], doctor: dict[str, Any]) -> bool:
    environment = doctor["environment"]
    return artifact.get("os") == environment["os"] and artifact.get("arch") == environment["arch"]


def _validate_manifest_payload(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema_version") != 1:
        errors.append("Unsupported release manifest schema version.")
    releases = manifest.get("releases")
    if not isinstance(releases, list) or not releases:
        errors.append("Release manifest does not define any releases.")
        return errors
    for release in releases:
        if "version" not in release:
            errors.append("A release entry is missing its version.")
        artifacts = release.get("artifacts")
        if not isinstance(artifacts, list):
            errors.append(f"Release {release.get('version', 'unknown')} does not define an artifacts list.")
            continue
        for artifact in artifacts:
            for field in ("id", "kind", "os", "arch", "url", "sha256"):
                if field not in artifact:
                    errors.append(f"Artifact {artifact.get('id', 'unknown')} is missing required field '{field}'.")
            if artifact.get("reused"):
                for field in ("version", "size"):
                    if field not in artifact:
                        errors.append(f"Reused artifact {artifact.get('id', 'unknown')} is missing required field '{field}'.")
                if artifact.get("sha256") == "TBD":
                    errors.append(f"Reused artifact {artifact.get('id', 'unknown')} must have a concrete sha256.")
            if artifact.get("kind") == "delta":
                for field in ("from_artifact", "to_artifact", "from_sha256", "to_sha256"):
                    if field not in artifact:
                        errors.append(f"Delta artifact {artifact.get('id', 'unknown')} is missing required field '{field}'.")
    return errors


def _select_release(manifest_file: Path, doctor: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[str], list[str]]:
    manifest = json.loads(manifest_file.read_text())
    errors = _validate_manifest_payload(manifest)
    if errors:
        return None, [], errors, []
    releases = manifest["releases"]
    active_release = next((release for release in releases if release.get("status") == "active"), releases[0])
    artifacts = active_release.get("artifacts", [])
    ordered: list[dict[str, Any]] = []
    selection_errors: list[str] = []
    for kind in ("cli", "toolchain"):
        artifact, selection_error = select_artifact_for_environment(doctor["environment"], artifacts, kind=kind)
        if artifact is not None:
            ordered.append(artifact)
        elif selection_error is not None:
            selection_errors.append(selection_error)
    return active_release, ordered, errors, selection_errors


def _path_export_hint(root: Path, os_name: str) -> str:
    if os_name == "windows":
        return f'. "{root / "GNUstep.ps1"}"'
    return f'export PATH="{root}/bin:{root}/Tools:{root}/System/Tools:$PATH"'


def _write_windows_activation_scripts(root: Path) -> None:
    tmp = root / "tmp"
    etc = root / "etc"
    tmp.mkdir(parents=True, exist_ok=True)
    etc.mkdir(parents=True, exist_ok=True)
    (etc / "fstab").write_text(f"{str(tmp).replace(chr(92), '/')} /tmp ntfs binary,noacl,posix=0,user 0 0\n", encoding="ascii")
    (root / "GNUstep.ps1").write_text(
        "\n".join(
            [
                "$prefix = Split-Path -Parent $MyInvocation.MyCommand.Path",
                "$env:GNUSTEP_MAKEFILES = Join-Path $prefix 'clang64\\share\\GNUstep\\Makefiles'",
                "$env:GNUSTEP_CONFIG_FILE = Join-Path $prefix 'clang64\\etc\\GNUstep\\GNUstep.conf'",
                "$env:TMPDIR = Join-Path $prefix 'tmp'",
                "$env:TEMP = $env:TMPDIR",
                "$env:TMP = $env:TMPDIR",
                "$env:PATH = (Join-Path $prefix 'clang64\\bin') + ';' + (Join-Path $prefix 'bin') + ';' + (Join-Path $prefix 'usr\\bin') + ';' + $env:PATH",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "GNUstep.bat").write_text(
        "\n".join(
            [
                "@echo off",
                'set "GNUSTEP_MAKEFILES=%~dp0clang64\\share\\GNUstep\\Makefiles"',
                'set "GNUSTEP_CONFIG_FILE=%~dp0clang64\\etc\\GNUstep\\GNUstep.conf"',
                'set "TMPDIR=%~dp0tmp"',
                'set "TEMP=%~dp0tmp"',
                'set "TMP=%~dp0tmp"',
                'set "PATH=%~dp0clang64\\bin;%~dp0bin;%~dp0usr\\bin;%PATH%"',
            ]
        )
        + "\n",
        encoding="ascii",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_writable_install_root(install_root: Path) -> bool:
    candidate = install_root if install_root.exists() else install_root.parent
    while not candidate.exists() and candidate.parent != candidate:
        candidate = candidate.parent
    return os.access(candidate, os.W_OK)


def _resolve_artifact_source(manifest_file: Path, artifact: dict[str, Any], download_dir: Path) -> Path:
    filename = artifact.get("filename")
    if filename:
        local_candidate = manifest_file.parent / filename
        if local_candidate.exists():
            return local_candidate
    url = artifact["url"]
    destination = download_dir / (filename or Path(url).name)
    urllib.request.urlretrieve(url, destination)
    return destination


def _extract_archive(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if archive_path.suffix == ".zip":
        with ZipFile(archive_path) as archive:
            archive.extractall(destination)
        return
    with tarfile.open(archive_path, "r:gz") as archive:
        archive.extractall(destination, filter="data")


def _flatten_single_root(directory: Path) -> Path:
    children = [child for child in directory.iterdir()]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return directory


def _copy_tree_contents(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        target = destination / child.name
        if child.is_dir():
            shutil.copytree(child, target, dirs_exist_ok=True)
        else:
            shutil.copy2(child, target)


def _install_cli_artifact(extracted_root: Path, install_root: Path) -> list[str]:
    source_root = _flatten_single_root(extracted_root)
    _copy_tree_contents(source_root, install_root)
    candidates = list((install_root / "bin").glob("gnustep*"))
    if not candidates:
        raise FileNotFoundError("gnustep binary not found in CLI artifact")
    for candidate in candidates:
        if candidate.is_file():
            os.chmod(candidate, 0o755)
    return [str(candidate) for candidate in candidates]


def _install_toolchain_artifact(extracted_root: Path, install_root: Path) -> list[str]:
    source_root = _flatten_single_root(extracted_root)
    _copy_tree_contents(source_root, install_root)
    return [str(install_root)]


def execute_setup(
    *,
    scope: str = "user",
    manifest_path: str | None = None,
    install_root: str | None = None,
) -> tuple[dict[str, Any], int]:
    payload, exit_code = build_setup_payload(scope=scope, manifest_path=manifest_path, install_root=install_root)
    if not payload["ok"]:
        return payload, exit_code
    if payload["plan"].get("install_mode") == "native":
        return payload, 0

    manifest_file = Path(manifest_path) if manifest_path else DEFAULT_MANIFEST
    install_path = Path(payload["plan"]["install_root"]).expanduser().resolve()
    doctor = build_doctor_payload(manifest_file, interface="bootstrap")
    _, selected_artifacts, validation_errors, selection_errors = _select_release(manifest_file, doctor)
    if validation_errors:
        payload["ok"] = False
        payload["status"] = "error"
        payload["summary"] = "Release manifest validation failed."
        payload["actions"] = [{"kind": "report_bug", "priority": 1, "message": validation_errors[0]}]
        payload["plan"]["manifest_validation_errors"] = validation_errors
        return payload, 2
    if selection_errors:
        payload["ok"] = False
        payload["status"] = "error"
        payload["summary"] = "Managed artifact selection failed."
        payload["actions"] = [{"kind": "report_bug", "priority": 1, "message": selection_errors[0]}]
        payload["plan"]["selection_errors"] = selection_errors
        return payload, 4
    if len(selected_artifacts) < 2:
        payload["ok"] = False
        payload["status"] = "error"
        payload["summary"] = "No complete managed artifact set was found for this host."
        payload["actions"] = [
            {
                "kind": "report_bug",
                "priority": 1,
                "message": "No compatible CLI/toolchain artifact pair is available for this host yet.",
            }
        ]
        return payload, 4
    install_path.mkdir(parents=True, exist_ok=True)
    staged = install_path / ".staging" / "setup"
    if staged.exists():
        shutil.rmtree(staged)
    staged.mkdir(parents=True, exist_ok=True)
    downloads = staged / "downloads"
    extracts = staged / "extracts"
    downloads.mkdir(parents=True, exist_ok=True)
    extracts.mkdir(parents=True, exist_ok=True)

    installed_items: list[dict[str, Any]] = []
    try:
        for artifact in selected_artifacts:
            source = _resolve_artifact_source(manifest_file, artifact, downloads)
            actual_sha = _sha256(source)
            if actual_sha != artifact["sha256"]:
                raise ValueError(f"checksum mismatch for {artifact['id']}")
            extract_dir = extracts / artifact["id"]
            _extract_archive(source, extract_dir)
            installed_paths = (
                _install_cli_artifact(extract_dir, install_path)
                if artifact["kind"] == "cli"
                else _install_toolchain_artifact(extract_dir, install_path)
            )
            installed_items.append({"artifact_id": artifact["id"], "paths": installed_paths})

        _relocate_managed_toolchain(install_path)
        if payload["doctor"]["os"] == "windows":
            _write_windows_activation_scripts(install_path)

        cli_artifact = next((artifact for artifact in selected_artifacts if artifact["kind"] == "cli"), None)
        toolchain_artifact = next((artifact for artifact in selected_artifacts if artifact["kind"] == "toolchain"), None)
        save_cli_state(
            install_path,
            {
                "schema_version": 1,
                "cli_version": payload["plan"]["selected_release"],
                "toolchain_version": payload["plan"]["selected_release"],
                "cli_artifact_id": cli_artifact.get("id") if cli_artifact else None,
                "cli_artifact_sha256": cli_artifact.get("sha256") if cli_artifact else None,
                "toolchain_artifact_id": toolchain_artifact.get("id") if toolchain_artifact else None,
                "toolchain_artifact_sha256": toolchain_artifact.get("sha256") if toolchain_artifact else None,
                "packages_version": 1,
                "last_action": "setup",
                "status": "healthy",
            },
        )
    finally:
        if staged.exists():
            shutil.rmtree(staged)

    payload["summary"] = "Managed installation completed."
    payload["actions"] = [
        {
            "kind": "add_path",
            "priority": 1,
            "message": (
                f"Add {install_path / 'bin'} to PATH for future shells. "
                "The CLI uses its private MSYS2 runtime internally."
            ),
        },
        {
            "kind": "delete_bootstrap",
            "priority": 2,
            "message": "The bootstrap script is no longer required and may be deleted.",
        },
    ]
    payload["install"] = {
        "installed_artifacts": installed_items,
        "path_hint": _path_export_hint(install_path, payload["doctor"]["os"]),
        "install_root": str(install_path),
    }
    return payload, 0


def build_setup_payload(
    *,
    scope: str = "user",
    manifest_path: str | None = None,
    install_root: str | None = None,
) -> tuple[dict[str, Any], int]:
    manifest_file = Path(manifest_path) if manifest_path else DEFAULT_MANIFEST
    doctor = build_doctor_payload(manifest_file, interface="bootstrap")
    os_name = doctor["environment"]["os"]
    selected_scope = scope
    selected_root = install_root or (_default_system_root(os_name) if selected_scope == "system" else _default_user_root(os_name))
    active_release, selected_artifacts, validation_errors, selection_errors = _select_release(manifest_file, doctor)
    system_priv_ok = selected_scope != "system" or _has_system_privileges(os_name)
    install_path = Path(selected_root).expanduser()
    native_toolchain_assessment = doctor["environment"].get("native_toolchain", {}).get("assessment", "unavailable")
    install_mode = "managed"
    disposition = "install_managed"

    status = "ok"
    ok = True
    summary = "Managed installation plan created."
    actions: list[dict[str, Any]] = []
    exit_code = 0

    if validation_errors:
        status = "error"
        ok = False
        summary = "Release manifest validation failed."
        actions.append({"kind": "report_bug", "priority": 1, "message": validation_errors[0]})
        exit_code = 2
    elif selection_errors:
        status = "error"
        ok = False
        summary = "Managed artifact selection failed."
        actions.append({"kind": "report_bug", "priority": 1, "message": selection_errors[0]})
        exit_code = 4
    elif not system_priv_ok:
        status = "error"
        ok = False
        summary = "System-wide installation requires elevated privileges."
        actions.append(
            {
                "kind": "rerun_with_elevated_privileges",
                "priority": 1,
                "message": (
                    "Re-run this command with sudo."
                    if os_name != "windows"
                    else "Re-run PowerShell as Administrator and try again."
                ),
            }
        )
        exit_code = 3
    elif install_root is not None and not _is_writable_install_root(install_path):
        status = "error"
        ok = False
        summary = "The selected install root is not writable."
        actions.append(
            {
                "kind": "rerun_with_elevated_privileges",
                "priority": 1,
                "message": "Choose a writable install root or rerun with sufficient privileges.",
            }
        )
        exit_code = 3
    elif install_root is None and selected_scope == "user" and native_toolchain_assessment in {"preferred", "supported"}:
        install_mode = "native"
        disposition = "use_existing_toolchain"
        summary = "Using the detected native GNUstep toolchain; managed installation is not required."
        actions.append(
            {
                "kind": "use_existing_toolchain",
                "priority": 1,
                "message": doctor["environment"]["native_toolchain"]["message"],
            }
        )
    elif not doctor["environment"]["bootstrap_prerequisites"]["curl"] and not doctor["environment"]["bootstrap_prerequisites"]["wget"]:
        status = "error"
        ok = False
        summary = "Bootstrap prerequisites are incomplete."
        actions.append(
            {
                "kind": "install_downloader",
                "priority": 1,
                "message": "Install curl or wget, then rerun setup.",
            }
        )
        exit_code = 3
    elif len(selected_artifacts) == 0:
        status = "error"
        ok = False
        summary = "No managed artifacts were found for this host."
        actions.append(
            {
                "kind": "report_bug",
                "priority": 1,
                "message": "No compatible managed artifacts are available for this host yet.",
            }
        )
        exit_code = 4
    elif len(selected_artifacts) < 2:
        status = "warning"
        summary = "Managed installation plan created, but the manifest does not yet contain a complete artifact set."
        actions.append(
            {
                "kind": "report_bug",
                "priority": 2,
                "message": "The current manifest is missing either the CLI or toolchain artifact for this host.",
            }
        )
    else:
        actions.append(
            {
                "kind": "apply_install_plan",
                "priority": 1,
                "message": "Proceed with artifact download, verification, and managed installation.",
            }
        )

    payload = {
        "schema_version": 1,
        "command": "setup",
        "cli_version": CLI_VERSION,
        "ok": ok,
        "status": status,
        "summary": summary,
        "doctor": {
            "status": doctor["status"],
            "environment_classification": doctor["environment_classification"],
            "summary": doctor["summary"],
            "os": os_name,
        },
        "plan": {
            "scope": selected_scope,
            "install_mode": install_mode,
            "disposition": disposition,
            "install_root": selected_root,
            "channel": "stable",
            "manifest_path": str(manifest_file),
            "selected_release": active_release["version"] if active_release else None,
            "native_toolchain_assessment": native_toolchain_assessment,
            "selected_artifacts": [artifact["id"] for artifact in selected_artifacts],
            "system_privileges_ok": system_priv_ok,
            "manifest_validation_errors": validation_errors,
            "selection_errors": selection_errors,
        },
        "actions": actions,
    }
    return payload, exit_code


def render_setup_human(payload: dict[str, Any]) -> str:
    plan = payload["plan"]
    lines = [
        f"setup: {payload['summary']}",
        f"setup: scope={plan['scope']} root={plan['install_root']}",
        f"setup: selected release={plan['selected_release']}",
    ]
    if "install" in payload:
        lines.append(f"setup: path hint={payload['install']['path_hint']}")
    for action in payload["actions"]:
        lines.append(f"next: {action['message']}")
    return "\n".join(lines)
