import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.integration import (
    generate_desktop_entry,
    generate_windows_shortcut_metadata,
    validate_gui_integration,
)


class IntegrationTests(unittest.TestCase):
    def test_desktop_entry_generation(self):
        content = generate_desktop_entry(
            app_id="org.example.hello",
            display_name="Hello",
            exec_path="/opt/hello/bin/hello",
            icon_name="hello",
            categories=["Development"],
        )
        self.assertIn("[Desktop Entry]", content)
        self.assertIn("Name=Hello", content)

    def test_windows_shortcut_metadata(self):
        payload = generate_windows_shortcut_metadata(
            app_id="org.example.hello",
            display_name="Hello",
            executable=r"C:\Hello\hello.exe",
            icon_path=r"C:\Hello\hello.ico",
        )
        self.assertEqual(payload["shortcut_name"], "Hello.lnk")

    def test_gui_integration_validation(self):
        payload = validate_gui_integration(
            package_id="org.example.hello",
            display_name="Hello",
            icon_path="icon.png",
            launcher_enabled=True,
            categories=["Development"],
        )
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()

