import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.package_repository import generate_package_index, write_package_index


class PackageRepositoryTests(unittest.TestCase):
    def test_generate_index_from_packages_root(self):
        with tempfile.TemporaryDirectory() as tempdir:
            package_dir = Path(tempdir) / "org.example.hello"
            package_dir.mkdir(parents=True)
            (package_dir / "package.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "org.example.hello",
                        "name": "Hello",
                        "version": "0.1.0",
                        "kind": "cli-tool",
                        "summary": "hello",
                        "requirements": {},
                        "dependencies": [],
                        "artifacts": [{"id": "hello-linux"}],
                    }
                )
            )
            payload = generate_package_index(tempdir)
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(len(payload["packages"]), 1)
            self.assertEqual(payload["packages"][0]["id"], "org.example.hello")

    def test_write_index(self):
        with tempfile.TemporaryDirectory() as tempdir:
            package_dir = Path(tempdir) / "org.example.hello"
            package_dir.mkdir(parents=True)
            (package_dir / "package.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "org.example.hello",
                        "name": "Hello",
                        "version": "0.1.0",
                        "kind": "cli-tool",
                        "summary": "hello",
                        "requirements": {},
                        "dependencies": [],
                        "artifacts": [{"id": "hello-linux"}],
                    }
                )
            )
            output = Path(tempdir) / "generated" / "package-index.json"
            write_package_index(tempdir, output)
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()

