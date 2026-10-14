import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dev" / "check-bundled-sonames.sh"


class CheckBundledSonamesTests(unittest.TestCase):
    def _archive(self, directory: Path, files: list[str]) -> Path:
        tree = directory / "tree"
        for relative in files:
            path = tree / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"not an elf\n")
        archive = directory / "artifact.tar.gz"
        with tarfile.open(archive, "w:gz") as handle:
            handle.add(tree, arcname=".")
        return archive

    def _run(self, archive: Path, icu_major: str) -> subprocess.CompletedProcess:
        env = dict(os.environ, ICU_MAJOR=icu_major)
        return subprocess.run(["sh", str(SCRIPT), str(archive)], capture_output=True, text=True, env=env)

    def test_rejects_bundled_glibc_and_foreign_icu(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._archive(Path(tmp), [
                "System/Library/Libraries/libc.so.6",
                "System/Library/Libraries/libicuuc.so.72",
                "Local/Library/Libraries/libgnustep-base.so.1.31",
            ])
            proc = self._run(archive, "76")
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn("System/Library/Libraries/libc.so.6", proc.stdout)
            self.assertIn("System/Library/Libraries/libicuuc.so.72", proc.stdout)

    def test_accepts_matching_icu_and_link_time_sysroot(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._archive(Path(tmp), [
                "System/Library/Libraries/libicuuc.so.78",
                "System/Sysroot/lib/x86_64-linux-gnu/libc.so.6",
                "Local/Library/Libraries/libgnustep-base.so.1.31",
            ])
            proc = self._run(archive, "78")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("ok: no bundled", proc.stdout)

    def test_requires_expected_icu_major(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._archive(Path(tmp), ["bin/gnustep"])
            env = {key: value for key, value in os.environ.items() if key != "ICU_MAJOR"}
            proc = subprocess.run(["sh", str(SCRIPT), str(archive)], capture_output=True, text=True, env=env)
            self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
