import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
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
        self.assertIn(
            payload["native_toolchain_assessment"],
            {"unavailable", "broken", "preferred", "supported", "interoperability_only", "incompatible"},
        )
        self.assertIn("toolchain", payload["environment"])
        self.assertIn("native_toolchain", payload["environment"])
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

    def test_bootstrap_doctor_uses_same_contract_with_limited_depth(self):
        payload = build_doctor_payload(interface="bootstrap")
        self.assertEqual(payload["command"], "doctor")
        self.assertEqual(payload["interface"], "bootstrap")
        self.assertEqual(payload["diagnostic_depth"], "installer")
        checks = {check["id"]: check for check in payload["checks"]}
        self.assertEqual(checks["toolchain.probe"]["status"], "not_run")
        self.assertEqual(checks["toolchain.probe"]["execution_tier"], "full_only")
        self.assertEqual(checks["managed.install.integrity"]["status"], "not_run")
        self.assertEqual(checks["managed.install.integrity"]["execution_tier"], "full_only")

    def test_bootstrap_and_full_share_check_vocabulary(self):
        bootstrap = build_doctor_payload(interface="bootstrap")
        full = build_doctor_payload(interface="full")
        bootstrap_ids = {check["id"] for check in bootstrap["checks"]}
        full_ids = {check["id"] for check in full["checks"]}
        self.assertEqual(bootstrap_ids, full_ids)

    def test_debian_gcc_is_classified_as_interoperability_only(self):
        fake_toolchain = {
            "present": True,
            "compiler_family": "gcc",
            "compiler_version": "14.2.0",
            "toolchain_flavor": "gcc",
            "objc_runtime": "gcc_libobjc",
            "objc_abi": "legacy",
            "gnustep_make": True,
            "gnustep_base": False,
            "gnustep_gui": False,
            "can_compile": True,
            "can_link": True,
            "can_run": True,
            "feature_flags": {
                "objc2_syntax": False,
                "blocks": False,
                "arc": False,
                "nonfragile_abi": False,
                "associated_objects": False,
                "exceptions": True,
            },
            "compiler_path": "/usr/bin/gcc",
            "gnustep_config_path": "/usr/bin/gnustep-config",
            "gnustep_makefiles": "/usr/share/GNUstep/Makefiles",
            "detected_layouts": ["debian"],
        }
        with patch("gnustep_cli_shared.doctor_engine._detect_os", return_value="linux"), patch(
            "gnustep_cli_shared.doctor_engine._read_os_release", return_value="debian-sid"
        ), patch("gnustep_cli_shared.doctor_engine._detect_arch", return_value="amd64"), patch(
            "gnustep_cli_shared.doctor_engine._detect_toolchain", return_value=fake_toolchain
        ):
            payload = build_doctor_payload(interface="full")
        self.assertEqual(payload["native_toolchain_assessment"], "interoperability_only")
        self.assertEqual(payload["environment"]["native_toolchain"]["preference"], "managed")
        self.assertIn("gcc_interop_only", {r["code"] for r in payload["environment"]["native_toolchain"]["reasons"]})

    def test_openbsd_clang_is_classified_as_preferred_native(self):
        fake_toolchain = {
            "present": True,
            "compiler_family": "clang",
            "compiler_version": "18.1.0",
            "toolchain_flavor": "clang",
            "objc_runtime": "libobjc2",
            "objc_abi": "modern",
            "gnustep_make": True,
            "gnustep_base": False,
            "gnustep_gui": False,
            "can_compile": True,
            "can_link": True,
            "can_run": True,
            "feature_flags": {
                "objc2_syntax": True,
                "blocks": True,
                "arc": True,
                "nonfragile_abi": True,
                "associated_objects": True,
                "exceptions": True,
            },
            "compiler_path": "/usr/bin/clang",
            "gnustep_config_path": "/usr/local/bin/gnustep-config",
            "gnustep_makefiles": "/usr/local/share/GNUstep/Makefiles",
            "detected_layouts": ["gnustep"],
        }
        with patch("gnustep_cli_shared.doctor_engine._detect_os", return_value="openbsd"), patch(
            "gnustep_cli_shared.doctor_engine._read_os_release", return_value=None
        ), patch("gnustep_cli_shared.doctor_engine._detect_arch", return_value="amd64"), patch(
            "gnustep_cli_shared.doctor_engine._detect_toolchain", return_value=fake_toolchain
        ):
            payload = build_doctor_payload(interface="full")
        self.assertEqual(payload["native_toolchain_assessment"], "preferred")
        self.assertEqual(payload["environment"]["native_toolchain"]["preference"], "native")

    def test_fedora_clang_is_classified_as_supported_native(self):
        fake_toolchain = {
            "present": True,
            "compiler_family": "clang",
            "compiler_version": "19.1.0",
            "toolchain_flavor": "clang",
            "objc_runtime": "libobjc2",
            "objc_abi": "modern",
            "gnustep_make": True,
            "gnustep_base": True,
            "gnustep_gui": True,
            "can_compile": True,
            "can_link": True,
            "can_run": True,
            "feature_flags": {
                "objc2_syntax": True,
                "blocks": True,
                "arc": True,
                "nonfragile_abi": True,
                "associated_objects": True,
                "exceptions": True,
            },
            "compiler_path": "/usr/bin/clang",
            "gnustep_config_path": "/usr/bin/gnustep-config",
            "gnustep_makefiles": "/usr/share/GNUstep/Makefiles",
            "detected_layouts": ["fedora"],
        }
        with patch("gnustep_cli_shared.doctor_engine._detect_os", return_value="linux"), patch(
            "gnustep_cli_shared.doctor_engine._read_os_release", return_value="fedora-42"
        ), patch("gnustep_cli_shared.doctor_engine._detect_arch", return_value="amd64"), patch(
            "gnustep_cli_shared.doctor_engine._detect_toolchain", return_value=fake_toolchain
        ):
            payload = build_doctor_payload(interface="full")
        self.assertEqual(payload["native_toolchain_assessment"], "supported")
        self.assertEqual(payload["environment"]["native_toolchain"]["preference"], "native")
        self.assertIn("fedora_packaged_candidate", {r["code"] for r in payload["environment"]["native_toolchain"]["reasons"]})

    def test_arch_clang_is_classified_as_supported_native(self):
        fake_toolchain = {
            "present": True,
            "compiler_family": "clang",
            "compiler_version": "19.1.0",
            "toolchain_flavor": "clang",
            "objc_runtime": "libobjc2",
            "objc_abi": "modern",
            "gnustep_make": True,
            "gnustep_base": True,
            "gnustep_gui": True,
            "can_compile": True,
            "can_link": True,
            "can_run": True,
            "feature_flags": {
                "objc2_syntax": True,
                "blocks": True,
                "arc": True,
                "nonfragile_abi": True,
                "associated_objects": True,
                "exceptions": True,
            },
            "compiler_path": "/usr/bin/clang",
            "gnustep_config_path": "/usr/bin/gnustep-config",
            "gnustep_makefiles": "/usr/share/GNUstep/Makefiles",
            "detected_layouts": ["arch"],
        }
        with patch("gnustep_cli_shared.doctor_engine._detect_os", return_value="linux"), patch(
            "gnustep_cli_shared.doctor_engine._read_os_release", return_value="arch-rolling"
        ), patch("gnustep_cli_shared.doctor_engine._detect_arch", return_value="amd64"), patch(
            "gnustep_cli_shared.doctor_engine._detect_toolchain", return_value=fake_toolchain
        ):
            payload = build_doctor_payload(interface="full")
        self.assertEqual(payload["native_toolchain_assessment"], "supported")
        self.assertEqual(payload["environment"]["native_toolchain"]["preference"], "native")
        self.assertIn("arch_packaged_candidate", {r["code"] for r in payload["environment"]["native_toolchain"]["reasons"]})


    def test_full_doctor_flags_interrupted_managed_install_state(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "state").mkdir()
            (root / ".staging" / "payload").mkdir(parents=True)
            (root / "state" / "cli-state.json").write_text(json.dumps({"schema_version": 1, "status": "upgrading"}))
            fake_toolchain = {
                "present": True,
                "compiler_family": "clang",
                "compiler_version": "18.1.0",
                "toolchain_flavor": "clang",
                "objc_runtime": "libobjc2",
                "objc_abi": "modern",
                "gnustep_make": True,
                "gnustep_base": True,
                "gnustep_gui": True,
                "can_compile": True,
                "can_link": True,
                "can_run": True,
                "feature_flags": {"blocks": True, "objc2_syntax": True, "arc": True, "nonfragile_abi": True, "associated_objects": True, "exceptions": True},
                "detected_layouts": ["gnustep"],
            }
            with patch("gnustep_cli_shared.doctor_engine._detect_toolchain", return_value=fake_toolchain):
                payload = build_doctor_payload(interface="full", managed_root=root)
            checks = {check["id"]: check for check in payload["checks"]}
            self.assertEqual(checks["managed.install.integrity"]["status"], "warning")
            self.assertEqual(checks["managed.install.integrity"]["details"]["state_status"], "upgrading")
            self.assertTrue(checks["managed.install.integrity"]["details"]["stale_paths"])

    def test_full_doctor_uses_deeper_detection_than_bootstrap(self):
        bootstrap_toolchain = {
            "present": True,
            "compiler_family": "clang",
            "compiler_version": "18.1.0",
            "toolchain_flavor": "clang",
            "objc_runtime": "libobjc2",
            "objc_abi": "modern",
            "gnustep_make": True,
            "gnustep_base": False,
            "gnustep_gui": False,
            "can_compile": True,
            "can_link": True,
            "can_run": True,
            "feature_flags": {
                "objc2_syntax": True,
                "blocks": True,
                "arc": True,
                "nonfragile_abi": True,
                "associated_objects": True,
                "exceptions": True,
            },
            "compiler_path": "/usr/bin/clang",
            "gnustep_config_path": "/usr/local/bin/gnustep-config",
            "gnustep_makefiles": "/usr/local/share/GNUstep/Makefiles",
            "detected_layouts": ["gnustep"],
            "detection_depth": "installer",
        }
        full_toolchain = dict(bootstrap_toolchain)
        full_toolchain["gnustep_base"] = True
        full_toolchain["gnustep_gui"] = True
        full_toolchain["detection_depth"] = "full"

        with patch("gnustep_cli_shared.doctor_engine._detect_toolchain", side_effect=[bootstrap_toolchain, full_toolchain]):
            bootstrap = build_doctor_payload(interface="bootstrap")
            full = build_doctor_payload(interface="full")

        self.assertEqual(bootstrap["environment"]["toolchain"]["detection_depth"], "installer")
        self.assertEqual(full["environment"]["toolchain"]["detection_depth"], "full")
        self.assertFalse(bootstrap["environment"]["toolchain"]["gnustep_base"])
        self.assertTrue(full["environment"]["toolchain"]["gnustep_base"])
        self.assertFalse(bootstrap["environment"]["toolchain"]["gnustep_gui"])
        self.assertTrue(full["environment"]["toolchain"]["gnustep_gui"])


if __name__ == "__main__":
    unittest.main()
