#!/usr/bin/env python3
"""Write release-stamped copies of the bootstrap scripts.

Usage: stamp_bootstrap.py <version> <output-dir>

Writes gnustep-bootstrap.sh and gnustep-bootstrap.ps1 with the release version
in place of the source default ("0.1.0-dev"), plus a <name>.sha256 file for
each, ready to upload as release assets. The version selects the release
manifest URL (and, in the .sh, the production trust root), so a release asset
must never carry the -dev default.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_DIR = ROOT / "scripts" / "bootstrap"
VERSION_LINES = {
    "gnustep-bootstrap.sh": (re.compile(r'^CLI_VERSION="[^"]*"$', re.M), 'CLI_VERSION="{version}"'),
    "gnustep-bootstrap.ps1": (re.compile(r'^\$Script:CliVersion = "[^"]*"$', re.M), '$Script:CliVersion = "{version}"'),
}


def stamp(text: str, name: str, version: str) -> str:
    pattern, replacement = VERSION_LINES[name]
    stamped, count = pattern.subn(replacement.format(version=version), text, count=1)
    if count != 1:
        raise ValueError(f"version line not found in {name}")
    return stamped


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    version, output = sys.argv[1], Path(sys.argv[2])
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        print(f"not a release version: {version}", file=sys.stderr)
        return 2
    output.mkdir(parents=True, exist_ok=True)
    for name in VERSION_LINES:
        source = (BOOTSTRAP_DIR / name).read_bytes().decode("utf-8")
        data = stamp(source, name, version).encode("utf-8")
        (output / name).write_bytes(data)
        (output / f"{name}.sha256").write_text(f"{hashlib.sha256(data).hexdigest()}  {name}\n", encoding="ascii")
        print(output / name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
