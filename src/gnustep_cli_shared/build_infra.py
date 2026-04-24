from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from .setup_planner import execute_setup
from .package_repository import package_index_trust_gate
from .smoke_harness import evaluate_release_gate, phase26_exit_status


UNIX_CORE_COMPONENTS = [
    "libobjc2",
    "libdispatch",
    "tools-make",
    "libs-base",
    "libs-corebase",
    "libs-gui",
    "libs-back",
]

TIER1_TARGETS = [
    {
        "id": "linux-amd64-clang",
        "os": "linux",
        "arch": "amd64",
        "compiler_family": "clang",
        "toolchain_flavor": "clang",
        "strategy": "source-build",
        "publish": True,
        "core_components": UNIX_CORE_COMPONENTS,
        "supported_distributions": ["debian"],
        "portability_policy": "distribution-scoped",
        "portability_notes": "Current source-built Linux artifact is validated on Debian only; Ubuntu requires its own distro-scoped artifact because ICU and other runtime SONAMEs differ by distro release.",
    },
    {
        "id": "linux-ubuntu2404-amd64-clang",
        "os": "linux",
        "arch": "amd64",
        "compiler_family": "clang",
        "toolchain_flavor": "clang",
        "strategy": "source-build",
        "publish": True,
        "core_components": UNIX_CORE_COMPONENTS,
        "supported_distributions": ["ubuntu"],
        "supported_os_versions": ["ubuntu-24.04"],
        "build_host": "ubuntu:24.04 docker amd64",
        "portability_policy": "distribution-scoped",
        "portability_notes": "Ubuntu amd64 managed target built in a base Ubuntu 24.04 Docker image; publish is enabled after runtime dependency closure and Docker setup smoke validation.",
    },
    {
        "id": "linux-arm64-clang",
        "os": "linux",
        "arch": "arm64",
        "compiler_family": "clang",
        "toolchain_flavor": "clang",
        "strategy": "source-build",
        "publish": False,
        "core_components": UNIX_CORE_COMPONENTS,
        "supported_distributions": ["debian"],
        "portability_policy": "distribution-scoped",
        "portability_notes": "Planned Debian aarch64 managed target; publish remains false until OracleTestVMs build/validation evidence exists.",
    },
    {
        "id": "openbsd-amd64-clang",
        "os": "openbsd",
        "arch": "amd64",
        "compiler_family": "clang",
        "toolchain_flavor": "clang",
        "strategy": "source-build",
        "publish": True,
        "core_components": UNIX_CORE_COMPONENTS,
    },
    {
        "id": "openbsd-arm64-clang",
        "os": "openbsd",
        "arch": "arm64",
        "compiler_family": "clang",
        "toolchain_flavor": "clang",
        "strategy": "source-build",
        "publish": False,
        "core_components": UNIX_CORE_COMPONENTS,
        "portability_policy": "platform-wide",
        "portability_notes": "Planned OpenBSD arm64 target; publish remains false until host-backed build/validation evidence exists.",
    },
    {
        "id": "windows-amd64-msys2-clang64",
        "os": "windows",
        "arch": "amd64",
        "compiler_family": "clang",
        "toolchain_flavor": "msys2-clang64",
        "strategy": "msys2-assembly",
        "publish": True,
        "core_components": [
            "libobjc2",
            "libdispatch",
            "tools-make",
            "libs-base",
            "libs-gui",
            "libs-back",
        ],
    },
    {
        "id": "windows-amd64-msvc",
        "os": "windows",
        "arch": "amd64",
        "compiler_family": "msvc",
        "toolchain_flavor": "msvc",
        "strategy": "source-build",
        "publish": False,
        "core_components": [
            "libobjc2",
            "tools-make",
            "libs-base",
            "libs-gui",
            "libs-back",
        ],
    },
]

SOURCE_COMPONENT_URLS = {
    "libobjc2": "https://github.com/gnustep/libobjc2.git",
    "libdispatch": "https://github.com/swiftlang/swift-corelibs-libdispatch.git",
    "tools-make": "https://github.com/gnustep/tools-make.git",
    "libs-base": "https://github.com/gnustep/libs-base.git",
    "libs-corebase": "https://github.com/gnustep/libs-corebase.git",
    "libs-gui": "https://github.com/gnustep/libs-gui.git",
    "libs-back": "https://github.com/gnustep/libs-back.git",
}

PINNED_SOURCE_REVISIONS = {
    "libobjc2": "b67709ad7851973fde127022d8ac6a710c82b1d5",
    "libdispatch": "4ce40128f607a6eb7b58077a06b7464c1518a30d",
    "tools-make": "50cf9619e672fb2ff6825f239b5a172c5dc55630",
    "libs-base": "d898f703e618b86f9b7ecb0f05a257cb6ed3ffac",
    "libs-corebase": "e5983493d5ddf9c5b7e562f166855d9517a3f179",
    "libs-gui": "7892137bdedd007eba8425f766e41481ddb4fda6",
    "libs-back": "bf3b3ced525f08415a20d109f05be1f91492414c",
}

MSYS2_PACKAGE_INPUTS = [
    "mingw-w64-clang-x86_64-clang",
    "mingw-w64-clang-x86_64-libobjc2",
    "mingw-w64-clang-x86_64-libdispatch",
    "mingw-w64-clang-x86_64-gnustep-make",
    "mingw-w64-clang-x86_64-gnustep-base",
    "mingw-w64-clang-x86_64-gnustep-gui",
    "mingw-w64-clang-x86_64-gnustep-back",
    "mingw-w64-clang-x86_64-cairo",
    "mingw-w64-clang-x86_64-fontconfig",
    "mingw-w64-clang-x86_64-freetype",
    "mingw-w64-clang-x86_64-harfbuzz",
    "mingw-w64-clang-x86_64-icu",
    "mingw-w64-clang-x86_64-libjpeg-turbo",
    "mingw-w64-clang-x86_64-libpng",
    "mingw-w64-clang-x86_64-libtiff",
    "mingw-w64-clang-x86_64-pixman",
    "mingw-w64-clang-x86_64-pkgconf",
]

MSYS2_INSTALLER_INPUT = {
    "name": "msys2-x86_64",
    "version": "latest",
    "url": "https://github.com/msys2/msys2-installer/releases/latest/download/msys2-x86_64-latest.exe",
    "sha256": "TBD",
    "source_channel": "msys2-installer",
}

MSYS2_HOST_PACKAGES = [
    "make",
]

MSYS2_DEVELOPER_BINARIES = [
    "bash.exe",
    "sh.exe",
    "make.exe",
    "sha256sum.exe",
]

MSYS2_DEVELOPER_RUNTIME_DLLS = [
    "msys-2.0.dll",
]

MANAGED_PREFIX_PLACEHOLDER = "__GNUSTEP_CLI_INSTALL_ROOT__"

LINUX_SYSTEM_TOOL_NAMES = [
    "gnustep-config",
    "gdomap",
    "gdnc",
    "make_services",
    "openapp",
    "plmerge",
    "defaults",
]


def tier1_targets() -> list[dict[str, Any]]:
    return deepcopy(TIER1_TARGETS)


def target_by_id(target_id: str) -> dict[str, Any]:
    for target in TIER1_TARGETS:
        if target["id"] == target_id:
            return deepcopy(target)
    raise ValueError(f"unknown target id: {target_id}")


def build_matrix() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "targets": tier1_targets(),
    }


def release_manifest_from_matrix(version: str, base_url: str) -> dict[str, Any]:
    artifacts: list[dict[str, Any]] = []
    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    for target in TIER1_TARGETS:
        cli_id = f"cli-{target['id']}"
        artifacts.append(
            {
                "id": cli_id,
                "kind": "cli",
                "version": version,
                "os": target["os"],
                "arch": target["arch"],
                "compiler_family": target["compiler_family"],
                "toolchain_flavor": target["toolchain_flavor"],
                "objc_runtime": "libobjc2" if target["compiler_family"] != "msvc" else "unknown",
                "objc_abi": "modern" if target["compiler_family"] != "msvc" else "unknown",
                "required_features": [],
                "format": "tar.gz" if target["os"] != "windows" else "zip",
                "supported_distributions": target.get("supported_distributions", []),
                "supported_os_versions": target.get("supported_os_versions", []),
                "portability_policy": target.get("portability_policy", "platform-wide"),
                "url": f"{base_url.rstrip('/')}/{version}/{cli_id}",
                "sha256": "TBD",
                "integrity": {"sha256": "TBD"},
                "published": target["publish"],
                "provenance": {
                    "build_system": "project-controlled",
                    "source_revision": "TBD",
                    "builder_identity": "TBD",
                    "attestation_url": None,
                },
            }
        )
        artifacts.append(
            {
                "id": f"toolchain-{target['id']}",
                "kind": "toolchain",
                "version": version,
                "os": target["os"],
                "arch": target["arch"],
                "compiler_family": target["compiler_family"],
                "toolchain_flavor": target["toolchain_flavor"],
                "objc_runtime": "libobjc2" if target["compiler_family"] != "msvc" else "unknown",
                "objc_abi": "modern" if target["compiler_family"] != "msvc" else "unknown",
                "required_features": ["blocks"] if target["compiler_family"] != "msvc" else [],
                "format": "tar.gz" if target["os"] != "windows" else "zip",
                "supported_distributions": target.get("supported_distributions", []),
                "supported_os_versions": target.get("supported_os_versions", []),
                "portability_policy": target.get("portability_policy", "platform-wide"),
                "url": f"{base_url.rstrip('/')}/{version}/toolchain-{target['id']}",
                "sha256": "TBD",
                "integrity": {"sha256": "TBD"},
                "published": target["publish"],
                "provenance": {
                    "build_system": "project-controlled",
                    "source_revision": "TBD",
                    "builder_identity": "TBD",
                    "attestation_url": None,
                },
            }
        )
    return {
        "schema_version": 1,
        "channel": "stable",
        "generated_at": generated_at,
        "metadata_version": 1,
        "expires_at": "TBD",
        "trust": {
            "root_version": 1,
            "signature_policy": "single-role-v1",
            "signatures": [],
        },
        "releases": [
            {
                "version": version,
                "status": "active",
                "artifacts": artifacts,
            }
        ],
    }


def _artifact_target_id(artifact: dict[str, Any]) -> str | None:
    artifact_id = artifact.get("id")
    if not isinstance(artifact_id, str):
        return None
    for prefix in ("cli-", "toolchain-", "package-", "delta-"):
        if artifact_id.startswith(prefix):
            return artifact_id.removeprefix(prefix)
    return None


def _artifact_immutable_reference_errors(artifact: dict[str, Any], *, expected_kind: str | None = None, expected_target_id: str | None = None) -> list[str]:
    errors: list[str] = []
    required = ("id", "kind", "version", "os", "arch", "url", "sha256", "size")
    for field in required:
        if artifact.get(field) in (None, ""):
            errors.append(f"artifact is missing immutable reference field: {field}")
    if expected_kind and artifact.get("kind") != expected_kind:
        errors.append(f"artifact kind must be {expected_kind}")
    if expected_target_id and _artifact_target_id(artifact) != expected_target_id:
        errors.append(f"artifact target must be {expected_target_id}")
    sha256 = artifact.get("sha256")
    if isinstance(sha256, str) and sha256 == "TBD":
        errors.append("artifact sha256 must be concrete for reuse")
    integrity = artifact.get("integrity")
    if isinstance(integrity, dict) and integrity.get("sha256") not in (None, sha256):
        errors.append("artifact integrity.sha256 must match sha256")
    return errors


def reusable_artifact_reference(
    artifact: dict[str, Any],
    *,
    expected_kind: str | None = None,
    expected_target_id: str | None = None,
) -> dict[str, Any]:
    errors = _artifact_immutable_reference_errors(
        artifact,
        expected_kind=expected_kind,
        expected_target_id=expected_target_id,
    )
    if errors:
        raise ValueError("; ".join(errors))
    reference = deepcopy(artifact)
    reference["reused"] = True
    reference["published"] = True
    reference.setdefault("integrity", {"sha256": reference["sha256"]})
    reference["reuse_policy"] = {
        "kind": "immutable-artifact-reference",
        "requires_url": True,
        "requires_sha256": True,
        "requires_size": True,
        "local_reupload_required": False,
    }
    reference.setdefault("layer", "managed-toolchain" if reference.get("kind") == "toolchain" else reference.get("kind"))
    return reference


def dogfood_snapshot_version(
    base_version: str,
    *,
    source_revision: str | None = None,
    timestamp: datetime | str | None = None,
    sequence: int = 0,
) -> str:
    if timestamp is None:
        timestamp_value = datetime.now(UTC)
    elif isinstance(timestamp, datetime):
        timestamp_value = timestamp.astimezone(UTC) if timestamp.tzinfo is not None else timestamp.replace(tzinfo=UTC)
    else:
        normalized = timestamp.replace("Z", "+00:00")
        timestamp_value = datetime.fromisoformat(normalized)
        if timestamp_value.tzinfo is None:
            timestamp_value = timestamp_value.replace(tzinfo=UTC)
        timestamp_value = timestamp_value.astimezone(UTC)
    stamp = timestamp_value.strftime("%Y%m%dT%H%M%SZ")
    revision = (source_revision or _git_revision() or "unknown").strip()
    revision_part = re.sub(r"[^A-Za-z0-9]+", "", revision)[:12] or "unknown"
    return f"{base_version}-dogfood.{stamp}.g{revision_part}.{sequence}"


