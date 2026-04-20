import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.package_tooling import apply_package_patches, init_package_manifest, validate_package_manifest


class PackageToolingTests(unittest.TestCase):
    def test_repo_tools_xctest_manifest_validates(self):
        payload = validate_package_manifest(ROOT / "packages" / "org.gnustep.tools-xctest" / "package.json")
        self.assertTrue(payload["ok"])

    def test_init_and_validate_gui_package(self):
        with tempfile.TemporaryDirectory() as tempdir:
            result = init_package_manifest(tempdir, "HelloApp", "gui-app")
            self.assertTrue(result["ok"])
            manifest = Path(tempdir) / "package.json"
            validated = validate_package_manifest(manifest)
            self.assertTrue(validated["ok"])
            self.assertTrue(validated["warnings"])

    def test_validate_missing_manifest(self):
        with tempfile.TemporaryDirectory() as tempdir:
            payload = validate_package_manifest(Path(tempdir) / "missing.json")
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["errors"][0]["code"], "manifest_missing")

    def test_validate_missing_gui_fields(self):
        with tempfile.TemporaryDirectory() as tempdir:
            manifest = Path(tempdir) / "package.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "org.example.bad",
                        "name": "Bad",
                        "version": "0.1.0",
                        "kind": "gui-app",
                        "summary": "Bad",
                        "license": "MIT",
                        "maintainers": [{"name": "X"}],
                        "source": {"type": "archive", "url": "https://example.invalid", "sha256": "x"},
                        "requirements": {
                            "supported_os": ["linux"],
                            "supported_arch": ["amd64"],
                            "supported_compiler_families": ["clang"],
                            "supported_objc_runtimes": ["libobjc2"],
                            "supported_objc_abi": ["modern"],
                            "required_features": [],
                            "forbidden_features": [],
                        },
                        "artifacts": [{"id": "x"}],
                        "install": {},
                    }
                )
            )
            payload = validate_package_manifest(manifest)
            self.assertFalse(payload["ok"])
            self.assertTrue(any(err["code"] == "missing_integration_field" for err in payload["errors"]))

    def test_validate_patch_metadata_requires_existing_file_and_digest(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            patch = root / "patches" / "fix.patch"
            patch.parent.mkdir()
            patch.write_text("diff --git a/file b/file\n")
            import hashlib
            digest = hashlib.sha256(patch.read_bytes()).hexdigest()
            manifest = root / "package.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "org.example.patched",
                        "name": "Patched",
                        "version": "0.1.0",
                        "kind": "cli-tool",
                        "summary": "Patched",
                        "license": "MIT",
                        "maintainers": [{"name": "X"}],
                        "source": {"type": "archive", "url": "https://example.invalid", "sha256": "x"},
                        "patches": [{"id": "fix", "path": "patches/fix.patch", "sha256": digest, "strip": 1, "applies_to": ["patched-linux"]}],
                        "requirements": {
                            "supported_os": ["linux"],
                            "supported_arch": ["amd64"],
                            "supported_compiler_families": ["clang"],
                            "supported_objc_runtimes": ["libobjc2"],
                            "supported_objc_abi": ["modern"],
                            "required_features": [],
                            "forbidden_features": [],
                        },
                        "artifacts": [{"id": "patched-linux"}],
                        "install": {"executables": ["patched"]},
                    }
                )
            )
            payload = validate_package_manifest(manifest)
            self.assertTrue(payload["ok"])

    def test_validate_patch_metadata_rejects_missing_or_mismatched_patch(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            manifest = root / "package.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "org.example.badpatch",
                        "name": "BadPatch",
                        "version": "0.1.0",
                        "kind": "cli-tool",
                        "summary": "BadPatch",
                        "license": "MIT",
                        "maintainers": [{"name": "X"}],
                        "source": {"type": "archive", "url": "https://example.invalid", "sha256": "x"},
                        "patches": [{"id": "fix", "path": "patches/missing.patch", "sha256": "0" * 64}],
                        "requirements": {
                            "supported_os": ["linux"],
                            "supported_arch": ["amd64"],
                            "supported_compiler_families": ["clang"],
                            "supported_objc_runtimes": ["libobjc2"],
                            "supported_objc_abi": ["modern"],
                            "required_features": [],
                            "forbidden_features": [],
                        },
                        "artifacts": [{"id": "badpatch-linux"}],
                        "install": {"executables": ["badpatch"]},
                    }
                )
            )
            payload = validate_package_manifest(manifest)
            self.assertFalse(payload["ok"])
            self.assertTrue(any(err["code"] == "patch_missing" for err in payload["errors"]))

    def test_apply_package_patches_applies_selected_patch(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = root / "source"
            source.mkdir()
            (source / "hello.txt").write_text("old\n")
            patch = root / "patches" / "fix.patch"
            patch.parent.mkdir()
            patch.write_text(
                "--- a/hello.txt\n"
                "+++ b/hello.txt\n"
                "@@ -1 +1 @@\n"
                "-old\n"
                "+new\n"
            )
            import hashlib
            digest = hashlib.sha256(patch.read_bytes()).hexdigest()
            manifest = root / "package.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "org.example.patched",
                        "name": "Patched",
                        "version": "0.1.0",
                        "kind": "cli-tool",
                        "summary": "Patched",
                        "license": "MIT",
                        "maintainers": [{"name": "X"}],
                        "source": {"type": "git", "url": "https://example.invalid", "sha256": "1" * 64},
                        "patches": [{"id": "fix", "path": "patches/fix.patch", "sha256": digest, "strip": 1, "applies_to": ["patched-linux"]}],
                        "requirements": {
                            "supported_os": ["linux"],
                            "supported_arch": ["amd64"],
                            "supported_compiler_families": ["clang"],
                            "supported_objc_runtimes": ["libobjc2"],
                            "supported_objc_abi": ["modern"],
                            "required_features": [],
                            "forbidden_features": [],
                        },
                        "artifacts": [{"id": "patched-linux"}],
                        "install": {"executables": ["patched"]},
                    }
                )
            )
            payload = apply_package_patches(manifest, source, target_id="patched-linux")
            self.assertTrue(payload["ok"])
            self.assertEqual((source / "hello.txt").read_text(), "new\n")
            self.assertEqual(payload["applied_patches"][0]["id"], "fix")

    def test_apply_package_patches_reports_failed_patch(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = root / "source"
            source.mkdir()
            patch = root / "patches" / "fix.patch"
            patch.parent.mkdir()
            patch.write_text(
                "--- a/missing.txt\n"
                "+++ b/missing.txt\n"
                "@@ -1 +1 @@\n"
                "-old\n"
                "+new\n"
            )
            import hashlib
            digest = hashlib.sha256(patch.read_bytes()).hexdigest()
            manifest = root / "package.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "org.example.badpatch",
                        "name": "BadPatch",
                        "version": "0.1.0",
                        "kind": "cli-tool",
                        "summary": "BadPatch",
                        "license": "MIT",
                        "maintainers": [{"name": "X"}],
                        "source": {"type": "git", "url": "https://example.invalid", "sha256": "1" * 64},
                        "patches": [{"id": "fix", "path": "patches/fix.patch", "sha256": digest, "strip": 1}],
                        "requirements": {
                            "supported_os": ["linux"],
                            "supported_arch": ["amd64"],
                            "supported_compiler_families": ["clang"],
                            "supported_objc_runtimes": ["libobjc2"],
                            "supported_objc_abi": ["modern"],
                            "required_features": [],
                            "forbidden_features": [],
                        },
                        "artifacts": [{"id": "badpatch-linux"}],
                        "install": {"executables": ["badpatch"]},
                    }
                )
            )
            payload = apply_package_patches(manifest, source)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["errors"][0]["code"], "patch_apply_failed")



if __name__ == "__main__":
    unittest.main()
