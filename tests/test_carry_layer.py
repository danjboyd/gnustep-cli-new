import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared import carry_layer
from gnustep_cli_shared.carry_layer import (
    CarryError,
    abi_failures,
    compare_exports,
    layer_files,
    layer_manifest,
    load_carry,
    parse_objdump_exports,
    patches_for,
    write_layer,
)

OBJDUMP_EXPORTS = """
gnustep-back-032.dll:	file format coff-x86-64

The Data Directory
Entry 0 0001a000 00000400 Export Directory [.edata (or where ever we found it)]

Export Table:
 DLL name: gnustep-back-032.dll
 Ordinal base: 1
 Ordinal      RVA  Name
       1  0x12a40  GSBackendClass
       2  0x12b00  _OBJC_CLASS_WIN32Server
       3  0x12c10  __objc_class_name_WIN32Server

The Import Tables:
  lookup 0001b0c8 time 00000000 fwd 00000000 name 0001b5d2 addr 0001b2e8
"""


def _write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class CarryJsonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _carry(self, patches, bases=None):
        doc = {"schema_version": 1, "bases": bases or {"libs-back/msys2-0.32.0": {"library": "libs-back"}}, "patches": patches}
        path = self.dir / "carry.json"
        path.write_text(json.dumps(doc))
        return path

    def _entry(self, pid, name, data=b"diff\n", **overrides):
        _write(self.dir / "libs-back" / "msys2-0.32.0" / name, data)
        entry = {
            "id": pid, "library": "libs-back", "base": "msys2-0.32.0", "platforms": ["windows-amd64-msys2-clang64"],
            "path": f"libs-back/msys2-0.32.0/{name}", "sha256": _sha(data), "summary": "s", "upstream": "not_sent",
            "defaults": [], "abi": "unchanged", "requested_by": ["App"], "owner": "agent", "verified_by": "check",
        }
        entry.update(overrides)
        return entry

    def test_a_valid_carry_json_loads_and_lists_a_base_in_file_order(self):
        path = self._carry([self._entry("b", "0002-b.patch"), self._entry("a", "0001-a.patch")])
        data = load_carry(path)
        self.assertEqual([p["id"] for p in patches_for(data, "libs-back", "msys2-0.32.0")], ["a", "b"])

    def test_a_patch_that_does_not_match_its_digest_is_refused(self):
        entry = self._entry("a", "0001-a.patch", sha256="0" * 64)
        with self.assertRaisesRegex(CarryError, "does not match its sha256"):
            load_carry(self._carry([entry]))

    def test_missing_fields_duplicate_ids_and_unknown_bases_are_refused(self):
        incomplete = self._entry("a", "0001-a.patch")
        del incomplete["owner"]
        with self.assertRaisesRegex(CarryError, "missing owner"):
            load_carry(self._carry([incomplete]))
        with self.assertRaisesRegex(CarryError, "duplicate id"):
            load_carry(self._carry([self._entry("a", "0001-a.patch"), self._entry("a", "0002-b.patch")]))
        with self.assertRaisesRegex(CarryError, "unknown base"):
            load_carry(self._carry([self._entry("a", "0001-a.patch", base="msys2-9.9")]))

    def test_the_repository_carry_json_is_consistent(self):
        data = load_carry(ROOT / "toolchains" / "carry" / "carry.json")
        self.assertTrue(data["patches"])
        self.assertTrue(carry_layer.layer_outputs(data))
        for entry in data["patches"]:
            self.assertIn("windows-amd64-msys2-clang64", entry["platforms"])


class LayerFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.stock = self.dir / "stock"
        _write(self.stock / "clang64/bin/gnustep-back-032.dll", b"stock back")
        _write(self.stock / "clang64/bin/gnustep-gui-0.dll", b"stock gui")
        _write(self.stock / "clang64/include/AppKit/AppKit.h", b"header")

    def tearDown(self):
        self.tmp.cleanup()

    OUTPUTS = ["clang64/bin/gnustep-back-*.dll", "clang64/lib/GNUstep/new*.txt"]

    def test_only_output_files_go_into_the_layer_and_other_changes_are_reported(self):
        package = self.dir / "back"
        _write(package / ".PKGINFO", b"meta")
        _write(package / "clang64/bin/gnustep-back-032.dll", b"patched back")
        _write(package / "clang64/include/AppKit/AppKit.h", b"header")
        _write(package / "clang64/lib/GNUstep/new.txt", b"new")
        _write(package / "clang64/bin/gpbs.exe", b"rebuilt tool")
        files, others = layer_files(self.stock, [package], self.OUTPUTS)
        self.assertEqual([f["path"] for f in files], ["clang64/bin/gnustep-back-032.dll", "clang64/lib/GNUstep/new.txt"])
        self.assertEqual(files[0]["stock_sha256"], _sha(b"stock back"))
        self.assertEqual(files[0]["sha256"], _sha(b"patched back"))
        self.assertIsNone(files[1]["stock_sha256"])
        self.assertEqual(others, ["clang64/bin/gpbs.exe"])

    def test_an_output_the_patches_did_not_change_or_did_not_build_is_refused(self):
        package = self.dir / "back"
        _write(package / "clang64/bin/gnustep-back-032.dll", b"stock back")
        _write(package / "clang64/lib/GNUstep/new.txt", b"new")
        with self.assertRaisesRegex(CarryError, "identical to stock"):
            layer_files(self.stock, [package], self.OUTPUTS)
        _write(package / "clang64/bin/gnustep-back-032.dll", b"patched back")
        with self.assertRaisesRegex(CarryError, "no built file matches clang64/bin/gpbs.exe"):
            layer_files(self.stock, [package], self.OUTPUTS + ["clang64/bin/gpbs.exe"])

    def test_two_packages_that_build_the_same_file_differently_are_refused(self):
        _write(self.dir / "one/clang64/bin/x.dll", b"one")
        _write(self.dir / "two/clang64/bin/x.dll", b"two")
        with self.assertRaisesRegex(CarryError, "built differently"):
            layer_files(self.stock, [self.dir / "one", self.dir / "two"], ["clang64/bin/x.dll"])

    def test_the_layer_zip_holds_the_files_and_its_manifest(self):
        package = self.dir / "back"
        _write(package / "clang64/bin/gnustep-back-032.dll", b"patched back")
        files, _ = layer_files(self.stock, [package], ["clang64/bin/gnustep-back-*.dll"])
        patch = {"id": "win32pbs-images", "library": "libs-back", "base": "msys2-0.32.0", "sha256": "ab", "upstream": "merged", "topic_commit": "3210007"}
        manifest = layer_manifest("windows-amd64-msys2-clang64", "0.1.9", "f" * 64, [patch], files, {})
        digest = write_layer(self.dir / "out" / "layer.zip", manifest, files)
        with zipfile.ZipFile(self.dir / "out" / "layer.zip") as archive:
            self.assertEqual(sorted(archive.namelist()), ["carry-layer.json", "clang64/bin/gnustep-back-032.dll"])
            stored = json.loads(archive.read("carry-layer.json"))
            self.assertEqual(archive.read("clang64/bin/gnustep-back-032.dll"), b"patched back")
        self.assertEqual(stored["requires_toolchain_sha256"], "f" * 64)
        self.assertEqual(stored["files"][0], {"path": "clang64/bin/gnustep-back-032.dll", "stock_sha256": _sha(b"stock back"), "sha256": _sha(b"patched back")})
        self.assertEqual(stored["patches"][0]["topic_commit"], "3210007")
        self.assertEqual(len(digest), 64)


class AbiTests(unittest.TestCase):
    def test_export_table_names_are_read_from_objdump_output(self):
        self.assertEqual(parse_objdump_exports(OBJDUMP_EXPORTS), {"GSBackendClass", "_OBJC_CLASS_WIN32Server", "__objc_class_name_WIN32Server"})

    def test_a_removed_export_fails_and_an_added_one_is_reported(self):
        stock = {"a", "b"}
        report = {"clang64/bin/x.dll": compare_exports(stock, {"a", "c"})}
        self.assertEqual(report["clang64/bin/x.dll"], {"removed": ["b"], "added": ["c"]})
        self.assertEqual(len(abi_failures(report)), 1)
        self.assertEqual(abi_failures({"y.dll": compare_exports(stock, stock | {"c"})}), [])


class CommandTests(unittest.TestCase):
    def test_check_accepts_the_repository_carry_json(self):
        self.assertEqual(carry_layer.main(["check", "--carry-json", str(ROOT / "toolchains" / "carry" / "carry.json")]), 0)


if __name__ == "__main__":
    unittest.main()
