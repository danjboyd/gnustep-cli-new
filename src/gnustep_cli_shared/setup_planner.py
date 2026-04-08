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


def _select_release(manifest_file: Path, doctor: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = json.loads(manifest_file.read_text())
    active_release = manifest["releases"][0]
    selected = [artifact for artifact in active_release.get("artifacts", []) if _artifact_matches_host(artifact, doctor)]
    return active_release, selected


def _path_export_hint(root: Path, os_name: str) -> str:
    if os_name == "windows":
        return rf"$env:Path = '{root}\bin;{root}\System\Tools;' + $env:Path"
    return f'export PATH="{root}/bin:{root}/System/Tools:$PATH"'


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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

    manifest_file = Path(manifest_path) if manifest_path else DEFAULT_MANIFEST
    install_path = Path(payload["plan"]["install_root"]).expanduser().resolve()
    doctor = build_doctor_payload(manifest_file)
    _, selected_artifacts = _select_release(manifest_file, doctor)
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

        save_cli_state(
            install_path,
            {
                "schema_version": 1,
                "cli_version": payload["plan"]["selected_release"],
                "toolchain_version": payload["plan"]["selected_release"],
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
            "message": f"Add {install_path / 'bin'} and {install_path / 'System/Tools'} to PATH for future shells.",
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
    doctor = build_doctor_payload(manifest_file)
    os_name = doctor["environment"]["os"]
    selected_scope = scope
    selected_root = install_root or (_default_system_root(os_name) if selected_scope == "system" else _default_user_root(os_name))
    active_release, selected_artifacts = _select_release(manifest_file, doctor)
    system_priv_ok = selected_scope != "system" or _has_system_privileges(os_name)

    status = "ok"
    ok = True
    summary = "Managed installation plan created."
    actions: list[dict[str, Any]] = []
    exit_code = 0

    if not system_priv_ok:
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
            "install_root": selected_root,
            "channel": "stable",
            "manifest_path": str(manifest_file),
            "selected_release": active_release["version"],
            "selected_artifacts": [artifact["id"] for artifact in selected_artifacts],
            "system_privileges_ok": system_priv_ok,
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
