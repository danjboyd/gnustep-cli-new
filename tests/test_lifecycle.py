import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.lifecycle import apply_upgrade_state, load_cli_state, plan_upgrade, repair_managed_root


class LifecycleTests(unittest.TestCase):
    def test_upgrade_plan_detects_cli_change(self):
        payload = plan_upgrade("/tmp/example", current_cli_version="0.1.0", target_cli_version="0.2.0")
        self.assertTrue(payload["actions"])
        self.assertEqual(payload["actions"][0]["kind"], "upgrade_cli")

    def test_apply_upgrade_state_persists(self):
        with tempfile.TemporaryDirectory() as tempdir:
            payload = apply_upgrade_state(tempdir, cli_version="0.2.0", toolchain_version="1.0.0")
            self.assertTrue(payload["ok"])
            state = load_cli_state(tempdir)
            self.assertEqual(state["cli_version"], "0.2.0")

    def test_repair_creates_state_and_packages_dirs(self):
        with tempfile.TemporaryDirectory() as tempdir:
            payload = repair_managed_root(tempdir)
            self.assertTrue(payload["ok"])
            self.assertTrue((Path(tempdir) / "state").exists())
            self.assertTrue((Path(tempdir) / "packages").exists())


if __name__ == "__main__":
    unittest.main()