def dogfood_snapshot_manifest(
    base_version: str,
    base_url: str,
    *,
    source_revision: str | None = None,
    timestamp: datetime | str | None = None,
    sequence: int = 0,
    cli_artifacts: list[dict[str, Any]] | None = None,
    reused_toolchain_artifacts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    version = dogfood_snapshot_version(
        base_version,
        source_revision=source_revision,
        timestamp=timestamp,
        sequence=sequence,
    )
    artifacts: list[dict[str, Any]] = []
    toolchain_by_target = {
        _artifact_target_id(artifact): reusable_artifact_reference(artifact, expected_kind="toolchain")
        for artifact in (reused_toolchain_artifacts or [])
    }
    for artifact in cli_artifacts or []:
        cli = deepcopy(artifact)
        cli["version"] = version
        target_id = _artifact_target_id(cli)
        toolchain = toolchain_by_target.get(target_id)
        if toolchain is not None:
            cli["requires_toolchain"] = {
                "artifact_id": toolchain["id"],
                "version": toolchain.get("version"),
                "sha256": toolchain.get("sha256"),
                "reused": True,
            }
            cli["layer_update_policy"] = {
                "kind": "cli-layer",
                "toolchain_rebuild_required": False,
                "toolchain_reuse_allowed": True,
            }
        artifacts.append(cli)
    artifacts.extend(toolchain_by_target.values())
    return {
        "schema_version": 1,
        "channel": "dogfood",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "metadata_version": 1,
        "expires_at": (datetime.now(UTC).replace(microsecond=0) + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
        "trust": {
            "root_version": 1,
            "signature_policy": "single-role-v1",
            "signatures": [],
            "revoked_artifacts": [],
        },
        "releases": [
            {
                "version": version,
                "status": "active",
                "snapshot": {
                    "kind": "dogfood",
                    "base_version": base_version,
                    "source_revision": source_revision or _git_revision(),
                    "sequence": sequence,
                },
                "artifacts": artifacts,
            }
        ],
        "retention": {
            "policy": "dogfood-snapshot-window",
            "keep_latest": 12,
            "max_age_days": 14,
        },
    }


def delta_artifact_record(
    *,
    delta_id: str,
    from_artifact: dict[str, Any],
    to_artifact: dict[str, Any],
    url: str,
    sha256: str,
    size: int,
    delta_format: str = "gnustep-delta-v1",
    algorithm: str = "metadata-only",
) -> dict[str, Any]:
    target_id = _artifact_target_id(to_artifact)
    if target_id is None:
        raise ValueError("target artifact id is not target-scoped")
    if from_artifact.get("kind") != to_artifact.get("kind"):
        raise ValueError("delta source and target artifacts must have the same kind")
    if _artifact_target_id(from_artifact) != target_id:
        raise ValueError("delta source and target artifacts must have the same target")
    record = {
        "id": delta_id,
        "kind": f"{to_artifact.get('kind')}-delta",
        "version": to_artifact.get("version"),
        "os": to_artifact.get("os"),
        "arch": to_artifact.get("arch"),
        "compiler_family": to_artifact.get("compiler_family"),
        "toolchain_flavor": to_artifact.get("toolchain_flavor"),
        "objc_runtime": to_artifact.get("objc_runtime"),
        "objc_abi": to_artifact.get("objc_abi"),
        "required_features": to_artifact.get("required_features", []),
        "format": delta_format,
        "delta_format": delta_format,
        "delta_algorithm": algorithm,
        "from_artifact": from_artifact.get("id"),
        "to_artifact": to_artifact.get("id"),
        "from_sha256": from_artifact.get("sha256"),
        "to_sha256": to_artifact.get("sha256"),
        "url": url,
        "sha256": sha256,
        "integrity": {"sha256": sha256},
        "size": size,
        "target_artifact": {
            "id": to_artifact.get("id"),
            "sha256": to_artifact.get("sha256"),
            "url": to_artifact.get("url"),
            "size": to_artifact.get("size"),
        },
    }
    errors = validate_delta_artifact_record(record)
    if errors:
        raise ValueError("; ".join(errors))
    return record


def validate_delta_artifact_record(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ("id", "kind", "from_artifact", "to_artifact", "from_sha256", "to_sha256", "url", "sha256", "size", "delta_format")
    for field in required:
        if artifact.get(field) in (None, ""):
            errors.append(f"delta artifact is missing required field: {field}")
    if artifact.get("delta_format") != "gnustep-delta-v1":
        errors.append("delta artifact format must be gnustep-delta-v1")
    for field in ("from_sha256", "to_sha256", "sha256"):
        value = artifact.get(field)
        if value == "TBD":
            errors.append(f"delta artifact {field} must be concrete")
    if artifact.get("kind") not in {"cli-delta", "toolchain-delta", "package-delta", "delta"}:
        errors.append("delta artifact kind must identify a delta layer")
    return errors


def _load_reusable_artifact(path: str | Path, *, expected_kind: str, expected_target_id: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text())
    if isinstance(payload, dict) and "releases" in payload:
        for release in payload.get("releases", []):
            for artifact in release.get("artifacts", []):
                if artifact.get("kind") == expected_kind and _artifact_target_id(artifact) == expected_target_id:
                    return reusable_artifact_reference(
                        artifact,
                        expected_kind=expected_kind,
                        expected_target_id=expected_target_id,
                    )
        raise ValueError(f"no {expected_kind} artifact for {expected_target_id} found in {path}")
    if not isinstance(payload, dict):
        raise ValueError(f"reusable artifact reference must be a JSON object: {path}")
    return reusable_artifact_reference(payload, expected_kind=expected_kind, expected_target_id=expected_target_id)


def source_lock_template(target_id: str) -> dict[str, Any]:
    target = target_by_id(target_id)
    if target["strategy"] != "source-build":
        raise ValueError(f"target does not use a source lock: {target_id}")
    sources = []
    for component in target["core_components"]:
        if component not in SOURCE_COMPONENT_URLS:
            continue
        sources.append(
            {
                "name": component,
                "source_type": "git",
                "url": SOURCE_COMPONENT_URLS[component],
                "revision": PINNED_SOURCE_REVISIONS.get(component, "TBD"),
                "revision_type": "commit",
                "archive_sha256": None,
                "configure_args": [],
                "patches": [],
            }
        )
    return {
        "schema_version": 1,
        "target": {
            "id": target["id"],
            "os": target["os"],
            "arch": target["arch"],
            "compiler_family": target["compiler_family"],
            "toolchain_flavor": target["toolchain_flavor"],
        },
        "strategy": target["strategy"],
        "runtime": {
            "objc_runtime": "libobjc2" if target["compiler_family"] != "msvc" else "unknown",
            "objc_abi": "modern" if target["compiler_family"] != "msvc" else "unknown",
        },
        "components": sources,
    }


def msys2_input_manifest_template() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "target": {
            "id": "windows-amd64-msys2-clang64",
            "os": "windows",
            "arch": "amd64",
            "compiler_family": "clang",
            "toolchain_flavor": "msys2-clang64",
        },
        "strategy": "msys2-assembly",
        "repository_snapshot": "TBD",
        "installer": dict(MSYS2_INSTALLER_INPUT),
        "root_layout": {
            "install_root": "private-msys2-root",
            "preserve": ["clang64", "usr", "etc", "var/lib/pacman/local"],
            "path_policy": "Expose only <install-root>/bin by default; use private MSYS2 paths internally.",
        },
        "host_packages": [
            {
                "name": name,
                "version": "TBD",
                "sha256": "TBD",
                "source_channel": "msys2",
            }
            for name in MSYS2_HOST_PACKAGES
        ],
        "packages": [
            {
                "name": name,
                "version": "TBD",
                "sha256": "TBD",
                "source_channel": "msys2-mingw-clang64",
            }
            for name in MSYS2_PACKAGE_INPUTS
        ],
        "conflict_rules": [
            {
                "path": "clang64/include/Block.h",
                "policy": "allow-managed-overwrite",
                "reason": "Known overlap between libobjc2 and blocks runtime packaging.",
            },
            {
                "path": "clang64/include/objc/blocks_runtime.h",
                "policy": "allow-managed-overwrite",
                "reason": "Known overlap between libobjc2 and blocks runtime packaging.",
            }
        ],
    }


def toolchain_manifest(target_id: str, toolchain_version: str) -> dict[str, Any]:
    target = target_by_id(target_id)
    payload = {
        "schema_version": 1,
        "kind": "managed-toolchain",
        "toolchain_version": toolchain_version,
        "target": {
            "id": target["id"],
            "os": target["os"],
            "arch": target["arch"],
            "compiler_family": target["compiler_family"],
            "toolchain_flavor": target["toolchain_flavor"],
        },
        "runtime": {
            "objc_runtime": "libobjc2" if target["compiler_family"] != "msvc" else "unknown",
            "objc_abi": "modern" if target["compiler_family"] != "msvc" else "unknown",
            "required_features": ["blocks"] if target["compiler_family"] != "msvc" else [],
        },
        "components": target["core_components"],
        "published": target["publish"],
        "platform_policy": {
            "supported_distributions": target.get("supported_distributions", []),
            "supported_os_versions": target.get("supported_os_versions", []),
            "portability_policy": target.get("portability_policy", "platform-wide"),
            "notes": target.get("portability_notes"),
        },
        "source_policy": {
            "strategy": target["strategy"],
            "production_eligible": target["strategy"] == "source-build" or target["strategy"] == "msys2-assembly",
            "lock_file": "source-lock.json" if target["strategy"] == "source-build" else "input-manifest.json",
            "component_inventory": "component-inventory.json",
            "host_origin_paths_allowed": False,
        },
    }
    if target["id"] == "windows-amd64-msys2-clang64":
        payload["source_policy"]["assembly_input"] = "official-msys2-installer"
        payload["source_policy"]["private_root_required"] = True
        payload["developer_entrypoints"] = {
            "compiler": ["clang64/bin/clang.exe"],
            "build_shell": ["usr/bin/bash.exe", "usr/bin/sh.exe"],
            "build_driver": ["usr/bin/make.exe"],
            "checksum_tool": ["usr/bin/sha256sum.exe"],
            "gnustep_makefiles": ["clang64/share/GNUstep/Makefiles/common.make", "clang64/share/GNUstep/Makefiles/tool.make"],
            "app_launcher": ["clang64/bin/openapp"],
            "activation": ["GNUstep.ps1", "GNUstep.bat"],
        }
    return payload


def component_inventory(target_id: str, toolchain_version: str) -> dict[str, Any]:
    target = target_by_id(target_id)
    components = []
    for name in target["core_components"]:
        entry = {
            "name": name,
            "version": "TBD",
            "source": "upstream-source" if target["strategy"] == "source-build" else "curated-binary-input",
        }
        if target["strategy"] == "source-build":
            entry.update(
                {
                    "source_url": SOURCE_COMPONENT_URLS.get(name),
                    "source_revision": PINNED_SOURCE_REVISIONS.get(name, "TBD"),
                    "source_lock": "source-lock.json",
                }
            )
        elif target["id"] == "windows-amd64-msys2-clang64":
            entry.update(
                {
                    "input_manifest": "input-manifest.json",
                    "source_channel": "msys2-mingw-clang64",
                }
            )
        components.append(entry)
    return {
        "schema_version": 1,
        "target": {
            "id": target["id"],
            "os": target["os"],
            "arch": target["arch"],
            "compiler_family": target["compiler_family"],
            "toolchain_flavor": target["toolchain_flavor"],
        },
        "toolchain_version": toolchain_version,
        "platform_policy": {
            "supported_distributions": target.get("supported_distributions", []),
            "supported_os_versions": target.get("supported_os_versions", []),
            "portability_policy": target.get("portability_policy", "platform-wide"),
            "notes": target.get("portability_notes"),
        },
        "components": components,
    }


def windows_msys2_component_inventory(
    *,
    toolchain_version: str,
    packages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    target = target_by_id("windows-amd64-msys2-clang64")
    package_records = packages or [
        {
            "name": name,
            "version": "TBD",
            "package_sha256": "TBD",
            "installed_files_sha256": "TBD",
            "layer": "base",
        }
        for name in [*MSYS2_HOST_PACKAGES, *MSYS2_PACKAGE_INPUTS]
    ]
    return {
        "schema_version": 1,
        "target": {
            "id": target["id"],
            "os": target["os"],
            "arch": target["arch"],
            "compiler_family": target["compiler_family"],
            "toolchain_flavor": target["toolchain_flavor"],
        },
        "toolchain_version": toolchain_version,
        "strategy": "msys2-package-inventory",
        "packages": package_records,
    }


def compare_windows_msys2_inventories(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    old_packages = {package.get("name"): package for package in old.get("packages", []) if isinstance(package, dict)}
    new_packages = {package.get("name"): package for package in new.get("packages", []) if isinstance(package, dict)}
    added = sorted(name for name in new_packages if name not in old_packages)
    removed = sorted(name for name in old_packages if name not in new_packages)
    changed: list[dict[str, Any]] = []
    for name in sorted(set(old_packages) & set(new_packages)):
        before = old_packages[name]
        after = new_packages[name]
        if (
            before.get("version") != after.get("version")
            or before.get("package_sha256") != after.get("package_sha256")
            or before.get("installed_files_sha256") != after.get("installed_files_sha256")
        ):
            changed.append(
                {
                    "name": name,
                    "old_version": before.get("version"),
                    "new_version": after.get("version"),
                    "old_package_sha256": before.get("package_sha256"),
                    "new_package_sha256": after.get("package_sha256"),
                    "old_installed_files_sha256": before.get("installed_files_sha256"),
                    "new_installed_files_sha256": after.get("installed_files_sha256"),
                }
            )
    destructive_change = bool(removed)
    action = "reuse_existing_toolchain" if not added and not removed and not changed else ("full_toolchain_checkpoint" if destructive_change else "component_update")
    return {
        "schema_version": 1,
        "command": "compare-windows-msys2-inventories",
        "ok": True,
        "status": "ok",
        "summary": "Windows MSYS2 inventory comparison completed.",
        "action": action,
        "added_packages": added,
        "removed_packages": removed,
        "changed_packages": changed,
        "requires_full_toolchain_artifact": action == "full_toolchain_checkpoint",
        "component_replacement_sufficient": action == "component_update",
    }


_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
HOST_ORIGIN_PATH_PATTERNS = [
    "/usr/share/GNUstep",
    "/usr/include/x86_64-linux-gnu/GNUstep",
    "/usr/lib/x86_64-linux-gnu/GNUstep",
    "/usr/local/include/GNUstep",
    "/usr/local/lib/GNUstep",
    str(Path.home() / "GNUstep"),
]


def validate_source_lock(payload: dict[str, Any], *, target_id: str | None = None) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    target = target_by_id(target_id or payload.get("target", {}).get("id", ""))

    def add_error(path: str, message: str) -> None:
        errors.append({"path": path, "message": message})

    if payload.get("schema_version") != 1:
        add_error("schema_version", "source lock schema_version must be 1")
    if payload.get("strategy") != "source-build":
        add_error("strategy", "source lock strategy must be source-build")
    if payload.get("target", {}).get("id") != target["id"]:
        add_error("target.id", f"source lock target must be {target['id']}")
    components = payload.get("components")
    if not isinstance(components, list) or not components:
        add_error("components", "source lock must contain components")
        components = []
    expected = [name for name in target["core_components"] if name in SOURCE_COMPONENT_URLS]
    actual = [component.get("name") for component in components if isinstance(component, dict)]
    if actual != expected:
        add_error("components", f"source lock components must match pinned order: {', '.join(expected)}")
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            add_error(f"components[{index}]", "component entry must be an object")
            continue
        name = component.get("name")
        if name not in expected:
            add_error(f"components[{index}].name", "component is not part of the target core component set")
            continue
        if component.get("url") != SOURCE_COMPONENT_URLS[name]:
            add_error(f"components[{index}].url", "component URL must match the authoritative upstream URL")
        revision = component.get("revision")
        if not isinstance(revision, str) or not _REVISION_RE.match(revision):
            add_error(f"components[{index}].revision", "component revision must be a pinned 40-character git commit")
        if component.get("source_type") not in {"git", None}:
            add_error(f"components[{index}].source_type", "source_type must be git when present")
        if not isinstance(component.get("patches", []), list):
            add_error(f"components[{index}].patches", "patches must be a list")
        if not isinstance(component.get("configure_args", []), list):
            add_error(f"components[{index}].configure_args", "configure_args must be a list")
    return {
        "schema_version": 1,
        "command": "validate-source-lock",
        "ok": not errors,
        "status": "ok" if not errors else "error",
        "target_id": target["id"],
        "errors": errors,
    }


def validate_input_manifest(payload: dict[str, Any], *, target_id: str | None = None) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    expected_target = target_by_id(target_id or payload.get("target", {}).get("id", ""))

    def add_error(path: str, message: str) -> None:
        errors.append({"path": path, "message": message})

    if payload.get("schema_version") != 1:
        add_error("schema_version", "input manifest schema_version must be 1")
    if payload.get("strategy") != expected_target["strategy"]:
        add_error("strategy", f"input manifest strategy must be {expected_target['strategy']}")
    if payload.get("target", {}).get("id") != expected_target["id"]:
        add_error("target.id", f"input manifest target must be {expected_target['id']}")
    if expected_target["id"] == "windows-amd64-msys2-clang64":
        installer = payload.get("installer", {})
        if not isinstance(installer, dict):
            add_error("installer", "MSYS2 installer input must be recorded")
        else:
            for key in ("name", "version", "url", "sha256", "source_channel"):
                if key not in installer:
                    add_error(f"installer.{key}", f"{key} is required")
            if installer.get("source_channel") != "msys2-installer":
                add_error("installer.source_channel", "installer source_channel must be msys2-installer")
        preserve = payload.get("root_layout", {}).get("preserve", [])
        for required_path in ("clang64", "usr", "etc", "var/lib/pacman/local"):
            if required_path not in preserve:
                add_error("root_layout.preserve", f"private MSYS2 root must preserve {required_path}")
        package_names = [item.get("name") for item in payload.get("packages", []) if isinstance(item, dict)]
        host_names = [item.get("name") for item in payload.get("host_packages", []) if isinstance(item, dict)]
        if package_names != MSYS2_PACKAGE_INPUTS:
            add_error("packages", "MSYS2 package list must match the curated clang64 input set")
        if host_names != MSYS2_HOST_PACKAGES:
            add_error("host_packages", "MSYS2 host package list must match the curated input set")
        for collection_name in ("packages", "host_packages"):
            for index, item in enumerate(payload.get(collection_name, [])):
                if not isinstance(item, dict):
                    add_error(f"{collection_name}[{index}]", "package entry must be an object")
                    continue
                for key in ("name", "version", "sha256", "source_channel"):
                    if key not in item:
                        add_error(f"{collection_name}[{index}].{key}", f"{key} is required")
    return {
        "schema_version": 1,
        "command": "validate-input-manifest",
        "ok": not errors,
        "status": "ok" if not errors else "error",
        "target_id": expected_target["id"],
        "errors": errors,
    }



def _rewrite_text_files(root: Path, replacements: dict[str, str]) -> list[str]:
    rewritten: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated = content
        for old, new in replacements.items():
            if old:
                updated = updated.replace(old, new)
        if updated != content:
            path.write_text(updated, encoding="utf-8")
            rewritten.append(str(path.relative_to(root)))
    return rewritten


def normalize_source_built_toolchain_paths(toolchain_root: str | Path, build_prefix: str | Path) -> dict[str, Any]:
    root = Path(toolchain_root).resolve()
    prefix = Path(build_prefix).resolve()
    user_gnustep = Path.home() / "GNUstep"
    replacements = {
        str(prefix): MANAGED_PREFIX_PLACEHOLDER,
        str(user_gnustep / "Library" / "Headers"): f"{MANAGED_PREFIX_PLACEHOLDER}/Library/Headers",
        str(user_gnustep / "Library" / "Libraries"): f"{MANAGED_PREFIX_PLACEHOLDER}/Library/Libraries",
        str(user_gnustep / "Tools"): f"{MANAGED_PREFIX_PLACEHOLDER}/Tools",
        str(user_gnustep / "Applications"): f"{MANAGED_PREFIX_PLACEHOLDER}/Applications",
    }
    rewritten = _rewrite_text_files(root, replacements)
    patched_files: list[str] = []
    base_make = root / "System" / "Library" / "Makefiles" / "Additional" / "base.make"
    if base_make.exists():
        content = base_make.read_text(encoding="utf-8")
        updated = content.replace("FND_LIBS = -lgnustep-base", "FND_LIBS = -lgnustep-base -ldispatch -lBlocksRuntime")
        if updated != content:
            base_make.write_text(updated, encoding="utf-8")
            patched_files.append(str(base_make.relative_to(root)))
    for pc in (
        root / "Local" / "Library" / "Libraries" / "pkgconfig" / "gnustep-base.pc",
        root / "Local" / "Library" / "Libraries" / "pkgconfig" / "gnustep-gui.pc",
    ):
        if pc.exists():
            content = pc.read_text(encoding="utf-8")
            lines = []
            changed = False
            for line in content.splitlines():
                if line.startswith("Libs:") and "-ldispatch" not in line:
                    line = line + " -ldispatch -lBlocksRuntime"
                    changed = True
                lines.append(line)
            if changed:
                pc.write_text("\n".join(lines) + "\n", encoding="utf-8")
                patched_files.append(str(pc.relative_to(root)))
    return {
        "schema_version": 1,
        "command": "normalize-source-built-toolchain-paths",
        "ok": True,
        "status": "ok",
        "toolchain_root": str(root),
        "build_prefix": str(prefix),
        "placeholder": MANAGED_PREFIX_PLACEHOLDER,
        "rewritten_files": rewritten,
        "patched_files": patched_files,
    }


def toolchain_tree_host_origin_audit(toolchain_root: str | Path) -> dict[str, Any]:
    root = Path(toolchain_root).resolve()
    findings: list[dict[str, str]] = []
    if not root.exists():
        return {
            "schema_version": 1,
            "command": "toolchain-host-origin-audit",
            "ok": False,
            "status": "error",
            "summary": "Toolchain root is missing.",
            "toolchain_root": str(root),
            "findings": [{"path": str(root), "pattern": "missing"}],
        }
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if "System/Sysroot" in path.as_posix():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in HOST_ORIGIN_PATH_PATTERNS:
            if pattern and pattern in content:
                findings.append(
                    {
                        "path": str(path.relative_to(root)),
                        "pattern": pattern,
                    }
                )
    return {
        "schema_version": 1,
        "command": "toolchain-host-origin-audit",
        "ok": not findings,
        "status": "ok" if not findings else "error",
        "summary": "No host-origin GNUstep paths found." if not findings else "Host-origin GNUstep paths found.",
        "toolchain_root": str(root),
        "patterns": HOST_ORIGIN_PATH_PATTERNS,
        "findings": findings,
    }


def write_toolchain_metadata(output_root: str | Path, target_id: str, toolchain_version: str, *, production_eligible: bool) -> dict[str, Any]:
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = target_by_id(target_id)
    written: dict[str, str] = {}
    if target["strategy"] == "source-build":
        source_lock = source_lock_template(target_id)
        validation = validate_source_lock(source_lock, target_id=target_id)
        if not validation["ok"]:
            raise ValueError(f"invalid source lock for {target_id}: {validation['errors']}")
        path = root / "source-lock.json"
        path.write_text(json.dumps(source_lock, indent=2) + "\n", encoding="utf-8")
        written["source_lock"] = str(path)
    elif target["id"] == "windows-amd64-msys2-clang64":
        input_manifest = msys2_input_manifest_template()
        validation = validate_input_manifest(input_manifest, target_id=target_id)
        if not validation["ok"]:
            raise ValueError(f"invalid input manifest for {target_id}: {validation['errors']}")
        path = root / "input-manifest.json"
        path.write_text(json.dumps(input_manifest, indent=2) + "\n", encoding="utf-8")
        written["input_manifest"] = str(path)
    inventory_path = root / "component-inventory.json"
    inventory_path.write_text(json.dumps(component_inventory(target_id, toolchain_version), indent=2) + "\n", encoding="utf-8")
    written["component_inventory"] = str(inventory_path)
    manifest = toolchain_manifest(target_id, toolchain_version)
    manifest["source_policy"]["production_eligible"] = production_eligible
    manifest_path = root / "toolchain-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    written["toolchain_manifest"] = str(manifest_path)
    return {
        "schema_version": 1,
        "command": "write-toolchain-metadata",
        "ok": True,
        "status": "ok",
        "target_id": target_id,
        "toolchain_version": toolchain_version,
        "production_eligible": production_eligible,
        "written": written,
    }


def _unix_source_build_script(target_id: str, prefix: str, sources_dir: str, build_root: str, *, host_os: str) -> str:
    target = target_by_id(target_id)
    if target["strategy"] != "source-build":
        raise ValueError(f"target does not use a source build strategy: {target_id}")
    source_lock = source_lock_template(target_id)
    jobs_expr = '$(getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)'
    lines = [
        "#!/bin/sh",
        "set -eu",
        "",
        f'PREFIX="{prefix}"',
        f'SOURCES_DIR="{sources_dir}"',
        f'BUILD_ROOT="{build_root}"',
        f'HOST_OS="{host_os}"',
        f'JOBS="{jobs_expr}"',
        "",
        'mkdir -p "$PREFIX" "$SOURCES_DIR" "$BUILD_ROOT"',
        "",
    ]
    for component in source_lock["components"]:
        lines.extend(
            [
                f'if [ ! -d "$SOURCES_DIR/{component["name"]}/.git" ]; then',
                f'  git clone "{component["url"]}" "$SOURCES_DIR/{component["name"]}"',
                "fi",
                f'git -C "$SOURCES_DIR/{component["name"]}" fetch --tags origin',
                f'git -C "$SOURCES_DIR/{component["name"]}" checkout --detach "{component["revision"]}"',
                "",
            ]
        )
    lines.extend(
        [
            'case "$HOST_OS" in',
            '  linux)',
            '    : "${MAKE:=make}"',
            '    export MAKE',
            '    ;;',
            '  openbsd)',
            '    export MAKE=gmake',
            '    export PKG_CONFIG=pkg-config',
            '    export AUTOCONF_VERSION=${AUTOCONF_VERSION:-2.72}',
            '    export AUTOMAKE_VERSION=${AUTOMAKE_VERSION:-1.17}',
            '    ;;',
            'esac',
            "",
            'cd "$SOURCES_DIR/libobjc2"',
            'rm -rf build',
            'cmake -S . -B build \\',
            '  -DCMAKE_BUILD_TYPE=RelWithDebInfo \\',
            '  -DCMAKE_INSTALL_PREFIX="$PREFIX" \\',
            '  -DCMAKE_C_COMPILER=clang \\',
            '  -DCMAKE_CXX_COMPILER=clang++ \\',
            '  -DCMAKE_OBJC_COMPILER=clang \\',
            '  -DCMAKE_OBJCXX_COMPILER=clang++ \\',
            '  -DGNUSTEP_INSTALL_TYPE=NONE \\',
            '  -DEMBEDDED_BLOCKS_RUNTIME=ON',
            'cmake --build build -j"$JOBS"',
            'cmake --install build',
            "",
            'cd "$SOURCES_DIR/libdispatch"',
            'rm -rf build',
            'cmake -S . -B build -G Ninja \\',
            '  -DCMAKE_BUILD_TYPE=RelWithDebInfo \\',
            '  -DCMAKE_INSTALL_PREFIX="$PREFIX" \\',
            '  -DCMAKE_C_COMPILER=clang \\',
            '  -DCMAKE_CXX_COMPILER=clang++ \\',
            '  -DCMAKE_PREFIX_PATH="$PREFIX" \\',
            '  -DBUILD_TESTING=OFF',
            'cmake --build build -j"$JOBS"',
            'cmake --install build',
            "",
            'export CC=clang',
            'export CXX=clang++',
            'export OBJC=clang',
            'export OBJCXX=clang++',
            'export PATH="$PREFIX/System/Tools:$PREFIX/bin:$PATH"',
            'export LD_LIBRARY_PATH="$PREFIX/lib:$PREFIX/lib64:${LD_LIBRARY_PATH:-}"',
            'export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:$PREFIX/lib64/pkgconfig:${PKG_CONFIG_PATH:-}"',
            'export CPPFLAGS="-I$PREFIX/include ${CPPFLAGS:-}"',
            'export CFLAGS="-I$PREFIX/include ${CFLAGS:-}"',
            'export CXXFLAGS="-I$PREFIX/include ${CXXFLAGS:-}"',
            'export OBJCFLAGS="-I$PREFIX/include ${OBJCFLAGS:-}"',
            'export OBJCXXFLAGS="-I$PREFIX/include ${OBJCXXFLAGS:-}"',
            'export LDFLAGS="-L$PREFIX/lib -L$PREFIX/lib64 ${LDFLAGS:-}"',
            "",
            'cd "$SOURCES_DIR/tools-make"',
            './configure --prefix="$PREFIX" --with-layout=gnustep --enable-native-objc-exceptions --enable-objc-arc --with-library-combo=ng-gnu-gnu',
            '"${MAKE:-make}" -j"$JOBS"',
            '"${MAKE:-make}" install',
            "",
            'export GNUSTEP_SYSTEM_ROOT="$PREFIX/System"',
            'export GNUSTEP_LOCAL_ROOT="$PREFIX/Local"',
            'export GNUSTEP_NETWORK_ROOT="$PREFIX/Network"',
            'export GNUSTEP_MAKEFILES="$PREFIX/System/Library/Makefiles"',
            'set +u',
            '. "$GNUSTEP_MAKEFILES/GNUstep.sh"',
            'set -u',
            'unset GNUSTEP_SYSTEM_ROOT GNUSTEP_LOCAL_ROOT GNUSTEP_NETWORK_ROOT',
            "",
            '# Expose the managed Objective-C runtime headers through the GNUstep header domain.',
            'mkdir -p "$PREFIX/Local/Library/Headers"',
            'ln -sfn "$PREFIX/include/objc" "$PREFIX/Local/Library/Headers/objc"',
            'cp -f "$PREFIX/include/Block.h" "$PREFIX/Local/Library/Headers/Block.h"',
            'cp -f "$PREFIX/include/Block_private.h" "$PREFIX/Local/Library/Headers/Block_private.h"',
            "",
            'for lib in libs-base libs-corebase libs-gui libs-back; do',
            '  cd "$SOURCES_DIR/$lib"',
            '  "${MAKE:-make}" distclean >/dev/null 2>&1 || true',
            '  ./configure --prefix="$PREFIX"',
            '  "${MAKE:-make}" -j"$JOBS"',
            '  "${MAKE:-make}" install',
            'done',
            "",
            'printf "%s\\n" "$HOST_OS managed toolchain build completed at $PREFIX"',
            "",
        ]
    )
    return "\n".join(lines)


def linux_build_script(target_id: str, prefix: str, sources_dir: str, build_root: str) -> str:
    target = target_by_id(target_id)
    if target["os"] != "linux" or target["strategy"] != "source-build":
        raise ValueError(f"linux build script is only supported for source-built linux targets: {target_id}")
    return _unix_source_build_script(target_id, prefix, sources_dir, build_root, host_os="linux")


def openbsd_build_script(target_id: str, prefix: str, sources_dir: str, build_root: str) -> str:
    target = target_by_id(target_id)
    if target["os"] != "openbsd" or target["strategy"] != "source-build":
        raise ValueError(f"openbsd build script is only supported for source-built openbsd targets: {target_id}")
    return _unix_source_build_script(target_id, prefix, sources_dir, build_root, host_os="openbsd")


def msys2_assembly_script(prefix: str, cache_dir: str) -> str:
    packages = " ".join(MSYS2_PACKAGE_INPUTS)
    host_packages = " ".join(MSYS2_HOST_PACKAGES)
    developer_binaries = "', '".join(MSYS2_DEVELOPER_BINARIES)
    lines = [
        "[CmdletBinding()]",
        "param(",
        f'  [string]$Prefix = "{prefix}",',
        f'  [string]$CacheDir = "{cache_dir}",',
        "  [string]$MsysRoot = '',",
        f'  [string]$InstallerUrl = "{MSYS2_INSTALLER_INPUT["url"]}"',
        ")",
        "",
        "$ErrorActionPreference = 'Stop'",
        "$ProgressPreference = 'SilentlyContinue'",
        "",
        "New-Item -ItemType Directory -Force -Path $Prefix | Out-Null",
        "New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null",
        "if (-not $MsysRoot) {",
        "  $MsysRoot = $Prefix",
        "}",
        "$prefixFull = [System.IO.Path]::GetFullPath($Prefix).TrimEnd('\\')",
        "$msysRootFull = [System.IO.Path]::GetFullPath($MsysRoot).TrimEnd('\\')",
        "$installingIntoManagedRoot = [string]::Equals($prefixFull, $msysRootFull, [System.StringComparison]::OrdinalIgnoreCase)",
        "",
        "$bash = Join-Path $MsysRoot 'usr\\bin\\bash.exe'",
        "$installer = Join-Path $CacheDir 'msys2-x86_64-latest.exe'",
        "",
        "if (-not (Test-Path $bash)) {",
        "  Invoke-WebRequest -UseBasicParsing -Uri $InstallerUrl -OutFile $installer",
        "  & $installer in --confirm-command --accept-messages --root ($MsysRoot -replace '\\\\', '/')",
        "}",
        "",
        "if (-not (Test-Path $bash)) {",
        "  throw 'MSYS2 installation did not produce bash.exe at the expected path.'",
        "}",
        "",
        "$env:CHERE_INVOKING = '1'",
        "$pacmanLock = Join-Path $MsysRoot 'var\\lib\\pacman\\db.lck'",
        "if (Test-Path $pacmanLock) {",
        "  Remove-Item -Force $pacmanLock -ErrorAction SilentlyContinue",
        "}",
        "",
        '& $bash -lc "true"',
        "if ($LASTEXITCODE -ne 0) { throw 'MSYS2 shell bootstrap command failed.' }",
        '& $bash -lc "pacman -Syuu --noconfirm || true"',
        "if ($LASTEXITCODE -ne 0) { throw 'MSYS2 package database refresh failed.' }",
        f'& $bash -lc "pacman -S --noconfirm --needed {host_packages}"',
        "if ($LASTEXITCODE -ne 0) { throw 'MSYS2 host-package installation failed.' }",
        f'& $bash -lc "pacman -S --overwrite /clang64/include/Block.h --noconfirm --needed {packages}"',
        "if ($LASTEXITCODE -ne 0) { throw 'MSYS2 GNUstep package installation failed.' }",
        '& $bash -lc "pacman -Qkk"',
        "if ($LASTEXITCODE -ne 0) { throw 'MSYS2 local package database integrity check failed.' }",
        "",
        "$clangRoot = Join-Path $MsysRoot 'clang64'",
        "if (-not (Test-Path $clangRoot)) {",
        "  throw 'MSYS2 clang64 root not found after package installation.'",
        "}",
        "",
        "$toolDirs = @('bin','etc','include','lib','libexec','share')",
        "$clangPrefix = Join-Path $Prefix 'clang64'",
        "New-Item -ItemType Directory -Force -Path $clangPrefix | Out-Null",
        "foreach ($entry in $toolDirs) {",
        "  $source = Join-Path $clangRoot $entry",
        "  if (Test-Path $source) {",
        "    $destination = Join-Path $clangPrefix $entry",
        "    if (-not [string]::Equals([System.IO.Path]::GetFullPath($source).TrimEnd('\\'), [System.IO.Path]::GetFullPath($destination).TrimEnd('\\'), [System.StringComparison]::OrdinalIgnoreCase)) {",
        "      Copy-Item -Recurse -Force $source $destination",
        "    }",
        "  }",
        "}",
        "",
        "$msysRootDirs = @('usr','etc','var')",
        "foreach ($entry in $msysRootDirs) {",
        "  $source = Join-Path $MsysRoot $entry",
        "  if (Test-Path $source) {",
        "    $destination = Join-Path $Prefix $entry",
        "    if (-not [string]::Equals([System.IO.Path]::GetFullPath($source).TrimEnd('\\'), [System.IO.Path]::GetFullPath($destination).TrimEnd('\\'), [System.StringComparison]::OrdinalIgnoreCase)) {",
        "      Copy-Item -Recurse -Force $source $destination",
        "    }",
        "  }",
        "}",
        "",
        "# Compatibility links for older activation code. The canonical MSYS2 layout is",
        "# <prefix>\\clang64 plus <prefix>\\usr, but these root-level directories keep",
        "# existing release smoke scripts working while callers move to clang64 paths.",
        "foreach ($entry in $toolDirs) {",
        "  $source = Join-Path $clangRoot $entry",
        "  if (Test-Path $source) {",
        "    $destination = Join-Path $Prefix $entry",
        "    if (-not [string]::Equals([System.IO.Path]::GetFullPath($source).TrimEnd('\\'), [System.IO.Path]::GetFullPath($destination).TrimEnd('\\'), [System.StringComparison]::OrdinalIgnoreCase)) {",
        "      Copy-Item -Recurse -Force $source $destination",
        "    }",
        "  }",
        "}",
        "",
        "$developerBin = Join-Path $Prefix 'usr\\bin'",
        "New-Item -ItemType Directory -Force -Path $developerBin | Out-Null",
        f"$developerTools = @('{developer_binaries}')",
        "foreach ($tool in $developerTools) {",
        "  $source = Join-Path $MsysRoot ('usr\\\\bin\\\\' + $tool)",
        "  if (-not (Test-Path $source)) {",
        "    throw ('Required MSYS2 developer tool is missing: ' + $source)",
        "  }",
        "  $destination = Join-Path $developerBin $tool",
        "  if (-not [string]::Equals([System.IO.Path]::GetFullPath($source), [System.IO.Path]::GetFullPath($destination), [System.StringComparison]::OrdinalIgnoreCase)) {",
        "    Copy-Item -Force $source $destination",
        "  }",
        "}",
        "$developerRuntimeFiles = Get-ChildItem -Path (Join-Path $MsysRoot 'usr\\bin') -File | Where-Object { $_.Extension -in @('.exe', '.dll') }",
        "if ($developerRuntimeFiles.Count -eq 0) {",
        "  throw 'No MSYS2 usr\\bin executable/DLL runtime files were found for developer tools.'",
        "}",
        "foreach ($runtimeFile in $developerRuntimeFiles) {",
        "  $destination = Join-Path $developerBin $runtimeFile.Name",
        "  if (-not [string]::Equals([System.IO.Path]::GetFullPath($runtimeFile.FullName), [System.IO.Path]::GetFullPath($destination), [System.StringComparison]::OrdinalIgnoreCase)) {",
        "    Copy-Item -Force $runtimeFile.FullName $destination",
        "  }",
        "}",
        "",
        "$activateBat = @(",
        "  '@echo off',",
        "  'set GNUSTEP_MAKEFILES=%~dp0clang64\\share\\GNUstep\\Makefiles',",
        "  'set GNUSTEP_CONFIG_FILE=%~dp0clang64\\etc\\GNUstep\\GNUstep.conf',",
        "  'set PATH=%~dp0clang64\\bin;%~dp0bin;%~dp0usr\\bin;%PATH%'",
        ")",
        "Set-Content -Path (Join-Path $Prefix 'GNUstep.bat') -Value $activateBat -Encoding ASCII",
        "",
        "$activatePs1 = @(",
        "  '$prefix = Split-Path -Parent $MyInvocation.MyCommand.Path',",
        "  '$env:GNUSTEP_MAKEFILES = Join-Path $prefix ''clang64\\share\\GNUstep\\Makefiles''',",
        "  '$env:GNUSTEP_CONFIG_FILE = Join-Path $prefix ''clang64\\etc\\GNUstep\\GNUstep.conf''',",
        "  '$env:PATH = (Join-Path $prefix ''clang64\\bin'') + '';'' + (Join-Path $prefix ''bin'') + '';'' + (Join-Path $prefix ''usr\\bin'') + '';'' + $env:PATH'",
        ")",
        "Set-Content -Path (Join-Path $Prefix 'GNUstep.ps1') -Value $activatePs1 -Encoding ASCII",
        "",
        'Write-Host "MSYS2 managed toolchain assembly completed at $Prefix"',
    ]
    return "\n".join(lines) + "\n"


def msvc_status() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "target": {
            "id": "windows-amd64-msvc",
            "os": "windows",
            "arch": "amd64",
            "compiler_family": "msvc",
            "toolchain_flavor": "msvc",
        },
        "publish": False,
        "status": "deferred_for_v1",
        "summary": "The MSVC managed toolchain remains tracked, but it is explicitly deferred for the v0.1.x line and is not validated or published.",
        "blocking_areas": [
            "libdispatch viability under the MSVC stack is not yet proven",
            "the GNUstep runtime and library build pipeline for MSVC is not implemented in this repository",
            "no validated managed artifact or live-validation evidence exists yet",
        ],
        "next_steps": [
            "keep MSVC documented as a deferred target until a dedicated build pipeline exists",
            "prototype libobjc2/tools-make/libs-base/libs-gui/libs-back builds under an MSVC-oriented environment",
            "add live-validation evidence before changing publish status",
        ],
    }


def toolchain_plan(target_id: str) -> dict[str, Any]:
    target = target_by_id(target_id)
    plan: dict[str, Any] = {
        "schema_version": 1,
        "target": target,
        "published": target["publish"],
        "steps": [],
        "validation": [],
    }
    if target["strategy"] == "source-build":
        plan["steps"] = [
            {"id": "prepare-host", "title": "Prepare bootstrap compiler and build host"},
            {"id": "fetch-sources", "title": "Fetch pinned upstream source set"},
            {"id": "build-components", "title": "Build managed GNUstep components into a staging prefix"},
            {"id": "archive-toolchain", "title": "Archive the staged managed toolchain"},
            {"id": "emit-metadata", "title": "Write source lock, component inventory, and checksums"},
        ]
    else:
        plan["steps"] = [
            {"id": "prepare-host", "title": "Prepare assembly host and package cache"},
            {"id": "fetch-packages", "title": "Fetch pinned MSYS2 package inputs"},
            {"id": "normalize-layout", "title": "Normalize package contents into the managed install layout"},
            {"id": "archive-toolchain", "title": "Archive the staged managed toolchain"},
            {"id": "emit-metadata", "title": "Write input manifest, component inventory, and checksums"},
        ]
    plan["validation"] = [
        {"id": "doctor", "title": "Run doctor against the staged managed toolchain"},
        {"id": "compile-probe", "title": "Compile and link a minimal Objective-C probe"},
        {"id": "build-fixture", "title": "Build a minimal GNUstep Make fixture project"},
    ]
    if target["os"] == "windows":
        plan["validation"].append({"id": "otvm-smoke", "title": "Validate bootstrap and install smoke path on an otvm Windows lease"})
        plan["validation"].extend(
            [
                {"id": "gui-smoke", "title": "Launch a minimal AppKit window and verify a nonblank screenshot"},
                {"id": "gorm-build", "title": "Build Gorm with the managed MSYS2 clang64 toolchain"},
                {"id": "gorm-run", "title": "Launch Gorm through managed GNUstep.sh/openapp and verify menu, inspector, and palette windows by screenshot"},
            ]
        )
    return plan


def debian_gcc_interop_plan() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "command": "debian-gcc-interop-plan",
        "ok": True,
        "status": "ok",
        "summary": "Debian GCC interoperability validation plan generated.",
        "host_requirements": {
            "provider": "otvm-or-equivalent",
            "os": "linux",
            "distribution": "debian",
            "toolchain_profile": "stock-gnu-gcc-gnustep",
            "lifetime": "disposable",
        },
        "goal": (
            "Verify that the Objective-C full CLI can still be built in a stock Debian GCC-based "
            "GNUstep environment as an interoperability check."
        ),
        "constraints": [
            "Treat this as GCC interoperability evidence, not as a managed Tier 1 artifact target.",
            "Use Debian-provided GNUstep packages rather than the managed Clang toolchain.",
            "Destroy the leased or disposable host after validation completes.",
        ],
        "steps": [
            {
                "id": "prepare-host",
                "title": "Provision disposable Debian host",
                "details": "Create a short-lived Debian lease or equivalent disposable VM with shell access.",
            },
            {
                "id": "install-packages",
                "title": "Install Debian GNUstep and build prerequisites",
                "details": (
                    "Install clang-free Debian packages needed to build the full CLI, such as gcc, gobjc, "
                    "gnustep-make, libgnustep-base-dev, libgnustep-gui-dev, libgnustep-back-dev, and make."
                ),
            },
            {
                "id": "source-gnu-environment",
                "title": "Load the GNUstep Make environment",
                "details": "Source the GNUstep environment script so GNUSTEP_MAKEFILES and related variables are available.",
            },
            {
                "id": "build-full-cli",
                "title": "Build the Objective-C full CLI",
                "details": "Run make in src/full-cli and capture stdout/stderr plus the compiler identity.",
            },
            {
                "id": "smoke-cli",
                "title": "Smoke-test the built CLI",
                "details": "Run the built gnustep binary with --help, --version, and doctor --json.",
            },
            {
                "id": "record-evidence",
                "title": "Record interoperability evidence",
                "details": "Persist package versions, compiler version, command output, and any known GCC-specific limitations.",
            },
        ],
        "evidence": [
            "dpkg package list for GNUstep-related packages",
            "gcc --version output",
            "make output from src/full-cli",
            "CLI smoke-test output",
        ],
    }


def native_linux_validation_plan(distribution: str) -> dict[str, Any]:
    if distribution not in {"fedora", "arch"}:
        raise ValueError(f"unsupported linux native validation target: {distribution}")

    package_hint = (
        "dnf install clang gnustep-make gnustep-base-devel gnustep-gui-devel gnustep-back"
        if distribution == "fedora"
        else "pacman -S --needed clang gnustep-make gnustep-base gnustep-gui gnustep-back"
    )
    host_hint = "Fedora disposable VM or container host" if distribution == "fedora" else "Arch disposable VM or container host"
    return {
        "schema_version": 1,
        "command": "linux-native-validation-plan",
        "ok": True,
        "status": "ok",
        "distribution": distribution,
        "summary": f"{distribution.capitalize()} native GNUstep validation plan generated.",
        "host_requirements": {
            "provider": "disposable-vm-or-equivalent",
            "os": "linux",
            "distribution": distribution,
            "toolchain_profile": "packaged-clang-gnustep",
            "lifetime": "disposable",
        },
        "goal": (
            f"Validate that the packaged {distribution.capitalize()} Clang/libobjc2 GNUstep environment is sufficient "
            "for the supported native doctor/setup/install/remove workflows."
        ),
        "constraints": [
            "Use the distro-packaged GNUstep environment rather than the managed toolchain.",
            "Capture exact package versions and compiler identity as evidence.",
            "Destroy the disposable validation host after evidence is recorded.",
        ],
        "steps": [
            {
                "id": "prepare-host",
                "title": "Provision disposable validation host",
                "details": f"Create a short-lived {host_hint} with shell access and outbound network access.",
            },
            {
                "id": "install-packages",
                "title": "Install packaged GNUstep prerequisites",
                "details": package_hint,
            },
            {
                "id": "run-doctor",
                "title": "Run doctor and capture classification",
                "details": "Run gnustep doctor --json and record the native_toolchain_assessment plus compatibility details.",
            },
            {
                "id": "run-setup",
                "title": "Run setup and confirm native path selection",
                "details": "Run gnustep setup --json and confirm install_mode=native with use_existing_toolchain disposition.",
            },
            {
                "id": "package-flow",
                "title": "Validate package install/remove flow",
                "details": "Install a reviewed package from a generated index, verify its selected artifact, then remove it cleanly.",
            },
            {
                "id": "record-evidence",
                "title": "Record validation evidence",
                "details": "Persist package versions, compiler version, doctor/setup JSON, and package install/remove output.",
            },
        ],
        "evidence": [
            f"{distribution} package list for GNUstep-related packages",
            "clang --version output",
            "doctor --json payload",
            "setup --json payload",
            "package install/remove JSON output",
        ],
    }


def current_support_matrix() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "command": "support-matrix",
        "ok": True,
        "status": "ok",
        "summary": "Current release support matrix snapshot generated.",
        "targets": [
            {
                "id": "openbsd-amd64-clang",
                "os": "openbsd",
                "arch": "amd64",
                "toolchain_model": "packaged-clang-libobjc2",
                "status": "validated_native_preferred",
                "evidence_status": "validated",
                "notes": "Packaged OpenBSD GNUstep is currently treated as the preferred native path when compatibility checks pass, fresh libvirt host evidence was rerun on April 14, 2026 with the ~/.ssh/otvm operator keypair, and an April 17, 2026 fresh lease built the current full CLI and passed native package install/remove smoke after OpenBSD OS detection was fixed.",
            },
            {
                "id": "fedora-amd64-clang",
                "os": "linux",
                "distribution": "fedora",
                "arch": "amd64",
                "toolchain_model": "packaged-clang-libobjc2",
                "status": "interoperability_only",
                "evidence_status": "validated",
                "notes": "Fresh libvirt evidence from April 16, 2026 shows Fedora packaged GNUstep builds and runs the CLI through GCC/libobjc interoperability, not the preferred Clang/libobjc2 stack. Managed Clang support is blocked until a distro-scoped artifact or dependency closure exists.",
            },
            {
                "id": "debian-amd64-gcc",
                "os": "linux",
                "distribution": "debian",
                "arch": "amd64",
                "toolchain_model": "packaged-gcc-gnustep",
                "status": "interoperability_only",
                "evidence_status": "validated",
                "notes": "Debian remains primarily a GCC interoperability target unless a validated packaged Clang/libobjc2 path is proven, and fresh libvirt host evidence was rerun on April 14, 2026 with the ~/.ssh/otvm operator keypair.",
            },
            {
                "id": "debian-arm64-managed-clang",
                "os": "linux",
                "distribution": "debian",
                "arch": "arm64",
                "toolchain_model": "managed-clang-libobjc2",
                "status": "planned_build_target",
                "evidence_status": "not_started",
                "notes": "Planned Debian aarch64 managed target for the full CLI and official packages. Build and validation should use ../OracleTestVMs local libvirt/mac capacity first and fall back to OCI only when local capacity is unavailable.",
            },
            {
                "id": "arch-amd64-clang",
                "os": "linux",
                "distribution": "arch",
                "arch": "amd64",
                "toolchain_model": "packaged-clang-libobjc2",
                "status": "interoperability_only",
                "evidence_status": "validated",
                "notes": "Fresh libvirt evidence from April 16, 2026 shows Arch packaged GNUstep builds and runs the CLI through GCC/libobjc interoperability, not the preferred Clang/libobjc2 stack. Managed Clang support is blocked until a distro-scoped artifact or dependency closure exists.",
            },
            {
                "id": "openbsd-arm64-clang",
                "os": "openbsd",
                "arch": "arm64",
                "toolchain_model": "packaged-or-managed-clang-libobjc2",
                "status": "planned_build_target",
                "evidence_status": "not_started",
                "notes": "Planned OpenBSD arm64 target for the full CLI and official packages. Use the available OpenBSD arm64 server for initial build/validation evidence before enabling publication.",
            },
            {
                "id": "windows-amd64-msys2-clang64",
                "os": "windows",
                "arch": "amd64",
                "toolchain_model": "managed-msys2-clang64",
                "status": "managed_target_staged_artifacts_validated",
                "evidence_status": "validated_staged_release_artifacts",
                "notes": "April 17, 2026 Windows libvirt evidence shows the checked-in MSYS2 assembly path can stage clang64 GNUstep tooling, rebuild the full Objective-C CLI, pass --version/--help, and complete native package install/remove with SHA-256 verification. A later clean Windows lease qualified the refreshed staged release ZIPs directly with version/help plus package install/remove smoke. The GitHub prerelease assets have been published, digest-verified, made public, and now include signed provenance metadata. Follow-up public-manifest bootstrap setup passed in direct-process diagnostic mode with retained JSONL trace evidence; the extracted toolchain rebuilt the Objective-C CLI and doctor --json passed against an explicit local Windows manifest. Remaining work is automated published-URL release qualification and production trust-root handling.",
            },
            {
                "id": "windows-amd64-msvc",
                "os": "windows",
                "arch": "amd64",
                "toolchain_model": "managed-msvc",
                "status": "deferred",
                "evidence_status": "not_started",
                "notes": "MSVC remains explicitly deferred for v0.1.x.",
            },
        ],
        "deferred_discovery_targets": ["openSUSE", "RHEL-family", "Alpine"],
    }


def release_candidate_qualification_status() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "command": "release-candidate-qualification",
        "ok": True,
        "status": "ok",
        "summary": "Release-candidate qualification status snapshot generated.",
        "phase_status": [
            {
                "phase": "12",
                "name": "Official build infrastructure",
                "status": "completed_for_local_release_tooling",
                "remaining": [
                    "Provision CI-owned production release and package-index signing keys or a signing service.",
                    "Move host-backed qualification from operator-run lanes to release automation.",
                    "Promote package artifact build plans into controlled CI build jobs that emit signed artifacts.",
                    "Run production-channel expiry, rollback, revocation, and key-rotation drills with production-like trust roots.",
                ],
            },
            {
                "phase": "13",
                "name": "Upgrade, repair, and lifecycle operations",
                "status": "completed_for_native_dogfood",
                "remaining": [
                    "Dogfood old-to-new updates against two real published update-capable releases.",
                    "Run update-all application against a release containing both CLI/toolchain and package updates.",
                    "Exercise final key-mismatch and signed-metadata failure cases with production-like trust roots.",
                ],
            },
            {
                "phase": "14",
                "name": "Cross-platform integration polish",
                "status": "completed_for_current_command_surface",
                "remaining": [
                    "Continue replacing transitional repository Python helpers where they still define future shipped behavior.",
                    "Expand native Objective-C command tests as command behavior moves out of shared tooling.",
                    "Automate live Windows and Unix release smoke lanes instead of relying on manual evidence capture.",
                ],
            },
            {
                "phase": "18",
                "name": "Full GNUstep CLI implementation and build",
                "status": "completed_for_linux_amd64_and_staged_cross_platform_artifacts",
                "remaining": [
                    "Build and qualify every final Tier 1 full-CLI artifact from the production build lanes.",
                    "Keep the no-bundled-Python release gate mandatory for every shipped full-CLI artifact.",
                    "Complete native doctor deep-detection parity before claiming full native diagnostic replacement.",
                ],
            },
        ],
        "artifact_checks": [
            {
                "id": "regression-gate",
                "status": "completed",
                "notes": "Python/shared and native Objective-C tools-xctest suites are green.",
            },
            {
                "id": "bootstrap-to-full-handoff",
                "status": "completed",
                "notes": "Qualification checks installed binary, runtime bundle, no-bundled-Python state, and CLI state health.",
            },
            {
                "id": "release-package-index-sync",
                "status": "completed",
                "notes": "Committed package index is checked against generated output in CI.",
            },
            {
                "id": "artifact-package-flow-smoke",
                "status": "completed_for_staged_artifacts",
                "notes": "Package-flow smoke behavior is covered in Python and native tests. Debian libvirt host validation passed against staged release artifacts, Debian dogfood covers managed compile/run plus new/build/run and package install/remove, April 17, 2026 Debian published-URL bootstrap/full-CLI/package qualification passed from the public GitHub manifest, and Windows validation completed native package install/remove, refreshed staged release-artifact package-flow smoke, public-manifest setup with trace evidence, and extracted-toolchain rebuild/doctor qualification.",
            },
            {
                "id": "package-index-trust-gate",
                "status": "completed",
                "notes": "Generated package indexes carry trust metadata; tooling emits provenance, supports OpenSSL signatures, and can verify against an explicit trusted public key for production gates.",
            },
            {
                "id": "release-trust-root-gate",
                "status": "completed_for_tooling",
                "notes": "Release metadata trust-gate verification supports an externally pinned public key; production remains blocked on CI-owned key material and rotation policy.",
            },
        ],
        "live_host_checks": [
            {
                "id": "openbsd-native-qualification",
                "status": "completed",
                "blocked": False,
                "notes": "OpenBSD libvirt preflight and live acceptance were rerun successfully on April 14, 2026 using the ~/.ssh/otvm operator keypair, a fresh lease passed pkg_add plus Foundation compile-link-run validation, and an April 17, 2026 fresh lease built the current full CLI and passed native package install/remove smoke.",
            },
            {
                "id": "fedora-native-qualification",
                "status": "completed",
                "blocked": False,
                "blocked_by": None,
                "notes": "Fedora libvirt preflight, acceptance, native CLI build, and package install/remove smoke passed on April 16, 2026; the packaged stack is classified as GCC/libobjc interoperability-only.",
            },
            {
                "id": "debian-native-qualification",
                "status": "completed",
                "blocked": False,
                "notes": "Debian libvirt preflight and live acceptance were rerun successfully on April 14, 2026 using the ~/.ssh/otvm operator keypair.",
            },
            {
                "id": "arch-native-qualification",
                "status": "completed",
                "blocked": False,
                "blocked_by": None,
                "notes": "Arch libvirt preflight, acceptance, native CLI build, and package install/remove smoke passed on April 16, 2026; the packaged stack is classified as GCC/libobjc interoperability-only.",
            },
            {
                "id": "windows-libvirt-readiness",
                "status": "completed",
                "blocked": False,
                "notes": "Windows libvirt readiness reached full ready state and April 17, 2026 validation completed MSYS2 assembly, native full-CLI build, --version/--help, and package install/remove smoke on a fresh lease.",
            },
            {
                "id": "windows-public-bootstrap-stability",
                "status": "completed_with_trace_evidence",
                "blocked": False,
                "blocked_by": None,
                "notes": "A fresh April 17, 2026 Windows libvirt lease passed public GitHub prerelease setup in direct-process diagnostic mode with retained JSONL trace evidence. Installed CLI version/help passed; the follow-up doctor hang was isolated to native path handling rather than bootstrap setup.",
            },
            {
                "id": "windows-extracted-toolchain-rebuild",
                "status": "completed_with_manual_live_evidence",
                "blocked": False,
                "blocked_by": None,
                "notes": "The checked-in Windows MSYS2 assembly now preserves clang64/bin and copies the MSYS usr/bin executable/DLL runtime closure. A fresh April 17, 2026 Windows libvirt lease rebuilt the Objective-C CLI from the extracted toolchain and ran doctor --json successfully against an explicit local Windows manifest.",
            },
        ],
    }


