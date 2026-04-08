import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
EXAMPLES = ROOT / "examples"


class RepositoryContractsTests(unittest.TestCase):
    def load_json(self, path: Path):
        return json.loads(path.read_text())

    def test_all_schema_files_are_valid_json(self):
        for path in sorted(SCHEMAS.glob("*.json")):
            with self.subTest(path=path.name):
                self.assertIsInstance(self.load_json(path), dict)

    def test_vocabulary_has_required_collections(self):
        payload = self.load_json(SCHEMAS / "compatibility-vocabulary-v1.json")
        for key in (
            "os_values",
            "arch_values",
            "compiler_family_values",
            "toolchain_flavor_values",
            "objc_runtime_values",
            "objc_abi_values",
            "feature_flag_values",
        ):
            with self.subTest(key=key):
                self.assertIn(key, payload)
                self.assertTrue(payload[key])

    def test_examples_exist_and_are_valid_json(self):
        expected = {
            "release-manifest-v1.json",
            "doctor-output-v1.json",
            "package-manifest-v1.json",
            "package-index-v1.json",
            "toolchain-source-lock-v1.json",
            "msys2-toolchain-input-manifest-v1.json",
            "toolchain-component-inventory-v1.json",
            "toolchain-manifest-v1.json",
        }
        found = {path.name for path in EXAMPLES.glob("*.json")}
        self.assertEqual(found, expected)
        for path in sorted(EXAMPLES.glob("*.json")):
            with self.subTest(path=path.name):
                self.assertIsInstance(self.load_json(path), dict)

    def test_release_manifest_example_shape(self):
        payload = self.load_json(EXAMPLES / "release-manifest-v1.json")
        self.assertEqual(payload["schema_version"], 1)
        self.assertIsInstance(payload["releases"], list)
        self.assertTrue(payload["releases"])

    def test_doctor_example_shape(self):
        payload = self.load_json(EXAMPLES / "doctor-output-v1.json")
        self.assertEqual(payload["command"], "doctor")
        self.assertIn("environment", payload)
        self.assertIn("compatibility", payload)
        self.assertIn("checks", payload)
        self.assertIn("actions", payload)

    def test_package_manifest_example_shape(self):
        payload = self.load_json(EXAMPLES / "package-manifest-v1.json")
        self.assertEqual(payload["schema_version"], 1)
        self.assertIn(payload["kind"], {"gui-app", "cli-tool", "library", "template"})
        self.assertTrue(payload["artifacts"])

    def test_package_index_example_shape(self):
        payload = self.load_json(EXAMPLES / "package-index-v1.json")
        self.assertEqual(payload["schema_version"], 1)
        self.assertTrue(payload["packages"])

    def test_toolchain_source_lock_example_shape(self):
        payload = self.load_json(EXAMPLES / "toolchain-source-lock-v1.json")
        self.assertEqual(payload["strategy"], "source-build")
        self.assertTrue(payload["components"])

    def test_msys2_toolchain_input_manifest_example_shape(self):
        payload = self.load_json(EXAMPLES / "msys2-toolchain-input-manifest-v1.json")
        self.assertEqual(payload["strategy"], "msys2-assembly")
        self.assertTrue(payload["packages"])

    def test_toolchain_component_inventory_example_shape(self):
        payload = self.load_json(EXAMPLES / "toolchain-component-inventory-v1.json")
        self.assertEqual(payload["schema_version"], 1)
        self.assertTrue(payload["components"])

    def test_toolchain_manifest_example_shape(self):
        payload = self.load_json(EXAMPLES / "toolchain-manifest-v1.json")
        self.assertEqual(payload["kind"], "managed-toolchain")
        self.assertTrue(payload["components"])


if __name__ == "__main__":
    unittest.main()
