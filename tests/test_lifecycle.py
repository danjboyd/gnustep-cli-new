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


    def test_repair_clears_stale_transactions_and_marks_interrupted_state(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "state").mkdir()
            (root / "packages").mkdir()
            (root / ".staging" / "pkg").mkdir(parents=True)
            (root / ".transactions" / "upgrade").mkdir(parents=True)
            (root / "state" / "setup-transaction.json").write_text("{}")
            (root / "state" / "cli-state.json").write_text('{"schema_version": 1, "status": "upgrading"}')
            payload = repair_managed_root(root)
            kinds = {repair["kind"] for repair in payload["repairs"]}
            codes = {issue["code"] for issue in payload["issues"]}
            self.assertIn("clear_staging", kinds)
            self.assertIn("clear_transactions", kinds)
            self.assertIn("clear_setup_transaction", kinds)
            self.assertIn("mark_needs_repair", kinds)
            self.assertIn("interrupted_lifecycle_action", codes)
            self.assertFalse((root / ".staging").exists())
            self.assertFalse((root / ".transactions").exists())
            self.assertFalse((root / "state" / "setup-transaction.json").exists())
            self.assertEqual(load_cli_state(root)["status"], "needs_repair")


if __name__ == "__main__":
    unittest.main()