def windows_extracted_toolchain_rebuild_plan() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "command": "windows-extracted-toolchain-rebuild-plan",
        "ok": True,
        "status": "validated_manual_live_evidence",
        "target": "windows-amd64-msys2-clang64",
        "blocked_by": None,
        "summary": "Windows extracted-toolchain developer rebuild is validated manually for the current MSYS2 clang64 layout; remaining work is automation in the release qualification lane.",
        "required_environment": {
            "path_entries": [
                "<toolchain>/bin",
                "<toolchain>/usr/bin",
                "<toolchain>/clang64/bin",
            ],
            "variables": [
                "GNUSTEP_MAKEFILES",
                "GNUSTEP_SYSTEM_ROOT",
                "GNUSTEP_LOCAL_ROOT",
            ],
            "shells": [
                "PowerShell",
                "cmd.exe",
            ],
        },
        "validation_steps": [
            {
                "id": "extract-published-toolchain",
                "description": "Extract the published Windows MSYS2 clang64 toolchain ZIP into a clean directory outside the repository.",
            },
            {
                "id": "activate-toolchain-environment",
                "description": "Populate PATH and GNUstep environment variables using only files from the extracted toolchain.",
            },
            {
                "id": "verify-compiler",
                "description": "Run clang --version from the activated environment.",
            },
            {
                "id": "verify-gnustep-make",
                "description": "Run gnustep-config and GNUstep Make from the activated environment.",
            },
            {
                "id": "rebuild-full-cli",
                "description": "Build src/full-cli using the extracted toolchain as the only GNUstep runtime.",
            },
            {
                "id": "run-rebuilt-cli",
                "description": "Run the rebuilt gnustep.exe --version, --help, doctor --json, and package install/remove smoke.",
            },
        ],
        "evidence_required": [
            "toolchain archive filename and SHA256",
            "activation environment dump with sensitive values redacted",
            "clang --version output",
            "gnustep-config output",
            "full CLI build log",
            "rebuilt gnustep.exe smoke output",
        ],
    }


