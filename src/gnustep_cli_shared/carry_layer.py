"""Build the patch layer: the files where a carried-patch build differs from stock.

docs/specs/patch-layer.md describes the layer; docs/carried-patches/README.md describes
the carried patches (toolchains/carry/carry.json). This module:

- checks carry.json against the patch files it names;
- compares packages built with the carried patches against the stock toolchain root,
  keeping only the files that differ;
- compares a library's exports with the stock one (the ABI rule: nothing removed): a
  DLL's export table on Windows, an ELF shared object's dynamic symbols on Linux;
- writes the layer zip, with carry-layer.json describing it.

It runs on the layer builds (windows-carry-layer.yml, linux-carry-layer.yml) and in the
unit tests.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

LAYER_SCHEMA_VERSION = 1
LAYER_MANIFEST_NAME = "carry-layer.json"
# Package metadata, not installed files.
_PACKAGE_METADATA = {".BUILDINFO", ".PKGINFO", ".MTREE", ".INSTALL"}
REQUIRED_PATCH_FIELDS = (
    "id", "library", "base", "platforms", "path", "sha256", "summary",
    "upstream", "defaults", "abi", "requested_by", "owner", "verified_by",
)


class CarryError(Exception):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_carry(carry_json: Path) -> dict:
    """Read carry.json and check it: required fields, unique ids, known bases, digests."""
    data = json.loads(carry_json.read_text())
    base_dir = carry_json.parent
    problems = []
    seen = set()
    bases = data.get("bases") or {}
    for entry in data.get("patches") or []:
        pid = entry.get("id", "?")
        missing = [field for field in REQUIRED_PATCH_FIELDS if field not in entry]
        if missing:
            problems.append(f"{pid}: missing {', '.join(missing)}")
            continue
        if pid in seen:
            problems.append(f"{pid}: duplicate id")
        seen.add(pid)
        key = f"{entry['library']}/{entry['base']}"
        if key not in bases:
            problems.append(f"{pid}: unknown base {key}")
        patch = base_dir / entry["path"]
        if not patch.is_file():
            problems.append(f"{pid}: no file {entry['path']}")
        elif sha256_file(patch) != entry["sha256"]:
            problems.append(f"{pid}: {entry['path']} does not match its sha256")
        elif PurePosixPath(entry["path"]).parent != PurePosixPath(entry["library"], entry["base"]):
            problems.append(f"{pid}: {entry['path']} is not under {entry['library']}/{entry['base']}/")
    if problems:
        raise CarryError("carry.json: " + "; ".join(problems))
    return data


def patches_for(data: dict, library: str, base: str) -> list:
    """The patch entries for one base, in apply order (the file names' order)."""
    entries = [p for p in data["patches"] if p["library"] == library and p["base"] == base]
    return sorted(entries, key=lambda p: PurePosixPath(p["path"]).name)


def _installed_files(package_root: Path):
    for path in sorted(package_root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            relative = path.relative_to(package_root).as_posix()
            if relative.split("/", 1)[0] in _PACKAGE_METADATA:
                continue
            yield relative, path


def bases_for(data: dict, target: str | None = None) -> dict:
    """The bases a target's layer is built from: those whose platforms list it. A base
    without a platforms list counts for every target (carry.json before Linux had none)."""
    return {
        key: base for key, base in (data.get("bases") or {}).items()
        if target is None or "platforms" not in base or target in base["platforms"]
    }


def layer_outputs(data: dict, target: str | None = None) -> list:
    """The output patterns of a target's bases (every base without a target): the
    installed files the layer takes from a rebuild."""
    patterns = []
    for key, base in sorted(bases_for(data, target).items()):
        outputs = base.get("outputs") or []
        if not outputs:
            raise CarryError(f"base {key} lists no outputs")
        patterns.extend(outputs)
    return patterns


def layer_files(stock_root: Path, package_roots: list, outputs: list) -> tuple:
    """The output files the carried-patch packages install, and everything else they change.

    stock_root is the toolchain root as installed, with the same layout as the package
    trees (clang64/...). Only files matching an output pattern go into the layer; each
    pattern must match at least one file, and each matched file must differ from stock
    (otherwise the patches didn't reach it). Other files that differ (a rebuilt tool's
    timestamp, say) are returned separately, to report, not to ship. A file absent from
    stock has stock_sha256 None.
    """
    files = {}
    others = []
    matched = {pattern: 0 for pattern in outputs}
    for package_root in package_roots:
        for relative, path in _installed_files(Path(package_root)):
            hits = [pattern for pattern in outputs if fnmatch.fnmatchcase(relative, pattern)]
            for pattern in hits:
                matched[pattern] += 1
            digest = sha256_file(path)
            stock = stock_root / relative
            stock_digest = sha256_file(stock) if stock.is_file() else None
            if not hits:
                if digest != stock_digest:
                    others.append(relative)
                continue
            if digest == stock_digest:
                raise CarryError(f"{relative} is identical to stock: the carried patches did not change it")
            if relative in files and files[relative]["sha256"] != digest:
                raise CarryError(f"{relative} is built differently by two carried packages")
            files[relative] = {"path": relative, "stock_sha256": stock_digest, "sha256": digest, "source": str(path)}
    unmatched = [pattern for pattern, count in matched.items() if count == 0]
    if unmatched:
        raise CarryError("no built file matches " + ", ".join(unmatched))
    return [files[key] for key in sorted(files)], sorted(set(others))


def parse_objdump_exports(text: str) -> set:
    """Exported names from `llvm-objdump -p <dll>` (its export table)."""
    names = set()
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Export Table:"):
            in_table = True
            continue
        if not in_table:
            continue
        if stripped.startswith("Ordinal") and "RVA" in stripped:
            continue
        parts = stripped.split()
        # Rows are "<ordinal> <rva> <name>"; the table ends at the first other line.
        if len(parts) >= 3 and parts[0].isdigit() and parts[1].startswith("0x"):
            names.add(parts[2])
        elif stripped and not stripped.startswith(("DLL name:", "Ordinal base:", "Ordinal")):
            if names:
                break
    return names


def compare_exports(stock: set, patched: set) -> dict:
    return {"removed": sorted(stock - patched), "added": sorted(patched - stock)}


_IVAR_OFFSET = "__objc_ivar_offset_"


def _ivar_key(symbol: str) -> str | None:
    """`Class.ivar` from libobjc2's `__objc_ivar_offset_<Class>.<ivar>.<type encoding>`."""
    if not symbol.startswith(_IVAR_OFFSET):
        return None
    parts = symbol[len(_IVAR_OFFSET):].split(".", 2)
    return f"{parts[0]}.{parts[1]}" if len(parts) == 3 else None


def stock_imports(nm: str, stock_root: Path, skip: set) -> set:
    """Every dynamic symbol the stock root's ELF files (other than `skip`, root-relative)
    import: what something in the toolchain could need from a bundle."""
    imports = set()
    for path in sorted(stock_root.rglob("*")):
        relative = path.relative_to(stock_root).as_posix()
        if relative in skip or not path.is_file() or path.is_symlink():
            continue
        try:
            with open(path, "rb") as handle:
                if handle.read(4) != b"\x7fELF":
                    continue
        except OSError:
            continue
        run = subprocess.run([nm, "-D", "--undefined-only", str(path)], capture_output=True, text=True)
        for line in run.stdout.splitlines():
            parts = line.split()
            if parts:
                imports.add(parts[-1].split("@", 1)[0])
    return imports


def compare_bundle_exports(stock: set, patched: set, imported: set | None = None) -> dict:
    """compare_exports for a plugin bundle (a GNUstep backend bundle: loaded by libs-gui,
    linked against by nothing, its headers not installed). libobjc2 puts an ivar's type in
    its offset symbol, so a carried patch that changes the type of one of the bundle's
    own ivars renames that symbol. When the same Class.ivar is still exported, the change
    is internal to the bundle: it is reported, not counted as a removal."""
    result = compare_exports(stock, patched)
    added_keys = {_ivar_key(symbol) for symbol in result["added"]} - {None}
    internal = [symbol for symbol in result["removed"] if _ivar_key(symbol) in added_keys]
    if internal:
        result["removed"] = [symbol for symbol in result["removed"] if symbol not in internal]
        result["ivar_types_changed"] = sorted({_ivar_key(symbol) for symbol in internal})
    # Nothing links against a bundle: a symbol it stops exporting matters only if a file
    # in the toolchain imports it. The rest are reported as unreferenced removals.
    if imported is not None:
        unreferenced = [symbol for symbol in result["removed"] if symbol not in imported]
        if unreferenced:
            result["removed"] = [symbol for symbol in result["removed"] if symbol in imported]
            result["removed_unreferenced"] = unreferenced
    return result


def dll_exports(objdump: str, dll: Path) -> set:
    output = subprocess.run([objdump, "-p", str(dll)], check=True, capture_output=True, text=True).stdout
    return parse_objdump_exports(output)


def parse_nm_exports(text: str) -> set:
    """Defined dynamic symbols from `nm -D --defined-only <so>`: "<value> <type> <name>"
    rows (the value is missing for absolute symbols). Undefined (U) and weak-undefined
    (w, v) symbols are imports, not exports."""
    names = set()
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and len(parts[-2]) == 1:
            kind, name = parts[-2], parts[-1]
            if kind not in ("U", "w", "v"):
                names.add(name.split("@", 1)[0])
    return names


def so_exports(nm: str, path: Path) -> set:
    output = subprocess.run([nm, "-D", "--defined-only", str(path)], check=True, capture_output=True, text=True).stdout
    return parse_nm_exports(output)


def _is_shared_object(path: str, file: Path | None = None) -> bool:
    """A .so by name, or (a GNUstep bundle's binary has no suffix) an ELF file whose
    header says it is a shared object (e_type ET_DYN), checked when `file` is given."""
    name = PurePosixPath(path).name
    if name.endswith(".so") or ".so." in name:
        return True
    if file is None or "." in name:
        return False
    try:
        with open(file, "rb") as handle:
            header = handle.read(18)
    except OSError:
        return False
    if len(header) < 18 or header[:4] != b"\x7fELF":
        return False
    byteorder = "little" if header[5] == 1 else "big"
    return int.from_bytes(header[16:18], byteorder) == 3


def abi_report(objdump: str | None, stock_root: Path, files: list, nm: str | None = None) -> dict:
    """Export comparison of every replaced library (DLLs with objdump, ELF shared objects
    with nm). Fails the build on a removal, or when a library's tool wasn't given."""
    report = {}
    imported = None
    for entry in files:
        if entry["stock_sha256"] is None:
            continue
        path = entry["path"]
        if path.lower().endswith(".dll"):
            if not objdump:
                raise CarryError(f"{path}: the ABI check of a DLL needs --objdump")
            stock = dll_exports(objdump, stock_root / path)
            patched = dll_exports(objdump, Path(entry["source"]))
        elif _is_shared_object(path, stock_root / path):
            if not nm:
                raise CarryError(f"{path}: the ABI check of a shared object needs --nm")
            stock = so_exports(nm, stock_root / path)
            patched = so_exports(nm, Path(entry["source"]))
            if ".bundle/" in path:
                if imported is None:
                    imported = stock_imports(nm, stock_root, {f["path"] for f in files})
                report[path] = compare_bundle_exports(stock, patched, imported)
                continue
        else:
            continue
        report[path] = compare_exports(stock, patched)
    return report


def abi_failures(report: dict) -> list:
    return [f"{path}: removes {', '.join(change['removed'][:10])}" for path, change in report.items() if change["removed"]]


def layer_manifest(target: str, release: str, toolchain_sha256: str, patches: list, files: list, abi: dict) -> dict:
    return {
        "schema_version": LAYER_SCHEMA_VERSION,
        "target": target,
        "release": release,
        "requires_toolchain_sha256": toolchain_sha256,
        "patches": [
            {key: p[key] for key in ("id", "library", "base", "sha256", "upstream") if key in p}
            | ({"topic_commit": p["topic_commit"]} if "topic_commit" in p else {})
            for p in patches
        ],
        "files": [{key: f[key] for key in ("path", "stock_sha256", "sha256")} for f in files],
        "abi": abi,
    }


def write_layer(out_zip: Path, manifest: dict, files: list) -> str:
    """The layer zip: each file at its root-relative path, plus carry-layer.json."""
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in files:
            archive.write(entry["source"], entry["path"])
        archive.writestr(LAYER_MANIFEST_NAME, json.dumps(manifest, indent=2) + "\n")
    return sha256_file(out_zip)


def read_layer_manifest(layer_zip: Path) -> dict:
    with zipfile.ZipFile(layer_zip) as archive:
        try:
            return json.loads(archive.read(LAYER_MANIFEST_NAME))
        except KeyError as error:
            raise CarryError(f"{layer_zip.name} has no {LAYER_MANIFEST_NAME}") from error


def _toolchain_member_digests(toolchain_archive: Path) -> dict:
    """sha256 of each file in a toolchain archive, keyed by its path below the archive's
    root (a single top-level directory, as staged toolchains have, is stripped)."""
    digests = {}
    if zipfile.is_zipfile(toolchain_archive):
        with zipfile.ZipFile(toolchain_archive) as archive:
            members = [(info.filename.replace("\\", "/"), info) for info in archive.infolist() if not info.is_dir()]
            tops = {name.split("/", 1)[0] for name, _ in members}
            strip = len(tops) == 1 and all("/" in name for name, _ in members)
            for name, info in members:
                key = name.split("/", 1)[1] if strip else name
                digests[key] = hashlib.sha256(archive.read(info)).hexdigest()
        return digests
    import tarfile
    with tarfile.open(toolchain_archive) as archive:
        members = [member for member in archive if member.isfile()]
        names = [member.name.lstrip("./") for member in members]
        tops = {name.split("/", 1)[0] for name in names}
        strip = len(tops) == 1 and all("/" in name for name in names)
        for member, name in zip(members, names):
            handle = archive.extractfile(member)
            if handle is not None:
                digests[name.split("/", 1)[1] if strip else name] = hashlib.sha256(handle.read()).hexdigest()
    return digests


def verify_against_toolchain(layer_zip: Path, toolchain_archive: Path, toolchain_sha256: str) -> list:
    """Errors if the layer wasn't built for exactly this toolchain archive: its recorded
    toolchain sha256, and each replaced file's stock_sha256 against the archive's copy."""
    errors = []
    layer = read_layer_manifest(layer_zip)
    if layer.get("requires_toolchain_sha256") != toolchain_sha256:
        errors.append(f"layer requires toolchain {layer.get('requires_toolchain_sha256')}, staged toolchain is {toolchain_sha256}")
    digests = _toolchain_member_digests(toolchain_archive)
    with zipfile.ZipFile(layer_zip) as archive:
        names = set(archive.namelist())
        for entry in layer.get("files") or []:
            path = entry.get("path", "")
            if path not in names:
                errors.append(f"{path} is listed but not in the layer")
            elif hashlib.sha256(archive.read(path)).hexdigest() != entry.get("sha256"):
                errors.append(f"{path} in the layer does not match its sha256")
            stock = entry.get("stock_sha256")
            if stock is None:
                if path in digests:
                    errors.append(f"{path} is new in the layer but the toolchain has it")
            elif digests.get(path) != stock:
                errors.append(f"{path}: the toolchain's copy is not the stock file the layer replaces")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="check carry.json and its patch files")
    check.add_argument("--carry-json", type=Path, required=True)
    build = sub.add_parser("build", help="build the layer from carried-patch package trees")
    build.add_argument("--carry-json", type=Path, required=True)
    build.add_argument("--stock-root", type=Path, required=True)
    build.add_argument("--package-root", type=Path, action="append", required=True)
    build.add_argument("--target", required=True)
    build.add_argument("--release", required=True)
    build.add_argument("--toolchain-sha256", required=True)
    build.add_argument("--objdump", help="llvm-objdump, for the ABI check of DLLs (Windows)")
    build.add_argument("--nm", help="nm, for the ABI check of ELF shared objects (Linux)")
    build.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        data = load_carry(args.carry_json)
        if args.command == "check":
            print(f"carry.json ok: {len(data['patches'])} patches")
            return 0
        patches = [p for p in data["patches"] if args.target in p["platforms"]]
        files, others = layer_files(args.stock_root, args.package_root, layer_outputs(data, args.target))
        abi = abi_report(args.objdump, args.stock_root, files, nm=args.nm)
        failures = abi_failures(abi)
        manifest = layer_manifest(args.target, args.release, args.toolchain_sha256, patches, files, abi)
        print(json.dumps({"files": manifest["files"], "abi": abi, "other_changed_files_not_shipped": others}, indent=2))
        if failures:
            raise CarryError("ABI: " + "; ".join(failures))
        digest = write_layer(args.out, manifest, files)
        print(f"layer {args.out} sha256 {digest}: {len(files)} files, {len(patches)} patches")
        return 0
    except CarryError as error:
        print(f"carry_layer: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
