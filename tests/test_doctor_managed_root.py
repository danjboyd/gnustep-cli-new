import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.doctor_engine import _managed_root_in_use, build_doctor_payload


def _managed_root(base: Path, name: str = "managed", status: str = "healthy") -> Path:
    root = base / name
    (root / "state").mkdir(parents=True)
    (root / "state" / "cli-state.json").write_text(json.dumps({"schema_version": 1, "status": status}))
    (root / "System" / "Library" / "Makefiles").mkdir(parents=True)
    return root


class ManagedRootInUseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def state(self, root: Path) -> str:
        return str(root / "state" / "cli-state.json")

    def test_makefiles_inside_a_healthy_managed_root(self):
        root = _managed_root(self.base)
        self.assertEqual(_managed_root_in_use(str(root / "System/Library/Makefiles"), self.state(root)), str(root))

    def test_sibling_with_the_root_as_a_string_prefix_is_not_managed(self):
        root = _managed_root(self.base)
        other = self.base / "managed-other" / "System" / "Library" / "Makefiles"
        other.mkdir(parents=True)
        self.assertIsNone(_managed_root_in_use(str(other), self.state(root)))

    def test_external_native_toolchain_is_not_managed(self):
        root = _managed_root(self.base)
        self.assertIsNone(_managed_root_in_use("/usr/share/GNUstep/Makefiles", self.state(root)))

    def test_symlink_into_the_root_counts_and_symlink_out_does_not(self):
        root = _managed_root(self.base)
        inside_link = self.base / "link-in"
        os.symlink(root / "System", inside_link)
        self.assertEqual(_managed_root_in_use(str(inside_link / "Library/Makefiles"), self.state(root)), str(root))
        outside = self.base / "elsewhere" / "Makefiles"
        outside.mkdir(parents=True)
        os.symlink(outside, root / "System" / "Library" / "LinkedMakefiles")
        self.assertIsNone(_managed_root_in_use(str(root / "System/Library/LinkedMakefiles"), self.state(root)))

    def test_unhealthy_missing_or_corrupt_state_is_not_ready(self):
        for status in ("needs_repair", "installing", "upgrading"):
            root = _managed_root(self.base, name=f"m-{status}", status=status)
            self.assertIsNone(_managed_root_in_use(str(root / "System/Library/Makefiles"), self.state(root)))
        root = _managed_root(self.base, name="corrupt")
        (root / "state" / "cli-state.json").write_text("{not json")
        self.assertIsNone(_managed_root_in_use(str(root / "System/Library/Makefiles"), self.state(root)))
        self.assertIsNone(_managed_root_in_use(str(root / "System/Library/Makefiles"), str(self.base / "absent.json")))
        self.assertIsNone(_managed_root_in_use(None, self.state(root)))

    def test_the_root_itself_is_not_a_toolchain_inside_it(self):
        root = _managed_root(self.base)
        self.assertIsNone(_managed_root_in_use(str(root), self.state(root)))


class DoctorManagedWordingTests(unittest.TestCase):
    SUPPORTED = {
        "assessment": "supported",
        "preference": "native",
        "message": "The detected native GNUstep environment satisfies the managed runtime expectations.",
        "reasons": [],
    }

    def payload(self, root: Path, makefiles: str) -> dict:
        toolchain = {
            "present": True, "compiler_family": "clang", "compiler_version": "19", "toolchain_flavor": "clang",
            "objc_runtime": "libobjc2", "objc_abi": "modern", "gnustep_make": True, "gnustep_base": True,
            "gnustep_gui": True, "can_compile": True, "can_link": True, "can_run": True,
            "feature_flags": {"blocks": True}, "detected_layouts": ["gnustep"], "gnustep_makefiles": makefiles,
        }
        with patch("gnustep_cli_shared.doctor_engine._detect_toolchain", return_value=toolchain), \
             patch("gnustep_cli_shared.doctor_engine._assess_native_toolchain", return_value=dict(self.SUPPORTED)):
            return build_doctor_payload(interface="full", managed_root=root)

    def test_managed_install_gets_managed_wording(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _managed_root(Path(tmp).resolve())
            payload = self.payload(root, str(root / "System/Library/Makefiles"))
        checks = {check["id"]: check for check in payload["checks"]}
        self.assertIn("managed install at", checks["native-toolchain.assess"]["message"])
        self.assertEqual(checks["native-toolchain.assess"]["details"]["managed_root"], str(root))
        kinds = [action["kind"] for action in payload["actions"]]
        self.assertIn("use_managed_toolchain", kinds)
        self.assertNotIn("choose a managed install", " ".join(action["message"] for action in payload["actions"]))

    def test_external_toolchain_keeps_native_wording(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _managed_root(Path(tmp).resolve())
            payload = self.payload(root, "/usr/share/GNUstep/Makefiles")
        kinds = [action["kind"] for action in payload["actions"]]
        self.assertIn("use_existing_toolchain", kinds)
        self.assertNotIn("use_managed_toolchain", kinds)

    def test_repair_state_is_not_called_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _managed_root(Path(tmp).resolve(), status="needs_repair")
            payload = self.payload(root, str(root / "System/Library/Makefiles"))
        checks = {check["id"]: check for check in payload["checks"]}
        self.assertEqual(checks["managed.install.integrity"]["status"], "warning")
        self.assertNotIn("use_managed_toolchain", [action["kind"] for action in payload["actions"]])


if __name__ == "__main__":
    unittest.main()
