import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.package_manager import install_package, remove_package


class PackageManagerTests(unittest.TestCase):
    def _make_artifact(self, directory: Path) -> Path:
        artifact = directory / "artifact.tar.gz"
        payload_dir = directory / "payload"
        payload_dir.mkdir()
        (payload_dir / "bin").mkdir()
        (payload_dir / "bin" / "hello").write_text("#!/bin/sh\necho hello\n")
        with tarfile.open(artifact, "w:gz") as archive:
            archive.add(payload_dir, arcname=".")
        return artifact

    def test_install_and_remove_package(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact = self._make_artifact(root)
            manifest = root / "package.json"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "org.example.hello",
                        "artifacts": [{"url": f"file://{artifact}"}],
                    }
                )
            )
            payload, code = install_package(manifest, root / "managed")
            self.assertEqual(code, 0)
            self.assertTrue(payload["ok"])
            installed = root / "managed" / "packages" / "org.example.hello"
            self.assertTrue(installed.exists())
            removed, remove_code = remove_package("org.example.hello", root / "managed")
            self.assertEqual(remove_code, 0)
            self.assertTrue(removed["ok"])
            self.assertFalse(installed.exists())

    def test_remove_missing_package(self):
        with tempfile.TemporaryDirectory() as tempdir:
            payload, code = remove_package("missing", Path(tempdir) / "managed")
            self.assertEqual(code, 1)
            self.assertFalse(payload["ok"])


if __name__ == "__main__":
    unittest.main()

