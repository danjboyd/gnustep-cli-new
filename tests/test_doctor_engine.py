import json
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.compatibility import normalize_arch, normalize_os
from gnustep_cli_shared.doctor_engine import build_doctor_payload


class DoctorEngineTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalize_os("Linux"), "linux")
        self.assertEqual(normalize_os("Darwin"), "macos")
        self.assertEqual(normalize_arch("x86_64"), "amd64")

    def test_doctor_payload_shape(self):
        payload = build_doctor_payload()
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["command"], "doctor")
        self.assertIn(payload["status"], {"ok", "warning", "error"})
        self.assertIn(
            payload["environment_classification"],
            {"no_toolchain", "toolchain_compatible", "toolchain_incompatible", "toolchain_broken"},
        )
        self.assertIn("toolchain", payload["environment"])
        self.assertIn("checks", payload)
        self.assertIn("actions", payload)
        self.assertTrue(payload["checks"])

    def test_doctor_payload_json_round_trip(self):
        payload = build_doctor_payload()
        encoded = json.dumps(payload)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["command"], "doctor")

    def test_doctor_detects_bootstrap_prerequisites(self):
        payload = build_doctor_payload()
        prereqs = payload["environment"]["bootstrap_prerequisites"]
        self.assertIn("curl", prereqs)
        self.assertIn("wget", prereqs)

    def test_doctor_reports_linux_here(self):
        payload = build_doctor_payload()
        self.assertEqual(payload["environment"]["os"], "linux")


if __name__ == "__main__":
    unittest.main()

