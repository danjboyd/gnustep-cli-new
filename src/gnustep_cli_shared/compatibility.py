from __future__ import annotations

from typing import Any


def normalize_os(value: str) -> str:
    value = value.lower()
    mapping = {
        "linux": "linux",
        "openbsd": "openbsd",
        "windows": "windows",
        "win32": "windows",
        "cygwin": "windows",
        "msys": "windows",
        "darwin": "macos",
        "macos": "macos",
    }
    return mapping.get(value, value)


def normalize_arch(value: str) -> str:
    value = value.lower()
    mapping = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    return mapping.get(value, value)


def classify_environment(environment: dict[str, Any]) -> str:
    toolchain = environment.get("toolchain", {})
    if not toolchain.get("present"):
        return "no_toolchain"
    if not toolchain.get("can_compile") or not toolchain.get("can_link") or not toolchain.get("can_run"):
        return "toolchain_broken"
    if environment.get("compatibility", {}).get("compatible") is False:
        return "toolchain_incompatible"
    return "toolchain_compatible"


def evaluate_environment_against_artifact(
    environment: dict[str, Any], artifact: dict[str, Any] | None
) -> dict[str, Any]:
    reasons: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if artifact is None:
        return {
            "compatible": False,
            "target_kind": None,
            "target_id": None,
            "reasons": [
                {
                    "code": "unsupported_os",
                    "message": "No managed artifact matched the detected operating system and architecture.",
                }
            ],
            "warnings": [],
        }

    if environment["os"] != artifact["os"]:
        reasons.append(
            {
                "code": "unsupported_os",
                "message": f"Detected OS {environment['os']} does not match artifact OS {artifact['os']}.",
            }
        )
    if environment["arch"] != artifact["arch"]:
        reasons.append(
            {
                "code": "unsupported_arch",
                "message": f"Detected architecture {environment['arch']} does not match artifact arch {artifact['arch']}.",
            }
        )

    toolchain = environment.get("toolchain", {})
    if toolchain.get("present"):
        detected_compiler = toolchain.get("compiler_family")
        if detected_compiler and detected_compiler != artifact.get("compiler_family"):
            reasons.append(
                {
                    "code": "compiler_family_mismatch",
                    "message": (
                        f"Detected compiler family is {detected_compiler}, "
                        f"but the selected managed artifact requires {artifact.get('compiler_family')}."
                    ),
                }
            )
        required_features = artifact.get("required_features", [])
        feature_flags = toolchain.get("feature_flags", {})
        for feature in required_features:
            if not feature_flags.get(feature, False):
                reasons.append(
                    {
                        "code": "missing_required_feature",
                        "message": f"The detected toolchain does not support required feature '{feature}'.",
                    }
                )
        if detected_compiler == "gcc":
            warnings.append(
                {
                    "code": "gcc_toolchain_detected",
                    "message": (
                        "A GCC-based GNUstep environment is installed. "
                        "Some modern Objective-C features require a Clang-based toolchain."
                    ),
                }
            )
    else:
        warnings.append(
            {
                "code": "toolchain_not_present",
                "message": "No preexisting GNUstep toolchain was detected; a managed install will be required.",
            }
        )

    return {
        "compatible": len(reasons) == 0,
        "target_kind": artifact.get("kind"),
        "target_id": artifact.get("id"),
        "reasons": reasons,
        "warnings": warnings,
    }

