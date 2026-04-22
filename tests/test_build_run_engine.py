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

from gnustep_cli_shared.build_run_engine import detect_project, execute_build, execute_clean, execute_run, plan_build, plan_clean, plan_run
import gnustep_cli_shared.build_run_engine as build_run_engine


class BuildRunEngineTests(unittest.TestCase):
    def test_detect_missing_project(self):
        with tempfile.TemporaryDirectory() as tempdir:
            payload = detect_project(tempdir)
            self.assertFalse(payload["supported"])
            self.assertEqual(payload["reason"], "missing_gnumakefile")

    def test_detect_tool_project(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "GNUmakefile"
            path.write_text("include $(GNUSTEP_MAKEFILES)/common.make\nTOOL_NAME = hello\n")
            payload = detect_project(tempdir)
            self.assertTrue(payload["supported"])
            self.assertEqual(payload["project_type"], "tool")
            self.assertEqual(payload["target_name"], "hello")


    def test_detect_aggregate_gnumakefile_as_buildable(self):
        with tempfile.TemporaryDirectory() as tempdir:
            (Path(tempdir) / "GNUmakefile").write_text(
                "SUBPROJECTS = InterfaceBuilder GormCore Tools\n"
                "include $(GNUSTEP_MAKEFILES)/aggregate.make\n"
            )
            payload = detect_project(tempdir)
            self.assertTrue(payload["supported"])
            self.assertEqual(payload["project_type"], "aggregate")
            self.assertIsNone(payload["target_name"])
            self.assertEqual(payload["build_system"], "gnustep-make")
            self.assertEqual(payload["detection_reason"], "gnumakefile_marker")

    def test_plan_build_accepts_unknown_gnumakefile(self):
        with tempfile.TemporaryDirectory() as tempdir:
            (Path(tempdir) / "GNUmakefile").write_text("include $(GNUSTEP_MAKEFILES)/common.make\n")
            payload = plan_build(tempdir)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["project"]["project_type"], "unknown")
            self.assertEqual(payload["invocation"], ["make"])


    def test_execute_build_invokes_make_for_aggregate_project(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "GNUmakefile").write_text("SUBPROJECTS = Tools\ninclude $(GNUSTEP_MAKEFILES)/aggregate.make\n")
            fake_bin = root / "bin"
            fake_bin.mkdir()
            marker = root / "make-invoked"
            fake_make = fake_bin / "make"
            fake_make.write_text(f"#!/bin/sh\ntouch '{marker}'\necho fake make ran\n")
            fake_make.chmod(0o755)
            old_path = os.environ.get("PATH", "")
            os.environ["PATH"] = f"{fake_bin}:{old_path}"
            try:
                payload, exit_code = execute_build(root)
            finally:
                os.environ["PATH"] = old_path
            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["project"]["project_type"], "aggregate")
            self.assertTrue(marker.exists())
            self.assertIn("fake make ran", payload["stdout"])

    def test_plan_clean_uses_backend_clean_operation(self):
        with tempfile.TemporaryDirectory() as tempdir:
            (Path(tempdir) / "GNUmakefile").write_text("SUBPROJECTS = Tools\ninclude $(GNUSTEP_MAKEFILES)/aggregate.make\n")
            payload = plan_clean(tempdir)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["command"], "clean")
            self.assertEqual(payload["backend"], "gnustep-make")
            self.assertEqual(payload["operation"], "clean")
            self.assertEqual(payload["invocation"], ["make", "distclean"])

    def test_execute_clean_invokes_distclean_for_gnustep_make_project(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "GNUmakefile").write_text("SUBPROJECTS = Tools\ninclude $(GNUSTEP_MAKEFILES)/aggregate.make\n")
            fake_bin = root / "bin"
            fake_bin.mkdir()
            marker = root / "make-clean-invoked"
            fake_make = fake_bin / "make"
            fake_make.write_text(f"#!/bin/sh\ntest \"$1\" = distclean\ntouch '{marker}'\necho fake clean ran\n")
            fake_make.chmod(0o755)
            old_path = os.environ.get("PATH", "")
            os.environ["PATH"] = f"{fake_bin}:{old_path}"
            try:
                payload, exit_code = execute_clean(root)
            finally:
                os.environ["PATH"] = old_path
            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["ok"])
            self.assertTrue(marker.exists())
            self.assertIn("fake clean ran", payload["stdout"])

    def test_plan_clean_build_has_clean_and_build_phases(self):
        with tempfile.TemporaryDirectory() as tempdir:
            (Path(tempdir) / "GNUmakefile").write_text("SUBPROJECTS = Tools\ninclude $(GNUSTEP_MAKEFILES)/aggregate.make\n")
            payload = plan_build(tempdir, clean_first=True)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["operation"], "clean_build")
            self.assertEqual([phase["name"] for phase in payload["phases"]], ["clean", "build"])
            self.assertEqual(payload["phases"][0]["invocation"], ["make", "distclean"])
            self.assertEqual(payload["phases"][1]["invocation"], ["make"])

    def test_plan_run_rejects_aggregate_without_runnable_targets(self):
        with tempfile.TemporaryDirectory() as tempdir:
            (Path(tempdir) / "GNUmakefile").write_text("SUBPROJECTS = Libraries\ninclude $(GNUSTEP_MAKEFILES)/aggregate.make\n")
            library = Path(tempdir) / "Libraries"
            library.mkdir()
            (library / "GNUmakefile").write_text("LIBRARY_NAME = Stuff\ninclude $(GNUSTEP_MAKEFILES)/library.make\n")
            payload = plan_run(tempdir)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["project"]["project_type"], "aggregate")
            self.assertEqual(payload["summary"], "This GNUstep project can be built, but no runnable target was detected.")

    def test_plan_run_discovers_single_app_under_aggregate_project(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "GNUmakefile").write_text("SUBPROJECTS = Applications\ninclude $(GNUSTEP_MAKEFILES)/aggregate.make\n")
            (root / "Applications").mkdir()
            (root / "Applications" / "GNUmakefile").write_text("SUBPROJECTS = Gorm\ninclude $(GNUSTEP_MAKEFILES)/aggregate.make\n")
            app_dir = root / "Applications" / "Gorm"
            app_dir.mkdir()
            (app_dir / "GNUmakefile").write_text("APP_NAME = Gorm\ninclude $(GNUSTEP_MAKEFILES)/application.make\n")
            payload = plan_run(root)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["backend"], "openapp")
            if os.name == "nt":
                self.assertEqual(payload["invocation"][:2], ["bash.exe", "-lc"])
                self.assertIn("/clang64/share/GNUstep/Makefiles/GNUstep.sh", payload["invocation"][2])
                self.assertIn('export PATH="/clang64/bin:/usr/bin:', payload["invocation"][2])
                self.assertIn("/clang64/bin/openapp './Gorm.app'", payload["invocation"][2])
            else:
                self.assertEqual(payload["invocation"], ["openapp", "Gorm.app"])
            self.assertEqual(payload["run_project"]["project_dir"], str(app_dir.resolve()))

    def test_plan_run_reports_multiple_runnable_targets(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "GNUmakefile").write_text("SUBPROJECTS = Applications\ninclude $(GNUSTEP_MAKEFILES)/aggregate.make\n")
            (root / "Applications").mkdir()
            (root / "Applications" / "GNUmakefile").write_text("SUBPROJECTS = One Two\ninclude $(GNUSTEP_MAKEFILES)/aggregate.make\n")
            for name in ("One", "Two"):
                app_dir = root / "Applications" / name
                app_dir.mkdir()
                (app_dir / "GNUmakefile").write_text(f"APP_NAME = {name}\ninclude $(GNUSTEP_MAKEFILES)/application.make\n")
            payload = plan_run(root)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["summary"], "Multiple runnable targets were detected. Run from a specific app or tool directory.")
            self.assertEqual(len(payload["runnable_targets"]), 2)

    def test_plan_run_ignores_recursive_subproject_symlink(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "GNUmakefile").write_text("SUBPROJECTS = Loop\ninclude $(GNUSTEP_MAKEFILES)/aggregate.make\n")
            (root / "Loop").symlink_to(root, target_is_directory=True)
            payload = plan_run(root)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["summary"], "This GNUstep project can be built, but no runnable target was detected.")

    def test_plan_build_for_tool(self):
        with tempfile.TemporaryDirectory() as tempdir:
            (Path(tempdir) / "GNUmakefile").write_text("TOOL_NAME = hello\n")
            payload = plan_build(tempdir)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["backend"], "gnustep-make")
            self.assertEqual(payload["invocation"], ["make"])

    def test_plan_build_uses_gmake_on_openbsd(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            fake_gmake = fake_bin / "gmake"
            fake_gmake.write_text("#!/bin/sh\n")
            fake_gmake.chmod(0o755)
            (root / "GNUmakefile").write_text("TOOL_NAME = hello\n")
            old_path = os.environ.get("PATH", "")
            os.environ["PATH"] = f"{fake_bin}:{old_path}"
            try:
                with patch.object(build_run_engine.sys, "platform", "openbsd7"):
                    build_payload = plan_build(root)
                    clean_payload = plan_clean(root)
            finally:
                os.environ["PATH"] = old_path
            self.assertEqual(build_payload["invocation"], [str(fake_gmake)])
            self.assertEqual(clean_payload["invocation"], [str(fake_gmake), "distclean"])

    def test_plan_run_for_app(self):
        with tempfile.TemporaryDirectory() as tempdir:
            (Path(tempdir) / "GNUmakefile").write_text("APP_NAME = HelloApp\n")
            payload = plan_run(tempdir)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["backend"], "openapp")
            if os.name == "nt":
                self.assertEqual(payload["invocation"][:2], ["bash.exe", "-lc"])
                self.assertIn("/clang64/share/GNUstep/Makefiles/GNUstep.sh", payload["invocation"][2])
                self.assertIn('export PATH="/clang64/bin:/usr/bin:', payload["invocation"][2])
                self.assertIn("/clang64/bin/openapp './HelloApp.app'", payload["invocation"][2])
            else:
                self.assertEqual(payload["invocation"], ["openapp", "HelloApp.app"])

    def test_plan_run_uses_windows_tool_executable_when_present(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "GNUmakefile").write_text("TOOL_NAME = hello\n")
            (root / "obj").mkdir()
            (root / "obj" / "hello.exe").write_text("")
            payload = plan_run(tempdir)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["backend"], "direct-exec")
            self.assertEqual(payload["invocation"], ["./obj/hello.exe"])

    def test_execute_run_handles_missing_binary(self):
        with tempfile.TemporaryDirectory() as tempdir:
            (Path(tempdir) / "GNUmakefile").write_text("TOOL_NAME = hello\n")
            payload, exit_code = execute_run(tempdir)
            self.assertFalse(payload["ok"])
            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["summary"], "Run target was not found. Build the project before running it.")


if __name__ == "__main__":
    unittest.main()
