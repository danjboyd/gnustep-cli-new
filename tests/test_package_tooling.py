import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.package_tooling import init_package_manifest, validate_package_manifest


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


if __name__ == "__main__":
    unittest.main()
