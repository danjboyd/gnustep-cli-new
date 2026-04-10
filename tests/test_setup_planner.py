import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.build_infra import bundle_full_cli, stage_release_assets
from gnustep_cli_shared.setup_planner import build_setup_payload, execute_setup


class SetupPlannerTests(unittest.TestCase):
    def test_user_scope_plan(self):
        payload, exit_code = build_setup_payload(scope="user")
        self.assertEqual(payload["command"], "setup")
        self.assertEqual(payload["plan"]["scope"], "user")
        self.assertEqual(exit_code, 0)

    def test_system_scope_requires_privileges_for_non_root(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("test expects non-root execution")
        payload, exit_code = build_setup_payload(scope="system")
        self.assertEqual(payload["status"], "error")
        self.assertEqual(exit_code, 3)
        self.assertEqual(payload["actions"][0]["kind"], "rerun_with_elevated_privileges")

    def test_setup_payload_json_round_trip(self):
        payload, _ = build_setup_payload(scope="user")
        encoded = json.dumps(payload)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["command"], "setup")
        self.assertIn("manifest_validation_errors", decoded["plan"])

    def test_invalid_manifest_fails_validation(self):
        with tempfile.TemporaryDirectory() as tempdir:
            manifest = Path(tempdir) / "release-manifest.json"
            manifest.write_text('{"schema_version": 99, "releases": []}\n')
            payload, exit_code = build_setup_payload(scope="user", manifest_path=manifest)
            self.assertFalse(payload["ok"])
            self.assertEqual(exit_code, 2)
            self.assertEqual(payload["summary"], "Release manifest validation failed.")
            self.assertTrue(payload["plan"]["manifest_validation_errors"])

    def test_execute_setup_from_local_staged_release(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            cli_binary = temp / "gnustep"
            cli_binary.write_text("binary")
            cli_bundle = temp / "cli-bundle"
            bundle_full_cli(cli_binary, cli_bundle, repo_root=ROOT)
            toolchain_dir = temp / "toolchain"
            toolchain_dir.mkdir()
            (toolchain_dir / "System" / "Tools").mkdir(parents=True)
            (toolchain_dir / "System" / "Tools" / "make").write_text("tool")
            staged = stage_release_assets(
                "0.1.0-test",
                temp / "dist",
                "https://example.invalid/releases",
                cli_inputs={"linux-amd64-clang": cli_bundle},
                toolchain_inputs={"linux-amd64-clang": toolchain_dir},
            )
            install_root = temp / "install-root"
            payload, exit_code = execute_setup(
                scope="user",
                manifest_path=Path(staged["manifest_path"]),
                install_root=install_root,
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["ok"])
            self.assertTrue((install_root / "bin" / "gnustep").exists())
            self.assertTrue((install_root / "System" / "Tools" / "make").exists())
            self.assertIn("path_hint", payload["install"])


if __name__ == "__main__":
    unittest.main()
