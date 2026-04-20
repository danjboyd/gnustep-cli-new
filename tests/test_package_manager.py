import hashlib
import io
import json
import sys
import tarfile
import tempfile
import unittest
import zipfile
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.package_manager import install_package, install_package_from_index, recover_package_transactions, remove_package, upgrade_package, upgrade_package_from_index


class PackageManagerTests(unittest.TestCase):
    def _make_artifact(self, directory: Path, message: str = "hello") -> Path:
        artifact = directory / f"artifact-{message}.tar.gz"
        payload_dir = directory / f"payload-{message}"
        payload_dir.mkdir()
        (payload_dir / "bin").mkdir()
        (payload_dir / "bin" / "hello").write_text(f"#!/bin/sh\necho {message}\n")
        with tarfile.open(artifact, "w:gz") as archive:
            archive.add(payload_dir, arcname=".")
        return artifact

    def _sha256(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_install_and_remove_package(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact = self._make_artifact(root)
            manifest = root / "package.json"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "org.example.hello",
                        "artifacts": [{"url": f"file://{artifact}", "sha256": self._sha256(artifact)}],
                    }
                )
            )
            payload, code = install_package(manifest, root / "managed")
            self.assertEqual(code, 0)
            self.assertTrue(payload["ok"])
            installed = root / "managed" / "packages" / "org.example.hello"
            self.assertTrue(installed.exists())
            removed, remove_code = remove_package("org.example.hello", root / "managed")
            self.assertEqual(remove_code, 0)
            self.assertTrue(removed["ok"])
            self.assertFalse(installed.exists())


    def test_install_rejects_digest_mismatch(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact = self._make_artifact(root)
            manifest = root / "package.json"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "org.example.hello",
                        "artifacts": [{"url": f"file://{artifact}", "sha256": "0" * 64}],
                    }
                )
            )
            payload, code = install_package(manifest, root / "managed")
            self.assertEqual(code, 1)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["summary"], "Artifact digest verification failed.")

    def test_install_zip_package(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact = root / "artifact.zip"
            with zipfile.ZipFile(artifact, "w") as archive:
                archive.writestr("bin/hello.cmd", "@echo hello\n")
            manifest = root / "package.json"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "org.example.hello",
                        "artifacts": [{"url": f"file://{artifact}", "format": "zip", "sha256": self._sha256(artifact)}],
                    }
                )
            )
            payload, code = install_package(manifest, root / "managed")
            self.assertEqual(code, 0)
            self.assertTrue(payload["ok"])
            self.assertTrue((root / "managed" / "packages" / "org.example.hello" / "bin" / "hello.cmd").exists())


    def test_install_from_unsigned_index_requires_dev_override(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact = self._make_artifact(root)
            index = root / "package-index.json"
            index.write_text(json.dumps({
                "schema_version": 1,
                "packages": [{"id": "org.example.hello", "artifacts": [{"url": f"file://{artifact}", "sha256": self._sha256(artifact)}]}],
            }))
            payload, code = install_package_from_index(index, "org.example.hello", root / "managed")
            self.assertEqual(code, 4)
            self.assertFalse(payload["ok"])
            payload, code = install_package_from_index(index, "org.example.hello", root / "managed", require_signed_index=False)
            self.assertEqual(code, 4)
            self.assertFalse(payload["ok"])

    def test_install_from_signed_index(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact = self._make_artifact(root)
            index = root / "package-index.json"
            index.write_text(json.dumps({
                "schema_version": 1,
                "channel": "stable",
                "metadata_version": 1,
                "expires_at": "TBD",
                "packages": [{"id": "org.example.hello", "artifacts": [{"url": f"file://{artifact}", "sha256": self._sha256(artifact)}]}],
            }) + "\n")
            from gnustep_cli_shared.package_repository import sign_package_index_metadata
            key = root / "package-index-key.pem"
            subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(key)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            signed = sign_package_index_metadata(index, key)
            self.assertTrue(signed["ok"])
            payload, code = install_package_from_index(index, "org.example.hello", root / "managed", trusted_public_key_path=root / "package-index-signing-public.pem")
            self.assertEqual(code, 0)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["package_id"], "org.example.hello")


    def test_upgrade_package_replaces_files_transactionally(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            old_artifact = self._make_artifact(root, "old")
            new_artifact = self._make_artifact(root, "new")
            old_manifest = root / "old-package.json"
            new_manifest = root / "new-package.json"
            old_manifest.write_text(json.dumps({
                "id": "org.example.hello",
                "version": "1.0.0",
                "artifacts": [{"url": f"file://{old_artifact}", "sha256": self._sha256(old_artifact)}],
            }))
            new_manifest.write_text(json.dumps({
                "id": "org.example.hello",
                "version": "2.0.0",
                "artifacts": [{"url": f"file://{new_artifact}", "sha256": self._sha256(new_artifact)}],
            }))
            install_payload, install_code = install_package(old_manifest, root / "managed")
            upgrade_payload, upgrade_code = upgrade_package(new_manifest, root / "managed")
            installed_file = root / "managed" / "packages" / "org.example.hello" / "bin" / "hello"
            state = json.loads((root / "managed" / "state" / "installed-packages.json").read_text())
            self.assertEqual(install_code, 0)
            self.assertEqual(upgrade_code, 0)
            self.assertTrue(install_payload["ok"])
            self.assertTrue(upgrade_payload["ok"])
            self.assertEqual(upgrade_payload["command"], "upgrade")
            self.assertIn("echo new", installed_file.read_text())
            self.assertEqual(state["packages"]["org.example.hello"]["version"], "2.0.0")
            self.assertFalse((root / "managed" / ".transactions" / "packages" / "org.example.hello.json").exists())

    def test_remove_records_and_clears_transaction(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact = self._make_artifact(root)
            manifest = root / "package.json"
            manifest.write_text(json.dumps({
                "id": "org.example.hello",
                "artifacts": [{"url": f"file://{artifact}", "sha256": self._sha256(artifact)}],
            }))
            install_package(manifest, root / "managed")
            payload, code = remove_package("org.example.hello", root / "managed")
            self.assertEqual(code, 0)
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["transaction"]["completed"])
            self.assertFalse(Path(payload["transaction"]["path"]).exists())


    def test_upgrade_package_from_signed_index(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            old_artifact = self._make_artifact(root, "old")
            new_artifact = self._make_artifact(root, "new")
            old_manifest = root / "old-package.json"
            old_manifest.write_text(json.dumps({
                "id": "org.example.hello",
                "version": "1.0.0",
                "artifacts": [{"url": f"file://{old_artifact}", "sha256": self._sha256(old_artifact)}],
            }))
            install_package(old_manifest, root / "managed")
            index = root / "package-index.json"
            index.write_text(json.dumps({
                "schema_version": 1,
                "channel": "stable",
                "metadata_version": 1,
                "expires_at": "TBD",
                "packages": [{"id": "org.example.hello", "version": "2.0.0", "artifacts": [{"url": f"file://{new_artifact}", "sha256": self._sha256(new_artifact)}]}],
            }) + "\n")
            from gnustep_cli_shared.package_repository import sign_package_index_metadata
            key = root / "package-index-key.pem"
            subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(key)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            self.assertTrue(sign_package_index_metadata(index, key)["ok"])
            payload, code = upgrade_package_from_index(index, "org.example.hello", root / "managed", trusted_public_key_path=root / "package-index-signing-public.pem")
            installed_file = root / "managed" / "packages" / "org.example.hello" / "bin" / "hello"
            self.assertEqual(code, 0)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["command"], "upgrade")
            self.assertIn("echo new", installed_file.read_text())

    def test_recover_package_transactions_restores_upgrade_backup(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            managed = root / "managed"
            package_id = "org.example.hello"
            final_root = managed / "packages" / package_id
            backup_root = managed / ".transactions" / "package-backups" / package_id
            final_root.mkdir(parents=True)
            (final_root / "new.txt").write_text("new")
            backup_root.mkdir(parents=True)
            (backup_root / "old.txt").write_text("old")
            tx = managed / ".transactions" / "packages" / f"{package_id}.json"
            tx.parent.mkdir(parents=True)
            tx.write_text(json.dumps({
                "schema_version": 1,
                "operation": "upgrade",
                "package_id": package_id,
                "final_root": str(final_root),
                "backup_root": str(backup_root),
            }))
            audit, audit_code = recover_package_transactions(managed)
            recovered, recovery_code = recover_package_transactions(managed, apply=True)
            self.assertEqual(audit_code, 0)
            self.assertEqual(recovery_code, 0)
            self.assertEqual(len(audit["transactions"]), 1)
            self.assertTrue(recovered["transactions"][0]["recovered"])
            self.assertTrue((final_root / "old.txt").exists())
            self.assertFalse(tx.exists())


    def test_recover_package_transactions_restores_remove_state(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            managed = root / "managed"
            package_id = "org.example.hello"
            install_root = managed / "packages" / package_id
            backup_root = managed / ".transactions" / "package-remove-backups" / package_id
            backup_root.mkdir(parents=True)
            (backup_root / "old.txt").write_text("old")
            (managed / "state").mkdir(parents=True)
            (managed / "state" / "installed-packages.json").write_text(json.dumps({"packages": {}}))
            record = {"install_root": str(install_root), "installed_files": ["packages/org.example.hello/old.txt"], "version": "1.0.0"}
            tx = managed / ".transactions" / "packages" / f"{package_id}.json"
            tx.parent.mkdir(parents=True)
            tx.write_text(json.dumps({
                "schema_version": 1,
                "operation": "remove",
                "package_id": package_id,
                "install_root": str(install_root),
                "backup_root": str(backup_root),
                "package_record": record,
            }))
            payload, code = recover_package_transactions(managed, apply=True)
            state = json.loads((managed / "state" / "installed-packages.json").read_text())
            self.assertEqual(code, 0)
            self.assertTrue(payload["transactions"][0]["recovered"])
            self.assertTrue((install_root / "old.txt").exists())
            self.assertEqual(state["packages"][package_id]["version"], "1.0.0")
            self.assertFalse(tx.exists())

    def test_remove_missing_package(self):
        with tempfile.TemporaryDirectory() as tempdir:
            payload, code = remove_package("missing", Path(tempdir) / "managed")
            self.assertEqual(code, 1)
            self.assertFalse(payload["ok"])

    def test_reinstall_returns_existing_state_without_reextracting(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact = self._make_artifact(root)
            manifest = root / "package.json"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "org.example.hello",
                        "artifacts": [{"url": f"file://{artifact}", "sha256": self._sha256(artifact)}],
                    }
                )
            )
            first_payload, first_code = install_package(manifest, root / "managed")
            second_payload, second_code = install_package(manifest, root / "managed")
            self.assertEqual(first_code, 0)
            self.assertEqual(second_code, 0)
            self.assertTrue(second_payload["ok"])
            self.assertEqual(second_payload["summary"], "Package is already installed.")
            self.assertEqual(second_payload["installed_files"], first_payload["installed_files"])

    def test_remove_updates_state_file(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact = self._make_artifact(root)
            manifest = root / "package.json"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "org.example.hello",
                        "artifacts": [{"url": f"file://{artifact}", "sha256": self._sha256(artifact)}],
                    }
                )
            )
            install_package(manifest, root / "managed")
            payload, code = remove_package("org.example.hello", root / "managed")
            state = json.loads((root / "managed" / "state" / "installed-packages.json").read_text())
            self.assertEqual(code, 0)
            self.assertTrue(payload["ok"])
            self.assertEqual(state["packages"], {})


if __name__ == "__main__":
    unittest.main()
