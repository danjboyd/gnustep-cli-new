import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.package_repository import (
    generate_package_index,
    package_index_trust_gate,
    sign_package_index_metadata,
    write_package_index,
    write_package_index_provenance,
)


class PackageRepositoryTests(unittest.TestCase):
    def test_committed_package_index_matches_generated_output(self):
        generated = generate_package_index(ROOT / "packages")
        committed = json.loads((ROOT / "packages" / "package-index.json").read_text())
        self.assertEqual(committed, generated)

    def test_repo_packages_include_tools_xctest(self):
        payload = generate_package_index(ROOT / "packages")
        package_ids = {record["id"] for record in payload["packages"]}
        self.assertIn("org.gnustep.tools-xctest", package_ids)


    def test_package_index_has_trust_metadata(self):
        payload = generate_package_index(ROOT / "packages")
        self.assertEqual(payload["metadata_version"], 1)
        self.assertEqual(payload["trust"]["signature_policy"], "single-role-v1")

    def test_package_index_artifacts_include_source_and_selected_patches(self):
        payload = generate_package_index(ROOT / "packages")
        package = next(package for package in payload["packages"] if package["id"] == "org.gnustep.tools-xctest")
        self.assertEqual(package["build"]["backend"], "gnustep-cli")
        artifact = next(artifact for artifact in package["artifacts"] if artifact["id"] == "tools-xctest-linux-amd64-clang")
        self.assertEqual(artifact["source"]["tracking_strategy"], "commit-with-submitted-downstream-patch")
        self.assertEqual(artifact["patches"][0]["id"], "add-apple-style-xctest-cli-filters")
        self.assertEqual(artifact["patches"][0]["upstream_status"], "submitted")

    def test_package_index_unsigned_trust_gate_requires_provenance(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            package_dir = root / "org.example.hello"
            package_dir.mkdir(parents=True)
            (package_dir / "package.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "org.example.hello",
                        "name": "Hello",
                        "version": "0.1.0",
                        "kind": "cli-tool",
                        "summary": "hello",
                        "requirements": {},
                        "dependencies": [],
                        "artifacts": [{"id": "hello-linux", "sha256": "abc"}],
                    }
                )
            )
            output = root / "package-index.json"
            write_package_index(root, output)
            self.assertFalse(package_index_trust_gate(output, require_signatures=False)["ok"])
            write_package_index_provenance(output)
            self.assertTrue(package_index_trust_gate(output, require_signatures=False)["ok"])
            self.assertFalse(package_index_trust_gate(output)["ok"])

    def test_package_index_signing_and_trust_gate(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            package_dir = root / "org.example.hello"
            package_dir.mkdir(parents=True)
            (package_dir / "package.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "org.example.hello",
                        "name": "Hello",
                        "version": "0.1.0",
                        "kind": "cli-tool",
                        "summary": "hello",
                        "requirements": {},
                        "dependencies": [],
                        "artifacts": [{"id": "hello-linux", "sha256": "abc"}],
                    }
                )
            )
            output = root / "package-index.json"
            private_key = root / "package-signing-private.pem"
            write_package_index(root, output)
            import subprocess
            subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private_key)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            signed = sign_package_index_metadata(output, private_key)
            self.assertTrue(signed["ok"])
            self.assertTrue(package_index_trust_gate(output)["ok"])
            self.assertTrue(package_index_trust_gate(output, trusted_public_key_path=root / "package-index-signing-public.pem")["ok"])
            other_key = root / "other-package-index-key.pem"
            other_pub = root / "other-package-index-public.pem"
            subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(other_key)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            subprocess.run(["openssl", "pkey", "-in", str(other_key), "-pubout", "-out", str(other_pub)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            self.assertFalse(package_index_trust_gate(output, trusted_public_key_path=other_pub)["ok"])
            payload = json.loads(output.read_text())
            payload["packages"][0]["version"] = "9.9.9"
            output.write_text(json.dumps(payload, indent=2) + "\n")
            self.assertFalse(package_index_trust_gate(output)["ok"])

    def test_package_index_trust_gate_rejects_expired_metadata_and_revoked_package(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            package_dir = root / "org.example.hello"
            package_dir.mkdir(parents=True)
            (package_dir / "package.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "org.example.hello",
                        "name": "Hello",
                        "version": "0.1.0",
                        "kind": "cli-tool",
                        "summary": "hello",
                        "requirements": {},
                        "dependencies": [],
                        "artifacts": [{"id": "hello-linux", "sha256": "abc"}],
                    }
                )
            )
            output = root / "package-index.json"
            write_package_index(root, output)
            payload = json.loads(output.read_text())
            payload["expires_at"] = "2000-01-01T00:00:00Z"
            payload["trust"]["revoked_packages"] = ["org.example.hello"]
            output.write_text(json.dumps(payload, indent=2) + "\n")
            write_package_index_provenance(output)
            gate = package_index_trust_gate(output, require_signatures=False)
            checks = {check["id"]: check for check in gate["checks"]}
            self.assertFalse(gate["ok"])
            self.assertFalse(checks["metadata-not-expired"]["ok"])
            self.assertFalse(checks["revoked-packages-absent"]["ok"])

    def test_package_repo_cli_exits_nonzero_when_trust_gate_fails(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            package_dir = root / "org.example.hello"
            package_dir.mkdir(parents=True)
            (package_dir / "package.json").write_text(json.dumps({
                "schema_version": 1,
                "id": "org.example.hello",
                "name": "Hello",
                "version": "0.1.0",
                "kind": "cli-tool",
                "summary": "hello",
                "requirements": {},
                "dependencies": [],
                "artifacts": [{"id": "hello-linux", "sha256": "abc"}],
            }))
            output = root / "package-index.json"
            write_package_index(root, output)
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "internal" / "package_repo.py"), "--json", "--trust-gate", str(output)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 1)
            self.assertFalse(json.loads(proc.stdout)["ok"])

    def test_generate_index_from_packages_root(self):
        with tempfile.TemporaryDirectory() as tempdir:
            package_dir = Path(tempdir) / "org.example.hello"
            package_dir.mkdir(parents=True)
            (package_dir / "package.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "org.example.hello",
                        "name": "Hello",
                        "version": "0.1.0",
                        "kind": "cli-tool",
                        "summary": "hello",
                        "requirements": {},
                        "dependencies": [],
                        "artifacts": [{"id": "hello-linux"}],
                    }
                )
            )
            payload = generate_package_index(tempdir)
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(len(payload["packages"]), 1)
            self.assertEqual(payload["packages"][0]["id"], "org.example.hello")

    def test_write_index(self):
        with tempfile.TemporaryDirectory() as tempdir:
            package_dir = Path(tempdir) / "org.example.hello"
            package_dir.mkdir(parents=True)
            (package_dir / "package.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "org.example.hello",
                        "name": "Hello",
                        "version": "0.1.0",
                        "kind": "cli-tool",
                        "summary": "hello",
                        "requirements": {},
                        "dependencies": [],
                        "artifacts": [{"id": "hello-linux"}],
                    }
                )
            )
            output = Path(tempdir) / "generated" / "package-index.json"
            write_package_index(tempdir, output)
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
