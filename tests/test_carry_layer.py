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
    parse_nm_exports,
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
        bases = data["bases"]
        for entry in data["patches"]:
            # A patch is built only for the platforms of its base.
            base = bases[f"{entry['library']}/{entry['base']}"]
            self.assertTrue(set(entry["platforms"]) <= set(base["platforms"]), entry["id"])
        self.assertEqual(carry_layer.layer_outputs(data, "linux-amd64-clang"), ["Local/Library/Bundles/libgnustep-back-*.bundle/libgnustep-back-*", "Local/Library/Libraries/libgnustep-gui.so", "Local/Library/Libraries/libgnustep-gui.so.*"])
        self.assertNotIn("Local/Library/Libraries/libgnustep-gui.so.*", carry_layer.layer_outputs(data, "windows-amd64-msys2-clang64"))
        linux = [p["id"] for p in data["patches"] if "linux-amd64-clang" in p["platforms"]]
        self.assertEqual(linux[:6], ["gui-theme-live-switch-linux", "gui-command-key-bindings-linux", "gui-nsview-did-hide-linux", "gui-nsopenglview-visibility-linux", "gui-nsopenglview-leave-window-linux", "gui-nsopenglview-tests-linux"])
        self.assertEqual([p.split("-linux")[0] for p in linux[6:]], ["x11-xlibimage-layer", "x11-enable-wraster-option", "x11-no-wraster-by-default", "x11-keep-wm-functions", "x11-window-types", "x11-borderless-alpha", "x11-orderwindow-focus-root", "x11-window-shadows", "x11-popover-shadows", "x11-opengl-subwindow"])

    def test_bases_without_platforms_count_for_every_target(self):
        data = {"bases": {"a/x": {"outputs": ["a"]}, "b/y": {"platforms": ["linux-amd64-clang"], "outputs": ["b"]}}}
        self.assertEqual(carry_layer.layer_outputs(data, "windows-amd64-msys2-clang64"), ["a"])
        self.assertEqual(carry_layer.layer_outputs(data, "linux-amd64-clang"), ["a", "b"])
        self.assertEqual(carry_layer.layer_outputs(data), ["a", "b"])


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

    def test_dynamic_symbols_are_read_from_nm_output(self):
        text = """0000000000123a40 T GSBackendClass
0000000000456b00 D _OBJC_CLASS_NSInputManager
                 U objc_msgSend
                 w __gmon_start__
0000000000000000 A GNUSTEP_GUI_0.32
0000000000789c00 T NSApplicationMain@@GNUSTEP_GUI_0.32
"""
        self.assertEqual(parse_nm_exports(text), {"GSBackendClass", "_OBJC_CLASS_NSInputManager", "GNUSTEP_GUI_0.32", "NSApplicationMain"})

    def test_a_shared_object_needs_nm_and_a_dll_needs_objdump(self):
        with tempfile.TemporaryDirectory() as tmp:
            stock = Path(tmp)
            so = {"path": "Local/Library/Libraries/libgnustep-gui.so.0.32.0", "stock_sha256": "x", "source": str(stock / "p.so")}
            dll = {"path": "clang64/bin/gnustep-gui-0.dll", "stock_sha256": "x", "source": str(stock / "p.dll")}
            with self.assertRaisesRegex(CarryError, "needs --nm"):
                carry_layer.abi_report("llvm-objdump", stock, [so])
            with self.assertRaisesRegex(CarryError, "needs --objdump"):
                carry_layer.abi_report(None, stock, [dll], nm="nm")
            # A bundle binary has no suffix: it counts when its ELF header says ET_DYN.
            elf = bytearray(b"\x7fELF" + b"\x02\x01\x01" + b"\x00" * 9 + b"\x03\x00" + b"\x00" * 46)
            _write(stock / "Local/Library/Bundles/libgnustep-back-032.bundle/libgnustep-back-032", bytes(elf))
            _write(stock / "Local/Tools/gpbs", bytes(elf[:16]) + b"\x02\x00" + bytes(elf[18:]))
            bundle = {"path": "Local/Library/Bundles/libgnustep-back-032.bundle/libgnustep-back-032", "stock_sha256": "x", "source": "p"}
            with self.assertRaisesRegex(CarryError, "needs --nm"):
                carry_layer.abi_report(None, stock, [bundle])
            self.assertEqual(carry_layer.abi_report(None, stock, [{"path": "Local/Tools/gpbs", "stock_sha256": "x", "source": "p"}]), {})
            # A new file (no stock) and a non-library are not compared.
            self.assertEqual(carry_layer.abi_report(None, stock, [dict(so, stock_sha256=None), {"path": "a.txt", "stock_sha256": "x", "source": "a"}]), {})

    def test_a_bundle_ivar_whose_type_changed_is_internal_but_a_vanished_one_is_removed(self):
        stock = {"GSBackendClass", "__objc_ivar_offset_XGServer.generic.{XGGeneric=[70Q]}", "__objc_ivar_offset_XGServer.gone.i"}
        patched = {"GSBackendClass", "__objc_ivar_offset_XGServer.generic.{XGGeneric=[72Q]}", "__objc_ivar_offset_XGServer.xfixesEventBase.i"}
        change = carry_layer.compare_bundle_exports(stock, patched)
        self.assertEqual(change["removed"], ["__objc_ivar_offset_XGServer.gone.i"])
        self.assertEqual(change["ivar_types_changed"], ["XGServer.generic"])
        self.assertIn("__objc_ivar_offset_XGServer.xfixesEventBase.i", change["added"])
        # A removal nothing in the toolchain imports is reported, not counted.
        change = carry_layer.compare_bundle_exports(stock | {"RCreateImage", "GSUsed"}, patched, imported={"GSUsed"})
        self.assertEqual(change["removed"], ["GSUsed"])
        self.assertEqual(change["removed_unreferenced"], ["RCreateImage", "__objc_ivar_offset_XGServer.gone.i"])
        # A linked library gets no such allowance.
        self.assertEqual(len(compare_exports(stock, patched)["removed"]), 2)

    def test_a_removed_export_fails_and_an_added_one_is_reported(self):
        stock = {"a", "b"}
        report = {"clang64/bin/x.dll": compare_exports(stock, {"a", "c"})}
        self.assertEqual(report["clang64/bin/x.dll"], {"removed": ["b"], "added": ["c"]})
        self.assertEqual(len(abi_failures(report)), 1)
        self.assertEqual(abi_failures({"y.dll": compare_exports(stock, stock | {"c"})}), [])


