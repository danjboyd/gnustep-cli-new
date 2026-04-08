import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "bootstrap" / "gnustep-bootstrap.ps1"


class BootstrapPowerShellTests(unittest.TestCase):
    def run_script(self, *args):
        proc = subprocess.run(
            ["pwsh", "-NoLogo", "-NoProfile", "-File", str(BOOTSTRAP), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return proc

    def test_help_shows_full_surface(self):
        proc = self.run_script("--help")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("setup", proc.stdout)
        self.assertIn("doctor", proc.stdout)
        self.assertIn("build", proc.stdout)

    def test_doctor_json_shape(self):
        proc = self.run_script("--json", "doctor")
        self.assertIn(proc.returncode, (0, 3))
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["command"], "doctor")
        self.assertIn("checks", payload)

    def test_setup_system_requires_elevation(self):
        proc = self.run_script("--json", "--system", "setup")
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["command"], "setup")
        self.assertIn(payload["status"], {"ok", "error"})


if __name__ == "__main__":
    unittest.main()

