import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.msys2_lock import lock_input_manifest, parse_pacman_query


def write_sync_db(path: Path, packages: list[tuple[str, str, str, str]]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name, version, filename, sha256 in packages:
            desc = (
                f"%FILENAME%\n{filename}\n\n%NAME%\n{name}\n\n%VERSION%\n{version}\n\n"
                f"%CSIZE%\n1234\n\n%SHA256SUM%\n{sha256}\n\n"
            ).encode("utf-8")
            info = tarfile.TarInfo(f"{name}-{version}/desc")
            info.size = len(desc)
            archive.addfile(info, io.BytesIO(desc))


class Msys2LockTests(unittest.TestCase):
    def make_resolve_dir(self, root: Path, installed: str) -> Path:
        (root / "resolve.json").write_text(json.dumps({"resolved_at": "2026-10-16T20:00:00Z"}))
        (root / "pacman-Q.txt").write_text(installed)
        write_sync_db(root / "msys.db", [("make", "4.4.1-2", "make-4.4.1-2-x86_64.pkg.tar.zst", "a" * 64)])
        write_sync_db(
            root / "clang64.db",
            [
                ("mingw-w64-clang-x86_64-curl", "8.23.0-1", "mingw-w64-clang-x86_64-curl-8.23.0-1-any.pkg.tar.zst", "b" * 64),
                ("mingw-w64-clang-x86_64-curl", "8.22.0-1", "mingw-w64-clang-x86_64-curl-8.22.0-1-any.pkg.tar.zst", "c" * 64),
            ],
        )
        return root

    def manifest(self) -> dict:
        return {
            "schema_version": 1,
            "repository_snapshot": "TBD",
            "host_packages": [{"name": "make", "version": "TBD", "sha256": "TBD"}],
            "packages": [{"name": "mingw-w64-clang-x86_64-curl", "version": "TBD", "sha256": "TBD"}],
        }

    def test_parse_pacman_query(self):
        self.assertEqual(parse_pacman_query("make 4.4.1-2\n\nbash 5.3-1\n"), {"make": "4.4.1-2", "bash": "5.3-1"})
        with self.assertRaises(ValueError):
            parse_pacman_query("not a package line here\n")

    def test_lock_pins_exact_installed_version_and_full_closure(self):
        with tempfile.TemporaryDirectory() as tmp:
            resolve = self.make_resolve_dir(Path(tmp), "make 4.4.1-2\nmingw-w64-clang-x86_64-curl 8.23.0-1\n")
            locked = lock_input_manifest(self.manifest(), resolve)
        self.assertEqual(locked["repository_snapshot"], "2026-10-16T20:00:00Z")
        self.assertEqual(locked["packages"][0]["version"], "8.23.0-1")
        self.assertEqual(locked["packages"][0]["sha256"], "b" * 64)
        self.assertEqual(locked["host_packages"][0]["sha256"], "a" * 64)
        by_name = {entry["name"]: entry for entry in locked["locked_packages"]}
        self.assertEqual(
            by_name["mingw-w64-clang-x86_64-curl"]["url"],
            "https://repo.msys2.org/mingw/clang64/mingw-w64-clang-x86_64-curl-8.23.0-1-any.pkg.tar.zst",
        )
        self.assertEqual(by_name["make"]["url"], "https://repo.msys2.org/msys/x86_64/make-4.4.1-2-x86_64.pkg.tar.zst")

    def test_lock_fails_when_installed_version_is_not_in_sync_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            resolve = self.make_resolve_dir(Path(tmp), "make 4.4.1-2\nmingw-w64-clang-x86_64-curl 8.21.0-1\n")
            with self.assertRaisesRegex(ValueError, "curl 8.21.0-1"):
                lock_input_manifest(self.manifest(), resolve)

    def test_lock_fails_when_requested_package_was_not_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            resolve = self.make_resolve_dir(Path(tmp), "make 4.4.1-2\n")
            with self.assertRaisesRegex(ValueError, "requested package mingw-w64-clang-x86_64-curl"):
                lock_input_manifest(self.manifest(), resolve)

    @unittest.skipUnless(shutil.which("zstd"), "zstd not installed")
    def test_reads_zstd_compressed_sync_databases(self):
        with tempfile.TemporaryDirectory() as tmp:
            resolve = self.make_resolve_dir(Path(tmp), "make 4.4.1-2\nmingw-w64-clang-x86_64-curl 8.23.0-1\n")
            for name in ("msys.db", "clang64.db"):
                path = resolve / name
                gz = path.read_bytes()
                import gzip
                compressed = subprocess.run(["zstd", "-q", "-c"], input=gzip.decompress(gz), capture_output=True, check=True).stdout
                path.write_bytes(compressed)
            locked = lock_input_manifest(self.manifest(), resolve)
        self.assertEqual(len(locked["locked_packages"]), 2)

    def test_checked_in_windows_manifest_requests_curl(self):
        manifest = json.loads((ROOT / "toolchains" / "windows-amd64-msys2-clang64" / "input-manifest.json").read_text())
        self.assertIn("mingw-w64-clang-x86_64-curl", [package["name"] for package in manifest["packages"]])
        self.assertTrue(manifest["installer"]["url"].endswith("/msys2-x86_64-20260927.exe"))
        self.assertRegex(manifest["installer"]["sha256"], "^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
