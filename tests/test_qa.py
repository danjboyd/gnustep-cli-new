import sys
import unittest
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.qa import regression_suite


class QATests(unittest.TestCase):
    def test_regression_suite_runner(self):
        payload = regression_suite()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["exit_status"], 0)
        if os.environ.get("GNUSTEP_CLI_QA_NESTED") == "1":
            self.assertEqual(payload["summary"], "Nested regression invocation skipped.")
        else:
            stage_ids = [stage["id"] for stage in payload["stages"]]
            self.assertEqual(stage_ids, ["python", "native-full-cli"])
            self.assertTrue(all(stage["ok"] for stage in payload["stages"]))


if __name__ == "__main__":
    unittest.main()
