import json
import os
import tempfile
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "bootstrap" / "gnustep-bootstrap.sh"


class BootstrapShTests(unittest.TestCase):
    def run_script(self, *args):
        # Always run with a throwaway HOME: `setup` without --root installs into
        # $HOME/.local/share/gnustep-cli and must never touch the real user's
        # managed environment.
        with tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, HOME=home, XDG_CONFIG_HOME=f"{home}/.config",
                       XDG_CACHE_HOME=f"{home}/.cache", XDG_STATE_HOME=f"{home}/.local/state",
                       XDG_DATA_HOME=f"{home}/.local/share")
            proc = subprocess.run(
                ["sh", str(BOOTSTRAP), *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                env=env,
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

    def test_json_option_is_recognized_after_command(self):
        proc = self.run_script("doctor", "--json")
        self.assertIn(proc.returncode, (0, 3))
        self.assertEqual(json.loads(proc.stdout)["command"], "doctor")
        proc = self.run_script("doctor", "--yes", "--json")
        self.assertIn(proc.returncode, (0, 3))
        self.assertEqual(json.loads(proc.stdout)["command"], "doctor")

    def test_setup_reports_missing_local_manifest_as_json(self):
        with tempfile.TemporaryDirectory() as tempdir:
            missing = Path(tempdir) / "missing" / "release-manifest.json"
            proc = self.run_script("--json", "setup", "--root", f"{tempdir}/root", "--manifest", str(missing))
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["ok"])
        self.assertIn("not found", payload["summary"])

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
        # A local signed fixture keeps this offline and deterministic; it fails
        # at artifact selection, after the envelope fields are known.
        if not self._openssl():
            self.skipTest("openssl not available")
        directory, pubkey = self._signed_release_dir(sign=True)
        proc = self._setup(directory / "release-manifest.json", trust_root=pubkey)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["command"], "setup")
        self.assertFalse(payload["ok"])
        self.assertIn("summary", payload)
        self.assertIn("plan", payload)
        self.assertIn("actions", payload)

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

    def test_setup_records_artifact_digests_in_cli_state(self):
        import hashlib
        import shutil
        import tarfile

        doctor =json.loads(self.run_script("--json", "doctor").stdout)
        if doctor["environment"]["os"] != "linux" or doctor["environment"]["platform"] not in {"debian", "ubuntu"}:
            self.skipTest("managed target mapping exercised on Debian/Ubuntu hosts only")
        directory = Path(tempfile.mkdtemp(prefix="gnustep-state-test-"))
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)

        def tarball(name, files):
            staging = directory / f"{name}-src" / name
            for relative, text in files.items():
                path = staging / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
                path.chmod(0o755)
            archive = directory / f"{name}.tar.gz"
            with tarfile.open(archive, "w:gz") as handle:
                handle.add(staging, arcname=name)
            return archive, hashlib.sha256(archive.read_bytes()).hexdigest()

        cli, cli_sha = tarball("cli", {"bin/gnustep": "#!/bin/sh\necho 0.1.3-test\n"})
        toolchain, toolchain_sha = tarball("toolchain", {"share/GNUstep/Makefiles/GNUstep.sh": "true\n"})
        artifacts = []
        for suffix in ("linux-amd64-clang", "linux-arm64-clang", "linux-ubuntu2404-amd64-clang",
                       "linux-ubuntu2604-amd64-clang"):
            artifacts += [
                {"id": f"cli-{suffix}", "kind": "cli", "published": True,
                 "url": f"https://example.invalid/{cli.name}", "sha256": cli_sha},
                {"id": f"toolchain-{suffix}", "kind": "toolchain", "version": "2026.10.17", "published": True,
                 "url": f"https://example.invalid/{toolchain.name}", "sha256": toolchain_sha},
            ]
        manifest = directory / "release-manifest.json"
        manifest.write_text(json.dumps({"version": "0.1.3-test", "releases": [
            {"version": "0.1.3-test", "artifacts": artifacts}]}, indent=2) + "\n", encoding="utf-8")

        proc = self._setup(manifest, "--allow-unsigned")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        state = json.loads((directory / "install-root" / "state" / "cli-state.json").read_text())
        self.assertEqual(state["cli_artifact_sha256"], cli_sha)
        self.assertEqual(state["toolchain_artifact_sha256"], toolchain_sha)
        self.assertEqual(state["cli_version"], "0.1.3-test")
        self.assertEqual(state["toolchain_version"], "2026.10.17")
        self.assertTrue(state["cli_artifact_id"].startswith("cli-linux-"))
        self.assertEqual(state["toolchain_artifact_id"], state["cli_artifact_id"].replace("cli-", "toolchain-", 1))


    def test_bootstrap_knows_ubuntu_distro_scoped_target(self):
        content = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("managed_target_suffix", content)
        self.assertIn("linux-ubuntu2404-amd64-clang", content)
        self.assertIn("json_file_bool", content)
        self.assertIn("published", content)

    def _managed_target_suffix(self, *args):
        content = BOOTSTRAP.read_text(encoding="utf-8")
        start = content.index("managed_target_suffix() {")
        end = content.index("\n}\n", start) + 3
        script = content[start:end] + 'managed_target_suffix "$@"\n'
        proc = subprocess.run(["sh", "-c", script, "sh", *args], capture_output=True, text=True, check=True)
        return proc.stdout.strip()

    def test_managed_target_suffix_maps_ubuntu_lts_releases(self):
        self.assertEqual(self._managed_target_suffix("linux", "amd64", "ubuntu", "ubuntu-24.04"), "linux-ubuntu2404-amd64-clang")
        self.assertEqual(self._managed_target_suffix("linux", "amd64", "ubuntu", "ubuntu-26.04"), "linux-ubuntu2604-amd64-clang")
        self.assertEqual(self._managed_target_suffix("linux", "amd64", "ubuntu", "ubuntu-25.10"), "linux-ubuntu-unsupported-amd64-clang")
        self.assertEqual(self._managed_target_suffix("linux", "amd64", "debian", "debian-13"), "linux-amd64-clang")
        self.assertEqual(self._managed_target_suffix("linux", "arm64", "debian", "debian-13"), "linux-arm64-clang")

    def test_bootstrap_uses_canonical_arm64_architecture(self):
        content = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn('aarch64|arm64) printf \'%s\\n\' "arm64"', content)
        self.assertNotIn('aarch64|arm64) printf \'%s\\n\' "aarch64"', content)

    def test_bootstrap_has_temporary_dogfood_manifest_option(self):
        content = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("--dogfood", content)
        self.assertIn("DOGFOOD_MANIFEST_URL", content)
        self.assertIn("/releases/download/dogfood/release-manifest.json", content)

    def _emit_pinned_trust_root(self, cli_version="0.1.0", dogfood_mode=0):
        # Extract the trust-root emitter functions and exercise the real shell
        # channel selection in isolation.
        content = BOOTSTRAP.read_text(encoding="utf-8")
        import re
        block = re.search(
            r"emit_production_trust_root\(\) \{.*?\nemit_pinned_trust_root\(\) \{.*?\n\}",
            content,
            re.S,
        )
        self.assertIsNotNone(block, "trust-root emitter functions not found")
        proc = subprocess.run(
            ["sh", "-c", f"{block.group(0)}\nCLI_VERSION={cli_version} DOGFOOD_MODE={dogfood_mode} emit_pinned_trust_root"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True,
        )
        return proc.stdout

    def test_release_version_pins_production_trust_root(self):
        pem = (ROOT / "scripts" / "bootstrap" / "release-signing-trust-root.pem").read_text(encoding="utf-8")
        production = self._emit_pinned_trust_root(cli_version="0.1.0", dogfood_mode=0)
        dev_version = self._emit_pinned_trust_root(cli_version="0.1.0-dev", dogfood_mode=0)
        dogfood = self._emit_pinned_trust_root(cli_version="0.1.0", dogfood_mode=1)
        # A release version selects the production key, which is the canonical
        # release-signing-trust-root.pem.
        self.assertEqual(production, pem)
        # A -dev version and --dogfood both select a different (dev) key.
        self.assertNotEqual(production, dev_version)
        self.assertEqual(dev_version, dogfood)
        self.assertIn("BEGIN PUBLIC KEY", dev_version)

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