class StagingTests(unittest.TestCase):
    TARGET = "windows-amd64-msys2-clang64"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _toolchain_zip(self, gui=b"stock gui"):
        path = self.dir / "in" / f"gnustep-toolchain-{self.TARGET}-0.1.9.zip"
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("gnustep-toolchain-root/clang64/bin/gnustep-gui-0.dll", gui)
            archive.writestr("gnustep-toolchain-root/clang64/bin/other.dll", b"other")
        return path

    def _layer_zip(self, toolchain_sha, stock=b"stock gui"):
        stock_root = self.dir / "stock"
        _write(stock_root / "clang64/bin/gnustep-gui-0.dll", stock)
        package = self.dir / "pkg"
        _write(package / "clang64/bin/gnustep-gui-0.dll", b"patched gui")
        files, _ = layer_files(stock_root, [package], ["clang64/bin/gnustep-gui-*.dll"])
        manifest = layer_manifest(self.TARGET, "0.1.9", toolchain_sha, [], files, {})
        out = self.dir / "carry" / f"gnustep-carry-{self.TARGET}-0.1.9.zip"
        write_layer(out, manifest, files)
        return out

    def test_a_layer_is_checked_against_the_toolchain_archive(self):
        toolchain = self._toolchain_zip()
        sha = hashlib.sha256(toolchain.read_bytes()).hexdigest()
        self.assertEqual(carry_layer.verify_against_toolchain(self._layer_zip(sha), toolchain, sha), [])
        errors = carry_layer.verify_against_toolchain(self._layer_zip("0" * 64, stock=b"other stock"), toolchain, sha)
        self.assertEqual(len(errors), 2, errors)

    def test_staging_adds_the_layer_only_for_its_toolchain_and_verify_release_checks_it(self):
        from gnustep_cli_shared.build_infra import stage_release_assets, verify_release_directory

        toolchain = self._toolchain_zip()
        sha = hashlib.sha256(toolchain.read_bytes()).hexdigest()
        layer = self._layer_zip(sha)
        payload = stage_release_assets("0.1.9", self.dir / "out", "https://example.invalid/releases",
                                       toolchain_inputs={self.TARGET: toolchain}, carry_inputs={self.TARGET: layer.parent})
        release_dir = self.dir / "out" / "stable" / "0.1.9"
        manifest = json.loads((release_dir / "release-manifest.json").read_text())
        carry = [a for a in manifest["releases"][0]["artifacts"] if a["kind"] == "carry-layer"]
        self.assertEqual(len(carry), 1, payload)
        self.assertEqual(carry[0]["id"], f"carry-layer-{self.TARGET}")
        self.assertEqual(carry[0]["requires_toolchain"]["sha256"], sha)
        self.assertIn(carry[0]["filename"], (release_dir / "SHA256SUMS").read_text())
        verified = verify_release_directory(release_dir)
        self.assertTrue(verified["ok"], verified)

        other = self._layer_zip("f" * 64)
        with self.assertRaisesRegex(ValueError, "does not match its toolchain"):
            stage_release_assets("0.1.9", self.dir / "out2", "https://example.invalid/releases",
                                 toolchain_inputs={self.TARGET: toolchain}, carry_inputs={self.TARGET: other})


