from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


VALID_KINDS = {"gui-app", "cli-tool", "library", "template"}
CORE_REQUIRED_FIELDS = {
    "schema_version",
    "id",
    "name",
    "version",
    "kind",
    "summary",
    "license",
    "maintainers",
    "source",
    "requirements",
    "artifacts",
}


def init_package_manifest(package_dir: str | Path, package_name: str, kind: str) -> dict[str, Any]:
    dest = Path(package_dir).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    manifest_path = dest / "package.json"
    if kind not in VALID_KINDS:
        return {
            "schema_version": 1,
            "command": "package-init",
            "ok": False,
            "status": "error",
            "summary": f"Unknown package kind: {kind}",
            "manifest_path": str(manifest_path),
        }

    payload: dict[str, Any] = {
        "schema_version": 1,
        "id": f"org.example.{package_name.lower()}",
        "name": package_name,
        "version": "0.1.0",
        "kind": kind,
        "summary": f"{package_name} package",
        "license": "TBD",
        "maintainers": [{"name": "TBD"}],
        "source": {"type": "archive", "url": "https://example.invalid/source.tar.gz", "sha256": "TBD"},
        "requirements": {
            "supported_os": ["linux"],
            "supported_arch": ["amd64"],
            "supported_compiler_families": ["clang"],
            "supported_objc_runtimes": ["libobjc2"],
            "supported_objc_abi": ["modern"],
            "required_features": [],
            "forbidden_features": [],
        },
        "artifacts": [
            {
                "id": f"{package_name.lower()}-linux-amd64-clang",
                "os": "linux",
                "arch": "amd64",
                "compiler_family": "clang",
                "toolchain_flavor": "clang",
                "objc_runtime": "libobjc2",
                "objc_abi": "modern",
                "url": "https://example.invalid/artifact.tar.gz",
                "sha256": "TBD",
            }
        ],
        "patches": [],
        "install": {
            "strategy": "archive",
            "prefix_layout": "gnustep",
        },
    }
    if kind == "gui-app":
        payload["integration"] = {
            "display_name": package_name,
            "icon": {"source": "Resources/AppIcon.png"},
            "categories": ["Development"],
            "launcher": True,
        }
        payload["install"]["primary_executable"] = package_name
    elif kind == "cli-tool":
        payload["install"]["executables"] = [package_name]
    elif kind == "library":
        payload["install"]["library_files"] = [f"lib{package_name}.so"]
        payload["install"]["headers"] = [f"{package_name}.h"]
    elif kind == "template":
        payload["install"]["template_root"] = f"Templates/{package_name}"

    manifest_path.write_text(json.dumps(payload, indent=2) + "\n")
    return {
        "schema_version": 1,
        "command": "package-init",
        "ok": True,
        "status": "ok",
        "summary": "Package manifest created.",
        "manifest_path": str(manifest_path),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_placeholder_digest(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return True
    lowered = value.lower()
    return value == "TBD" or lowered.endswith("tbd") or "placeholder" in lowered or "development" in lowered


def _selected_patches(patches: list[dict[str, Any]], target_id: str | None = None) -> list[dict[str, Any]]:
    selected = []
    for patch in patches:
        applies_to = patch.get("applies_to")
        if target_id is None or applies_to is None or target_id in applies_to:
            selected.append(patch)
    return selected


def apply_package_patches(manifest_path: str | Path, source_dir: str | Path, target_id: str | None = None) -> dict[str, Any]:
    manifest = Path(manifest_path).resolve()
    source_root = Path(source_dir).resolve()
    validation = validate_package_manifest(manifest)
    if not validation.get("ok"):
        return {
            "schema_version": 1,
            "command": "package-apply-patches",
            "ok": False,
            "status": "error",
            "summary": "Package manifest validation failed before patch application.",
            "manifest_path": str(manifest),
            "source_dir": str(source_root),
            "target_id": target_id,
            "applied_patches": [],
            "errors": validation.get("errors", []),
        }
    if not source_root.exists() or not source_root.is_dir():
        return {
            "schema_version": 1,
            "command": "package-apply-patches",
            "ok": False,
            "status": "error",
            "summary": "Source directory does not exist.",
            "manifest_path": str(manifest),
            "source_dir": str(source_root),
            "target_id": target_id,
            "applied_patches": [],
            "errors": [{"code": "source_dir_missing", "message": "Source directory does not exist."}],
        }

    payload = json.loads(manifest.read_text())
    patches = _selected_patches(payload.get("patches", []) or [], target_id=target_id)
    applied: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for patch_entry in patches:
        patch_path = (manifest.parent / patch_entry["path"]).resolve()
        actual_digest = _sha256(patch_path)
        if actual_digest != patch_entry["sha256"]:
            errors.append({
                "code": "patch_digest_mismatch",
                "patch": patch_entry.get("id"),
                "message": "Patch digest changed after validation.",
            })
            break
        strip = int(patch_entry.get("strip", 1))
        proc = subprocess.run(
            ["patch", "--batch", "--forward", f"-p{strip}", "-i", str(patch_path)],
            cwd=source_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        record = {
            "id": patch_entry.get("id"),
            "path": patch_entry.get("path"),
            "sha256": patch_entry.get("sha256"),
            "strip": strip,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
        if proc.returncode != 0:
            errors.append({
                "code": "patch_apply_failed",
                "patch": patch_entry.get("id"),
                "message": "Patch command failed.",
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            })
            break
        applied.append(record)

    ok = not errors
    return {
        "schema_version": 1,
        "command": "package-apply-patches",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": "Declared package patches applied." if ok else "Package patch application failed.",
        "manifest_path": str(manifest),
        "source_dir": str(source_root),
        "target_id": target_id,
        "applied_patches": applied,
        "skipped_patch_count": len((payload.get("patches", []) or [])) - len(patches),
        "errors": errors,
    }


def validate_package_manifest(manifest_path: str | Path) -> dict[str, Any]:
    path = Path(manifest_path).resolve()
    if not path.exists():
        return {
            "schema_version": 1,
            "command": "package-validate",
            "ok": False,
            "status": "error",
            "summary": "Package manifest not found.",
            "errors": [{"code": "manifest_missing", "message": "Package manifest not found."}],
            "warnings": [],
        }
    payload = json.loads(path.read_text())
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    for field in sorted(CORE_REQUIRED_FIELDS):
        if field not in payload:
            errors.append({"code": "missing_field", "message": f"Missing required field '{field}'."})

    kind = payload.get("kind")
    if kind not in VALID_KINDS:
        errors.append({"code": "invalid_kind", "message": f"Invalid package kind '{kind}'."})

    install = payload.get("install", {})
    integration = payload.get("integration", {})
    if kind == "gui-app":
        for field in ("display_name", "icon", "categories", "launcher"):
            if field not in integration:
                errors.append({"code": "missing_integration_field", "message": f"Missing gui-app integration field '{field}'."})
        if "primary_executable" not in install:
            errors.append({"code": "missing_install_field", "message": "Missing gui-app install field 'primary_executable'."})
    elif kind == "cli-tool":
        if "executables" not in install:
            errors.append({"code": "missing_install_field", "message": "Missing cli-tool install field 'executables'."})
    elif kind == "library":
        if "library_files" not in install:
            errors.append({"code": "missing_install_field", "message": "Missing library install field 'library_files'."})
    elif kind == "template":
        if "template_root" not in install:
            errors.append({"code": "missing_install_field", "message": "Missing template install field 'template_root'."})

    if payload.get("license") == "TBD":
        warnings.append({"code": "placeholder_license", "message": "Package manifest still uses placeholder license data."})
    source = payload.get("source", {}) if isinstance(payload.get("source", {}), dict) else {}
    if source.get("sha256") == "TBD":
        warnings.append({"code": "placeholder_checksum", "message": "Package manifest still uses placeholder checksum data."})
    for field in ("tracking_strategy", "update_cadence", "channel_policy"):
        if source and field not in source:
            warnings.append({"code": "missing_source_policy", "message": f"Package source is missing update policy field '{field}'."})

    patches = payload.get("patches", [])
    if patches is None:
        patches = []
    if not isinstance(patches, list):
        errors.append({"code": "invalid_patches", "message": "Package manifest 'patches' must be an array when present."})
    else:
        for index, patch in enumerate(patches):
            if not isinstance(patch, dict):
                errors.append({"code": "invalid_patch", "message": f"Patch entry at index {index} must be an object."})
                continue
            patch_id = patch.get("id")
            patch_path = patch.get("path")
            patch_sha = patch.get("sha256")
            if not isinstance(patch_id, str) or not patch_id:
                errors.append({"code": "missing_patch_field", "message": f"Patch entry at index {index} is missing field 'id'."})
            if not isinstance(patch_path, str) or not patch_path:
                errors.append({"code": "missing_patch_field", "message": f"Patch entry at index {index} is missing field 'path'."})
                continue
            if Path(patch_path).is_absolute() or ".." in Path(patch_path).parts:
                errors.append({"code": "unsafe_patch_path", "message": f"Patch '{patch_id or index}' path must be relative to the package directory and must not contain '..'."})
                continue
            resolved_patch = path.parent / patch_path
            if not resolved_patch.exists():
                errors.append({"code": "patch_missing", "message": f"Patch '{patch_id or index}' does not exist at '{patch_path}'."})
            if _is_placeholder_digest(patch_sha):
                errors.append({"code": "missing_patch_digest", "message": f"Patch '{patch_id or index}' is missing a verified sha256 digest."})
            elif resolved_patch.exists():
                actual = _sha256(resolved_patch)
                if actual != patch_sha:
                    errors.append({"code": "patch_digest_mismatch", "message": f"Patch '{patch_id or index}' sha256 does not match the patch file."})
            strip = patch.get("strip", 1)
            if not isinstance(strip, int) or strip < 0:
                errors.append({"code": "invalid_patch_strip", "message": f"Patch '{patch_id or index}' field 'strip' must be a non-negative integer."})
            applies_to = patch.get("applies_to")
            if applies_to is not None and (not isinstance(applies_to, list) or not all(isinstance(item, str) and item for item in applies_to)):
                errors.append({"code": "invalid_patch_applies_to", "message": f"Patch '{patch_id or index}' field 'applies_to' must be an array of target ids when present."})

    return {
        "schema_version": 1,
        "command": "package-validate",
        "ok": len(errors) == 0,
        "status": "ok" if len(errors) == 0 else "error",
        "summary": "Package manifest is valid." if len(errors) == 0 else "Package manifest validation failed.",
        "manifest_path": str(path),
        "errors": errors,
        "warnings": warnings,
    }

