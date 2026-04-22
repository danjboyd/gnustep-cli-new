import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "bootstrap" / "gnustep-bootstrap.sh"


class BootstrapShTests(unittest.TestCase):
    def run_script(self, *args):
        proc = subprocess.run(
            ["sh", str(BOOTSTRAP), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return proc

    def test_help_shows_full_command_surface(self):
        proc = self.run_script("--help")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("setup", proc.stdout)
        self.assertIn("doctor", proc.stdout)
        self.assertIn("build", proc.stdout)
        self.assertIn("shell", proc.stdout)
        self.assertIn("remove", proc.stdout)
        self.assertIn("update", proc.stdout)

    def test_unknown_option_fails_with_usage_code(self):
        proc = self.run_script("--bogus")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Unknown option", proc.stderr)

    def test_no_command_returns_usage_code(self):
        proc = self.run_script()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Usage:", proc.stdout)

    def test_unsupported_command_returns_bootstrap_unavailable(self):
        proc = self.run_script("build")
        self.assertEqual(proc.returncode, 3)
        self.assertIn("unavailable in bootstrap", proc.stdout)

    def test_dogfood_option_is_recognized_before_and_after_command(self):
        proc = self.run_script("--dogfood", "build")
        self.assertEqual(proc.returncode, 3)
        self.assertIn("unavailable in bootstrap", proc.stdout)
        proc = self.run_script("build", "--dogfood")
        self.assertEqual(proc.returncode, 3)
        self.assertIn("unavailable in bootstrap", proc.stdout)

    def test_doctor_json_shape(self):
        proc = self.run_script("--json", "doctor")
        self.assertIn(proc.returncode, (0, 3))
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["command"], "doctor")
        self.assertIn("checks", payload)
        self.assertIn("actions", payload)

    def test_doctor_reports_tools_scripts_host_prerequisites(self):
        proc = self.run_script("--json", "doctor")
        self.assertIn(proc.returncode, (0, 3))
        payload = json.loads(proc.stdout)
        host_prereqs = payload["environment"]["host_prerequisites"]
        self.assertEqual(host_prereqs["source"], "https://github.com/gnustep/tools-scripts")
        if payload["environment"]["platform"] in {"debian", "ubuntu"}:
            self.assertIn("libxml2-dev", host_prereqs["packages"])
            self.assertIn("libavahi-client-dev", host_prereqs["packages"])
            self.assertIn("libcurl4-gnutls-dev", host_prereqs["packages"])

    def test_setup_json_shape(self):
        proc = self.run_script("--json", "setup")
        self.assertIn(proc.returncode, (0, 3, 4))
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["command"], "setup")
        self.assertIn("summary", payload)


    def test_bootstrap_knows_ubuntu_distro_scoped_target(self):
        content = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("managed_target_suffix", content)
        self.assertIn("linux-ubuntu2404-amd64-clang", content)
        self.assertIn("json_file_bool", content)
        self.assertIn("published", content)

    def test_bootstrap_has_temporary_dogfood_manifest_option(self):
        content = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("--dogfood", content)
        self.assertIn("DOGFOOD_MANIFEST_URL", content)
        self.assertIn("/releases/download/dogfood/release-manifest.json", content)

    def test_openbsd_prerequisites_include_native_gnustep_runtime(self):
        content = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("gnustep-make gnustep-base gnustep-gui gnustep-back gnustep-libobjc2", content)
        self.assertIn("doas \"$@\"", content)
        self.assertIn("bootstrap_user_home", content)
        self.assertIn("bootstrap_user_name", content)
        self.assertIn("chown -R \"$owner_user\" \"$selected_root\"", content)

    def test_bootstrap_script_does_not_depend_on_python(self):
        content = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertNotIn("python3", content)
        self.assertNotIn("scripts/internal/doctor.py", content)
        self.assertNotIn("scripts/internal/setup_plan.py", content)


if __name__ == "__main__":
    unittest.main()
