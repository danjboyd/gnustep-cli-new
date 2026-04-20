from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
from zipfile import ZipFile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .package_repository import package_index_trust_gate


def _state_dir(managed_root: Path) -> Path:
    return managed_root / "state"


def _db_path(managed_root: Path) -> Path:
    return _state_dir(managed_root) / "installed-packages.json"


def _transactions_dir(managed_root: Path) -> Path:
    return managed_root / ".transactions" / "packages"


def _transaction_path(managed_root: Path, package_id: str) -> Path:
    safe_id = package_id.replace("/", "_")
    return _transactions_dir(managed_root) / f"{safe_id}.json"


def _write_transaction(managed_root: Path, package_id: str, payload: dict[str, Any]) -> Path:
    path = _transaction_path(managed_root, package_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


def _clear_transaction(managed_root: Path, package_id: str) -> None:
    path = _transaction_path(managed_root, package_id)
    if path.exists():
        path.unlink()


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_artifact_digest(artifact_path: Path, artifact: dict[str, Any]) -> bool:
    expected = artifact.get("sha256") or artifact.get("integrity", {}).get("sha256")
    if not expected:
        return False
    return _sha256(artifact_path).lower() == str(expected).lower()


def _extract_artifact(artifact_path: Path, staging: Path, artifact: dict[str, Any]) -> None:
    artifact_format = artifact.get("format")
    if artifact_format == "zip" or artifact_path.suffix == ".zip":
        with ZipFile(artifact_path) as archive:
            archive.extractall(staging)
        return
    with tarfile.open(artifact_path, "r:gz") as archive:
        archive.extractall(staging, filter="data")


def _write_package_record_as_manifest(package_record: dict[str, Any], root: Path) -> Path:
    scratch = root / ".staging" / ".resolved-manifests"
    scratch.mkdir(parents=True, exist_ok=True)
    path = scratch / f"{package_record['id']}.json"
    path.write_text(json.dumps(package_record, indent=2) + "\n")
    return path


def _package_from_index(
    index_path: str | Path,
    package_id: str,
    managed_root: str | Path,
    *,
    operation: str,
    require_signed_index: bool = True,
    trusted_public_key_path: str | Path | None = None,
) -> tuple[dict[str, Any], int]:
    index_file = Path(index_path).resolve()
    root = Path(managed_root).resolve()
    trust = package_index_trust_gate(index_file, require_signatures=require_signed_index, trusted_public_key_path=trusted_public_key_path)
    if not trust["ok"]:
        return (
            {
                "schema_version": 1,
                "command": operation,
                "ok": False,
                "status": "error",
                "summary": "Package index trust verification failed.",
                "package_id": package_id,
                "package_index": str(index_file),
                "trust": trust,
            },
            4,
        )
    payload = json.loads(index_file.read_text())
    for package_record in payload.get("packages", []):
        if package_record.get("id") == package_id:
            manifest_path = _write_package_record_as_manifest(package_record, root)
            if operation == "upgrade":
                result, code = upgrade_package(manifest_path, root)
            else:
                result, code = install_package(manifest_path, root)
            result["package_index"] = str(index_file)
            result["trust"] = {"ok": True, "require_signed_index": require_signed_index}
            return result, code
    return (
        {
            "schema_version": 1,
            "command": operation,
            "ok": False,
            "status": "error",
            "summary": f"Package '{package_id}' was not found in the package index.",
            "package_id": package_id,
            "package_index": str(index_file),
        },
        1,
    )


def install_package_from_index(
    index_path: str | Path,
    package_id: str,
    managed_root: str | Path,
    *,
    require_signed_index: bool = True,
    trusted_public_key_path: str | Path | None = None,
) -> tuple[dict[str, Any], int]:
    return _package_from_index(
        index_path,
        package_id,
        managed_root,
        operation="install",
        require_signed_index=require_signed_index,
        trusted_public_key_path=trusted_public_key_path,
    )


def upgrade_package_from_index(
    index_path: str | Path,
    package_id: str,
    managed_root: str | Path,
    *,
    require_signed_index: bool = True,
    trusted_public_key_path: str | Path | None = None,
) -> tuple[dict[str, Any], int]:
    return _package_from_index(
        index_path,
        package_id,
        managed_root,
        operation="upgrade",
        require_signed_index=require_signed_index,
        trusted_public_key_path=trusted_public_key_path,
    )


def _install_or_upgrade_package(manifest_path: str | Path, managed_root: str | Path, *, allow_upgrade: bool) -> tuple[dict[str, Any], int]:
    manifest_file = Path(manifest_path).resolve()
    root = Path(managed_root).resolve()
    payload = json.loads(manifest_file.read_text())
    package_id = payload["id"]
    state = _load_state(root)
    existing = state["packages"].get(package_id)
    operation = "upgrade" if existing and allow_upgrade else "install"
    if existing and not allow_upgrade:
        return (
            {
                "schema_version": 1,
                "command": "install",
                "ok": True,
                "status": "ok",
                "summary": "Package is already installed.",
                "package_id": package_id,
                "installed_files": existing["installed_files"],
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

    if not _verify_artifact_digest(artifact_path, artifact):
        return (
            {
                "schema_version": 1,
                "command": "install",
                "ok": False,
                "status": "error",
                "summary": "Artifact digest verification failed.",
                "package_id": package_id,
            },
            1,
        )

    staging = root / ".staging" / package_id
    backup = root / ".transactions" / "package-backups" / package_id
    final_root = root / "packages" / package_id
    transaction = _write_transaction(root, package_id, {
        "schema_version": 1,
        "operation": operation,
        "package_id": package_id,
        "manifest_path": str(manifest_file),
        "staging": str(staging),
        "final_root": str(final_root),
        "backup_root": str(backup) if existing else None,
    })
    if staging.exists():
        shutil.rmtree(staging)
    if backup.exists():
        shutil.rmtree(backup)
    staging.mkdir(parents=True, exist_ok=True)

    installed_files: list[str] = []
    try:
        _extract_artifact(artifact_path, staging, artifact)
        final_root.parent.mkdir(parents=True, exist_ok=True)
        if final_root.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(final_root), str(backup))
        shutil.move(str(staging), str(final_root))
        for path in sorted(final_root.rglob("*")):
            if path.is_file():
                installed_files.append(str(path.relative_to(root)))

        state["packages"][package_id] = {
            "manifest_path": str(manifest_file),
            "install_root": str(final_root),
            "installed_files": installed_files,
            "version": payload.get("version"),
        }
        _save_state(root, state)
        if backup.exists():
            shutil.rmtree(backup)
        _clear_transaction(root, package_id)
    except Exception:
        if final_root.exists() and existing and backup.exists():
            shutil.rmtree(final_root)
        if existing and backup.exists():
            shutil.move(str(backup), str(final_root))
        if staging.exists():
            shutil.rmtree(staging)
        _clear_transaction(root, package_id)
        raise

    return (
        {
            "schema_version": 1,
            "command": "install" if operation == "install" else "upgrade",
            "ok": True,
            "status": "ok",
            "summary": "Package installed." if operation == "install" else "Package upgraded.",
            "package_id": package_id,
            "installed_files": installed_files,
            "transaction": {"path": str(transaction), "completed": True},
        },
        0,
    )


def install_package(manifest_path: str | Path, managed_root: str | Path) -> tuple[dict[str, Any], int]:
    return _install_or_upgrade_package(manifest_path, managed_root, allow_upgrade=False)


def upgrade_package(manifest_path: str | Path, managed_root: str | Path) -> tuple[dict[str, Any], int]:
    return _install_or_upgrade_package(manifest_path, managed_root, allow_upgrade=True)



def recover_package_transactions(managed_root: str | Path, *, apply: bool = False) -> tuple[dict[str, Any], int]:
    root = Path(managed_root).resolve()
    transactions_root = _transactions_dir(root)
    transactions = []
    if transactions_root.exists():
        for path in sorted(transactions_root.glob("*.json")):
            try:
                payload = json.loads(path.read_text())
            except Exception as exc:
                transactions.append({"path": str(path), "ok": False, "summary": f"transaction file is invalid: {exc}"})
                continue
            operation = payload.get("operation")
            final_root = Path(payload.get("final_root") or payload.get("install_root") or "")
            backup_root = Path(payload.get("backup_root") or "") if payload.get("backup_root") else None
            staging = Path(payload.get("staging") or "") if payload.get("staging") else None
            recovered = False
            if apply:
                if operation in {"upgrade", "install"}:
                    if staging and staging.exists():
                        shutil.rmtree(staging)
                    if operation == "upgrade" and backup_root and backup_root.exists():
                        if final_root.exists():
                            shutil.rmtree(final_root)
                        final_root.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(backup_root), str(final_root))
                        recovered = True
                elif operation == "remove":
                    if backup_root and backup_root.exists() and not final_root.exists():
                        final_root.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(backup_root), str(final_root))
                        recovered = True
                    package_record = payload.get("package_record")
                    package_id = payload.get("package_id")
                    if isinstance(package_record, dict) and package_id:
                        state = _load_state(root)
                        state.setdefault("packages", {})[package_id] = package_record
                        _save_state(root, state)
                        recovered = True
                path.unlink()
            transactions.append({
                "path": str(path),
                "ok": True,
                "operation": operation,
                "package_id": payload.get("package_id"),
                "recovered": recovered,
            })
    return (
        {
            "schema_version": 1,
            "command": "package-transaction-recovery",
            "ok": True,
            "status": "ok",
            "summary": "Package transaction recovery applied." if apply else "Package transaction recovery audit completed.",
            "managed_root": str(root),
            "apply": apply,
            "transactions": transactions,
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
    backup = root / ".transactions" / "package-remove-backups" / package_id
    transaction = _write_transaction(root, package_id, {
        "schema_version": 1,
        "operation": "remove",
        "package_id": package_id,
        "install_root": str(install_root),
        "backup_root": str(backup),
        "package_record": record,
    })
    if backup.exists():
        shutil.rmtree(backup)
    try:
        if install_root.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(install_root), str(backup))
        del state["packages"][package_id]
        _save_state(root, state)
        if backup.exists():
            shutil.rmtree(backup)
        _clear_transaction(root, package_id)
    except Exception:
        if not install_root.exists() and backup.exists():
            shutil.move(str(backup), str(install_root))
        _clear_transaction(root, package_id)
        raise
    return (
        {
            "schema_version": 1,
            "command": "remove",
            "ok": True,
            "status": "ok",
            "summary": "Package removed.",
            "package_id": package_id,
            "transaction": {"path": str(transaction), "completed": True},
        },
        0,
    )
