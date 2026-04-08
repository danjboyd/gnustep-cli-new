import json
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.setup_planner import build_setup_payload


class SetupPlannerTests(unittest.TestCase):
    def test_user_scope_plan(self):
        payload, exit_code = build_setup_payload(scope="user")
        self.assertEqual(payload["command"], "setup")
        self.assertEqual(payload["plan"]["scope"], "user")
        self.assertEqual(exit_code, 0)

    def test_system_scope_requires_privileges_for_non_root(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("test expects non-root execution")
        payload, exit_code = build_setup_payload(scope="system")
        self.assertEqual(payload["status"], "error")
        self.assertEqual(exit_code, 3)
        self.assertEqual(payload["actions"][0]["kind"], "rerun_with_elevated_privileges")

    def test_setup_payload_json_round_trip(self):
        payload, _ = build_setup_payload(scope="user")
        encoded = json.dumps(payload)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["command"], "setup")


if __name__ == "__main__":
    unittest.main()

