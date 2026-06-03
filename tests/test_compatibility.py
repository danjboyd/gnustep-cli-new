import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gnustep_cli_shared.compatibility import (  # noqa: E402
    artifact_matches_host,
    evaluate_environment_against_artifact,
    runtime_library_findings,
    select_artifact_for_environment,
)


def _linux_env(*, distribution_id="debian", os_version="debian-13", icu_major=76, glibc="2.41"):
    return {
        "os": "linux",
        "arch": "amd64",
        "distribution_id": distribution_id,
        "os_version": os_version,
        "runtime_libraries": {"icu_major": icu_major, "glibc_version": glibc},
        "toolchain": {"present": False},
    }


def _toolchain_artifact(**overrides):
    artifact = {
        "id": "toolchain-linux-amd64-clang",
        "kind": "toolchain",
        "os": "linux",
        "arch": "amd64",
        "supported_distributions": ["debian"],
        "runtime_requirements": {"icu_major": 76, "glibc_min": "2.41"},
    }
    artifact.update(overrides)
    return artifact


class RuntimeLibraryGateTests(unittest.TestCase):
    def test_matching_icu_and_glibc_is_compatible(self):
        env = _linux_env(icu_major=76, glibc="2.41")
        artifact = _toolchain_artifact()
        reasons, warnings = runtime_library_findings(env, artifact)
        self.assertEqual(reasons, [])
        self.assertEqual(warnings, [])
        self.assertTrue(artifact_matches_host(env, artifact))
        self.assertTrue(evaluate_environment_against_artifact(env, artifact)["compatible"])

    def test_icu_major_mismatch_is_incompatible(self):
        # The exact regression: a Debian 12 (ICU 72) host vs a Debian 13 (ICU 76) artifact.
        env = _linux_env(distribution_id="debian", os_version="debian-12", icu_major=72)
        artifact = _toolchain_artifact()
        reasons, _ = runtime_library_findings(env, artifact)
        self.assertEqual([r["code"] for r in reasons], ["icu_major_mismatch"])
        self.assertFalse(artifact_matches_host(env, artifact))
        result = evaluate_environment_against_artifact(env, artifact)
        self.assertFalse(result["compatible"])
        self.assertIn("icu_major_mismatch", [r["code"] for r in result["reasons"]])

    def test_newer_host_icu_still_blocks_old_artifact(self):
        env = _linux_env(icu_major=76)
        artifact = _toolchain_artifact(runtime_requirements={"icu_major": 74, "glibc_min": "2.39"})
        self.assertFalse(artifact_matches_host(env, artifact))

    def test_glibc_too_old_is_incompatible(self):
        env = _linux_env(icu_major=76, glibc="2.36")
        artifact = _toolchain_artifact()
        reasons, _ = runtime_library_findings(env, artifact)
        self.assertEqual([r["code"] for r in reasons], ["glibc_too_old"])
        self.assertFalse(artifact_matches_host(env, artifact))

    def test_glibc_equal_or_newer_is_ok(self):
        for glibc in ("2.41", "2.42", "2.50"):
            env = _linux_env(icu_major=76, glibc=glibc)
            self.assertTrue(artifact_matches_host(env, _toolchain_artifact()), glibc)

    def test_undetected_host_icu_warns_but_does_not_exclude(self):
        # If we cannot detect the host ICU we must not silently pass *or* falsely
        # exclude: selection keeps the artifact, doctor surfaces a warning.
        env = _linux_env(icu_major=None, glibc=None)
        artifact = _toolchain_artifact()
        reasons, warnings = runtime_library_findings(env, artifact)
        self.assertEqual(reasons, [])
        self.assertEqual(
            sorted(w["code"] for w in warnings),
            ["glibc_version_undetected", "icu_major_undetected"],
        )
        self.assertTrue(artifact_matches_host(env, artifact))
        result = evaluate_environment_against_artifact(env, artifact)
        self.assertTrue(result["compatible"])
        self.assertIn("icu_major_undetected", [w["code"] for w in result["warnings"]])

    def test_artifact_without_runtime_requirements_is_unaffected(self):
        # Backward compatibility: legacy manifests with no runtime_requirements
        # behave exactly as before (no new constraint).
        env = _linux_env(icu_major=72)
        artifact = _toolchain_artifact(runtime_requirements={})
        reasons, warnings = runtime_library_findings(env, artifact)
        self.assertEqual((reasons, warnings), ([], []))
        self.assertTrue(artifact_matches_host(env, artifact))

    def test_non_linux_host_ignores_runtime_requirements(self):
        env = {"os": "openbsd", "arch": "amd64", "runtime_libraries": {}, "toolchain": {"present": False}}
        artifact = _toolchain_artifact(os="openbsd")
        self.assertEqual(runtime_library_findings(env, artifact), ([], []))

    def test_selection_excludes_icu_mismatched_artifact(self):
        env = _linux_env(os_version="debian-12", icu_major=72)
        good = _toolchain_artifact(id="toolchain-icu72", runtime_requirements={"icu_major": 72, "glibc_min": "2.36"})
        bad = _toolchain_artifact(id="toolchain-icu76", runtime_requirements={"icu_major": 76, "glibc_min": "2.41"})
        selected, error = select_artifact_for_environment(env, [good, bad], kind="toolchain")
        self.assertIsNone(error)
        self.assertEqual(selected["id"], "toolchain-icu72")


if __name__ == "__main__":
    unittest.main()
