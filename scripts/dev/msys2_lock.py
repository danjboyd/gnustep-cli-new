#!/usr/bin/env python3
"""Pin input-manifest.json to the packages of an MSYS2 resolve run.

Usage: msys2_lock.py <resolve-dir> [--manifest toolchains/windows-amd64-msys2-clang64/input-manifest.json]

The resolve run's signed sync databases are copied to msys2-sync/ next to the
manifest and pinned; locked builds ship them in the root.

<resolve-dir> is the gnustep-windows-msys2-resolve artifact of the
"Windows Current Source Artifacts" workflow run with toolchain_source=resolve-msys2 (resolve.json, pacman-Q.txt, msys.db, clang64.db).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.msys2_lock import lock_input_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("resolve_dir", type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "toolchains" / "windows-amd64-msys2-clang64" / "input-manifest.json",
    )
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    locked = lock_input_manifest(manifest, args.resolve_dir, sync_dir=args.manifest.parent / "msys2-sync")
    args.manifest.write_text(json.dumps(locked, indent=2) + "\n", encoding="utf-8")
    print(f"locked {len(locked['locked_packages'])} packages at snapshot {locked['repository_snapshot']} into {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