def _artifact_basename(kind: str, target_id: str, version: str) -> str:
    return f"gnustep-{kind}-{target_id}-{version}"


def _artifact_extension(target: dict[str, Any]) -> str:
    return ".zip" if target["os"] == "windows" else ".tar.gz"


def _artifact_filename(kind: str, target_id: str, version: str) -> str:
    target = target_by_id(target_id)
    return f"{_artifact_basename(kind, target_id, version)}{_artifact_extension(target)}"


def _artifact_url(base_url: str, version: str, filename: str) -> str:
    return f"{base_url.rstrip('/')}/download/v{version}/{filename}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _archive_directory(source_dir: Path, archive_path: Path, root_name: str) -> None:
    if archive_path.suffix == ".zip":
        with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
            for path in sorted(source_dir.rglob("*")):
                if path.is_dir():
                    continue
                relative = path.relative_to(source_dir)
                archive.write(path, arcname=(Path(root_name) / relative).as_posix())
        return

    with tarfile.open(archive_path, "w:gz", dereference=True) as archive:
        archive.add(source_dir, arcname=root_name)


def _is_supported_archive(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".tar.gz") or name.endswith(".zip")


def _archive_file(source_file: Path, archive_path: Path, root_name: str) -> None:
    if _is_supported_archive(source_file):
        shutil.copy2(source_file, archive_path)
        return

    if archive_path.suffix == ".zip":
        with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
            archive.write(source_file, arcname=(Path(root_name) / source_file.name).as_posix())
        return

    with tarfile.open(archive_path, "w:gz", dereference=True) as archive:
        archive.add(source_file, arcname=str(Path(root_name) / source_file.name))


def _copy_tree_if_exists(source: Path | None, destination: Path) -> bool:
    if source is None or not source.exists():
        return False
    shutil.copytree(source, destination, dirs_exist_ok=True)
    return True


