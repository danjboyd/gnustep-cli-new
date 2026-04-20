import json
import tempfile
import zipfile
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "bootstrap" / "gnustep-bootstrap.ps1"


class BootstrapPowerShellTests(unittest.TestCase):
    def run_script(self, *args):
        proc = subprocess.run(
            ["pwsh", "-NoLogo", "-NoProfile", "-File", str(BOOTSTRAP), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return proc

    def test_help_shows_full_surface(self):
        proc = self.run_script("--help")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("setup", proc.stdout)
        self.assertIn("doctor", proc.stdout)
        self.assertIn("build", proc.stdout)
        self.assertIn("update", proc.stdout)

    def test_doctor_json_shape(self):
        proc = self.run_script("--json", "doctor")
        self.assertIn(proc.returncode, (0, 3))
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["command"], "doctor")
        self.assertIn("checks", payload)

    def test_setup_system_requires_elevation(self):
        proc = self.run_script("--json", "--system", "setup")
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["command"], "setup")
        self.assertIn(payload["status"], {"ok", "error"})

    def test_setup_uses_local_manifest_and_zip_artifacts(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            release_dir = temp / "release"
            release_dir.mkdir()

            cli_zip = release_dir / "gnustep-cli-windows-amd64-msys2-clang64-0.1.0-dev.zip"
            with zipfile.ZipFile(cli_zip, "w") as archive:
                archive.writestr("gnustep-cli-windows-amd64-msys2-clang64-0.1.0-dev/bin/gnustep.exe", "binary")
                archive.writestr("gnustep-cli-windows-amd64-msys2-clang64-0.1.0-dev/examples/release-manifest-v1.json", "{}")

            toolchain_zip = release_dir / "gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0-dev.zip"
            long_name = "x" * 120
            with zipfile.ZipFile(toolchain_zip, "w") as archive:
                archive.writestr(r"gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0-dev\System\Tools\make.exe", "tool")
                archive.writestr(
                    f"gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0-dev/lib/{long_name}/{long_name}/{long_name}/payload.txt",
                    "payload",
                )

            def sha256(path: Path) -> str:
                import hashlib
                return hashlib.sha256(path.read_bytes()).hexdigest()

            manifest = {
                "schema_version": 1,
                "channel": "stable",
                "generated_at": "2026-04-15T00:00:00Z",
                "releases": [
                    {
                        "version": "0.1.0-dev",
                        "status": "active",
                        "artifacts": [
                            {
                                "id": "cli-windows-amd64-msys2-clang64",
                                "kind": "cli",
                                "version": "0.1.0-dev",
                                "os": "windows",
                                "arch": "amd64",
                                "compiler_family": "clang",
                                "toolchain_flavor": "msys2-clang64",
                                "objc_runtime": "libobjc2",
                                "objc_abi": "modern",
                                "required_features": [],
                                "format": "zip",
                                "url": "https://example.invalid/gnustep-cli-windows-amd64-msys2-clang64-0.1.0-dev.zip",
                                "sha256": sha256(cli_zip),
                                "filename": cli_zip.name,
                            },
                            {
                                "id": "toolchain-windows-amd64-msys2-clang64",
                                "kind": "toolchain",
                                "version": "0.1.0-dev",
                                "os": "windows",
                                "arch": "amd64",
                                "compiler_family": "clang",
                                "toolchain_flavor": "msys2-clang64",
                                "objc_runtime": "libobjc2",
                                "objc_abi": "modern",
                                "required_features": ["blocks"],
                                "format": "zip",
                                "url": "https://example.invalid/gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0-dev.zip",
                                "sha256": sha256(toolchain_zip),
                                "filename": toolchain_zip.name,
                            },
                        ],
                    }
                ],
            }
            manifest_path = release_dir / "release-manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            install_root = temp / "install-root"

            proc = self.run_script(
                "--json",
                "setup",
                "--root",
                str(install_root),
                "--manifest",
                str(manifest_path),
            )
            payload = json.loads(proc.stdout)
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertTrue(payload["ok"], msg=proc.stdout + proc.stderr)
            self.assertTrue((install_root / "bin" / "gnustep.exe").exists())
            self.assertTrue((install_root / "System" / "Tools" / "make.exe").exists())
            self.assertTrue((install_root / "state" / "cli-state.json").exists())


    def test_setup_human_mode_reports_progress(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            release_dir = temp / "release"
            release_dir.mkdir()
            cli_zip = release_dir / "gnustep-cli-windows-amd64-msys2-clang64-0.1.0-dev.zip"
            with zipfile.ZipFile(cli_zip, "w") as archive:
                archive.writestr("gnustep-cli-windows-amd64-msys2-clang64-0.1.0-dev/bin/gnustep.exe", "binary")
            toolchain_zip = release_dir / "gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0-dev.zip"
            with zipfile.ZipFile(toolchain_zip, "w") as archive:
                archive.writestr("gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0-dev/System/Tools/make.exe", "tool")

            def sha256(path: Path) -> str:
                import hashlib
                return hashlib.sha256(path.read_bytes()).hexdigest()

            manifest = {
                "schema_version": 1,
                "channel": "stable",
                "generated_at": "2026-04-20T00:00:00Z",
                "releases": [{"version": "0.1.0-dev", "status": "active", "artifacts": [
                    {"id": "cli-windows-amd64-msys2-clang64", "url": cli_zip.name, "sha256": sha256(cli_zip)},
                    {"id": "toolchain-windows-amd64-msys2-clang64", "url": toolchain_zip.name, "sha256": sha256(toolchain_zip)},
                ]}],
            }
            manifest_path = release_dir / "release-manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            install_root = temp / "install-root"
            proc = self.run_script("setup", "--root", str(install_root), "--manifest", str(manifest_path))
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("setup: starting managed installation", proc.stdout)
            self.assertIn("setup: fetching CLI artifact", proc.stdout)
            self.assertIn("setup: extracting toolchain artifact", proc.stdout)
            self.assertIn("setup: managed installation completed", proc.stdout)


    def test_setup_writes_trace_file(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            release_dir = temp / "release"
            release_dir.mkdir()
            cli_zip = release_dir / "gnustep-cli-windows-amd64-msys2-clang64-0.1.0-dev.zip"
            with zipfile.ZipFile(cli_zip, "w") as archive:
                archive.writestr("gnustep-cli-windows-amd64-msys2-clang64-0.1.0-dev/bin/gnustep.exe", "binary")
            toolchain_zip = release_dir / "gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0-dev.zip"
            with zipfile.ZipFile(toolchain_zip, "w") as archive:
                archive.writestr("gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0-dev/System/Tools/make.exe", "tool")
            def sha256(path: Path) -> str:
                import hashlib
                return hashlib.sha256(path.read_bytes()).hexdigest()
            manifest = {
                "schema_version": 1,
                "channel": "stable",
                "generated_at": "2026-04-17T00:00:00Z",
                "releases": [{"version": "0.1.0-dev", "status": "active", "artifacts": [
                    {"id": "cli-windows-amd64-msys2-clang64", "url": cli_zip.name, "sha256": sha256(cli_zip)},
                    {"id": "toolchain-windows-amd64-msys2-clang64", "url": toolchain_zip.name, "sha256": sha256(toolchain_zip)},
                ]}],
            }
            manifest_path = release_dir / "release-manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            trace_path = temp / "setup-trace.jsonl"
            install_root = temp / "install-root"
            proc = self.run_script("--json", "setup", "--root", str(install_root), "--manifest", str(manifest_path), "--trace", str(trace_path))
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            trace = trace_path.read_text()
            self.assertIn('"step":"setup.start"', trace)
            self.assertIn('"step":"install.state.complete"', trace)
            self.assertIn('"step":"setup.success"', trace)


if __name__ == "__main__":
    unittest.main()

