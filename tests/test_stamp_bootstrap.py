import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dev" / "stamp_bootstrap.py"


class StampBootstrapTests(unittest.TestCase):
    def test_stamps_only_the_version_line_of_both_bootstraps(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([sys.executable, str(SCRIPT), "0.1.1", tmp], check=True, capture_output=True)
            for name, expected in (
                ("gnustep-bootstrap.sh", 'CLI_VERSION="0.1.1"'),
                ("gnustep-bootstrap.ps1", '$Script:CliVersion = "0.1.1"'),
            ):
                source = (ROOT / "scripts" / "bootstrap" / name).read_text().splitlines()
                stamped_bytes = (Path(tmp) / name).read_bytes()
                stamped = stamped_bytes.decode().splitlines()
                self.assertIn(expected, stamped)
                self.assertNotIn("0.1.0-dev", stamped_bytes.decode())
                changed = [i for i, (a, b) in enumerate(zip(source, stamped)) if a != b]
                self.assertEqual(len(changed), 1, name)
                self.assertEqual(len(source), len(stamped))
                digest = (Path(tmp) / f"{name}.sha256").read_text().split()[0]
                self.assertEqual(digest, hashlib.sha256(stamped_bytes).hexdigest())

    def test_rejects_non_release_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(SCRIPT), "0.1.1-dev", tmp], capture_output=True)
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
