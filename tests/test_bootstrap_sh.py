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
        self.assertIn("list", proc.stdout)
        self.assertIn("search", proc.stdout)
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

    # --- release-manifest signature verification ---------------------------

    def _openssl(self):
        return __import__("shutil").which("openssl")

    def _signed_release_dir(self, *, sign=True, tamper=False):
        """Create a release dir with a minimal manifest, return (dir, pubkey_path)."""
        import shutil
        import subprocess as sp
        import tempfile

        directory = Path(tempfile.mkdtemp(prefix="gnustep-sig-test-"))
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        manifest = {
            "version": "0.1.0-dev",
            "releases": [{"version": "0.1.0-dev", "artifacts": [
                {"id": "cli-linux-amd64-clang", "kind": "cli", "published": True,
                 "url": "https://example.invalid/cli.tar.gz", "sha256": "00"},
                {"id": "toolchain-linux-amd64-clang", "kind": "toolchain", "published": True,
                 "url": "https://example.invalid/tc.tar.gz", "sha256": "00"},
            ]}],
        }
        manifest_path = directory / "release-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        pubkey_path = directory / "trust.pub.pem"
        if sign:
            key_path = directory / "key.pem"
            sp.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048",
                    "-out", str(key_path)], check=True, capture_output=True)
            sp.run(["openssl", "dgst", "-sha256", "-sign", str(key_path),
                    "-out", str(directory / "release-manifest.json.sig"), str(manifest_path)],
                   check=True, capture_output=True)
            sp.run(["openssl", "pkey", "-in", str(key_path), "-pubout", "-out", str(pubkey_path)],
                   check=True, capture_output=True)
        if tamper:
            tampered = json.loads(manifest_path.read_text())
            tampered["releases"][0]["version"] = "9.9.9-evil"
            manifest_path.write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")
        return directory, pubkey_path

    def _setup(self, manifest, *extra, trust_root=None):
        import os
        env = dict(os.environ)
        if trust_root is not None:
            env["RELEASE_TRUST_ROOT"] = str(trust_root)
        root = manifest.parent / "install-root"
        proc = subprocess.run(
            ["sh", str(BOOTSTRAP), "--json", "setup", "--root", str(root),
             "--manifest", str(manifest), *extra],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False, env=env,
        )
        return proc

    def _trust_failed(self, proc):
        try:
            payload = json.loads(proc.stdout)
        except ValueError:
            return False
        return bool(payload.get("trust", {}).get("verified") is False)

    def test_setup_refuses_unsigned_manifest(self):
        if not self._openssl():
            self.skipTest("openssl not available")
        directory, _ = self._signed_release_dir(sign=False)
        proc = self._setup(directory / "release-manifest.json")
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(self._trust_failed(proc))
        self.assertIn("not signed", json.loads(proc.stdout)["trust"]["reason"])

    def test_setup_refuses_tampered_manifest(self):
        if not self._openssl():
            self.skipTest("openssl not available")
        directory, pubkey = self._signed_release_dir(sign=True, tamper=True)
        proc = self._setup(directory / "release-manifest.json", trust_root=pubkey)
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(self._trust_failed(proc))
        self.assertIn("did not verify", json.loads(proc.stdout)["trust"]["reason"])

    def test_setup_accepts_signed_manifest_with_pinned_trust_root(self):
        if not self._openssl():
            self.skipTest("openssl not available")
        directory, pubkey = self._signed_release_dir(sign=True)
        proc = self._setup(directory / "release-manifest.json", trust_root=pubkey)
        # Verification passes against the matching pinned key, so setup proceeds
        # past trust (and only then fails on the unreachable artifact URLs).
        self.assertFalse(self._trust_failed(proc))

    def test_setup_allow_unsigned_bypasses_verification(self):
        directory, _ = self._signed_release_dir(sign=False)
        proc = self._setup(directory / "release-manifest.json", "--allow-unsigned")
        self.assertFalse(self._trust_failed(proc))
        self.assertIn("verification skipped", proc.stderr)


    def test_bootstrap_knows_ubuntu_distro_scoped_target(self):
        content = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("managed_target_suffix", content)
        self.assertIn("linux-ubuntu2404-amd64-clang", content)
        self.assertIn("json_file_bool", content)
        self.assertIn("published", content)

    def test_bootstrap_uses_canonical_arm64_architecture(self):
        content = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn('aarch64|arm64) printf \'%s\\n\' "arm64"', content)
        self.assertNotIn('aarch64|arm64) printf \'%s\\n\' "aarch64"', content)

    def test_bootstrap_has_temporary_dogfood_manifest_option(self):
        content = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("--dogfood", content)
        self.assertIn("DOGFOOD_MANIFEST_URL", content)
        self.assertIn("/releases/download/dogfood/release-manifest.json", content)

    def test_openbsd_prerequisites_include_native_gnustep_runtime(self):
        content = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("gnustep-make gnustep-base gnustep-gui gnustep-back gnustep-libobjc2", content)
        self.assertIn("bash gmake", content)
        self.assertIn("doas \"$@\"", content)
        self.assertIn("bootstrap_user_home", content)
        self.assertIn("bootstrap_user_name", content)
        self.assertIn("chown -R \"$owner_user\" \"$selected_root\"", content)

    def test_bootstrap_accepts_single_directory_and_direct_root_artifacts(self):
        content = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn('child_count=$(find "$parent" -mindepth 1 -maxdepth 1 | wc -l)', content)
        self.assertIn('printf \'%s\\n\' "$parent"', content)

    def test_bootstrap_script_does_not_depend_on_python(self):
        content = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertNotIn("python3", content)
        self.assertNotIn("scripts/internal/doctor.py", content)
        self.assertNotIn("scripts/internal/setup_plan.py", content)


if __name__ == "__main__":
    unittest.main()