class CommandTests(unittest.TestCase):
    def test_check_accepts_the_repository_carry_json(self):
        self.assertEqual(carry_layer.main(["check", "--carry-json", str(ROOT / "toolchains" / "carry" / "carry.json")]), 0)


if __name__ == "__main__":
    unittest.main()


class DoctorVariantTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _write(self.root / "state" / "cli-state.json", json.dumps({"schema_version": 1, "status": "healthy"}).encode())

    def tearDown(self):
        self.tmp.cleanup()

    def _check(self):
        from gnustep_cli_shared.doctor_engine import _toolchain_variant_check

        return _toolchain_variant_check("full", self.root)

    def _record(self, current: bytes):
        _write(self.root / "clang64/bin/gnustep-gui-0.dll", current)
        record = {"release": "0.1.9", "patches": [{"id": "gui-layout-sanity-checks"}],
                  "files": [{"path": "clang64/bin/gnustep-gui-0.dll", "stock_sha256": _sha(b"stock"), "sha256": _sha(b"patched")}]}
        _write(self.root / "carry-layer.json", json.dumps(record).encode())

    def test_stock_patched_and_mixed_installs(self):
        self.assertEqual((self._check().status, self._check().details["toolchain_variant"]), ("ok", "stock"))
        self._record(b"patched")
        check = self._check()
        self.assertEqual(check.status, "ok")
        self.assertEqual(check.details["patches"], ["gui-layout-sanity-checks"])
        self._record(b"stock")
        check = self._check()
        self.assertEqual(check.status, "error")
        self.assertEqual(check.details["stock_files"], ["clang64/bin/gnustep-gui-0.dll"])

    def test_a_patched_state_without_its_record_is_an_error(self):
        _write(self.root / "state" / "cli-state.json", json.dumps({"toolchain_variant": "patched"}).encode())
        self.assertEqual(self._check().status, "error")

    def test_bootstrap_reports_it_as_full_only(self):
        from gnustep_cli_shared.doctor_engine import _toolchain_variant_check

        self.assertEqual(_toolchain_variant_check("bootstrap", self.root).status, "not_run")
