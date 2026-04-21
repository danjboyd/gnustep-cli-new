import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.build_run_engine import detect_project, execute_build, execute_run, plan_build, plan_run


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

    def test_plan_run_rejects_aggregate_with_run_specific_message(self):
        with tempfile.TemporaryDirectory() as tempdir:
            (Path(tempdir) / "GNUmakefile").write_text("SUBPROJECTS = Tools\ninclude $(GNUSTEP_MAKEFILES)/aggregate.make\n")
            payload = plan_run(tempdir)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["project"]["project_type"], "aggregate")
            self.assertEqual(payload["summary"], "This GNUstep project can be built, but no runnable target was detected.")

    def test_plan_build_for_tool(self):
        with tempfile.TemporaryDirectory() as tempdir:
            (Path(tempdir) / "GNUmakefile").write_text("TOOL_NAME = hello\n")
            payload = plan_build(tempdir)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["backend"], "gnustep-make")
            self.assertEqual(payload["invocation"], ["make"])

    def test_plan_run_for_app(self):
        with tempfile.TemporaryDirectory() as tempdir:
            (Path(tempdir) / "GNUmakefile").write_text("APP_NAME = HelloApp\n")
            payload = plan_run(tempdir)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["backend"], "openapp")
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
