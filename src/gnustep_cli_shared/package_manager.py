from __future__ import annotations

import json
import shutil
import tarfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _state_dir(managed_root: Path) -> Path:
    return managed_root / "state"


def _db_path(managed_root: Path) -> Path:
    return _state_dir(managed_root) / "installed-packages.json"


def _load_state(managed_root: Path) -> dict[str, Any]:
    path = _db_path(managed_root)
    if not path.exists():
        return {"packages": {}}
    return json.loads(path.read_text())


def _save_state(managed_root: Path, state: dict[str, Any]) -> None:
    path = _db_path(managed_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n")


def _resolve_artifact(artifact: dict[str, Any]) -> Path:
    url = artifact["url"]
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return Path(parsed.path)
    return Path(url)


def install_package(manifest_path: str | Path, managed_root: str | Path) -> tuple[dict[str, Any], int]:
    manifest_file = Path(manifest_path).resolve()
    root = Path(managed_root).resolve()
    payload = json.loads(manifest_file.read_text())
    package_id = payload["id"]
    state = _load_state(root)
    if package_id in state["packages"]:
        return (
            {
                "schema_version": 1,
                "command": "install",
                "ok": True,
                "status": "ok",
                "summary": "Package is already installed.",
                "package_id": package_id,
                "installed_files": state["packages"][package_id]["installed_files"],
            },
            0,
        )

    artifact = payload["artifacts"][0]
    artifact_path = _resolve_artifact(artifact)
    if not artifact_path.exists():
        return (
            {
                "schema_version": 1,
                "command": "install",
                "ok": False,
                "status": "error",
                "summary": "Artifact not found.",
                "package_id": package_id,
            },
            1,
        )

    staging = root / ".staging" / package_id
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    installed_files: list[str] = []
    with tarfile.open(artifact_path, "r:gz") as archive:
        archive.extractall(staging, filter="data")
    final_root = root / "packages" / package_id
    if final_root.exists():
        shutil.rmtree(final_root)
    final_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(staging), str(final_root))
    for path in sorted(final_root.rglob("*")):
        if path.is_file():
            installed_files.append(str(path.relative_to(root)))

    state["packages"][package_id] = {
        "manifest_path": str(manifest_file),
        "install_root": str(final_root),
        "installed_files": installed_files,
    }
    _save_state(root, state)
    return (
        {
            "schema_version": 1,
            "command": "install",
            "ok": True,
            "status": "ok",
            "summary": "Package installed.",
            "package_id": package_id,
            "installed_files": installed_files,
        },
        0,
    )


def remove_package(package_id: str, managed_root: str | Path) -> tuple[dict[str, Any], int]:
    root = Path(managed_root).resolve()
    state = _load_state(root)
    record = state["packages"].get(package_id)
    if not record:
        return (
            {
                "schema_version": 1,
                "command": "remove",
                "ok": False,
                "status": "error",
                "summary": "Package is not installed.",
                "package_id": package_id,
            },
            1,
        )
    install_root = Path(record["install_root"])
    if install_root.exists():
        shutil.rmtree(install_root)
    del state["packages"][package_id]
    _save_state(root, state)
    return (
        {
            "schema_version": 1,
            "command": "remove",
            "ok": True,
            "status": "ok",
            "summary": "Package removed.",
            "package_id": package_id,
        },
        0,
    )
