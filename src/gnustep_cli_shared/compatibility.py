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


def _parse_version_tuple(value: Any) -> tuple[int, ...]:
    parts: list[int] = []
    for component in str(value).split("."):
        if component.isdigit():
            parts.append(int(component))
        else:
            break
    return tuple(parts)


def runtime_library_findings(
    environment: dict[str, Any], artifact: dict[str, Any]
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Evaluate host runtime libraries against an artifact's hard ABI requirements.

    Managed Linux artifacts link the build distribution's versioned ICU SONAME
    and a minimum glibc. ICU has no cross-major ABI compatibility, so a host
    whose ICU major differs cannot load the managed runtime — installing anyway
    is the crash class this gate prevents. Returns (reasons, warnings): a definite
    mismatch is a hard reason (incompatible); an undetectable host value is a
    warning rather than a silent pass.
    """
    reasons: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    requirements = artifact.get("runtime_requirements") or {}
    if not requirements or environment.get("os") != "linux":
        return reasons, warnings
    host = environment.get("runtime_libraries") or {}

    required_icu = requirements.get("icu_major")
    if required_icu is not None:
        host_icu = host.get("icu_major")
        if host_icu is None:
            warnings.append(
                {
                    "code": "icu_major_undetected",
                    "message": (
                        f"The managed artifact links ICU major {required_icu}, but the host ICU "
                        "version could not be detected; the managed runtime may fail to load if it "
                        "does not match."
                    ),
                }
            )
        elif int(host_icu) != int(required_icu):
            reasons.append(
                {
                    "code": "icu_major_mismatch",
                    "message": (
                        f"The host provides ICU major {host_icu}, but the selected managed artifact "
                        f"links ICU major {required_icu}. ICU has no cross-major ABI compatibility, "
                        "so the managed GNUstep runtime would fail to load."
                    ),
                }
            )

    required_glibc = requirements.get("glibc_min")
    if required_glibc is not None:
        host_glibc = host.get("glibc_version")
        if host_glibc is None:
            warnings.append(
                {
                    "code": "glibc_version_undetected",
                    "message": (
                        f"The managed artifact requires glibc >= {required_glibc}, but the host "
                        "glibc version could not be detected."
                    ),
                }
            )
        elif _parse_version_tuple(host_glibc) < _parse_version_tuple(required_glibc):
            reasons.append(
                {
                    "code": "glibc_too_old",
                    "message": (
                        f"The host provides glibc {host_glibc}, but the selected managed artifact "
                        f"requires glibc >= {required_glibc}."
                    ),
                }
            )

    return reasons, warnings


def artifact_matches_host(environment: dict[str, Any], artifact: dict[str, Any]) -> bool:
    if environment.get("os") != artifact.get("os") or environment.get("arch") != artifact.get("arch"):
        return False
    supported_distributions = artifact.get("supported_distributions") or []
    if environment.get("os") == "linux" and supported_distributions:
        if environment.get("distribution_id") not in supported_distributions:
            return False
    supported_os_versions = artifact.get("supported_os_versions") or []
    if environment.get("os") == "linux" and supported_os_versions:
        if environment.get("os_version") not in supported_os_versions:
            return False
    # A definite runtime-library ABI mismatch (e.g. ICU major) excludes the
    # artifact from selection so setup never installs something that cannot load.
    runtime_reasons, _ = runtime_library_findings(environment, artifact)
    if runtime_reasons:
        return False
    return True


def artifact_matches_detected_toolchain(environment: dict[str, Any], artifact: dict[str, Any]) -> bool:
    toolchain = environment.get("toolchain", {})
    if not toolchain.get("present"):
        return False

    for field in ("compiler_family", "toolchain_flavor", "objc_runtime", "objc_abi"):
        expected = artifact.get(field)
        if expected in (None, "unknown"):
            continue
        detected = toolchain.get(field)
        if detected in (None, "unknown") or detected != expected:
            return False

    required_features = artifact.get("required_features", [])
    feature_flags = toolchain.get("feature_flags", {})
    for feature in required_features:
        if not feature_flags.get(feature, False):
            return False

    return True


def select_artifact_for_environment(
    environment: dict[str, Any], artifacts: list[dict[str, Any]], *, kind: str
) -> tuple[dict[str, Any] | None, str | None]:
    candidates = [artifact for artifact in artifacts if artifact.get("kind") == kind and artifact_matches_host(environment, artifact)]
    if not candidates:
        return None, None
    if len(candidates) == 1:
        return candidates[0], None

    matching = [artifact for artifact in candidates if artifact_matches_detected_toolchain(environment, artifact)]
    if len(matching) == 1:
        return matching[0], None
    if len(matching) > 1:
        return None, f"Multiple {kind} artifacts match the detected host and toolchain; selection is ambiguous."
    return None, f"Multiple {kind} artifacts match the detected host, but the current environment does not identify a unique target."


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
    supported_distributions = artifact.get("supported_distributions") or []
    if environment.get("os") == "linux" and supported_distributions and environment.get("distribution_id") not in supported_distributions:
        reasons.append(
            {
                "code": "unsupported_distribution",
                "message": (
                    f"Detected Linux distribution {environment.get('distribution_id') or 'unknown'} "
                    f"is not in the artifact's supported distributions: {', '.join(supported_distributions)}."
                ),
            }
        )
    supported_os_versions = artifact.get("supported_os_versions") or []
    if environment.get("os") == "linux" and supported_os_versions and environment.get("os_version") not in supported_os_versions:
        reasons.append(
            {
                "code": "unsupported_os_version",
                "message": (
                    f"Detected Linux OS version {environment.get('os_version') or 'unknown'} "
                    f"is not in the artifact's supported OS versions: {', '.join(supported_os_versions)}."
                ),
            }
        )

    runtime_reasons, runtime_warnings = runtime_library_findings(environment, artifact)
    reasons.extend(runtime_reasons)
    warnings.extend(runtime_warnings)

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
        for field, label in (
            ("toolchain_flavor", "toolchain flavor"),
            ("objc_runtime", "Objective-C runtime"),
            ("objc_abi", "Objective-C ABI"),
        ):
            expected = artifact.get(field)
            detected = toolchain.get(field)
            if expected and expected != "unknown" and detected and detected != "unknown" and detected != expected:
                reasons.append(
                    {
                        "code": f"{field}_mismatch",
                        "message": f"Detected {label} is {detected}, but the selected managed artifact requires {expected}.",
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
