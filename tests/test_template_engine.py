import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.template_engine import available_templates, create_template


class TemplateEngineTests(unittest.TestCase):
    def test_available_templates(self):
        self.assertIn("gui-app", available_templates())
        self.assertIn("cli-tool", available_templates())

    def test_create_cli_tool_template(self):
        with tempfile.TemporaryDirectory() as tempdir:
            dest = Path(tempdir) / "hello-cli"
            payload = create_template("cli-tool", dest, "HelloCLI")
            self.assertTrue(payload["ok"])
            self.assertTrue((dest / "GNUmakefile").exists())
            self.assertTrue((dest / "main.m").exists())
            self.assertTrue((dest / "package.json").exists())
            gnumakefile = (dest / "GNUmakefile").read_text()
            self.assertIn("ADDITIONAL_OBJCFLAGS", gnumakefile)
            self.assertIn("ADDITIONAL_LDFLAGS", gnumakefile)

    def test_create_cli_alias_template(self):
        with tempfile.TemporaryDirectory() as tempdir:
            dest = Path(tempdir) / "hello-cli"
            payload = create_template("cli", dest, "HelloCLI")
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["template"], "cli-tool")
            self.assertTrue((dest / "GNUmakefile").exists())
            self.assertTrue((dest / "main.m").exists())
            self.assertTrue((dest / "package.json").exists())

    def test_create_gui_app_template(self):
        with tempfile.TemporaryDirectory() as tempdir:
            dest = Path(tempdir) / "hello-app"
            payload = create_template("gui-app", dest, "HelloApp")
            self.assertTrue(payload["ok"])
            self.assertTrue((dest / "Resources" / "Info-gnustep.plist").exists())


if __name__ == "__main__":
    unittest.main()