def _gnustep_config_value(name: str) -> Path | None:
    proc = subprocess.run(
        ["gnustep-config", "--variable", name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    if not value:
        return None
    return Path(value)


def _linux_shared_library_dependencies(binary_path: Path) -> list[Path]:
    proc = subprocess.run(
        ["ldd", str(binary_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"ldd failed for {binary_path}")

    dependencies: list[Path] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or "linux-vdso" in line:
            continue
        if "=>" in line:
            _, remainder = line.split("=>", 1)
            candidate = remainder.strip().split(" ", 1)[0]
        else:
            candidate = line.split(" ", 1)[0]
        if not candidate.startswith("/"):
            continue
        path = Path(candidate)
        if path.name.startswith("ld-linux"):
            continue
        if path.exists() and path not in dependencies:
            dependencies.append(path)
    return dependencies


def _write_linux_dpkg_architecture_shim(destination: Path) -> None:
    destination.write_text(
        "#!/usr/bin/env sh\n"
        "set -eu\n"
        "if [ \"$#\" -ne 2 ] || [ \"$1\" != \"--query\" ] || [ \"$2\" != \"DEB_HOST_MULTIARCH\" ]; then\n"
        "  printf '%s\\n' 'unsupported dpkg-architecture invocation' >&2\n"
        "  exit 2\n"
        "fi\n"
        "if [ -x /usr/bin/dpkg-architecture ]; then\n"
        "  exec /usr/bin/dpkg-architecture --query DEB_HOST_MULTIARCH\n"
        "fi\n"
        "if command -v gcc >/dev/null 2>&1; then\n"
        "  multiarch=$(gcc -print-multiarch 2>/dev/null || true)\n"
        "  if [ -n \"$multiarch\" ]; then\n"
        "    printf '%s\\n' \"$multiarch\"\n"
        "    exit 0\n"
        "  fi\n"
        "fi\n"
        "cpu=$(uname -m)\n"
        "case \"$cpu\" in\n"
        "  x86_64|amd64) cpu=x86_64 ;;\n"
        "  aarch64|arm64) cpu=aarch64 ;;\n"
        "  armv7l|armv7*) cpu=arm-linux-gnueabihf ;;\n"
        "  *) ;;\n"
        "esac\n"
        "if [ \"$cpu\" = \"arm-linux-gnueabihf\" ]; then\n"
        "  printf '%s\\n' \"$cpu\"\n"
        "else\n"
        "  printf '%s\\n' \"${cpu}-linux-gnu\"\n"
        "fi\n",
        encoding="utf-8",
    )
    destination.chmod(0o755)


def _linux_clang_binary() -> Path | None:
    compiler = shutil.which("clang")
    if compiler is None:
        return None
    return Path(compiler).resolve()


def _linux_clang_resource_dir(compiler_path: Path) -> Path | None:
    proc = subprocess.run(
        [str(compiler_path), "-print-resource-dir"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    resource_dir = proc.stdout.strip()
    if not resource_dir:
        return None
    path = Path(resource_dir)
    if not path.exists():
        return None
    return path


def _linux_linker_binary() -> Path | None:
    linker = shutil.which("ld")
    if linker is None:
        return None
    return Path(linker).resolve()


def _linux_gcc_runtime_dir() -> Path | None:
    gcc = shutil.which("x86_64-linux-gnu-gcc-14") or shutil.which("gcc")
    if gcc is None:
        return None
    proc = subprocess.run(
        [gcc, "-print-libgcc-file-name"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    libgcc = proc.stdout.strip()
    if not libgcc:
        return None
    path = Path(libgcc)
    if not path.exists():
        return None
    return path.parent


def _write_linux_tool_wrapper(
    destination: Path, target_relative_path: str, extra_args: list[str] | None = None
) -> None:
    extra_args = extra_args or []
    extra = "".join(f' "{arg}"' for arg in extra_args)
    destination.write_text(
        "#!/usr/bin/env sh\n"
        "set -eu\n"
        'PROGRAM_PATH="$0"\n'
        'while [ -L "$PROGRAM_PATH" ]; do\n'
        '  PROGRAM_PATH="$(readlink "$PROGRAM_PATH")"\n'
        "done\n"
        'TOOLS_DIR=$(CDPATH= cd -- "$(dirname "$PROGRAM_PATH")" && pwd)\n'
        'exec "$TOOLS_DIR/%s"%s "$@"\n' % (target_relative_path, extra),
        encoding="utf-8",
    )
    destination.chmod(0o755)


def _write_linux_compiler_wrapper(destination: Path, target_relative_path: str) -> None:
    destination.write_text(
        "#!/usr/bin/env sh\n"
        "set -eu\n"
        'PROGRAM_PATH="$0"\n'
        'while [ -L "$PROGRAM_PATH" ]; do\n'
        '  PROGRAM_PATH="$(readlink "$PROGRAM_PATH")"\n'
        "done\n"
        'TOOLS_DIR=$(CDPATH= cd -- "$(dirname "$PROGRAM_PATH")" && pwd)\n'
        'SYSROOT=$(CDPATH= cd -- "$TOOLS_DIR/../Sysroot" && pwd)\n'
        'GCC_RUNTIME_DIR=$(CDPATH= cd -- "$SYSROOT/usr/lib/gcc/x86_64-linux-gnu/14" && pwd)\n'
        'exec "$TOOLS_DIR/%s" --sysroot="$SYSROOT" -B"$GCC_RUNTIME_DIR" -L"$GCC_RUNTIME_DIR" "$@"\n'
        % target_relative_path,
        encoding="utf-8",
    )
    destination.chmod(0o755)

def _rewrite_managed_gnustep_make_for_relocation(output_root: Path) -> None:
    """Rewrite copied GNUstep Make config to an install-root placeholder."""
    placeholder = MANAGED_PREFIX_PLACEHOLDER
    replacements = {
        "/usr/share/GNUstep/Makefiles": f"{placeholder}/System/Library/Makefiles",
        "/usr/include/x86_64-linux-gnu/GNUstep": f"{placeholder}/System/Library/Headers",
        "/usr/local/include/GNUstep": f"{placeholder}/Local/Library/Headers",
        "/usr/include/libxml2": f"{placeholder}/System/Sysroot/usr/include/libxml2",
        "/usr/include/p11-kit-1": f"{placeholder}/System/Sysroot/usr/include/p11-kit-1",
        "/usr/lib/x86_64-linux-gnu/GNUstep": f"{placeholder}/System/Library",
        "/usr/lib/x86_64-linux-gnu": f"{placeholder}/System/Library/Libraries",
        "/usr/local/lib/GNUstep": f"{placeholder}/Local/Library",
        "/usr/local/lib": f"{placeholder}/Local/Library/Libraries",
        "/usr/local/bin": f"{placeholder}/Local/Tools",
        "/usr/local/sbin": f"{placeholder}/Local/Tools",
        "/usr/sbin": f"{placeholder}/System/Tools",
        "/usr/bin": f"{placeholder}/System/Tools",
        "/usr/share/GNUstep/Documentation": f"{placeholder}/System/Library/Documentation",
        "/usr/share/man": f"{placeholder}/System/Library/Documentation/man",
        "/usr/share/info": f"{placeholder}/System/Library/Documentation/info",
    }
    roots = [output_root / "System" / "Library" / "Makefiles", output_root / "System" / "Tools"]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            original = content
            for old, new in replacements.items():
                content = content.replace(old, new)
            if path.name == "gnustep-config":
                content = content.replace('echo "gcc"', 'echo "clang"')
                content = content.replace('echo "gcc -E"', 'echo "clang -E"')
                content = content.replace('echo "g++"', 'echo "clang++"')
                content = content.replace('echo "make"', 'echo "make"')
            if content != original:
                path.write_text(content, encoding="utf-8")


def assemble_linux_toolchain_artifact(
    output_dir: str | Path,
    *,
    runtime_binary: str | Path,
    makefiles_dir: str | Path | None = None,
    system_headers_dir: str | Path | None = None,
    user_headers_dir: str | Path | None = None,
    system_tools_dir: str | Path | None = None,
    user_tools_dir: str | Path | None = None,
    objc_headers_dir: str | Path | None = None,
    runtime_dependencies: list[str | Path] | None = None,
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    binary = Path(runtime_binary).resolve()
    if not binary.exists():
        raise FileNotFoundError(binary)
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    resolved_makefiles = Path(makefiles_dir).resolve() if makefiles_dir else (
        _gnustep_config_value("GNUSTEP_MAKEFILES") or Path("/usr/share/GNUstep/Makefiles")
    )
    resolved_system_headers = Path(system_headers_dir).resolve() if system_headers_dir else (
        _gnustep_config_value("GNUSTEP_SYSTEM_HEADERS") or Path("/usr/include/x86_64-linux-gnu/GNUstep")
    )
    resolved_user_headers = Path(user_headers_dir).resolve() if user_headers_dir else (
        _gnustep_config_value("GNUSTEP_USER_HEADERS") or (Path.home() / "GNUstep" / "Library" / "Headers")
    )
    resolved_system_tools = Path(system_tools_dir).resolve() if system_tools_dir else (
        _gnustep_config_value("GNUSTEP_SYSTEM_TOOLS") or Path("/usr/bin")
    )
    resolved_user_tools = Path(user_tools_dir).resolve() if user_tools_dir else (
        _gnustep_config_value("GNUSTEP_USER_TOOLS") or (Path.home() / "GNUstep" / "Tools")
    )
    resolved_objc_headers = Path(objc_headers_dir).resolve() if objc_headers_dir else Path("/usr/lib/gcc/x86_64-linux-gnu/14/include/objc")
    resolved_clang_binary = _linux_clang_binary()
    resolved_clang_resource_dir = (
        _linux_clang_resource_dir(resolved_clang_binary) if resolved_clang_binary is not None else None
    )
    resolved_linker_binary = _linux_linker_binary()
    resolved_gcc_runtime_dir = _linux_gcc_runtime_dir()

    copied_sections: list[str] = []
    copied_files: list[str] = []

    if _copy_tree_if_exists(resolved_makefiles, output_root / "System" / "Library" / "Makefiles"):
        copied_sections.append("System/Library/Makefiles")
    if _copy_tree_if_exists(resolved_system_headers, output_root / "System" / "Library" / "Headers"):
        copied_sections.append("System/Library/Headers")
    if _copy_tree_if_exists(resolved_user_headers, output_root / "Library" / "Headers"):
        copied_sections.append("Library/Headers")
    if _copy_tree_if_exists(resolved_objc_headers, output_root / "include" / "objc"):
        copied_sections.append("include/objc")

    system_tools_target = output_root / "System" / "Tools"
    system_tools_target.mkdir(parents=True, exist_ok=True)
    if resolved_system_tools and resolved_system_tools.exists():
        for name in LINUX_SYSTEM_TOOL_NAMES:
            candidate = resolved_system_tools / name
            if candidate.exists():
                shutil.copy2(candidate, system_tools_target / name)
                copied_files.append(str(system_tools_target / name))
    dpkg_architecture_shim = system_tools_target / "dpkg-architecture"
    _write_linux_dpkg_architecture_shim(dpkg_architecture_shim)
    copied_files.append(str(dpkg_architecture_shim))
    if resolved_clang_binary is not None and resolved_clang_binary.exists():
        compiler_root = output_root / "System" / "LLVM"
        compiler_bin_target = compiler_root / "bin"
        compiler_bin_target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(resolved_clang_binary, compiler_bin_target / "clang")
        copied_files.append(str(compiler_bin_target / "clang"))
        clangpp_target = compiler_bin_target / "clang++"
        if clangpp_target.exists() or clangpp_target.is_symlink():
            clangpp_target.unlink()
        os.symlink("clang", clangpp_target)
        copied_files.append(str(clangpp_target))
        for name, relative in (
            ("clang", "../LLVM/bin/clang"),
            ("clang++", "../LLVM/bin/clang++"),
            ("cc", "../LLVM/bin/clang"),
            ("c++", "../LLVM/bin/clang++"),
        ):
            wrapper = system_tools_target / name
            _write_linux_compiler_wrapper(wrapper, relative)
            copied_files.append(str(wrapper))
        if resolved_clang_resource_dir is not None and resolved_clang_resource_dir.exists():
            resource_target = compiler_root / "lib" / "clang" / resolved_clang_resource_dir.name
            shutil.copytree(resolved_clang_resource_dir, resource_target, dirs_exist_ok=True)
            copied_sections.append(f"System/LLVM/lib/clang/{resolved_clang_resource_dir.name}")
    if resolved_linker_binary is not None and resolved_linker_binary.exists():
        linker_target = system_tools_target / "ld"
        shutil.copy2(resolved_linker_binary, linker_target)
        copied_files.append(str(linker_target))
        for name in ("x86_64-linux-gnu-ld", "x86_64-linux-gnu-ld.bfd"):
            wrapper = system_tools_target / name
            _write_linux_tool_wrapper(wrapper, "ld")
            copied_files.append(str(wrapper))

    if resolved_user_tools and resolved_user_tools.exists():
        user_tools_target = output_root / "Tools"
        user_tools_target.mkdir(parents=True, exist_ok=True)
        for candidate in sorted(resolved_user_tools.iterdir()):
            if candidate.is_file():
                shutil.copy2(candidate, user_tools_target / candidate.name)
                copied_files.append(str(user_tools_target / candidate.name))

    if runtime_dependencies is None:
        dependencies = _linux_shared_library_dependencies(binary)
    else:
        dependencies = [Path(item).resolve() for item in runtime_dependencies]
    if resolved_clang_binary is not None and resolved_clang_binary.exists():
        for dependency in _linux_shared_library_dependencies(resolved_clang_binary):
            if dependency not in dependencies:
                dependencies.append(dependency)
    if resolved_linker_binary is not None and resolved_linker_binary.exists():
        for dependency in _linux_shared_library_dependencies(resolved_linker_binary):
            if dependency not in dependencies:
                dependencies.append(dependency)
    system_library_target = output_root / "System" / "Library" / "Libraries"
    system_library_target.mkdir(parents=True, exist_ok=True)
    for dependency in dependencies:
        if dependency.exists():
            target = system_library_target / dependency.name
            shutil.copy2(dependency, target)
            copied_files.append(str(target))

    linker_names = {
        "libgnustep-base.so": ("libgnustep-base.so.1.31", "libgnustep-base.so.1.30"),
        "libobjc.so": ("libobjc.so.4", "libobjc.so.4.6"),
    }
    for link_name, candidates in linker_names.items():
        link_path = system_library_target / link_name
        if link_path.exists():
            continue
        for candidate in candidates:
            if (system_library_target / candidate).exists():
                link_path.symlink_to(candidate)
                copied_files.append(str(link_path))
                break

    if resolved_gcc_runtime_dir is not None and resolved_gcc_runtime_dir.exists():
        sysroot = output_root / "System" / "Sysroot"
        usr_include_target = sysroot / "usr" / "include"
        for header_source in (Path("/usr/include"), Path("/usr/include/x86_64-linux-gnu")):
            if header_source.exists():
                header_target = usr_include_target if header_source.name == "include" else usr_include_target / header_source.name
                shutil.copytree(header_source, header_target, dirs_exist_ok=True)
                copied_sections.append(str(header_target.relative_to(output_root)))

        gcc_target = sysroot / "usr" / "lib" / "gcc" / "x86_64-linux-gnu" / resolved_gcc_runtime_dir.name
        gcc_target.mkdir(parents=True, exist_ok=True)
        for source in (
            resolved_gcc_runtime_dir / "crtbeginS.o",
            resolved_gcc_runtime_dir / "crtendS.o",
            resolved_gcc_runtime_dir / "libgcc.a",
            resolved_gcc_runtime_dir / "libgcc_s.so",
        ):
            if source.exists():
                shutil.copy2(source, gcc_target / source.name)
                copied_files.append(str(gcc_target / source.name))

        lib_target = sysroot / "lib" / "x86_64-linux-gnu"
        lib_target.mkdir(parents=True, exist_ok=True)
        for source in (
            Path("/lib/x86_64-linux-gnu/Scrt1.o"),
            Path("/lib/x86_64-linux-gnu/crti.o"),
            Path("/lib/x86_64-linux-gnu/crtn.o"),
            Path("/lib/x86_64-linux-gnu/libc.so.6"),
            Path("/lib/x86_64-linux-gnu/libgcc_s.so.1"),
        ):
            if source.exists():
                shutil.copy2(source, lib_target / source.name)
                copied_files.append(str(lib_target / source.name))

        lib64_target = sysroot / "lib64"
        lib64_target.mkdir(parents=True, exist_ok=True)
        dynamic_linker = Path("/lib64/ld-linux-x86-64.so.2")
        if dynamic_linker.exists():
            shutil.copy2(dynamic_linker, lib64_target / dynamic_linker.name)
            copied_files.append(str(lib64_target / dynamic_linker.name))

        usr_lib_target = sysroot / "usr" / "lib" / "x86_64-linux-gnu"
        usr_lib_target.mkdir(parents=True, exist_ok=True)
        for source in (
            Path("/usr/lib/x86_64-linux-gnu/libc.so"),
            Path("/usr/lib/x86_64-linux-gnu/libc_nonshared.a"),
            Path("/usr/lib/x86_64-linux-gnu/libpthread.so"),
            Path("/usr/lib/x86_64-linux-gnu/libpthread_nonshared.a"),
            Path("/usr/lib/x86_64-linux-gnu/libdl.so"),
            Path("/usr/lib/x86_64-linux-gnu/libm.so"),
            Path("/usr/lib/x86_64-linux-gnu/librt.so"),
        ):
            if source.exists():
                shutil.copy2(source, usr_lib_target / source.name)
                copied_files.append(str(usr_lib_target / source.name))

    _rewrite_managed_gnustep_make_for_relocation(output_root)

    source_policy = {
        "strategy": "host-derived-transitional",
        "production_eligible": False,
        "reason": "This assembler copies portions of the current host GNUstep/runtime tree and is only a bring-up artifact path.",
    }
    metadata_result = write_toolchain_metadata(
        output_root,
        "linux-amd64-clang",
        "2026.04.0",
        production_eligible=False,
    )
    host_origin_audit = toolchain_tree_host_origin_audit(output_root)
    metadata = {
        "schema_version": 1,
        "target": "linux-amd64-clang",
        "runtime_binary": str(binary),
        "source_policy": source_policy,
        "host_origin_audit": host_origin_audit,
        "toolchain_metadata": {
            key: Path(value).name for key, value in metadata_result["written"].items()
        },
        "copied_sections": copied_sections,
        "copied_files": copied_files,
    }
    metadata_path = output_root / "toolchain-assembly.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")

    return {
        "schema_version": 1,
        "command": "assemble-linux-toolchain",
        "ok": True,
        "status": "ok",
        "summary": "Linux managed toolchain artifact assembled from the current host as a transitional non-production artifact.",
        "output_root": str(output_root),
        "metadata_path": str(metadata_path),
        "source_policy": source_policy,
        "host_origin_audit": host_origin_audit,
        "copied_sections": copied_sections,
        "copied_file_count": len(copied_files),
    }


def ensure_linux_runtime_soname_aliases(root: Path) -> list[str]:
    """Create compatibility SONAME aliases expected by linked GNUstep binaries."""
    aliases = {
        "libBlocksRuntime.so.0": "libBlocksRuntime.so",
        "libobjc.so.4": "libobjc.so.4.6",
    }
    written: list[str] = []
    for library_dir in (root / "lib", root / "lib64", root / "System" / "Library" / "Libraries"):
        if not library_dir.exists():
            continue
        for link_name, target_name in aliases.items():
            link_path = library_dir / link_name
            target_path = library_dir / target_name
            if link_path.exists() or not target_path.exists():
                continue
            link_path.symlink_to(target_name)
            written.append(str(link_path.relative_to(root)))
    return written


def package_source_built_linux_toolchain_artifact(
    staging_prefix: str | Path,
    output_dir: str | Path,
    *,
    toolchain_version: str = "2026.04.0",
    target_id: str = "linux-amd64-clang",
) -> dict[str, Any]:
    source_root = Path(staging_prefix).resolve()
    output_root = Path(output_dir).resolve()
    if not source_root.exists():
        raise FileNotFoundError(source_root)
    if output_root.exists():
        shutil.rmtree(output_root)
    shutil.copytree(source_root, output_root)
    (output_root / "toolchain-assembly.json").unlink(missing_ok=True)
    runtime_aliases = ensure_linux_runtime_soname_aliases(output_root)
    normalization = normalize_source_built_toolchain_paths(output_root, source_root)
    metadata_result = write_toolchain_metadata(
        output_root,
        target_id,
        toolchain_version,
        production_eligible=True,
    )
    host_origin_audit = toolchain_tree_host_origin_audit(output_root)
    production_eligible = bool(host_origin_audit["ok"])
    if not production_eligible:
        manifest_path = output_root / "toolchain-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["source_policy"]["production_eligible"] = False
        manifest["source_policy"]["production_blockers"] = ["host-origin-path-leakage"]
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assembly_metadata = {
        "schema_version": 1,
        "target": target_id,
        "source_prefix": "<staging-prefix>",
        "source_policy": {
            "strategy": "source-build",
            "production_eligible": production_eligible,
            "lock_file": "source-lock.json",
            "component_inventory": "component-inventory.json",
            "host_origin_paths_allowed": False,
        },
        "toolchain_metadata": {
            key: Path(value).name for key, value in metadata_result["written"].items()
        },
        "runtime_aliases": runtime_aliases,
        "normalization": {
            "ok": normalization["ok"],
            "status": normalization["status"],
            "placeholder": normalization["placeholder"],
            "rewritten_files": normalization["rewritten_files"],
            "patched_files": normalization["patched_files"],
        },
        "host_origin_audit": {
            "ok": host_origin_audit["ok"],
            "status": host_origin_audit["status"],
            "summary": host_origin_audit["summary"],
            "findings": host_origin_audit["findings"],
        },
    }
    metadata_path = output_root / "toolchain-assembly.json"
    metadata_path.write_text(json.dumps(assembly_metadata, indent=2) + "\n", encoding="utf-8")
    return {
        "schema_version": 1,
        "command": "package-source-built-linux-toolchain",
        "ok": production_eligible,
        "status": "ok" if production_eligible else "error",
        "summary": "Source-built Linux managed toolchain packaged." if production_eligible else "Source-built Linux managed toolchain has host-origin path leakage.",
        "output_root": str(output_root),
        "metadata_path": str(metadata_path),
        "source_policy": assembly_metadata["source_policy"],
        "host_origin_audit": host_origin_audit,
    }


def bundle_full_cli(
    binary_path: str | Path,
    output_dir: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    binary = Path(binary_path).resolve()
    if not binary.exists():
        raise FileNotFoundError(binary)
    root = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[2]
    bundle_root = Path(output_dir).resolve()
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    (bundle_root / "bin").mkdir(parents=True, exist_ok=True)
    runtime_root = bundle_root / "libexec" / "gnustep-cli"
    shutil.copytree(root / "examples", runtime_root / "examples", dirs_exist_ok=True)
    runtime_binary_dir = runtime_root / "bin"
    runtime_binary_dir.mkdir(parents=True, exist_ok=True)
    runtime_binary = runtime_binary_dir / binary.name
    shutil.copy2(binary, runtime_binary)
    os.chmod(runtime_binary, 0o755)

    if binary.suffix.lower() == ".exe":
        shutil.copy2(runtime_binary, bundle_root / "bin" / binary.name)
        os.chmod(bundle_root / "bin" / binary.name, 0o755)
    else:
        launcher = bundle_root / "bin" / binary.name
        launcher.write_text(
            "#!/usr/bin/env sh\n"
            "set -eu\n"
            'PROGRAM_PATH="$0"\n'
            'while [ -L "$PROGRAM_PATH" ]; do\n'
            '  PROGRAM_PATH="$(readlink "$PROGRAM_PATH")"\n'
            "done\n"
            'BIN_DIR=$(CDPATH= cd -- "$(dirname "$PROGRAM_PATH")" && pwd)\n'
            'INSTALL_ROOT=$(CDPATH= cd -- "$BIN_DIR/.." && pwd)\n'
            'RUNTIME_ROOT="$INSTALL_ROOT/libexec/gnustep-cli"\n'
            'RUNTIME_BIN="$RUNTIME_ROOT/bin/gnustep"\n'
            'export PATH="$INSTALL_ROOT/bin:$INSTALL_ROOT/Tools:$INSTALL_ROOT/System/Tools:$INSTALL_ROOT/Local/Tools:$PATH"\n'
            'export LD_LIBRARY_PATH="$INSTALL_ROOT/Library/Libraries:$INSTALL_ROOT/Local/Library/Libraries:$INSTALL_ROOT/System/Library/Libraries:$INSTALL_ROOT/lib:$INSTALL_ROOT/lib64:${LD_LIBRARY_PATH:-}"\n'
            'MANAGED_MAKEFILES="$INSTALL_ROOT/System/Library/Makefiles"\n'
            'if [ -f "$MANAGED_MAKEFILES/GNUstep.sh" ]; then\n'
            '  export GNUSTEP_SYSTEM_ROOT="$INSTALL_ROOT/System"\n'
            '  export GNUSTEP_LOCAL_ROOT="$INSTALL_ROOT/Local"\n'
            '  export GNUSTEP_NETWORK_ROOT="$INSTALL_ROOT/Network"\n'
            '  export GNUSTEP_MAKEFILES="$MANAGED_MAKEFILES"\n'
            'elif command -v gnustep-config >/dev/null 2>&1; then\n'
            '  GNUSTEP_MAKEFILES=$(gnustep-config --variable=GNUSTEP_MAKEFILES 2>/dev/null || true)\n'
            '  if [ -n "$GNUSTEP_MAKEFILES" ]; then\n'
            '    export GNUSTEP_MAKEFILES\n'
            '  fi\n'
            'elif [ -f /usr/local/share/GNUstep/Makefiles/GNUstep.sh ]; then\n'
            '  export GNUSTEP_MAKEFILES=/usr/local/share/GNUstep/Makefiles\n'
            'elif [ -f /usr/share/GNUstep/Makefiles/GNUstep.sh ]; then\n'
            '  export GNUSTEP_MAKEFILES=/usr/share/GNUstep/Makefiles\n'
            'fi\n'
            'if [ -n "${GNUSTEP_MAKEFILES:-}" ] && [ -f "$GNUSTEP_MAKEFILES/GNUstep.sh" ]; then\n'
            '  set +u\n'
            '  . "$GNUSTEP_MAKEFILES/GNUstep.sh"\n'
            '  set -u\n'
            "fi\n"
            'exec "$RUNTIME_BIN" "$@"\n',
            encoding="utf-8",
        )
        os.chmod(launcher, 0o755)
    return {
        "schema_version": 1,
        "command": "bundle-cli",
        "ok": True,
        "status": "ok",
        "summary": "Full CLI runtime bundle created.",
        "bundle_root": str(bundle_root),
    }


def _replace_managed_prefix_placeholders(root: Path) -> list[str]:
    rewritten: list[str] = []
    placeholder = MANAGED_PREFIX_PLACEHOLDER
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            if path.stat().st_size > 2_000_000:
                continue
            data = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if placeholder in data:
            path.write_text(data.replace(placeholder, str(root)), encoding="utf-8")
            rewritten.append(str(path.relative_to(root)))
    return rewritten


def _shell_environment_for_managed_toolchain(managed_root: Path) -> str:
    return (
        "set +u; "
        f". {shlex_quote(str(managed_root / 'System' / 'Library' / 'Makefiles' / 'GNUstep.sh'))}; "
        "set -u; "
        "env"
    )


def _load_managed_toolchain_environment(managed_root: Path) -> dict[str, str]:
    proc = subprocess.run(
        ["bash", "-lc", _shell_environment_for_managed_toolchain(managed_root)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "failed to load managed GNUstep environment")
    env = os.environ.copy()
    for line in proc.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            env[key] = value
    return env


def _managed_gnustep_config(managed_root: Path, option: str, env: dict[str, str]) -> list[str]:
    tool = managed_root / "System" / "Tools" / "gnustep-config"
    proc = subprocess.run([str(tool), option], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"gnustep-config {option} failed")
    return proc.stdout.split()


def shlex_quote(value: str) -> str:
    return "'" + value.replace("'", "'\''") + "'"


def linux_cli_abi_audit(binary_path: str | Path) -> dict[str, Any]:
    binary = Path(binary_path).resolve()
    checks: list[dict[str, Any]] = []

    def add(check_id: str, ok: bool, message: str, **extra: Any) -> None:
        item = {"id": check_id, "ok": ok, "message": message}
        item.update(extra)
        checks.append(item)

    add("binary-present", binary.exists(), "CLI binary is present")
    if not binary.exists():
        return {"schema_version": 1, "command": "linux-cli-abi-audit", "ok": False, "status": "error", "summary": "Linux CLI ABI audit failed.", "binary": str(binary), "checks": checks}
    proc = subprocess.run(["nm", "-D", str(binary)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    add("nm-dynamic-symbols", proc.returncode == 0, "dynamic symbols are readable", stderr=proc.stderr.strip())
    symbols = proc.stdout if proc.returncode == 0 else ""
    legacy_symbol = "__objc_class_name_NSAutoreleasePool" in symbols
    modern_symbol = "._OBJC_REF_CLASS_NSAutoreleasePool" in symbols or "_OBJC_REF_CLASS_NSAutoreleasePool" in symbols
    add("no-legacy-gcc-objc-class-symbols", not legacy_symbol, "CLI does not reference GCC Objective-C class symbols")
    add("modern-objc2-class-symbols", modern_symbol, "CLI references modern Objective-C runtime class symbols")
    ok = all(check["ok"] for check in checks)
    return {"schema_version": 1, "command": "linux-cli-abi-audit", "ok": ok, "status": "ok" if ok else "error", "summary": "Linux CLI ABI audit passed." if ok else "Linux CLI ABI audit failed.", "binary": str(binary), "checks": checks}


def _linux_gcc_runtime_include_path() -> str | None:
    candidates = sorted(Path("/usr/lib/gcc/x86_64-linux-gnu").glob("*/include"))
    if not candidates:
        return None
    return str(candidates[-1])


def build_linux_cli_against_managed_toolchain(
    toolchain_archive: str | Path,
    output_archive: str | Path,
    *,
    version: str = "0.1.0-dev",
    target_id: str = "linux-amd64-clang",
    repo_root: str | Path | None = None,
    work_dir: str | Path | None = None,
    release_dir: str | Path | None = None,
    private_key: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[2]
    toolchain = Path(toolchain_archive).resolve()
    output = Path(output_archive).resolve()
    if not toolchain.exists():
        raise FileNotFoundError(toolchain)
    owns_work_dir = work_dir is None
    work = Path(tempfile.mkdtemp(prefix="gnustep-cli-managed-build-")) if work_dir is None else Path(work_dir).resolve()
    managed_root = work / "managed-root"
    build_dir = work / "build"
    bundle_dir = work / "bundle"
    try:
        if managed_root.exists():
            shutil.rmtree(managed_root)
        if build_dir.exists():
            shutil.rmtree(build_dir)
        if bundle_dir.exists():
            shutil.rmtree(bundle_dir)
        managed_root.mkdir(parents=True)
        build_dir.mkdir(parents=True)
        _extract_archive(toolchain, managed_root)
        children = list(managed_root.iterdir())
        if len(children) == 1 and children[0].is_dir():
            extracted_root = children[0]
            for child in list(extracted_root.iterdir()):
                shutil.move(str(child), managed_root / child.name)
            shutil.rmtree(extracted_root)
        rewritten = _replace_managed_prefix_placeholders(managed_root)
        env = _load_managed_toolchain_environment(managed_root)
        objc_flags = ["-fobjc-runtime=gnustep-2.0", "-fblocks"] + _managed_gnustep_config(managed_root, "--objc-flags", env)
        base_libs = _managed_gnustep_config(managed_root, "--base-libs", env)
        binary = build_dir / "gnustep"
        gcc_include = _linux_gcc_runtime_include_path()
        command = [
            "clang",
            *objc_flags,
            f"-I{managed_root / 'Local' / 'Library' / 'Headers'}",
            f"-I{managed_root / 'System' / 'Library' / 'Headers'}",
            *([f"-I{gcc_include}"] if gcc_include else []),
            f"-I{root / 'src' / 'full-cli'}",
            str(root / "src" / "full-cli" / "main.m"),
            str(root / "src" / "full-cli" / "GSCommandContext.m"),
            str(root / "src" / "full-cli" / "GSCommandRunner.m"),
            "-o",
            str(binary),
            f"-L{managed_root / 'Local' / 'Library' / 'Libraries'}",
            f"-L{managed_root / 'System' / 'Library' / 'Libraries'}",
            f"-L{managed_root / 'lib'}",
            "-Wl,-rpath,$ORIGIN/../../../Local/Library/Libraries",
            "-Wl,-rpath,$ORIGIN/../../../System/Library/Libraries",
            "-Wl,-rpath,$ORIGIN/../../../lib",
            *base_libs,
            "-lBlocksRuntime",
        ]
        proc = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, check=False)
        if proc.returncode != 0:
            return {"schema_version": 1, "command": "build-linux-cli-against-managed-toolchain", "ok": False, "status": "error", "summary": "Managed-prefix Linux CLI build failed.", "stdout": proc.stdout, "stderr": proc.stderr, "build_command": command}
        runtime_env = env.copy()
        runtime_env["LD_LIBRARY_PATH"] = ":".join([str(managed_root / "Local" / "Library" / "Libraries"), str(managed_root / "System" / "Library" / "Libraries"), str(managed_root / "lib"), runtime_env.get("LD_LIBRARY_PATH", "")])
        smoke = subprocess.run([str(binary), "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=runtime_env, check=False)
        if smoke.returncode != 0:
            return {"schema_version": 1, "command": "build-linux-cli-against-managed-toolchain", "ok": False, "status": "error", "summary": "Managed-prefix Linux CLI smoke failed.", "stdout": smoke.stdout, "stderr": smoke.stderr}
        abi = linux_cli_abi_audit(binary)
        if not abi["ok"]:
            return {"schema_version": 1, "command": "build-linux-cli-against-managed-toolchain", "ok": False, "status": "error", "summary": "Managed-prefix Linux CLI ABI audit failed.", "abi_audit": abi}
        bundle_full_cli(binary, bundle_dir, repo_root=root)
        output.parent.mkdir(parents=True, exist_ok=True)
        _archive_directory(bundle_dir, output, f"gnustep-cli-{target_id}-{version}")
        refresh = None
        if release_dir is not None:
            refresh = refresh_local_release_metadata(release_dir, private_key_path=private_key)
        return {"schema_version": 1, "command": "build-linux-cli-against-managed-toolchain", "ok": True, "status": "ok", "summary": "Linux CLI artifact built against managed GNUstep toolchain.", "toolchain_archive": str(toolchain), "output_archive": str(output), "version": version, "target_id": target_id, "work_dir": str(work), "rewritten_placeholders": rewritten, "abi_audit": abi, "refresh_release_metadata": refresh}
    finally:
        if owns_work_dir:
            shutil.rmtree(work, ignore_errors=True)


def refresh_local_release_metadata(release_dir: str | Path, *, private_key_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(release_dir).resolve()
    manifest_path = root / "release-manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for release in manifest.get("releases", []):
        for artifact in release.get("artifacts", []):
            filename = artifact.get("filename")
            if not filename:
                continue
            path = root / filename
            if not path.exists():
                continue
            digest = _sha256(path)
            artifact["sha256"] = digest
            artifact["integrity"] = {"sha256": digest}
            artifact["size"] = path.stat().st_size
    manifest.setdefault("metadata_version", 1)
    manifest.setdefault("expires_at", (datetime.now(UTC).replace(microsecond=0) + timedelta(days=30)).isoformat().replace("+00:00", "Z"))
    manifest.setdefault("trust", {"root_version": 1, "signature_policy": "single-role-v1", "signatures": [], "revoked_artifacts": []})
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    provenance_path = write_release_provenance(root)
    checksum_entries = []
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.name == "SHA256SUMS" or path.name.endswith(".sig") or path.name == "release-signing-public.pem":
            continue
        checksum_entries.append(f"{_sha256(path)}  {path.name}\n")
    (root / "SHA256SUMS").write_text("".join(checksum_entries), encoding="utf-8")
    signing = None
    if private_key_path is not None:
        signing = sign_release_metadata(root, private_key_path)
    verification = verify_release_directory(root)
    trust = release_trust_gate(root) if private_key_path is not None else None
    ok = verification["ok"] and (signing is None or signing["ok"]) and (trust is None or trust["ok"])
    return {"schema_version": 1, "command": "refresh-local-release-metadata", "ok": ok, "status": "ok" if ok else "error", "summary": "Local release metadata refreshed." if ok else "Local release metadata refresh failed.", "release_dir": str(root), "manifest_path": str(manifest_path), "provenance_path": str(provenance_path), "verify_release": verification, "sign_release_metadata": signing, "release_trust_gate": trust}



def _git_revision(repo_root: Path | None = None) -> str | None:
    root = repo_root or Path(__file__).resolve().parents[2]
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def release_provenance_document(release_dir: str | Path, *, builder_identity: str = "local", source_revision: str | None = None) -> dict[str, Any]:
    root = Path(release_dir).resolve()
    manifest_path = root / "release-manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = []
    for artifact in manifest["releases"][0]["artifacts"]:
        filename = artifact.get("filename")
        artifact_path = root / filename if filename else None
        artifacts.append({
            "id": artifact["id"],
            "kind": artifact["kind"],
            "version": artifact.get("version"),
            "os": artifact.get("os"),
            "arch": artifact.get("arch"),
            "filename": filename,
            "url": artifact.get("url"),
            "reused": bool(artifact.get("reused")),
            "sha256": artifact["sha256"],
            "size": artifact_path.stat().st_size if artifact_path and artifact_path.exists() else artifact.get("size"),
            "source_policy": artifact.get("metadata", {}).get("source_policy"),
            "lock_file": artifact.get("metadata", {}).get("lock_file"),
            "component_inventory": artifact.get("metadata", {}).get("component_inventory"),
            "toolchain_manifest": artifact.get("metadata", {}).get("toolchain_manifest"),
        })
    return {
        "schema_version": 1,
        "release_version": manifest["releases"][0]["version"],
        "channel": manifest.get("channel", "stable"),
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_revision": source_revision or _git_revision(),
        "builder_identity": builder_identity,
        "manifest": {"filename": "release-manifest.json", "sha256": _sha256(manifest_path)},
        "artifacts": artifacts,
        "qualification": {
            "release_verification": "required",
            "archive_audits": "required_for_toolchains",
            "published_url_qualification": "target-scoped",
        },
    }


def write_release_provenance(release_dir: str | Path, *, builder_identity: str = "local", source_revision: str | None = None) -> Path:
    root = Path(release_dir).resolve()
    provenance = release_provenance_document(root, builder_identity=builder_identity, source_revision=source_revision)
    path = root / "release-provenance.json"
    path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return path



def _parse_metadata_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or value in {"", "TBD"}:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _metadata_policy_checks(payload: dict[str, Any], *, artifact_ids: set[str] | None = None, package_ids: set[str] | None = None, now: datetime | None = None) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    current_time = now or datetime.now(UTC)

    def add(check_id: str, ok: bool, message: str) -> None:
        checks.append({"id": check_id, "ok": ok, "message": message})

    metadata_version = payload.get("metadata_version")
    add("metadata-version-supported", isinstance(metadata_version, int) and metadata_version >= 1, "metadata_version is supported")
    generated_at = _parse_metadata_time(payload.get("generated_at"))
    if generated_at is not None:
        add("metadata-generated-not-in-future", generated_at <= current_time, "metadata generated_at is not in the future")
    expires_at = _parse_metadata_time(payload.get("expires_at"))
    if expires_at is not None:
        add("metadata-not-expired", expires_at > current_time, "metadata expires_at is still valid")
    trust = payload.get("trust") if isinstance(payload.get("trust"), dict) else {}
    revoked_artifacts = set(trust.get("revoked_artifacts", []) or [])
    revoked_packages = set(trust.get("revoked_packages", []) or [])
    if artifact_ids is not None:
        revoked = sorted(revoked_artifacts & artifact_ids)
        add("revoked-artifacts-absent", not revoked, "release metadata does not reference revoked artifacts" if not revoked else f"revoked artifacts present: {', '.join(revoked)}")
    if package_ids is not None:
        revoked = sorted(revoked_packages & package_ids)
        add("revoked-packages-absent", not revoked, "package index does not reference revoked packages" if not revoked else f"revoked packages present: {', '.join(revoked)}")
    return checks

def _openssl_sign_file(input_path: Path, signature_path: Path, private_key_path: Path) -> bool:
    proc = subprocess.run(["openssl", "dgst", "-sha256", "-sign", str(private_key_path), "-out", str(signature_path), str(input_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    return proc.returncode == 0


def _openssl_verify_file(input_path: Path, signature_path: Path, public_key_path: Path) -> bool:
    proc = subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(public_key_path), "-signature", str(signature_path), str(input_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    return proc.returncode == 0


def sign_release_metadata(release_dir: str | Path, private_key_path: str | Path, public_key_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(release_dir).resolve()
    private_key = Path(private_key_path).resolve()
    if not private_key.exists():
        return {"schema_version": 1, "command": "sign-release-metadata", "ok": False, "status": "error", "summary": "Signing private key is missing.", "release_dir": str(root)}
    provenance_path = write_release_provenance(root, builder_identity=os.environ.get("GNUSTEP_CLI_BUILDER_ID", "local"))
    public_key = Path(public_key_path).resolve() if public_key_path else root / "release-signing-public.pem"
    if public_key_path is None:
        proc = subprocess.run(["openssl", "pkey", "-in", str(private_key), "-pubout", "-out", str(public_key)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if proc.returncode != 0:
            return {"schema_version": 1, "command": "sign-release-metadata", "ok": False, "status": "error", "summary": "Failed to derive release signing public key.", "release_dir": str(root), "stderr": proc.stderr}
    signatures = []
    ok = True
    for filename in ("release-manifest.json", "release-provenance.json"):
        input_path = root / filename
        signature_path = root / f"{filename}.sig"
        signed = input_path.exists() and _openssl_sign_file(input_path, signature_path, private_key)
        signatures.append({"filename": filename, "signature": signature_path.name, "ok": signed})
        ok = ok and signed
    return {"schema_version": 1, "command": "sign-release-metadata", "ok": ok, "status": "ok" if ok else "error", "summary": "Release metadata signed." if ok else "Release metadata signing failed.", "release_dir": str(root), "public_key": str(public_key), "signatures": signatures}


def release_trust_gate(release_dir: str | Path, *, require_signatures: bool = True, trusted_public_key_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(release_dir).resolve()
    checks: list[dict[str, Any]] = []
    def add(check_id: str, ok: bool, message: str) -> None:
        checks.append({"id": check_id, "ok": ok, "message": message})

    manifest_path = root / "release-manifest.json"
    provenance_path = root / "release-provenance.json"
    checksums_path = root / "SHA256SUMS"
    bundled_public_key_path = root / "release-signing-public.pem"
    public_key_path = Path(trusted_public_key_path).resolve() if trusted_public_key_path else bundled_public_key_path
    add("manifest-present", manifest_path.exists(), "release-manifest.json is present")
    add("provenance-present", provenance_path.exists(), "release-provenance.json is present")
    add("checksums-present", checksums_path.exists(), "SHA256SUMS is present")
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifact_ids = {
                artifact.get("id")
                for release in manifest.get("releases", [])
                for artifact in release.get("artifacts", [])
                if artifact.get("id")
            }
            checks.extend(_metadata_policy_checks(manifest, artifact_ids=artifact_ids))
        except Exception as exc:
            add("manifest-json", False, f"release-manifest.json is invalid: {exc}")
    if manifest_path.exists() and provenance_path.exists():
        try:
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            add("provenance-manifest-digest", provenance.get("manifest", {}).get("sha256") == _sha256(manifest_path), "provenance records the release manifest digest")
            for artifact in provenance.get("artifacts", []):
                if artifact.get("reused") and not artifact.get("filename"):
                    add(f"artifact-reference:{artifact.get('id')}", not _artifact_immutable_reference_errors(artifact), f"reused artifact reference is immutable for {artifact.get('id')}")
                    continue
                artifact_path = root / artifact.get("filename", "")
                add(f"artifact-digest:{artifact.get('filename')}", artifact_path.exists() and artifact.get("sha256") == _sha256(artifact_path), f"artifact digest matches for {artifact.get('filename')}")
        except Exception as exc:
            add("provenance-json", False, f"release-provenance.json is invalid: {exc}")
    if require_signatures:
        if trusted_public_key_path:
            add("trusted-public-key-present", public_key_path.exists(), "trusted release signing public key is present")
            if public_key_path.exists() and bundled_public_key_path.exists():
                add("bundled-public-key-matches-trust-root", _sha256(public_key_path) == _sha256(bundled_public_key_path), "bundled release public key matches the trusted root")
        else:
            add("public-key-present", public_key_path.exists(), "release signing public key is present")
        for filename in ("release-manifest.json", "release-provenance.json"):
            input_path = root / filename
            signature_path = root / f"{filename}.sig"
            add(f"signature-present:{filename}", signature_path.exists(), f"signature exists for {filename}")
            if input_path.exists() and signature_path.exists() and public_key_path.exists():
                add(f"signature-valid:{filename}", _openssl_verify_file(input_path, signature_path, public_key_path), f"signature verifies for {filename}")
    ok = all(check["ok"] for check in checks)
    return {"schema_version": 1, "command": "release-trust-gate", "ok": ok, "status": "ok" if ok else "error", "summary": "Release trust gate passed." if ok else "Release trust gate failed.", "release_dir": str(root), "require_signatures": require_signatures, "trusted_public_key": str(public_key_path) if trusted_public_key_path else None, "checks": checks}



def _load_json_evidence(path: Path) -> tuple[bool, str, dict[str, Any] | None]:
    if not path.exists():
        return False, f"{path.name} evidence is missing", None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return False, f"{path.name} evidence is invalid: {exc}", None
    return bool(payload.get("ok")), payload.get("summary", f"{path.name} evidence loaded"), payload


def write_windows_current_source_marker(
    release_dir: str | Path,
    *,
    artifact_id: str = "cli-windows-amd64-msys2-clang64",
    source_revision: str | None = None,
    builder_identity: str = "local",
) -> dict[str, Any]:
    root = Path(release_dir).resolve()
    manifest_path = root / "release-manifest.json"
    checks: list[dict[str, Any]] = []

    def add(check_id: str, ok: bool, message: str, **extra: Any) -> None:
        item = {"id": check_id, "ok": ok, "message": message}
        item.update(extra)
        checks.append(item)

    artifact: dict[str, Any] | None = None
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for release in manifest.get("releases", []):
                for candidate in release.get("artifacts", []):
                    if candidate.get("id") == artifact_id:
                        artifact = candidate
                        break
                if artifact:
                    break
            add("artifact-present", artifact is not None, f"{artifact_id} is present in release manifest")
        except Exception as exc:
            add("release-manifest-json", False, f"release manifest is invalid: {exc}")
    else:
        add("release-manifest-present", False, "release manifest is missing")

    revision = source_revision or _git_revision()
    add("source-revision-present", bool(revision), "source revision is recorded")
    ok = all(check["ok"] for check in checks)
    marker = root / "windows-current-source-artifact.json"
    payload = {
        "schema_version": 1,
        "command": "windows-current-source-marker",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": "Windows artifact is marked as rebuilt from current source." if ok else "Windows current-source marker could not be written as valid evidence.",
        "release_dir": str(root),
        "artifact_id": artifact_id,
        "artifact_filename": artifact.get("filename") if artifact else None,
        "source_revision": revision,
        "builder_identity": builder_identity,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "checks": checks,
    }
    marker.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    payload["marker_path"] = str(marker)
    return payload


def write_release_evidence_bundle(release_dir: str | Path, *, evidence_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(release_dir).resolve()
    evidence_root = Path(evidence_dir).resolve() if evidence_dir else root
    evidence_files = {
        "debian-otvm-smoke": evidence_root / "otvm-debian-13-gnome-wayland-smoke.json",
        "openbsd-otvm-smoke": evidence_root / "otvm-openbsd-7.8-fvwm-smoke.json",
        "windows-otvm-smoke": evidence_root / "otvm-windows-2022-smoke.json",
        "windows-current-source-artifact": evidence_root / "windows-current-source-artifact.json",
    }
    entries: list[dict[str, Any]] = []
    for evidence_id, path in evidence_files.items():
        ok, summary, payload = _load_json_evidence(path)
        entries.append({
            "id": evidence_id,
            "ok": ok,
            "summary": summary,
            "path": str(path),
            "sha256": _sha256(path) if path.exists() else None,
            "payload_command": payload.get("command") if isinstance(payload, dict) else None,
        })
    ok = all(entry["ok"] for entry in entries)
    bundle = {
        "schema_version": 1,
        "command": "release-evidence-bundle",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": "Release evidence bundle is complete." if ok else "Release evidence bundle is missing required evidence.",
        "release_dir": str(root),
        "evidence_dir": str(evidence_root),
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "evidence": entries,
    }
    bundle_path = root / "release-evidence-bundle.json"
    bundle_path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    bundle["bundle_path"] = str(bundle_path)
    return bundle


def release_key_rotation_drill(release_dir: str | Path, *, work_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(release_dir).resolve()
    temp_context = tempfile.TemporaryDirectory() if work_dir is None else None
    drill_root = Path(work_dir).resolve() if work_dir else Path(temp_context.name)
    drill_root.mkdir(parents=True, exist_ok=True)
    release_copy = drill_root / "release-copy"
    if release_copy.exists():
        shutil.rmtree(release_copy)
    shutil.copytree(root, release_copy)
    old_key = drill_root / "old-release-key.pem"
    new_key = drill_root / "new-release-key.pem"
    checks: list[dict[str, Any]] = []

    def add(check_id: str, ok: bool, message: str, **extra: Any) -> None:
        item = {"id": check_id, "ok": ok, "message": message}
        item.update(extra)
        checks.append(item)

    for key_path in (old_key, new_key):
        proc = subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(key_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        add(f"generate:{key_path.stem}", proc.returncode == 0, f"generated {key_path.name}")
    if all(check["ok"] for check in checks):
        old_sign = sign_release_metadata(release_copy, old_key)
        old_gate = release_trust_gate(release_copy, trusted_public_key_path=release_copy / "release-signing-public.pem")
        new_rejects_old = release_trust_gate(release_copy, trusted_public_key_path=new_key.with_suffix(".pub.pem"))
        # Derive the new public key before using it as the new trust root.
        subprocess.run(["openssl", "pkey", "-in", str(new_key), "-pubout", "-out", str(new_key.with_suffix(".pub.pem"))], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        new_rejects_old = release_trust_gate(release_copy, trusted_public_key_path=new_key.with_suffix(".pub.pem"))
        new_sign = sign_release_metadata(release_copy, new_key)
        new_gate = release_trust_gate(release_copy, trusted_public_key_path=release_copy / "release-signing-public.pem")
        old_rejects_new = release_trust_gate(release_copy, trusted_public_key_path=old_key.with_suffix(".pub.pem"))
        subprocess.run(["openssl", "pkey", "-in", str(old_key), "-pubout", "-out", str(old_key.with_suffix(".pub.pem"))], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        old_rejects_new = release_trust_gate(release_copy, trusted_public_key_path=old_key.with_suffix(".pub.pem"))
        add("old-signature-valid-with-old-root", bool(old_sign.get("ok")) and bool(old_gate.get("ok")), "old signing key verifies with old trust root")
        add("new-root-rejects-old-signature", not bool(new_rejects_old.get("ok")), "new trust root rejects old signatures")
        add("new-signature-valid-with-new-root", bool(new_sign.get("ok")) and bool(new_gate.get("ok")), "new signing key verifies with new trust root")
        add("old-root-rejects-new-signature", not bool(old_rejects_new.get("ok")), "old trust root rejects new signatures")
    ok = all(check["ok"] for check in checks)
    payload = {
        "schema_version": 1,
        "command": "release-key-rotation-drill",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": "Release key rotation drill passed." if ok else "Release key rotation drill failed.",
        "release_dir": str(root),
        "work_dir": str(drill_root),
        "checks": checks,
    }
    if temp_context is not None:
        temp_context.cleanup()
        payload["work_dir"] = None
    return payload

def release_claim_consistency_gate(
    release_dir: str | Path,
    *,
    evidence_dir: str | Path | None = None,
    require_windows_current_source: bool = True,
) -> dict[str, Any]:
    root = Path(release_dir).resolve()
    evidence_root = Path(evidence_dir).resolve() if evidence_dir else root
    checks: list[dict[str, Any]] = []

    def add(check_id: str, ok: bool, message: str, **extra: Any) -> None:
        item: dict[str, Any] = {"id": check_id, "ok": ok, "message": message}
        item.update(extra)
        checks.append(item)

    manifest_path = root / "release-manifest.json"
    manifest: dict[str, Any] = {}
    artifact_ids: set[str] = set()
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifact_ids = {
                artifact.get("id")
                for release in manifest.get("releases", [])
                for artifact in release.get("artifacts", [])
                if artifact.get("id")
            }
            add("release-manifest-present", True, "release manifest is present")
        except Exception as exc:
            add("release-manifest-json", False, f"release manifest is invalid: {exc}")
    else:
        add("release-manifest-present", False, "release manifest is missing")

    required_artifacts = {
        "debian-managed-linux": ["cli-linux-amd64-clang", "toolchain-linux-amd64-clang"],
        "windows-msys2-managed": ["cli-windows-amd64-msys2-clang64", "toolchain-windows-amd64-msys2-clang64"],
    }
    for claim, ids in required_artifacts.items():
        missing = [artifact_id for artifact_id in ids if artifact_id not in artifact_ids]
        add(f"artifacts:{claim}", not missing, f"{claim} has required artifacts", missing=missing)

    bundle_path = evidence_root / "release-evidence-bundle.json"
    if bundle_path.exists() and require_windows_current_source:
        ok, summary, _payload = _load_json_evidence(bundle_path)
        add("release-evidence-bundle", ok, summary, path=str(bundle_path))

    smoke_files = {
        "debian-otvm-smoke": evidence_root / "otvm-debian-13-gnome-wayland-smoke.json",
        "openbsd-otvm-smoke": evidence_root / "otvm-openbsd-7.8-fvwm-smoke.json",
        "windows-otvm-smoke": evidence_root / "otvm-windows-2022-smoke.json",
    }
    for check_id, path in smoke_files.items():
        ok, summary, _payload = _load_json_evidence(path)
        add(check_id, ok, summary, path=str(path))

    if require_windows_current_source:
        marker = evidence_root / "windows-current-source-artifact.json"
        ok, summary, _payload = _load_json_evidence(marker)
        add("windows-current-source-artifact", ok, summary, path=str(marker))

    ok = all(check["ok"] for check in checks)
    return {
        "schema_version": 1,
        "command": "release-claim-consistency-gate",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": "Release claims are consistent with artifacts and evidence." if ok else "Release claims are missing artifact or evidence support.",
        "release_dir": str(root),
        "evidence_dir": str(evidence_root),
        "checks": checks,
    }


def controlled_release_gate(
    release_dir: str | Path,
    *,
    package_index_path: str | Path | None = None,
    release_trust_root: str | Path | None = None,
    package_index_trust_root: str | Path | None = None,
    allow_unsigned_package_index: bool = False,
    tools_xctest_packages_dir: str | Path | None = None,
    tools_xctest_evidence_dir: str | Path | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    if release_trust_root is None:
        release_gate = release_trust_gate(release_dir, require_signatures=True, trusted_public_key_path=None)
        checks.append({
            "id": "release-trust-root-present",
            "ok": False,
            "summary": "A production controlled release requires an explicit release trust root.",
            "payload": {"trusted_public_key": None},
        })
    else:
        release_gate = release_trust_gate(release_dir, trusted_public_key_path=release_trust_root)
    checks.append({
        "id": "release-trust-gate",
        "ok": release_gate["ok"],
        "summary": release_gate["summary"],
        "payload": release_gate,
    })
    if package_index_path is not None:
        if not allow_unsigned_package_index and package_index_trust_root is None:
            checks.append({
                "id": "package-index-trust-root-present",
                "ok": False,
                "summary": "A production controlled release requires an explicit package-index trust root.",
                "payload": {"trusted_public_key": None},
            })
        package_gate = package_index_trust_gate(
            package_index_path,
            require_signatures=not allow_unsigned_package_index,
            trusted_public_key_path=package_index_trust_root,
        )
        checks.append({
            "id": "package-index-trust-gate",
            "ok": package_gate["ok"],
            "summary": package_gate["summary"],
            "payload": package_gate,
        })
    if tools_xctest_packages_dir is not None:
        xctest_gate = tools_xctest_release_gate(tools_xctest_packages_dir, evidence_dir=tools_xctest_evidence_dir)
        checks.append({
            "id": "tools-xctest-release-gate",
            "ok": xctest_gate["ok"],
            "summary": xctest_gate["summary"],
            "payload": xctest_gate,
        })
    ok = all(check["ok"] for check in checks)
    return {
        "schema_version": 1,
        "command": "controlled-release-gate",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": "Controlled release gate passed." if ok else "Controlled release gate failed.",
        "release_dir": str(Path(release_dir).resolve()),
        "package_index_path": str(Path(package_index_path).resolve()) if package_index_path else None,
        "tools_xctest_packages_dir": str(Path(tools_xctest_packages_dir).resolve()) if tools_xctest_packages_dir else None,
        "tools_xctest_evidence_dir": str(Path(tools_xctest_evidence_dir).resolve()) if tools_xctest_evidence_dir else None,
        "checks": checks,
    }


def phase12_production_hardening_status(
    *,
    release_dir: str | Path | None = None,
    package_index_path: str | Path | None = None,
    release_trust_root: str | Path | None = None,
    package_index_trust_root: str | Path | None = None,
    smoke_report_paths: list[str | Path] | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(check_id: str, ok: bool, summary: str, payload: dict[str, Any] | None = None) -> None:
        item: dict[str, Any] = {"id": check_id, "ok": ok, "summary": summary}
        if payload is not None:
            item["payload"] = payload
        checks.append(item)

    if release_dir is None:
        add("release-dir-supplied", False, "A release directory is required for production hardening.")
    else:
        add("release-dir-supplied", True, "A release directory was supplied.")
        controlled = controlled_release_gate(
            release_dir,
            package_index_path=package_index_path,
            release_trust_root=release_trust_root,
            package_index_trust_root=package_index_trust_root,
        )
        add("controlled-release-gate", bool(controlled.get("ok")), controlled.get("summary", "Controlled release gate evaluated."), controlled)
        rotation = release_key_rotation_drill(release_dir)
        add("release-key-rotation-drill", bool(rotation.get("ok")), rotation.get("summary", "Release key rotation drill evaluated."), rotation)

    phase26 = phase26_exit_status(smoke_report_paths or None)
    add("host-backed-smoke-evidence", bool(phase26.get("ok")), phase26.get("summary", "Host-backed smoke evidence evaluated."), phase26)

    ok = all(check["ok"] for check in checks)
    return {
        "schema_version": 1,
        "command": "phase12-production-hardening-status",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": "Phase 12 production hardening is complete." if ok else "Phase 12 production hardening still has blockers.",
        "checks": checks,
    }


def _report_has_passing_scenario(report: dict[str, Any], scenario_id: str) -> bool:
    return any(
        scenario.get("scenario_id") == scenario_id and bool(scenario.get("ok"))
        for scenario in report.get("scenario_reports", [])
    )


def phase13_update_hardening_status(
    *,
    smoke_report_paths: list[str | Path] | None = None,
    update_all_evidence_path: str | Path | None = None,
    release_dir: str | Path | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(check_id: str, ok: bool, summary: str, payload: dict[str, Any] | None = None) -> None:
        item: dict[str, Any] = {"id": check_id, "ok": ok, "summary": summary}
        if payload is not None:
            item["payload"] = payload
        checks.append(item)

    report_paths = smoke_report_paths or []
    if report_paths:
        reports = [json.loads(Path(path).read_text(encoding="utf-8")) for path in report_paths]
        gate = evaluate_release_gate(gate_id="dogfood", report_paths=report_paths)
        add("old-to-new-update-smoke-gate", bool(gate.get("ok")), gate.get("summary", "Update smoke gate evaluated."), gate)
        update_reports = [report for report in reports if _report_has_passing_scenario(report, "self-update-cli-only")]
        add(
            "self-update-cli-only-live-evidence",
            bool(update_reports),
            "At least one live smoke report proves the self-update CLI-only scenario." if update_reports else "No live smoke report proves the self-update CLI-only scenario.",
        )
    else:
        add("old-to-new-update-smoke-gate", False, "Live old-to-new smoke reports are required.")
        add("self-update-cli-only-live-evidence", False, "No live smoke report proves the self-update CLI-only scenario.")

    if update_all_evidence_path is None:
        add("update-all-production-like-evidence", False, "A production-like update all --yes evidence JSON file is required.")
    else:
        ok, summary, payload = _load_json_evidence(Path(update_all_evidence_path))
        add("update-all-production-like-evidence", ok, summary, payload)

    if release_dir is None:
        add("signed-metadata-key-mismatch-drill", False, "A release directory is required for signed metadata/key-mismatch drills.")
    else:
        rotation = release_key_rotation_drill(release_dir)
        add("signed-metadata-key-mismatch-drill", bool(rotation.get("ok")), rotation.get("summary", "Signed metadata/key-mismatch drill evaluated."), rotation)

    ok = all(check["ok"] for check in checks)
    return {
        "schema_version": 1,
        "command": "phase13-update-hardening-status",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": "Phase 13 update hardening is complete." if ok else "Phase 13 update hardening still has blockers.",
        "checks": checks,
    }


def stage_release_assets(
    version: str,
    output_dir: str | Path,
    base_url: str,
    *,
    cli_inputs: dict[str, str | Path] | None = None,
    toolchain_inputs: dict[str, str | Path] | None = None,
    reused_toolchain_artifacts: dict[str, dict[str, Any] | str | Path] | None = None,
    channel: str = "stable",
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    release_dir = output_root / channel / version
    release_dir.mkdir(parents=True, exist_ok=True)

    cli_inputs = cli_inputs or {}
    toolchain_inputs = toolchain_inputs or {}
    reused_toolchain_artifacts = reused_toolchain_artifacts or {}
    artifacts: list[dict[str, Any]] = []
    checksums: list[dict[str, str]] = []

    for target in tier1_targets():
        if not target["publish"]:
            continue
        target_artifacts: list[dict[str, Any]] = []
        for kind, inputs in (("cli", cli_inputs), ("toolchain", toolchain_inputs)):
            input_value = inputs.get(target["id"])
            if input_value is None:
                continue
            source = Path(input_value).resolve()
            if not source.exists():
                raise FileNotFoundError(source)
            filename = _artifact_filename(kind, target["id"], version)
            archive_path = release_dir / filename
            root_name = _artifact_basename(kind, target["id"], version)
            if source.is_dir():
                _archive_directory(source, archive_path, root_name)
            else:
                _archive_file(source, archive_path, root_name)

            artifact = {
                "id": f"{kind}-{target['id']}",
                "kind": kind,
                "version": version,
                "os": target["os"],
                "arch": target["arch"],
                "compiler_family": target["compiler_family"],
                "toolchain_flavor": target["toolchain_flavor"],
                "objc_runtime": "libobjc2" if target["compiler_family"] != "msvc" else "unknown",
                "objc_abi": "modern" if target["compiler_family"] != "msvc" else "unknown",
                "required_features": [] if kind == "cli" else (["blocks"] if target["compiler_family"] != "msvc" else []),
                "format": "zip" if target["os"] == "windows" else "tar.gz",
                "url": _artifact_url(base_url, version, filename),
                "sha256": _sha256(archive_path),
                "integrity": {"sha256": _sha256(archive_path)},
                "size": archive_path.stat().st_size,
                "filename": filename,
                "supported_distributions": target.get("supported_distributions", []),
                "supported_os_versions": target.get("supported_os_versions", []),
                "portability_policy": target.get("portability_policy", "platform-wide"),
                "published": True,
            }
            if kind == "toolchain":
                lock_file = "source-lock.json" if target["strategy"] == "source-build" else "input-manifest.json"
                artifact["metadata"] = {
                    "lock_file": lock_file if (source / lock_file).exists() else None,
                    "component_inventory": "component-inventory.json" if (source / "component-inventory.json").exists() else None,
                    "toolchain_manifest": "toolchain-manifest.json" if (source / "toolchain-manifest.json").exists() else None,
                    "assembly_metadata": "toolchain-assembly.json" if (source / "toolchain-assembly.json").exists() else None,
                    "source_policy": "source-build" if target["strategy"] == "source-build" else target["strategy"],
                }
            target_artifacts.append(artifact)
            checksums.append({"filename": filename, "sha256": artifact["sha256"]})

        reused_toolchain = reused_toolchain_artifacts.get(target["id"])
        if reused_toolchain is not None and target["id"] not in toolchain_inputs:
            if isinstance(reused_toolchain, dict):
                reused = reusable_artifact_reference(
                    reused_toolchain,
                    expected_kind="toolchain",
                    expected_target_id=target["id"],
                )
            else:
                reused = _load_reusable_artifact(
                    reused_toolchain,
                    expected_kind="toolchain",
                    expected_target_id=target["id"],
                )
            reused.setdefault("supported_distributions", target.get("supported_distributions", []))
            reused.setdefault("supported_os_versions", target.get("supported_os_versions", []))
            reused.setdefault("portability_policy", target.get("portability_policy", "platform-wide"))
            target_artifacts.append(reused)

        toolchain_artifact = next((artifact for artifact in target_artifacts if artifact.get("kind") == "toolchain"), None)
        for artifact in target_artifacts:
            if artifact.get("kind") == "cli" and toolchain_artifact is not None:
                artifact["requires_toolchain"] = {
                    "artifact_id": toolchain_artifact["id"],
                    "version": toolchain_artifact.get("version"),
                    "sha256": toolchain_artifact.get("sha256"),
                    "reused": bool(toolchain_artifact.get("reused")),
                }
                artifact["layer_update_policy"] = {
                    "kind": "cli-layer",
                    "toolchain_rebuild_required": False,
                    "toolchain_reuse_allowed": True,
                }
        artifacts.extend(target_artifacts)

    manifest = {
        "schema_version": 1,
        "channel": channel,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "metadata_version": 1,
        "expires_at": "TBD",
        "trust": {
            "root_version": 1,
            "signature_policy": "single-role-v1",
            "signatures": [],
            "revoked_artifacts": [],
        },
        "releases": [
            {
                "version": version,
                "status": "active",
                "artifacts": artifacts,
            }
        ],
    }
    manifest_path = release_dir / "release-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    provenance_path = write_release_provenance(release_dir)
    checksums.append({"filename": provenance_path.name, "sha256": _sha256(provenance_path)})
    checksums_path = release_dir / "SHA256SUMS"
    checksums_path.write_text(
        "".join(f"{entry['sha256']}  {entry['filename']}\n" for entry in checksums),
        encoding="utf-8",
    )

    return {
        "schema_version": 1,
        "command": "stage-release",
        "ok": True,
        "status": "ok",
        "summary": "Release assets staged.",
        "release_dir": str(release_dir),
        "manifest_path": str(manifest_path),
        "checksums_path": str(checksums_path),
        "provenance_path": str(provenance_path),
        "artifacts": artifacts,
    }


def verify_release_directory(release_dir: str | Path) -> dict[str, Any]:
    root = Path(release_dir).resolve()
    manifest_path = root / "release-manifest.json"
    checksums_path = root / "SHA256SUMS"
    if not manifest_path.exists():
        return {
            "schema_version": 1,
            "command": "verify-release",
            "ok": False,
            "status": "error",
            "summary": "Release manifest is missing.",
            "release_dir": str(root),
        }
    if not checksums_path.exists():
        return {
            "schema_version": 1,
            "command": "verify-release",
            "ok": False,
            "status": "error",
            "summary": "SHA256SUMS is missing.",
            "release_dir": str(root),
        }

    manifest = json.loads(manifest_path.read_text())
    artifacts = manifest["releases"][0]["artifacts"]
    checksum_map: dict[str, str] = {}
    for line in checksums_path.read_text().splitlines():
        if not line.strip():
            continue
        sha256, filename = line.split("  ", 1)
        checksum_map[filename] = sha256

    results: list[dict[str, Any]] = []
    ok = True
    for artifact in artifacts:
        filename = artifact.get("filename")
        if artifact.get("reused") and not filename:
            reference_errors = _artifact_immutable_reference_errors(artifact)
            reference_ok = not reference_errors
            results.append(
                {
                    "id": artifact.get("id"),
                    "reused": True,
                    "local_file_required": False,
                    "immutable_reference_ok": reference_ok,
                    "errors": reference_errors,
                }
            )
            ok = ok and reference_ok
            continue
        if not filename:
            results.append(
                {
                    "id": artifact.get("id"),
                    "reused": bool(artifact.get("reused")),
                    "local_file_required": True,
                    "exists": False,
                    "sha256_matches": False,
                    "errors": ["artifact is missing filename"],
                }
            )
            ok = False
            continue
        asset_path = root / filename
        exists = asset_path.exists()
        actual_sha = _sha256(asset_path) if exists else None
        checksum_ok = exists and checksum_map.get(filename) == actual_sha == artifact["sha256"]
        results.append(
            {
                "filename": filename,
                "exists": exists,
                "sha256_matches": checksum_ok,
            }
        )
        ok = ok and checksum_ok

    return {
        "schema_version": 1,
        "command": "verify-release",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": "Release directory verified." if ok else "Release directory verification failed.",
        "release_dir": str(root),
        "results": results,
    }


def _extract_archive(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if archive_path.suffix == ".zip":
        with ZipFile(archive_path) as archive:
            archive.extractall(destination)
        return
    with tarfile.open(archive_path, "r:gz") as archive:
        archive.extractall(destination, filter="data")


def _normalized_archive_names(archive_path: Path) -> list[str]:
    if archive_path.suffix == ".zip":
        with ZipFile(archive_path) as archive:
            names = archive.namelist()
    else:
        with tarfile.open(archive_path, "r:gz") as archive:
            names = archive.getnames()
    return ["/" + name.replace("\\", "/").strip("/").lower() for name in names]


def _archive_has_any(normalized_names: list[str], patterns: list[str]) -> bool:
    for pattern in patterns:
        regex = re.compile(pattern)
        if any(regex.search(name) for name in normalized_names):
            return True
    return False


def _pacman_local_db_missing_desc(normalized_names: list[str]) -> list[str]:
    packages: dict[str, set[str]] = {}
    for name in normalized_names:
        match = re.search(r"/var/lib/pacman/local/([^/]+)/([^/]+)$", name)
        if match is None:
            continue
        packages.setdefault(match.group(1), set()).add(match.group(2))
    return sorted(package for package, files in packages.items() if "desc" not in files)


def toolchain_archive_audit(archive_path: str | Path, *, target_id: str | None = None) -> dict[str, Any]:
    root = Path(archive_path).resolve()
    if not root.exists():
        return {
            "schema_version": 1,
            "command": "toolchain-archive-audit",
            "ok": False,
            "status": "error",
            "summary": "Toolchain archive is missing.",
            "archive_path": str(root),
        }

    inferred_target = target_id
    if inferred_target is None:
        lowered = root.name.lower()
        for target in tier1_targets():
            token = target["id"].lower()
            if token in lowered and "toolchain" in lowered:
                inferred_target = target["id"]
                break

    normalized_names = _normalized_archive_names(root)
    checks: list[dict[str, Any]] = []

    def add_check(check_id: str, title: str, patterns: list[str], *, required: bool = True) -> None:
        ok = _archive_has_any(normalized_names, patterns)
        checks.append(
            {
                "id": check_id,
                "title": title,
                "required": required,
                "ok": ok,
                "patterns": patterns,
            }
        )

    if inferred_target == "windows-amd64-msys2-clang64":
        add_check("gnustep_config", "Managed gnustep-config entrypoint is present.", [r"/bin/gnustep-config$"])
        add_check("clang", "Managed clang compiler entrypoint is present.", [r"/bin/clang(\.exe)?$", r"/clang64/bin/clang(\.exe)?$"])
        add_check("clang64_prefix", "MSYS2 clang64 prefix is preserved for GNUstep Make shell builds.", [r"/clang64/bin/clang(\.exe)?$"])
        add_check("bash", "Managed MSYS2 shell entrypoint is present.", [r"/usr/bin/bash(\.exe)?$", r"/usr/bin/sh(\.exe)?$"])
        add_check("make", "Managed make entrypoint is present.", [r"/bin/(g?make)(\.exe)?$", r"/usr/bin/(g?make)(\.exe)?$"])
        add_check("sha256sum", "Managed checksum utility is present.", [r"/usr/bin/sha256sum(\.exe)?$"])
        add_check("msys_runtime", "MSYS2 runtime DLL for usr/bin developer tools is present.", [r"/usr/bin/msys-2\.0\.dll$"])
        add_check("openapp", "GNUstep openapp launcher is present.", [r"/clang64/bin/openapp$"])
        add_check("common_make", "GNUstep Make common.make is present.", [r"/clang64/share/GNUstep/Makefiles/common\.make$", r"/common\.make$"])
        add_check("tool_make", "GNUstep Make tool.make is present.", [r"/clang64/share/GNUstep/Makefiles/tool\.make$", r"/tool\.make$"])
        add_check("msys_profile", "MSYS root profile configuration is present.", [r"/etc/profile$"])
        add_check("pacman_local_db", "MSYS2 local package metadata is present for provenance/debugging.", [r"/var/lib/pacman/local/"])
        missing_desc = _pacman_local_db_missing_desc(normalized_names)
        checks.append(
            {
                "id": "pacman_local_db_integrity",
                "title": "Every MSYS2 local package database entry includes a desc file.",
                "required": True,
                "ok": len(missing_desc) == 0,
                "patterns": [r"/var/lib/pacman/local/<package>/desc"],
                "missing_desc_packages": missing_desc,
            }
        )
        add_check("gnustep_env", "GNUstep environment activation script is present.", [r"/gnustep\.(sh|bat|ps1)$"], required=False)
    elif inferred_target in {"linux-amd64-clang", "linux-ubuntu2404-amd64-clang", "linux-arm64-clang", "openbsd-amd64-clang", "openbsd-arm64-clang"}:
        add_check("runtime_tools", "Managed tool directory is present.", [r"/system/tools/", r"/tools/"])
        add_check("source_lock", "Source-built managed toolchain source lock is present.", [r"/source-lock\.json$"])
        add_check("component_inventory", "Managed toolchain component inventory is present.", [r"/component-inventory\.json$"])
        add_check("toolchain_manifest", "Managed toolchain manifest is present.", [r"/toolchain-manifest\.json$"])
    else:
        checks.append(
            {
                "id": "target-specific-audit",
                "title": "No target-specific archive audit rules are defined for this artifact.",
                "required": False,
                "ok": True,
                "patterns": [],
            }
        )

    ok = all(check["ok"] for check in checks if check["required"])
    if inferred_target == "windows-amd64-msys2-clang64" and not ok:
        summary = "Windows MSYS2 toolchain archive is missing required build-capable components."
    else:
        summary = "Toolchain archive audit completed." if ok else "Toolchain archive audit failed."

    return {
        "schema_version": 1,
        "command": "toolchain-archive-audit",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": summary,
        "archive_path": str(root),
        "target_id": inferred_target,
        "checks": checks,
    }


def qualify_release_install(release_dir: str | Path, install_root: str | Path) -> dict[str, Any]:
    verification = verify_release_directory(release_dir)
    if not verification["ok"]:
        return verification

    root = Path(release_dir).resolve()
    destination = Path(install_root).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((root / "release-manifest.json").read_text())
    installs: list[dict[str, Any]] = []
    for artifact in manifest["releases"][0]["artifacts"]:
        filename = artifact.get("filename")
        if artifact.get("reused") and not filename:
            installs.append(
                {
                    "artifact_id": artifact["id"],
                    "reused": True,
                    "install_path": None,
                    "summary": "Reused immutable artifact reference is not extracted from the current release directory.",
                }
            )
            continue
        if not filename:
            return {
                "schema_version": 1,
                "command": "qualify-release",
                "ok": False,
                "status": "error",
                "summary": "Release artifact is missing filename for local qualification.",
                "artifact_id": artifact.get("id"),
            }
        asset_path = root / filename
        extract_root = destination / artifact["id"]
        if extract_root.exists():
            shutil.rmtree(extract_root)
        _extract_archive(asset_path, extract_root)
        installs.append(
            {
                "artifact_id": artifact["id"],
                "filename": filename,
                "install_path": str(extract_root),
            }
        )

    return {
        "schema_version": 1,
        "command": "qualify-release",
        "ok": True,
        "status": "ok",
        "summary": "Release assets verified and extracted into the qualification root.",
        "release_dir": str(root),
        "install_root": str(destination),
        "installs": installs,
    }


def qualify_full_cli_handoff(release_dir: str | Path, install_root: str | Path) -> dict[str, Any]:
    release_root = Path(release_dir).resolve()
    manifest_path = release_root / "release-manifest.json"
    install_path = Path(install_root).resolve()
    payload, exit_code = execute_setup(
        scope="user",
        manifest_path=str(manifest_path),
        install_root=str(install_path),
    )
    if exit_code != 0 or not payload.get("ok", False):
        return {
            "schema_version": 1,
            "command": "qualify-full-cli-handoff",
            "ok": False,
            "status": "error",
            "summary": "Bootstrap-to-full handoff qualification failed during setup.",
            "release_dir": str(release_root),
            "install_root": str(install_path),
            "setup_exit_code": exit_code,
            "setup_payload": payload,
        }

    binary_path = install_path / "bin" / "gnustep"
    runtime_binary = install_path / "libexec" / "gnustep-cli" / "bin" / "gnustep"
    runtime_root = install_path / "libexec" / "gnustep-cli"
    state_path = install_path / "state" / "cli-state.json"
    checks: list[dict[str, Any]] = []

    def add_check(check_id: str, ok: bool, message: str) -> None:
        checks.append(
            {
                "id": check_id,
                "ok": ok,
                "message": message,
            }
        )

    add_check("install.binary", binary_path.exists(), "Installed CLI binary is present.")
    add_check("install.binary_executable", os.access(binary_path, os.X_OK), "Installed CLI binary is executable.")
    add_check("install.runtime_binary", runtime_binary.exists(), "Installed runtime CLI binary is present under libexec/gnustep-cli/bin.")
    add_check(
        "install.runtime_bundle",
        runtime_root.exists(),
        "Installed CLI runtime bundle is present under libexec/gnustep-cli.",
    )
    add_check("install.state_file", state_path.exists(), "Installed CLI state file exists.")
    add_check(
        "install.no_python_runtime_scripts",
        not (runtime_root / "scripts" / "internal").exists(),
        "Installed CLI bundle does not contain the bundled Python scripts/internal runtime.",
    )
    add_check(
        "install.no_python_runtime_modules",
        not (runtime_root / "src" / "gnustep_cli_shared").exists(),
        "Installed CLI bundle does not contain the bundled gnustep_cli_shared Python runtime.",
    )
    add_check(
        "install.runtime_examples",
        (runtime_root / "examples").exists(),
        "Installed CLI runtime bundle includes bundled example manifests.",
    )
    if state_path.exists():
        try:
            state_payload = json.loads(state_path.read_text())
        except json.JSONDecodeError:
            state_payload = None
        add_check(
            "install.state_file_valid",
            isinstance(state_payload, dict) and state_payload.get("schema_version") == 1 and state_payload.get("status") == "healthy",
            "Installed CLI state file is valid JSON with healthy status.",
        )
    else:
        add_check("install.state_file_valid", False, "Installed CLI state file could not be validated because it is missing.")

    command_results: list[dict[str, Any]] = []
    for args, expected in (
        (["--version"], "0.1.0-dev"),
        (["--help"], "gnustep"),
    ):
        if not os.access(binary_path, os.X_OK):
            command_results.append(
                {
                    "args": args,
                    "ran": False,
                    "ok": False,
                    "stdout": "",
                    "stderr": "Installed CLI binary is not executable.",
                    "exit_status": None,
                }
            )
            continue
        proc = subprocess.run(
            [str(binary_path), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            cwd=str(install_path),
        )
        command_results.append(
            {
                "args": args,
                "ran": True,
                "ok": proc.returncode == 0 and expected in proc.stdout,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "exit_status": proc.returncode,
            }
        )

    ok = all(check["ok"] for check in checks) and all(result["ok"] for result in command_results)
    return {
        "schema_version": 1,
        "command": "qualify-full-cli-handoff",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": (
            "Bootstrap-to-full handoff qualification succeeded."
            if ok
            else "Bootstrap-to-full handoff qualification failed."
        ),
        "release_dir": str(release_root),
        "install_root": str(install_path),
        "setup_payload": payload,
        "checks": checks,
        "command_results": command_results,
    }


def github_release_plan(
    repo: str,
    version: str,
    release_dir: str | Path,
    *,
    channel: str = "stable",
    title: str | None = None,
) -> dict[str, Any]:
    root = Path(release_dir).resolve()
    tag = f"v{version}"
    title = title or f"GNUstep CLI {version}"
    asset_paths = sorted(str(path) for path in root.iterdir() if path.is_file())
    create_command = ["gh", "release", "create", tag, "--repo", repo, "--title", title]
    if channel != "stable":
        create_command.append("--prerelease")
    create_command.extend(asset_paths)
    return {
        "schema_version": 1,
        "command": "github-release-plan",
        "ok": True,
        "status": "ok",
        "repo": repo,
        "tag": tag,
        "release_dir": str(root),
        "assets": asset_paths,
        "command_line": create_command,
    }


def publish_github_release(
    repo: str,
    version: str,
    release_dir: str | Path,
    *,
    channel: str = "stable",
    title: str | None = None,
) -> dict[str, Any]:
    plan = github_release_plan(repo, version, release_dir, channel=channel, title=title)
    tag = plan["tag"]
    title = title or f"GNUstep CLI {version}"
    prerelease_args = ["--prerelease"] if channel != "stable" else []
    view_proc = subprocess.run(
        ["gh", "release", "view", tag, "--repo", repo],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    commands = []
    stdout_parts = []
    stderr_parts = []

    if view_proc.returncode == 0:
        edit_command = ["gh", "release", "edit", tag, "--repo", repo, "--title", title, *prerelease_args]
        upload_command = ["gh", "release", "upload", tag, "--repo", repo, "--clobber", *plan["assets"]]
        commands.extend([edit_command, upload_command])
    else:
        create_command = list(plan["command_line"])
        commands.append(create_command)

    ok = True
    exit_status = 0
    for command in commands:
        proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        stdout_parts.append(proc.stdout)
        stderr_parts.append(proc.stderr)
        if proc.returncode != 0:
            ok = False
            exit_status = proc.returncode
            break

    plan["executed_commands"] = commands
    plan["release_existed"] = view_proc.returncode == 0
    plan["stdout"] = "".join(stdout_parts)
    plan["stderr"] = "".join(stderr_parts)
    plan["exit_status"] = exit_status
    plan["ok"] = ok
    plan["status"] = "ok" if ok else "error"
    plan["summary"] = "GitHub Release published." if ok else "GitHub Release publication failed."
    return plan



def package_tools_xctest_artifact(
    output_dir: str | Path,
    *,
    source_dir: str | Path | None = None,
    source_url: str = "https://github.com/gnustep/tools-xctest.git",
    source_revision: str | None = None,
    installed_root: str | Path | None = None,
    target_id: str = "linux-amd64-clang",
    version: str = "0.1.0",
    rebuild: bool = False,
) -> dict[str, Any]:
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    work_root = out / "work"
    source = Path(source_dir).resolve() if source_dir else work_root / "tools-xctest-src"
    install_root = Path(installed_root).resolve() if installed_root else Path.home() / "GNUstep"
    commands: list[list[str]] = []

    if not source.exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        commands.append(["git", "clone", source_url, str(source)])
        clone = subprocess.run(commands[-1], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if clone.returncode != 0:
            return {"schema_version": 1, "command": "package-tools-xctest-artifact", "ok": False, "status": "error", "summary": "Failed to clone tools-xctest source.", "stdout": clone.stdout, "stderr": clone.stderr, "commands": commands}
    if source_revision:
        commands.append(["git", "-C", str(source), "checkout", source_revision])
        checkout = subprocess.run(commands[-1], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if checkout.returncode != 0:
            return {"schema_version": 1, "command": "package-tools-xctest-artifact", "ok": False, "status": "error", "summary": "Failed to check out tools-xctest source revision.", "stdout": checkout.stdout, "stderr": checkout.stderr, "commands": commands}
    revision_proc = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    revision = revision_proc.stdout.strip() if revision_proc.returncode == 0 else source_revision or "unknown"

    if rebuild:
        makefiles = os.environ.get("GNUSTEP_MAKEFILES_DIR", "/usr/share/GNUstep/Makefiles")
        gcc_headers = os.environ.get("GCC_OBJC_HEADERS", "/usr/lib/gcc/x86_64-linux-gnu/14/include")
        build_script = "set -e\n. \"{}/GNUstep.sh\"\nmake -C \"{}\" clean >/dev/null || true\nmake -C \"{}\" CC=clang OBJC=clang ADDITIONAL_OBJCFLAGS=\"-I{}\"\nmake -C \"{}\" CC=clang OBJC=clang ADDITIONAL_OBJCFLAGS=\"-I{}\" GNUSTEP_INSTALLATION_DOMAIN=USER install\n".format(makefiles, source, source, gcc_headers, source, gcc_headers)
        commands.append(["sh", "-c", build_script])
        built = subprocess.run(commands[-1], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if built.returncode != 0:
            return {"schema_version": 1, "command": "package-tools-xctest-artifact", "ok": False, "status": "error", "summary": "Failed to build and install tools-xctest.", "stdout": built.stdout, "stderr": built.stderr, "commands": commands}

    required = [install_root / "Tools" / "xctest", install_root / "Library" / "Headers" / "XCTest", install_root / "Library" / "Libraries" / "libXCTest.so"]
    missing = [str(item) for item in required if not item.exists()]
    if missing:
        return {"schema_version": 1, "command": "package-tools-xctest-artifact", "ok": False, "status": "error", "summary": "Installed tools-xctest files are missing; run the tools-xctest install first or pass --rebuild.", "missing": missing, "installed_root": str(install_root), "commands": commands}

    source_archive = out / f"tools-xctest-source-{revision[:12]}.tar.gz"
    archive_command = ["git", "-C", str(source), "archive", "--format=tar.gz", "-o", str(source_archive), "HEAD"]
    archive_proc = subprocess.run(archive_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    commands.append(archive_command)
    if archive_proc.returncode != 0:
        return {"schema_version": 1, "command": "package-tools-xctest-artifact", "ok": False, "status": "error", "summary": "Failed to archive tools-xctest source.", "stdout": archive_proc.stdout, "stderr": archive_proc.stderr, "commands": commands}

    package_root = out / "staging" / "tools-xctest"
    if package_root.exists():
        shutil.rmtree(package_root)
    (package_root / "bin").mkdir(parents=True)
    (package_root / "libexec").mkdir(parents=True)
    (package_root / "Library" / "Headers").mkdir(parents=True)
    (package_root / "Library" / "Libraries").mkdir(parents=True)
    shutil.copy2(install_root / "Tools" / "xctest", package_root / "libexec" / "xctest")
    launcher = package_root / "bin" / "xctest"
    launcher.write_text(
        "#!/bin/sh\n"
        "set -e\n"
        "bin_dir=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n"
        "package_root=$(CDPATH= cd -- \"$bin_dir/..\" && pwd)\n"
        "managed_root=$(CDPATH= cd -- \"$package_root/../..\" && pwd)\n"
        "runtime_libs=$package_root/Library/Libraries:$managed_root/Local/Library/Libraries:$managed_root/System/Library/Libraries:$managed_root/lib:$managed_root/lib64\n"
        "export LD_LIBRARY_PATH=\"$runtime_libs${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\"\n"
        "exec \"$package_root/libexec/xctest\" \"$@\"\n"
    )
    launcher.chmod(0o755)
    shutil.copytree(install_root / "Library" / "Headers" / "XCTest", package_root / "Library" / "Headers" / "XCTest")
    for lib in sorted((install_root / "Library" / "Libraries").glob("libXCTest.so*")):
        shutil.copy2(lib, package_root / "Library" / "Libraries" / lib.name)

    artifact_filename = f"tools-xctest-{target_id}-{version}.tar.gz"
    artifact_path = out / artifact_filename
    if artifact_path.exists():
        artifact_path.unlink()
    _archive_directory(package_root, artifact_path, ".")
    source_sha = _sha256(source_archive)
    artifact_sha = _sha256(artifact_path)
    return {
        "schema_version": 1,
        "command": "package-tools-xctest-artifact",
        "ok": True,
        "status": "ok",
        "summary": "tools-xctest package artifact generated.",
        "package_id": "org.gnustep.tools-xctest",
        "version": version,
        "target": target_id,
        "source": {"type": "git", "url": source_url, "revision": revision, "archive": str(source_archive), "sha256": source_sha},
        "artifact": {"id": f"tools-xctest-{target_id}", "path": str(artifact_path), "filename": artifact_filename, "sha256": artifact_sha, "format": "tar.gz"},
        "installed_root": str(install_root),
        "commands": commands,
    }

def package_artifact_build_plan(packages_dir: str | Path) -> dict[str, Any]:
    root = Path(packages_dir).resolve()
    entries: list[dict[str, Any]] = []
    plan_blockers: list[dict[str, str]] = []
    if not root.exists():
        return {
            "schema_version": 1,
            "command": "package-artifact-build-plan",
            "ok": False,
            "status": "error",
            "summary": "Package directory does not exist.",
            "packages_dir": str(root),
        }

    for manifest_path in sorted(root.glob('*/package.json')):
        manifest = json.loads(manifest_path.read_text())
        package_id = manifest["id"]
        source = manifest.get("source", {})
        patches = manifest.get("patches", []) or []
        build = manifest.get("build", {}) or {}
        source_sha = source.get("sha256")
        source_url = source.get("url")
        package_blockers: list[str] = []
        if not source_url:
            package_blockers.append("missing_source_url")
        if not source_sha or str(source_sha).endswith("tbd") or "placeholder" in str(source_sha).lower() or "development" in str(source_sha).lower():
            package_blockers.append("missing_verified_source_digest")
        for patch in patches:
            patch_id = patch.get("id", "") if isinstance(patch, dict) else ""
            patch_sha = patch.get("sha256") if isinstance(patch, dict) else None
            patch_path = patch.get("path") if isinstance(patch, dict) else None
            if not patch_id:
                package_blockers.append("missing_patch_id")
            if not patch_path:
                package_blockers.append("missing_patch_path")
            if not patch_sha or str(patch_sha).endswith("tbd") or "placeholder" in str(patch_sha).lower() or "development" in str(patch_sha).lower():
                package_blockers.append("missing_verified_patch_digest")
        for blocker in sorted(set(package_blockers)):
            plan_blockers.append({"package": package_id, "artifact": "", "code": blocker})
        artifacts = []
        for artifact in manifest.get("artifacts", []):
            artifact_sha = artifact.get("sha256")
            artifact_publishable = artifact.get("publish", True) is not False
            artifact_blockers = list(package_blockers) if artifact_publishable else []
            if artifact_publishable and not artifact.get("url"):
                artifact_blockers.append("missing_artifact_url")
            if artifact_publishable and (not artifact_sha or str(artifact_sha).endswith("tbd") or "placeholder" in str(artifact_sha).lower() or "published-artifact-checksum-tbd" == str(artifact_sha)):
                artifact_blockers.append("missing_published_artifact_digest")
            for blocker in artifact_blockers:
                if blocker not in package_blockers:
                    plan_blockers.append({"package": package_id, "artifact": artifact["id"], "code": blocker})
            artifact_ready = (not artifact_publishable) or len(artifact_blockers) == 0
            artifacts.append(
                {
                    "id": artifact["id"],
                    "os": artifact["os"],
                    "arch": artifact["arch"],
                    "compiler_family": artifact["compiler_family"],
                    "toolchain_flavor": artifact["toolchain_flavor"],
                    "format": artifact.get("format", "tar.gz" if artifact.get("os") != "windows" else "zip"),
                    "source_manifest": str(manifest_path),
                    "source": source,
                    "patches": patches,
                    "build": build,
                    "build_backend": build.get("backend", "unspecified"),
                    "build_invocation": build.get("build", []),
                    "build_from_source": True,
                    "provenance_required": artifact_publishable,
                    "signature_required": artifact_publishable,
                    "source_verified": (not artifact_publishable) or len(package_blockers) == 0,
                    "artifact_verified": (not artifact_publishable) or not any(blocker.startswith("missing_artifact") or blocker.startswith("missing_published") for blocker in artifact_blockers),
                    "production_ready": artifact_ready,
                    "publish": artifact_publishable and artifact_ready,
                    "policy_blockers": artifact_blockers,
                }
            )
        publishable_artifacts = [artifact for artifact in artifacts if artifact.get("publish") is not False or artifact.get("signature_required")]
        package_ready = len(package_blockers) == 0 and all(artifact["production_ready"] for artifact in publishable_artifacts)
        entries.append(
            {
                "id": package_id,
                "version": manifest["version"],
                "kind": manifest["kind"],
                "source": source,
                "patches": patches,
                "build": build,
                "source_type": source.get("type"),
                "source_url": source_url,
                "source_sha256": source_sha,
                "source_verified": len(package_blockers) == 0,
                "provenance_required": True,
                "production_ready": package_ready,
                "dependencies": manifest.get("dependencies", []),
                "policy_blockers": package_blockers,
                "artifacts": artifacts,
            }
        )
    production_ready = len(plan_blockers) == 0 and all(package["production_ready"] for package in entries)

    return {
        "schema_version": 1,
        "command": "package-artifact-build-plan",
        "ok": True,
        "status": "ok",
        "summary": "Package artifact build plan generated." if production_ready else "Package artifact build plan generated with policy blockers.",
        "packages_dir": str(root),
        "production_ready": production_ready,
        "policy_blockers": plan_blockers,
        "packages": entries,
    }




def package_artifact_publication_gate(packages_dir: str | Path) -> dict[str, Any]:
    plan = package_artifact_build_plan(packages_dir)
    checks: list[dict[str, Any]] = []
    if not plan.get("ok"):
        checks.append({
            "id": "package-artifact-build-plan",
            "ok": False,
            "summary": plan.get("summary", "Package artifact build plan failed."),
            "payload": plan,
        })
    else:
        checks.append({
            "id": "package-artifact-build-plan",
            "ok": True,
            "summary": plan.get("summary", "Package artifact build plan generated."),
            "payload": {
                "packages_dir": plan.get("packages_dir"),
                "package_count": len(plan.get("packages", [])),
            },
        })
        checks.append({
            "id": "package-artifacts-production-ready",
            "ok": bool(plan.get("production_ready")),
            "summary": "Package artifacts are production-ready." if plan.get("production_ready") else "Package artifacts have policy blockers and must not be published.",
            "payload": {
                "policy_blockers": plan.get("policy_blockers", []),
                "packages": [
                    {
                        "id": package.get("id"),
                        "production_ready": package.get("production_ready"),
                        "policy_blockers": package.get("policy_blockers", []),
                        "artifacts": [
                            {
                                "id": artifact.get("id"),
                                "production_ready": artifact.get("production_ready"),
                                "policy_blockers": artifact.get("policy_blockers", []),
                            }
                            for artifact in package.get("artifacts", [])
                        ],
                    }
                    for package in plan.get("packages", [])
                ],
            },
        })
    ok = all(check["ok"] for check in checks)
    return {
        "schema_version": 1,
        "command": "package-artifact-publication-gate",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": "Package artifact publication gate passed." if ok else "Package artifact publication gate failed.",
        "packages_dir": str(Path(packages_dir).resolve()),
        "checks": checks,
    }


def _package_digest_is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip().lower()
    if not text:
        return True
    return (
        text.endswith("tbd")
        or "placeholder" in text
        or "development" in text
        or text in {
            "published-artifact-checksum-tbd",
            "planned-artifact-checksum-tbd",
            "tbd",
        }
    )


def tools_xctest_release_gate(packages_dir: str | Path, *, evidence_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(packages_dir).resolve()
    evidence_root = Path(evidence_dir).resolve() if evidence_dir is not None else None
    manifest_path = root / "org.gnustep.tools-xctest" / "package.json"
    blockers: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []
    required_patch_id = "add-apple-style-xctest-cli-filters"
    dogfood_checks = [
        "native install org.gnustep.tools-xctest from a signed package index",
        "xctest binary smoke test",
        "minimal XCTest bundle execution",
        "native remove org.gnustep.tools-xctest cleanup verification",
    ]

    if not manifest_path.exists():
        return {
            "schema_version": 1,
            "command": "tools-xctest-release-gate",
            "ok": False,
            "status": "blocked",
            "summary": "tools-xctest package release gate is blocked.",
            "packages_dir": str(root),
            "evidence_dir": str(evidence_root) if evidence_root else None,
            "package_id": "org.gnustep.tools-xctest",
            "blockers": [
                {
                    "code": "tools_xctest_manifest_missing",
                    "message": "packages/org.gnustep.tools-xctest/package.json is required before tools-xctest can be release-gated.",
                }
            ],
            "targets": [],
            "dogfood_checks": dogfood_checks,
            "next_actions": ["Add the tools-xctest package manifest."],
        }

    manifest = json.loads(manifest_path.read_text())
    patches = manifest.get("patches", []) or []
    patch_by_id = {patch.get("id"): patch for patch in patches if isinstance(patch, dict)}
    declared_patch = patch_by_id.get(required_patch_id)
    if declared_patch is None:
        blockers.append(
            {
                "code": "required_patch_not_declared",
                "artifact": None,
                "message": f"tools-xctest must declare the downstream patch {required_patch_id}.",
            }
        )
    elif _package_digest_is_placeholder(declared_patch.get("sha256")):
        blockers.append(
            {
                "code": "required_patch_digest_missing",
                "artifact": None,
                "message": f"tools-xctest patch {required_patch_id} must have a verified sha256.",
            }
        )

    def load_dogfood_evidence(artifact_id: str | None) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
        if artifact_id is None:
            return "missing", None, {
                "code": "dogfood_evidence_missing",
                "artifact": artifact_id,
                "message": "tools-xctest artifact dogfood evidence is required.",
            }
        if evidence_root is None:
            return "missing", None, {
                "code": "dogfood_evidence_missing",
                "artifact": artifact_id,
                "message": f"{artifact_id} requires native install/smoke/remove dogfood evidence.",
            }
        candidates = [
            evidence_root / "tools-xctest" / f"{artifact_id}.json",
            evidence_root / f"{artifact_id}.json",
        ]
        evidence_path = next((candidate for candidate in candidates if candidate.exists()), None)
        if evidence_path is None:
            return "missing", None, {
                "code": "dogfood_evidence_missing",
                "artifact": artifact_id,
                "message": f"{artifact_id} requires native install/smoke/remove dogfood evidence under {evidence_root}.",
            }
        try:
            evidence = json.loads(evidence_path.read_text())
        except json.JSONDecodeError as exc:
            return "invalid", {"path": str(evidence_path), "error": str(exc)}, {
                "code": "dogfood_evidence_invalid",
                "artifact": artifact_id,
                "message": f"{artifact_id} dogfood evidence is not valid JSON.",
            }
        if evidence.get("ok") is not True:
            return "failed", evidence, {
                "code": "dogfood_evidence_failed",
                "artifact": artifact_id,
                "message": f"{artifact_id} dogfood evidence did not pass.",
            }
        if evidence.get("package_id") != "org.gnustep.tools-xctest" or evidence.get("artifact_id") != artifact_id:
            return "invalid", evidence, {
                "code": "dogfood_evidence_mismatch",
                "artifact": artifact_id,
                "message": f"{artifact_id} dogfood evidence does not match the package and artifact identity.",
            }
        return "accepted", evidence, None

    artifacts = manifest.get("artifacts", []) or []
    if not artifacts:
        blockers.append(
            {
                "code": "no_tools_xctest_artifacts",
                "artifact": None,
                "message": "tools-xctest must declare at least one artifact target.",
            }
        )

    for artifact in artifacts:
        artifact_id = artifact.get("id")
        artifact_status = artifact.get("status", "")
        publishable = artifact.get("publish", True) is not False
        selected_patch_ids = [
            patch.get("id")
            for patch in patches
            if isinstance(patch, dict)
            and (not patch.get("applies_to") or artifact_id in patch.get("applies_to", []))
        ]
        artifact_blockers: list[dict[str, Any]] = []

        if declared_patch is not None and required_patch_id not in selected_patch_ids:
            artifact_blockers.append(
                {
                    "code": "required_patch_not_applied_to_artifact",
                    "artifact": artifact_id,
                    "message": f"{artifact_id} does not select required patch {required_patch_id}.",
                }
            )
        if not publishable:
            artifact_blockers.append(
                {
                    "code": "artifact_not_publishable",
                    "artifact": artifact_id,
                    "message": f"{artifact_id} is marked publish=false and cannot be used for a release claim.",
                }
            )
        if "pending_rebuild" in str(artifact_status):
            artifact_blockers.append(
                {
                    "code": "artifact_pending_rebuild_with_declared_patches",
                    "artifact": artifact_id,
                    "message": f"{artifact_id} predates the declared patch set and must be rebuilt.",
                }
            )
        if str(artifact_status).startswith("planned"):
            artifact_blockers.append(
                {
                    "code": "artifact_not_built",
                    "artifact": artifact_id,
                    "message": f"{artifact_id} is planned but has not been built.",
                }
            )
        if _package_digest_is_placeholder(artifact.get("sha256")):
            artifact_blockers.append(
                {
                    "code": "artifact_digest_missing",
                    "artifact": artifact_id,
                    "message": f"{artifact_id} must have a verified artifact sha256.",
                }
            )
        if not artifact.get("url"):
            artifact_blockers.append(
                {
                    "code": "artifact_url_missing",
                    "artifact": artifact_id,
                    "message": f"{artifact_id} must declare an artifact URL.",
                }
            )

        evidence_status, evidence_payload, evidence_blocker = load_dogfood_evidence(artifact_id)
        if evidence_blocker is not None:
            artifact_blockers.append(evidence_blocker)

        documented_non_release_blocker = isinstance(evidence_payload, dict) and evidence_payload.get("non_release_blocker") is True
        if documented_non_release_blocker:
            deferrable_codes = {
                "artifact_not_publishable",
                "artifact_digest_missing",
                "artifact_not_built",
                "dogfood_evidence_missing",
                "dogfood_evidence_failed",
            }
            artifact_blockers = [
                blocker for blocker in artifact_blockers
                if blocker.get("code") not in deferrable_codes
            ]
            evidence_status = "deferred"

        blockers.extend(artifact_blockers)
        targets.append(
            {
                "id": artifact_id,
                "os": artifact.get("os"),
                "arch": artifact.get("arch"),
                "compiler_family": artifact.get("compiler_family"),
                "toolchain_flavor": artifact.get("toolchain_flavor"),
                "format": artifact.get("format", "tar.gz" if artifact.get("os") != "windows" else "zip"),
                "publish": publishable,
                "status": artifact_status or "unspecified",
                "url": artifact.get("url"),
                "sha256": artifact.get("sha256"),
                "selected_patches": selected_patch_ids,
                "dogfood_evidence": evidence_status,
                "dogfood_evidence_payload": evidence_payload,
                "required_dogfood_checks": dogfood_checks,
                "deferred_non_release_blocker": documented_non_release_blocker,
                "release_ready": len(artifact_blockers) == 0 and not documented_non_release_blocker,
                "blockers": artifact_blockers,
            }
        )

    ok = len(blockers) == 0
    return {
        "schema_version": 1,
        "command": "tools-xctest-release-gate",
        "ok": ok,
        "status": "ok" if ok else "blocked",
        "summary": "tools-xctest package is release-ready." if ok else "tools-xctest package release gate is blocked.",
        "packages_dir": str(root),
        "evidence_dir": str(evidence_root) if evidence_root else None,
        "package_id": "org.gnustep.tools-xctest",
        "phase": "24.E-G",
        "source": manifest.get("source", {}),
        "required_patch": required_patch_id,
        "dogfood_checks": dogfood_checks,
        "targets": targets,
        "blockers": blockers,
        "next_actions": [
            "Rebuild every tools-xctest artifact from the declared upstream revision plus declared patch set.",
            "Publish rebuilt artifacts through the signed package index only after verified sha256 and provenance are present.",
            "Run native install, xctest smoke, minimal XCTest bundle, and native remove validation on each target host.",
        ] if not ok else [],
    }

def published_url_qualification_plan(
    release_url: str,
    *,
    config_path: str = "~/oracletestvms-libvirt.toml",
) -> dict[str, Any]:
    release_manifest_url = release_url.rstrip("/") + "/release-manifest.json"
    targets = [
        {
            "id": "debian-public-bootstrap-full-cli-package",
            "profile": "debian-13-gnome-wayland",
            "status": "ready",
            "validation_kind": "published-url-managed-release",
            "manifest_url": release_manifest_url,
            "expected_probes": [
                "bootstrap setup from the public release-manifest.json",
                "installed gnustep --version and --help",
                "installed gnustep doctor --json",
                "package install/remove smoke from a reviewed package index",
            ],
        },
        {
            "id": "openbsd-public-native-package-smoke",
            "profile": "openbsd-7.8-fvwm",
            "status": "ready",
            "validation_kind": "published-url-native-packaged-release",
            "manifest_url": release_manifest_url,
            "expected_probes": [
                "pkg_add native GNUstep prerequisites",
                "build and run the full CLI against packaged GNUstep",
                "doctor --json native classification",
                "package install/remove smoke",
            ],
        },
        {
            "id": "fedora-public-gcc-interop-smoke",
            "profile": "fedora-gnome",
            "status": "ready",
            "validation_kind": "published-url-gcc-interoperability",
            "manifest_url": release_manifest_url,
            "expected_probes": [
                "install Fedora packaged GNUstep prerequisites",
                "build and run the full CLI against GCC/libobjc GNUstep",
                "doctor --json reports interoperability-only policy",
                "package install/remove smoke selects GCC-compatible artifacts",
            ],
        },
        {
            "id": "arch-public-gcc-interop-smoke",
            "profile": "arch-gnome",
            "status": "ready",
            "validation_kind": "published-url-gcc-interoperability",
            "manifest_url": release_manifest_url,
            "expected_probes": [
                "install Arch packaged GNUstep prerequisites",
                "build and run the full CLI against GCC/libobjc GNUstep",
                "doctor --json reports interoperability-only policy",
                "package install/remove smoke selects GCC-compatible artifacts",
            ],
        },
        {
            "id": "windows-public-bootstrap-runtime-package",
            "profile": "windows-2022",
            "status": "ready",
            "validation_kind": "published-url-managed-msys2-release",
            "manifest_url": release_manifest_url,
            "expected_probes": [
                "PowerShell bootstrap setup from public release-manifest.json",
                "installed gnustep.exe --version and --help from PowerShell and cmd.exe",
                "installed gnustep.exe doctor --json with managed msys2-clang64 classification",
                "package install/remove smoke",
                "extracted toolchain rebuild smoke using GNUstep.ps1/GNUstep.bat activation",
                "managed AppKit GUI smoke with screenshot verification",
                "managed Gorm build and launch with screenshot verification",
            ],
        },
    ]
    return {
        "schema_version": 1,
        "command": "published-url-qualification-plan",
        "ok": True,
        "status": "ready",
        "summary": "Published URL release qualification plan generated.",
        "release_url": release_url.rstrip("/"),
        "release_manifest_url": release_manifest_url,
        "config_path": config_path,
        "cleanup_policy": "destroy-on-exit",
        "targets": targets,
    }


def otvm_release_host_validation_plan(
    release_dir: str | Path,
    *,
    config_path: str = "~/oracletestvms-libvirt.toml",
) -> dict[str, Any]:
    root = Path(release_dir).resolve()
    manifest_path = root / "release-manifest.json"
    if not manifest_path.exists():
        return {
            "schema_version": 1,
            "command": "otvm-release-host-validation-plan",
            "ok": False,
            "status": "error",
            "summary": "Release manifest is missing.",
            "release_dir": str(root),
        }

    release_manifest_root_unix = "/tmp/gnustep-smoke/release"
    release_manifest_root_windows = r"C:\gnustep-smoke\release"
    release_manifest_guest_unix = f"{release_manifest_root_unix}/release-manifest.json"
    release_manifest_guest_windows = f"{release_manifest_root_windows}\\release-manifest.json"
    config_ref = config_path

    targets = [
        {
            "id": "debian-release-artifact-smoke",
            "profile": "debian-13-gnome-wayland",
            "status": "ready",
            "validation_kind": "managed-release-artifact",
            "commands": [
                f'PYTHONPATH=src python3 -m oracletestvms --config {config_ref} preflight debian-13-gnome-wayland',
                f'PYTHONPATH=src python3 -m oracletestvms --config {config_ref} create debian-13-gnome-wayland',
            ],
            "guest_release_manifest_path": release_manifest_guest_unix,
            "expected_probes": [
                "bootstrap setup against the staged release-manifest.json",
                "managed clang compile-link-run on a clean lease",
                "package install/remove smoke with reviewed package fixtures",
            ],
            "notes": "Use the staged release artifacts from this release directory and the ~/.ssh/otvm operator keypair.",
        },
        {
            "id": "openbsd-native-packaged-smoke",
            "profile": "openbsd-7.8-fvwm",
            "status": "ready",
            "validation_kind": "native-packaged-toolchain",
            "commands": [
                f'PYTHONPATH=src python3 -m oracletestvms --config {config_ref} preflight openbsd-7.8-fvwm',
                f'PYTHONPATH=src python3 -m oracletestvms --config {config_ref} create openbsd-7.8-fvwm',
            ],
            "guest_release_manifest_path": release_manifest_guest_unix,
            "expected_probes": [
                "pkg_add gmake gnustep-make gnustep-base gnustep-libobjc2",
                "source /usr/local/share/GNUstep/Makefiles/GNUstep.sh",
                "Foundation compile-link-run probe in the packaged GNUstep environment",
            ],
            "notes": "Keep OpenBSD on the native pkg_add path by default; do not substitute a managed OpenBSD toolchain unless qualification explicitly requires it.",
        },
        {
            "id": "windows-release-artifact-smoke",
            "profile": "windows-2022",
            "status": "ready",
            "validation_kind": "managed-msys2-release-artifact",
            "commands": [
                f'PYTHONPATH=src python3 -m oracletestvms --config {config_ref} preflight windows-2022',
                f'PYTHONPATH=src python3 -m oracletestvms --config {config_ref} create windows-2022',
            ],
            "guest_release_manifest_path": release_manifest_guest_windows,
            "expected_probes": [
                "stage the release directory onto the Windows lease",
                "assemble or activate the MSYS2 clang64 managed toolchain from the staged release",
                "run bootstrap/full CLI smoke against the staged release artifacts",
                "build and screenshot-launch a minimal AppKit app",
                "build and screenshot-launch Gorm through managed openapp",
            ],
            "notes": "Windows now uses the libvirt-backed otvm path rather than OCI-oriented assumptions.",
        },
    ]

    return {
        "schema_version": 1,
        "command": "otvm-release-host-validation-plan",
        "ok": True,
        "status": "ok",
        "summary": "Release-scoped otvm host validation plan generated.",
        "release_dir": str(root),
        "release_manifest_path": str(manifest_path),
        "config_path": config_ref,
        "operator_key_public": "~/.ssh/otvm/id_rsa.pub",
        "operator_key_private": "~/.ssh/otvm/id_rsa",
        "guest_stage_roots": {
            "unix": release_manifest_root_unix,
            "windows": release_manifest_root_windows,
        },
        "targets": targets,
    }


def prepare_github_release(
    repo: str,
    version: str,
    output_dir: str | Path,
    base_url: str,
    *,
    cli_inputs: dict[str, str | Path] | None = None,
    toolchain_inputs: dict[str, str | Path] | None = None,
    reused_toolchain_artifacts: dict[str, dict[str, Any] | str | Path] | None = None,
    install_root: str | Path | None = None,
    handoff_install_root: str | Path | None = None,
    channel: str = "stable",
    title: str | None = None,
) -> dict[str, Any]:
    staged = stage_release_assets(
        version,
        output_dir,
        base_url,
        cli_inputs=cli_inputs,
        toolchain_inputs=toolchain_inputs,
        reused_toolchain_artifacts=reused_toolchain_artifacts,
        channel=channel,
    )
    release_dir = staged["release_dir"]
    verification = verify_release_directory(release_dir)

    toolchain_audits = []
    manifest = json.loads((Path(release_dir) / "release-manifest.json").read_text())
    for artifact in manifest["releases"][0]["artifacts"]:
        if artifact["kind"] != "toolchain":
            continue
        if artifact.get("reused") and not artifact.get("filename"):
            toolchain_audits.append(
                {
                    "schema_version": 1,
                    "command": "toolchain-archive-audit",
                    "ok": True,
                    "status": "ok",
                    "summary": "Reused immutable toolchain artifact reference is not re-audited from the current release directory.",
                    "artifact_id": artifact.get("id"),
                    "reused": True,
                }
            )
            continue
        audit = toolchain_archive_audit(Path(release_dir) / artifact["filename"], target_id=artifact["id"].removeprefix("toolchain-"))
        toolchain_audits.append(audit)

    if install_root is None:
        install_root = Path(output_dir).resolve() / "qualification" / "artifacts"
    qualified = qualify_release_install(release_dir, install_root)

    handoff = None
    if handoff_install_root is not None:
        handoff = qualify_full_cli_handoff(release_dir, handoff_install_root)

    host_validation_plan = otvm_release_host_validation_plan(release_dir)
    host_validation_plan_path = Path(release_dir) / "otvm-host-validation-plan.json"
    host_validation_plan_path.write_text(json.dumps(host_validation_plan, indent=2) + "\n")

    publish_plan = github_release_plan(
        repo,
        version,
        release_dir,
        channel=channel,
        title=title,
    )

    ok = staged["ok"] and verification["ok"] and all(audit["ok"] for audit in toolchain_audits) and qualified["ok"] and (handoff is None or handoff["ok"])
    return {
        "schema_version": 1,
        "command": "prepare-github-release",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": (
            "Release staging, verification, qualification, and publish planning completed."
            if ok
            else "Release preparation failed."
        ),
        "stage_release": staged,
        "verify_release": verification,
        "toolchain_archive_audits": toolchain_audits,
        "qualify_release": qualified,
        "qualify_full_cli_handoff": handoff,
        "otvm_host_validation_plan": host_validation_plan,
        "otvm_host_validation_plan_path": str(host_validation_plan_path),
        "github_release_plan": publish_plan,
    }


def session_build_box_plan(
    *,
    targets: list[str] | None = None,
    ttl_hours: int = 8,
    channel: str = "dogfood",
    repo_root: str | Path = ".",
    otvm_config: str = "~/oracletestvms-libvirt.toml",
) -> dict[str, Any]:
    selected_targets = targets or [target["id"] for target in TIER1_TARGETS if target["publish"]]
    known_targets = {target["id"]: target for target in TIER1_TARGETS}
    unknown = [target for target in selected_targets if target not in known_targets]
    if unknown:
        return {
            "schema_version": 1,
            "command": "session-build-box-plan",
            "ok": False,
            "status": "error",
            "summary": "Unknown build targets requested.",
            "unknown_targets": unknown,
        }

    builders: list[dict[str, Any]] = []
    for target_id in selected_targets:
        target = known_targets[target_id]
        profile = {
            "linux": "debian-13-gnome-wayland" if target_id == "linux-amd64-clang" else "ubuntu-24.04-aarch64" if target["arch"] == "arm64" else "ubuntu-24.04-amd64",
            "openbsd": "openbsd-7.8-fvwm",
            "windows": "windows-2022",
        }.get(target["os"], target_id)
        builders.append(
            {
                "target_id": target_id,
                "os": target["os"],
                "arch": target["arch"],
                "toolchain_flavor": target["toolchain_flavor"],
                "otvm_profile": profile,
                "ttl_hours": ttl_hours,
                "state": "planned",
                "source_sync": {
                    "mode": "incremental",
                    "repo_root": str(Path(repo_root)),
                    "include": ["src/full-cli", "src/gnustep_cli_shared", "scripts", "schemas", "GNUmakefile"],
                    "exclude": ["dist", "vendor", ".git", "__pycache__"],
                },
                "artifact": {
                    "kind": "cli",
                    "target_id": target_id,
                    "channel": channel,
                    "toolchain_layer": "reuse-installed-compatible",
                },
            }
        )

    return {
        "schema_version": 1,
        "command": "session-build-box-plan",
        "ok": True,
        "status": "ok",
        "summary": "Session-scoped warm build box plan generated.",
        "channel": channel,
        "ttl_hours": ttl_hours,
        "otvm_config": otvm_config,
        "targets": selected_targets,
        "builders": builders,
        "steps": [
            {"id": "provision", "title": "Create or reuse one warm otvm build box per selected target."},
            {"id": "sync-source", "title": "Incrementally sync changed source and build metadata to each warm builder."},
            {"id": "build-cli", "title": "Build target-specific full CLI artifacts without rebuilding unchanged toolchain layers."},
            {"id": "collect-artifacts", "title": "Collect small CLI artifacts and build provenance from each builder."},
            {"id": "publish-dogfood-manifest", "title": "Publish or stage a dogfood manifest that references reused toolchain layers."},
            {"id": "cleanup", "title": "Destroy or extend warm builders explicitly before TTL expiry."},
        ],
        "cost_controls": {
            "default_ttl_hours": ttl_hours,
            "requires_explicit_cleanup": True,
            "list_active_leases_before_provisioning": True,
        },
    }


def write_release_manifest(version: str, base_url: str, output_path: str | Path) -> Path:
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(release_manifest_from_matrix(version, base_url), indent=2) + "\n")
    return output
