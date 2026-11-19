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

from gnustep_cli_shared.doctor_engine import _gnustep_sources_check, _managed_root_in_use, _upgrade_backups_check, build_doctor_payload


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


class UpgradeBackupsCheckTests(unittest.TestCase):
    """#80: doctor reports the upgrade backups beside the root and which one rollback uses."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.root = _managed_root(self.base)
        self.state_path = self.root / "state" / "cli-state.json"

    def tearDown(self):
        self.tmp.cleanup()

    def backup(self, name: str, size: int, root_name: str = "managed") -> Path:
        path = self.base / f".{root_name}.setup-backup-{name}"
        (path / "bin").mkdir(parents=True)
        (path / "bin" / "gnustep").write_bytes(b"x" * size)
        return path

    def record_rollback(self, path: Path) -> None:
        self.state_path.write_text(json.dumps({"schema_version": 1, "status": "healthy", "previous_release_path": str(path)}))

    def test_no_backups(self):
        check = _upgrade_backups_check(self.state_path)
        self.assertEqual(check.status, "ok")
        self.assertEqual(check.message, "No upgrade backups were found beside the managed install.")
        self.assertEqual(check.details["backups"], [])

    def test_only_the_backup_rollback_uses(self):
        kept = self.backup("b", 1000)
        self.record_rollback(kept)
        check = _upgrade_backups_check(self.state_path)
        self.assertEqual(check.status, "ok")
        self.assertEqual(check.message, f"One upgrade backup is kept for `gnustep setup --rollback`: {kept}.")
        self.assertEqual(check.details["backups"], [{"path": str(kept), "size_bytes": 1000, "used_by_rollback": True}])
        self.assertEqual(check.details["removable_paths"], [])

    def test_older_backups_are_a_warning_with_sizes(self):
        older = self.backup("a", 1500000)
        kept = self.backup("b", 1000)
        self.record_rollback(kept)
        check = _upgrade_backups_check(self.state_path)
        self.assertEqual(check.status, "warning")
        self.assertEqual(check.details["removable_paths"], [str(older)])
        self.assertEqual(check.details["removable_bytes"], 1500000)
        self.assertEqual(check.details["rollback_backup"], str(kept))
        self.assertEqual(
            check.message,
            f"1 older upgrade backup(s) beside the managed install use 1.5 MB and can be removed (rollback uses only {kept}): {older}",
        )

    def test_backups_without_a_recorded_rollback_are_all_removable(self):
        older = self.backup("a", 10)
        check = _upgrade_backups_check(self.state_path)
        self.assertEqual(check.status, "warning")
        self.assertIsNone(check.details["rollback_backup"])
        self.assertTrue(check.message.startswith("1 older upgrade backup(s) beside the managed install use 0.0 MB and can be removed: "))
        self.assertEqual(check.details["removable_paths"], [str(older)])

    def test_unrelated_paths_are_ignored(self):
        self.backup("x", 10, root_name="other")
        (self.base / ".managed.setup-backup-").mkdir()
        (self.base / ".managed.setup-backup-file").write_text("not a directory")
        target = self.base / "elsewhere"
        (target / "big").mkdir(parents=True)
        os.symlink(target, self.base / ".managed.setup-backup-link")
        kept = self.backup("b", 10)
        # A symlink inside a backup is not followed when sizing it.
        os.symlink(target, kept / "linked")
        (target / "big" / "data").write_bytes(b"y" * 5000)
        self.record_rollback(kept)
        check = _upgrade_backups_check(self.state_path)
        self.assertEqual(check.status, "ok")
        self.assertEqual(check.details["backups"], [{"path": str(kept), "size_bytes": 10, "used_by_rollback": True}])

    def test_no_or_unreadable_state(self):
        self.assertEqual(_upgrade_backups_check(None).status, "not_run")
        self.state_path.write_text("{not json")
        self.backup("a", 10)
        check = _upgrade_backups_check(self.state_path)
        self.assertEqual(check.status, "warning")
        self.assertIsNone(check.details["rollback_backup"])


class GnustepSourcesCheckTests(unittest.TestCase):
    """#87: doctor says where libs-base, libs-gui and libs-back come from."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _managed_root(Path(self.tmp.name).resolve())

    def tearDown(self):
        self.tmp.cleanup()

    def test_source_built_root_reports_git_revisions(self):
        (self.root / "component-inventory.json").write_text(json.dumps({"components": [
            {"name": "libobjc2", "source_revision": "b67709ad7851973fde127022d8ac6a710c82b1d5"},
            {"name": "libs-base", "source_revision": "d898f703e618b86f9b7ecb0f05a257cb6ed3ffac"},
            {"name": "libs-gui", "source_revision": "7892137bdedd007eba8425f766e41481ddb4fda6"},
            {"name": "libs-back", "source_revision": "bf3b3ced525f08415a20d109f05be1f91492414c"},
        ]}))
        check = _gnustep_sources_check("full", self.root)
        self.assertEqual(check.id, "managed.toolchain.sources")
        self.assertEqual(check.status, "ok")
        self.assertTrue(check.message.startswith(
            "GNUstep libraries: libs-base d898f703 (upstream git), libs-gui 7892137b (upstream git), libs-back bf3b3ced (upstream git). "))
        self.assertIn("issues/87", check.message)
        self.assertEqual(check.details["libraries"][0], {"library": "libs-base", "kind": "revision", "revision": "d898f703e618b86f9b7ecb0f05a257cb6ed3ffac"})

    def test_msys2_root_reports_release_packages(self):
        (self.root / "component-inventory.json").write_text(json.dumps({"components": [
            {"name": "libs-base", "version": "TBD", "source": "curated-binary-input"},
        ]}))
        local = self.root / "var" / "lib" / "pacman" / "local"
        for name in ("mingw-w64-clang-x86_64-gnustep-base-1.31.1-10.5", "mingw-w64-clang-x86_64-gnustep-gui-0.32.0-7",
                     "mingw-w64-clang-x86_64-gnustep-back-0.32.0-6", "mingw-w64-clang-x86_64-gnustep-make-2.9.3-1"):
            (local / name).mkdir(parents=True)
        check = _gnustep_sources_check("full", self.root)
        self.assertEqual(check.status, "ok")
        self.assertTrue(check.message.startswith(
            "GNUstep libraries: libs-base 1.31.1 release (MSYS2 package 1.31.1-10.5), "
            "libs-gui 0.32.0 release (MSYS2 package 0.32.0-7), libs-back 0.32.0 release (MSYS2 package 0.32.0-6). "))
        self.assertEqual(check.details["libraries"][1], {"library": "libs-gui", "kind": "release", "version": "0.32.0", "package_version": "0.32.0-7"})

    def test_nothing_recorded_or_no_install(self):
        self.assertEqual(_gnustep_sources_check("full", self.root).status, "not_run")
        (self.root / "component-inventory.json").write_text("{not json")
        self.assertEqual(_gnustep_sources_check("full", self.root).status, "not_run")
        (self.root / "state" / "cli-state.json").unlink()
        check = _gnustep_sources_check("full", self.root)
        self.assertEqual(check.status, "not_run")
        self.assertEqual(check.details, {"managed_install_detected": False})

    def test_bootstrap_lists_it_as_full_only(self):
        check = _gnustep_sources_check("bootstrap", self.root)
        self.assertEqual((check.status, check.execution_tier), ("not_run", "full_only"))


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
