"""Build the patch layer: the files where a carried-patch build differs from stock.

docs/specs/patch-layer.md describes the layer; docs/carried-patches/README.md describes
the carried patches (toolchains/carry/carry.json). This module:

- checks carry.json against the patch files it names;
- compares packages built with the carried patches against the stock toolchain root,
  keeping only the files that differ;
- compares a DLL's export table with the stock one (the ABI rule: nothing removed);
- writes the layer zip, with carry-layer.json describing it.

It runs on the Windows layer build (windows-carry-layer.yml) and in the unit tests.
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


def layer_outputs(data: dict) -> list:
    """Every base's output patterns: the installed files the layer takes from a rebuild."""
    patterns = []
    for key, base in sorted((data.get("bases") or {}).items()):
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


def dll_exports(objdump: str, dll: Path) -> set:
    output = subprocess.run([objdump, "-p", str(dll)], check=True, capture_output=True, text=True).stdout
    return parse_objdump_exports(output)


def abi_report(objdump: str, stock_root: Path, files: list) -> dict:
    """Export-table comparison of every replaced DLL. Fails the build on a removal."""
    report = {}
    for entry in files:
        if not entry["path"].lower().endswith(".dll") or entry["stock_sha256"] is None:
            continue
        stock = dll_exports(objdump, stock_root / entry["path"])
        patched = dll_exports(objdump, Path(entry["source"]))
        report[entry["path"]] = compare_exports(stock, patched)
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
    build.add_argument("--objdump", required=True)
    build.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        data = load_carry(args.carry_json)
        if args.command == "check":
            print(f"carry.json ok: {len(data['patches'])} patches")
            return 0
        patches = [p for p in data["patches"] if args.target in p["platforms"]]
        files, others = layer_files(args.stock_root, args.package_root, layer_outputs(data))
        abi = abi_report(args.objdump, args.stock_root, files)
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
