from __future__ import annotations

import json
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
    if payload.get("source", {}).get("sha256") == "TBD":
        warnings.append({"code": "placeholder_checksum", "message": "Package manifest still uses placeholder checksum data."})

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

