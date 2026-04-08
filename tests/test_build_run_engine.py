import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.build_run_engine import detect_project, execute_run, plan_build, plan_run


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

    def test_execute_run_handles_missing_binary(self):
        with tempfile.TemporaryDirectory() as tempdir:
            (Path(tempdir) / "GNUmakefile").write_text("TOOL_NAME = hello\n")
            payload, exit_code = execute_run(tempdir)
            self.assertFalse(payload["ok"])
            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["summary"], "Run target was not found. Build the project before running it.")


if __name__ == "__main__":
    unittest.main()
