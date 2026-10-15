import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.runtime_library_path import MARKER, add_runtime_library_path  # noqa: E402

ZSH_RESTORE = 'if [ -n "$GS_ZSH_NEED_TO_RESTORE_SET" ]; then\n  unsetopt shwordsplit\nfi\n# EOF\n'


def _toolchain(root: Path, *, with_lib: bool = True) -> Path:
    """A gnustep-layout root whose GNUstep.sh sets GNUSTEP_MAKEFILES like the real one."""
    makefiles = root / "System" / "Library" / "Makefiles"
    makefiles.mkdir(parents=True)
    (makefiles / "GNUstep.sh").write_text(
        f"GNUSTEP_MAKEFILES={makefiles}\nexport GNUSTEP_MAKEFILES\n\n" + ZSH_RESTORE
    )
    if with_lib:
        (root / "lib").mkdir()
    return makefiles


def _sourced_library_path(makefiles: Path, existing: str | None, times: int = 1) -> str:
    env = {"PATH": "/usr/bin:/bin"}
    if existing is not None:
        env["LD_LIBRARY_PATH"] = existing
    script = "; ".join([f". '{makefiles / 'GNUstep.sh'}'"] * times) + '; printf %s "$LD_LIBRARY_PATH"'
    return subprocess.run(["sh", "-ec", script], env=env, check=True, capture_output=True, text=True).stdout


class RuntimeLibraryPathTests(unittest.TestCase):
    def test_inserts_before_zsh_restore_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            makefiles = _toolchain(Path(tmp))
            self.assertTrue(add_runtime_library_path(makefiles))
            self.assertFalse(add_runtime_library_path(makefiles))
            text = (makefiles / "GNUstep.sh").read_text()
            self.assertEqual(text.count(MARKER), 1)
            self.assertLess(text.index(MARKER), text.index("GS_ZSH_NEED_TO_RESTORE_SET"))
            self.assertTrue(text.endswith("# EOF\n"))

    def test_appends_when_there_is_no_zsh_restore_and_skips_missing_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            makefiles = Path(tmp) / "Makefiles"
            makefiles.mkdir()
            self.assertFalse(add_runtime_library_path(makefiles))
            (makefiles / "GNUstep.sh").write_text("GNUSTEP_MAKEFILES=/x\n")
            self.assertTrue(add_runtime_library_path(makefiles))
            self.assertIn(MARKER, (makefiles / "GNUstep.sh").read_text())

    def test_sourcing_prepends_root_lib_without_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            makefiles = _toolchain(root)
            add_runtime_library_path(makefiles)
            lib = str(root / "lib")
            self.assertEqual(_sourced_library_path(makefiles, None), lib)
            self.assertEqual(_sourced_library_path(makefiles, "/opt/other"), f"{lib}:/opt/other")
            self.assertEqual(_sourced_library_path(makefiles, "/opt/other", times=2), f"{lib}:/opt/other")

    def test_sourcing_leaves_the_path_alone_without_a_root_lib(self):
        with tempfile.TemporaryDirectory() as tmp:
            makefiles = _toolchain(Path(tmp), with_lib=False)
            add_runtime_library_path(makefiles)
            self.assertEqual(_sourced_library_path(makefiles, "/opt/other"), "/opt/other")

    def test_snippet_works_under_nounset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            makefiles = _toolchain(root)
            add_runtime_library_path(makefiles)
            proc = subprocess.run(
                ["sh", "-euc", f". '{makefiles / 'GNUstep.sh'}'; printf %s \"$LD_LIBRARY_PATH\""],
                # GNUstep.sh's own zsh check is not nounset-safe; only the snippet is under test.
                env={"PATH": "/usr/bin:/bin", "GS_ZSH_NEED_TO_RESTORE_SET": ""}, capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout, str(root / "lib"))


if __name__ == "__main__":
    unittest.main()
