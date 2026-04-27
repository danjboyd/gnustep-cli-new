import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
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

    def test_ambiguous_same_host_artifacts_fail_selection(self):
        with tempfile.TemporaryDirectory() as tempdir:
            manifest = Path(tempdir) / "release-manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "releases": [
                            {
                                "version": "0.1.0-test",
                                "status": "active",
                                "artifacts": [
                                    {
                                        "id": "cli-linux-amd64-clang",
                                        "kind": "cli",
                                        "os": "linux",
                                        "arch": "amd64",
                                        "compiler_family": "clang",
                                        "toolchain_flavor": "clang",
                                        "objc_runtime": "libobjc2",
                                        "objc_abi": "modern",
                                        "required_features": ["blocks"],
                                        "url": "https://example.invalid/cli-clang.tar.gz",
                                        "sha256": "deadbeef",
                                    },
                                    {
                                        "id": "cli-linux-amd64-gcc",
                                        "kind": "cli",
                                        "os": "linux",
                                        "arch": "amd64",
                                        "compiler_family": "gcc",
                                        "toolchain_flavor": "gcc",
                                        "objc_runtime": "gcc_libobjc",
                                        "objc_abi": "legacy",
                                        "required_features": [],
                                        "url": "https://example.invalid/cli-gcc.tar.gz",
                                        "sha256": "deadbeef",
                                    },
                                    {
                                        "id": "toolchain-linux-amd64-clang",
                                        "kind": "toolchain",
                                        "os": "linux",
                                        "arch": "amd64",
                                        "compiler_family": "clang",
                                        "toolchain_flavor": "clang",
                                        "objc_runtime": "libobjc2",
                                        "objc_abi": "modern",
                                        "required_features": ["blocks"],
                                        "url": "https://example.invalid/toolchain-clang.tar.gz",
                                        "sha256": "deadbeef",
                                    },
                                    {
                                        "id": "toolchain-linux-amd64-gcc",
                                        "kind": "toolchain",
                                        "os": "linux",
                                        "arch": "amd64",
                                        "compiler_family": "gcc",
                                        "toolchain_flavor": "gcc",
                                        "objc_runtime": "gcc_libobjc",
                                        "objc_abi": "legacy",
                                        "required_features": [],
                                        "url": "https://example.invalid/toolchain-gcc.tar.gz",
                                        "sha256": "deadbeef",
                                    },
                                ],
                            }
                        ],
                    }
                )
            )
            fake_doctor = {
                "status": "warning",
                "environment_classification": "no_toolchain",
                "native_toolchain_assessment": "unavailable",
                "summary": "No GNUstep toolchain detected.",
                "environment": {
                    "os": "linux",
                    "arch": "amd64",
                    "native_toolchain": {"assessment": "unavailable"},
                    "toolchain": {
                        "present": False,
                        "compiler_family": "unknown",
                        "toolchain_flavor": "unknown",
                        "objc_runtime": "unknown",
                        "objc_abi": "unknown",
                        "feature_flags": {},
                    },
                },
            }
            with patch("gnustep_cli_shared.setup_planner.build_doctor_payload", return_value=fake_doctor):
                payload, exit_code = build_setup_payload(scope="user", manifest_path=manifest)
            self.assertFalse(payload["ok"])
            self.assertEqual(exit_code, 4)
            self.assertEqual(payload["summary"], "Managed artifact selection failed.")
            self.assertTrue(payload["plan"]["selection_errors"])

    def test_detected_toolchain_can_disambiguate_artifacts(self):
        with tempfile.TemporaryDirectory() as tempdir:
            manifest = Path(tempdir) / "release-manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "releases": [
                            {
                                "version": "0.1.0-test",
                                "status": "active",
                                "artifacts": [
                                    {
                                        "id": "cli-linux-amd64-clang",
                                        "kind": "cli",
                                        "os": "linux",
                                        "arch": "amd64",
                                        "compiler_family": "clang",
                                        "toolchain_flavor": "clang",
                                        "objc_runtime": "libobjc2",
                                        "objc_abi": "modern",
                                        "required_features": ["blocks"],
                                        "url": "https://example.invalid/cli-clang.tar.gz",
                                        "sha256": "deadbeef",
                                    },
                                    {
                                        "id": "cli-linux-amd64-gcc",
                                        "kind": "cli",
                                        "os": "linux",
                                        "arch": "amd64",
                                        "compiler_family": "gcc",
                                        "toolchain_flavor": "gcc",
                                        "objc_runtime": "gcc_libobjc",
                                        "objc_abi": "legacy",
                                        "required_features": [],
                                        "url": "https://example.invalid/cli-gcc.tar.gz",
                                        "sha256": "deadbeef",
                                    },
                                    {
                                        "id": "toolchain-linux-amd64-clang",
                                        "kind": "toolchain",
                                        "os": "linux",
                                        "arch": "amd64",
                                        "compiler_family": "clang",
                                        "toolchain_flavor": "clang",
                                        "objc_runtime": "libobjc2",
                                        "objc_abi": "modern",
                                        "required_features": ["blocks"],
                                        "url": "https://example.invalid/toolchain-clang.tar.gz",
                                        "sha256": "deadbeef",
                                    },
                                    {
                                        "id": "toolchain-linux-amd64-gcc",
                                        "kind": "toolchain",
                                        "os": "linux",
                                        "arch": "amd64",
                                        "compiler_family": "gcc",
                                        "toolchain_flavor": "gcc",
                                        "objc_runtime": "gcc_libobjc",
                                        "objc_abi": "legacy",
                                        "required_features": [],
                                        "url": "https://example.invalid/toolchain-gcc.tar.gz",
                                        "sha256": "deadbeef",
                                    },
                                ],
                            }
                        ],
                    }
                )
            )
            fake_doctor = {
                "status": "ok",
                "environment_classification": "toolchain_compatible",
                "summary": "Detected a compatible Clang toolchain.",
                "environment": {
                    "os": "linux",
                    "arch": "amd64",
                    "bootstrap_prerequisites": {"curl": True, "wget": False},
                    "toolchain": {
                        "present": True,
                        "compiler_family": "clang",
                        "toolchain_flavor": "clang",
                        "objc_runtime": "libobjc2",
                        "objc_abi": "modern",
                        "feature_flags": {"blocks": True},
                    },
                },
            }
            with patch("gnustep_cli_shared.setup_planner.build_doctor_payload", return_value=fake_doctor):
                payload, exit_code = build_setup_payload(scope="user", manifest_path=manifest)
            self.assertTrue(payload["ok"])
            self.assertEqual(exit_code, 0)
            self.assertEqual(
                payload["plan"]["selected_artifacts"],
                ["cli-linux-amd64-clang", "toolchain-linux-amd64-clang"],
            )

    def test_fedora_supported_native_toolchain_prefers_native_setup_mode(self):
        with tempfile.TemporaryDirectory() as tempdir:
            manifest = Path(tempdir) / "release-manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "releases": [
                            {
                                "version": "0.1.0-test",
                                "status": "active",
                                "artifacts": [
                                    {
                                        "id": "cli-linux-amd64-clang",
                                        "kind": "cli",
                                        "os": "linux",
                                        "arch": "amd64",
                                        "compiler_family": "clang",
                                        "toolchain_flavor": "clang",
                                        "objc_runtime": "libobjc2",
                                        "objc_abi": "modern",
                                        "required_features": ["blocks"],
                                        "url": "https://example.invalid/cli-clang.tar.gz",
                                        "sha256": "deadbeef",
                                    },
                                    {
                                        "id": "toolchain-linux-amd64-clang",
                                        "kind": "toolchain",
                                        "os": "linux",
                                        "arch": "amd64",
                                        "compiler_family": "clang",
                                        "toolchain_flavor": "clang",
                                        "objc_runtime": "libobjc2",
                                        "objc_abi": "modern",
                                        "required_features": ["blocks"],
                                        "url": "https://example.invalid/toolchain-clang.tar.gz",
                                        "sha256": "deadbeef",
                                    },
                                ],
                            }
                        ],
                    }
                )
            )
            fake_doctor = {
                "status": "ok",
                "environment_classification": "toolchain_compatible",
                "native_toolchain_assessment": "supported",
                "summary": "Detected a supported Fedora Clang toolchain.",
                "environment": {
                    "os": "linux",
                    "arch": "amd64",
                    "distribution_id": "fedora",
                    "bootstrap_prerequisites": {"curl": True, "wget": False},
                    "native_toolchain": {
                        "assessment": "supported",
                        "message": "Use the detected Fedora GNUstep toolchain.",
                    },
                    "toolchain": {
                        "present": True,
                        "compiler_family": "clang",
                        "toolchain_flavor": "clang",
                        "objc_runtime": "libobjc2",
                        "objc_abi": "modern",
                        "feature_flags": {"blocks": True},
                    },
                },
            }
            with patch("gnustep_cli_shared.setup_planner.build_doctor_payload", return_value=fake_doctor):
                payload, exit_code = build_setup_payload(scope="user", manifest_path=manifest)
            self.assertTrue(payload["ok"])
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["plan"]["install_mode"], "native")
            self.assertEqual(payload["plan"]["disposition"], "use_existing_toolchain")

    def test_arch_supported_native_toolchain_prefers_native_setup_mode(self):
        with tempfile.TemporaryDirectory() as tempdir:
            manifest = Path(tempdir) / "release-manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "releases": [
                            {
                                "version": "0.1.0-test",
                                "status": "active",
                                "artifacts": [
                                    {
                                        "id": "cli-linux-amd64-clang",
                                        "kind": "cli",
                                        "os": "linux",
                                        "arch": "amd64",
                                        "compiler_family": "clang",
                                        "toolchain_flavor": "clang",
                                        "objc_runtime": "libobjc2",
                                        "objc_abi": "modern",
                                        "required_features": ["blocks"],
                                        "url": "https://example.invalid/cli-clang.tar.gz",
                                        "sha256": "deadbeef",
                                    },
                                    {
                                        "id": "toolchain-linux-amd64-clang",
                                        "kind": "toolchain",
                                        "os": "linux",
                                        "arch": "amd64",
                                        "compiler_family": "clang",
                                        "toolchain_flavor": "clang",
                                        "objc_runtime": "libobjc2",
                                        "objc_abi": "modern",
                                        "required_features": ["blocks"],
                                        "url": "https://example.invalid/toolchain-clang.tar.gz",
                                        "sha256": "deadbeef",
                                    },
                                ],
                            }
                        ],
                    }
                )
            )
            fake_doctor = {
                "status": "ok",
                "environment_classification": "toolchain_compatible",
                "native_toolchain_assessment": "supported",
                "summary": "Detected a supported Arch Clang toolchain.",
                "environment": {
                    "os": "linux",
                    "arch": "amd64",
                    "distribution_id": "arch",
                    "bootstrap_prerequisites": {"curl": True, "wget": False},
                    "native_toolchain": {
                        "assessment": "supported",
                        "message": "Use the detected Arch GNUstep toolchain.",
                    },
                    "toolchain": {
                        "present": True,
                        "compiler_family": "clang",
                        "toolchain_flavor": "clang",
                        "objc_runtime": "libobjc2",
                        "objc_abi": "modern",
                        "feature_flags": {"blocks": True},
                    },
                },
            }
            with patch("gnustep_cli_shared.setup_planner.build_doctor_payload", return_value=fake_doctor):
                payload, exit_code = build_setup_payload(scope="user", manifest_path=manifest)
            self.assertTrue(payload["ok"])
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["plan"]["install_mode"], "native")
            self.assertEqual(payload["plan"]["disposition"], "use_existing_toolchain")

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
            (toolchain_dir / "lib").mkdir(parents=True)
            (toolchain_dir / "System" / "Tools" / "make").write_text("tool")
            (toolchain_dir / "System" / "Tools" / "gnustep-config").write_text("prefix=__GNUSTEP_CLI_INSTALL_ROOT__\n")
            binary_with_placeholder = b"\x7fELF\0__GNUSTEP_CLI_INSTALL_ROOT__\0tail"
            (toolchain_dir / "lib" / "libplaceholder.so").write_bytes(binary_with_placeholder)
            staged = stage_release_assets(
                "0.1.0-test",
                temp / "dist",
                "https://example.invalid/releases",
                cli_inputs={
                    "linux-amd64-clang": cli_bundle,
                    "linux-ubuntu2404-amd64-clang": cli_bundle,
                },
                toolchain_inputs={
                    "linux-amd64-clang": toolchain_dir,
                    "linux-ubuntu2404-amd64-clang": toolchain_dir,
                },
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
            self.assertEqual((install_root / "System" / "Tools" / "gnustep-config").read_text(), f"prefix={install_root.resolve()}\n")
            self.assertEqual((install_root / "lib" / "libplaceholder.so").read_bytes(), binary_with_placeholder)
            self.assertIn("path_hint", payload["install"])
            self.assertIn("/Tools:", payload["install"]["path_hint"])

    def test_windows_setup_writes_private_msys2_activation_helpers(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            release_dir = temp / "release"
            release_dir.mkdir()
            cli_zip = release_dir / "gnustep-cli-windows-amd64-msys2-clang64-0.1.0-dev.zip"
            with __import__("zipfile").ZipFile(cli_zip, "w") as archive:
                archive.writestr("cli/bin/gnustep.exe", "binary")
            toolchain_zip = release_dir / "gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0-dev.zip"
            with __import__("zipfile").ZipFile(toolchain_zip, "w") as archive:
                archive.writestr("toolchain/clang64/share/GNUstep/Makefiles/common.make", "common")
                archive.writestr("toolchain/clang64/etc/GNUstep/GNUstep.conf", "conf")
                archive.writestr("toolchain/usr/bin/bash.exe", "bash")
                archive.writestr("toolchain/etc/profile", "profile")
                archive.writestr("toolchain/var/lib/pacman/local/pkg/desc", "desc")

            def sha256(path: Path) -> str:
                import hashlib
                return hashlib.sha256(path.read_bytes()).hexdigest()

            manifest = {
                "schema_version": 1,
                "channel": "stable",
                "generated_at": "2026-04-21T00:00:00Z",
                "releases": [{"version": "0.1.0-dev", "status": "active", "artifacts": [
                    {
                        "id": "cli-windows-amd64-msys2-clang64",
                        "kind": "cli",
                        "os": "windows",
                        "arch": "amd64",
                        "compiler_family": "clang",
                        "toolchain_flavor": "msys2-clang64",
                        "url": "https://example.invalid/" + cli_zip.name,
                        "filename": cli_zip.name,
                        "sha256": sha256(cli_zip),
                    },
                    {
                        "id": "toolchain-windows-amd64-msys2-clang64",
                        "kind": "toolchain",
                        "os": "windows",
                        "arch": "amd64",
                        "compiler_family": "clang",
                        "toolchain_flavor": "msys2-clang64",
                        "url": "https://example.invalid/" + toolchain_zip.name,
                        "filename": toolchain_zip.name,
                        "sha256": sha256(toolchain_zip),
                    },
                ]}],
            }
            manifest_path = release_dir / "release-manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            fake_doctor = {
                "environment": {
                    "os": "windows",
                    "arch": "amd64",
                    "toolchain": {"toolchain_flavor": "msys2-clang64"},
                    "bootstrap_prerequisites": {"curl": True, "wget": False},
                },
                "doctor": {"os": "windows"},
                "status": "warning",
                "environment_classification": "no_toolchain",
                "summary": "No GNUstep toolchain detected.",
            }
            with patch("gnustep_cli_shared.setup_planner.build_doctor_payload", return_value=fake_doctor):
                payload, exit_code = execute_setup(scope="user", manifest_path=manifest_path, install_root=temp / "install")
            self.assertEqual(exit_code, 0)
            install_root = Path(payload["install"]["install_root"])
            self.assertTrue((install_root / "GNUstep.ps1").exists())
            self.assertIn("clang64\\share\\GNUstep\\Makefiles", (install_root / "GNUstep.ps1").read_text())
            self.assertIn("clang64\\etc\\GNUstep\\GNUstep.conf", (install_root / "GNUstep.bat").read_text())
            self.assertTrue((install_root / "var" / "lib" / "pacman" / "local" / "pkg" / "desc").exists())
            self.assertEqual(payload["install"]["path_hint"], f'. "{install_root / "GNUstep.ps1"}"')
            self.assertIn("bin", payload["actions"][0]["message"])


if __name__ == "__main__":
    unittest.main()
