#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.package_repository import generate_package_index, write_package_index


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--channel", default="stable")
    parser.add_argument("packages_root")
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.output:
        output = write_package_index(args.packages_root, args.output, channel=args.channel)
        payload = {"schema_version": 1, "command": "package-repo", "ok": True, "status": "ok", "output": str(output)}
    else:
        payload = generate_package_index(args.packages_root, channel=args.channel)

    if args.json:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print("Package index generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

