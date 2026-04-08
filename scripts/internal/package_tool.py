#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.package_tooling import init_package_manifest, validate_package_manifest


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--json", action="store_true")
    subparsers = parser.add_subparsers(dest="subcommand")

    init_parser = subparsers.add_parser("init", add_help=False)
    init_parser.add_argument("package_dir")
    init_parser.add_argument("--name", required=True)
    init_parser.add_argument("--kind", required=True)

    validate_parser = subparsers.add_parser("validate", add_help=False)
    validate_parser.add_argument("manifest_path")

    args = parser.parse_args()
    if args.subcommand == "init":
        payload = init_package_manifest(args.package_dir, args.name, args.kind)
        code = 0 if payload["ok"] else 1
    elif args.subcommand == "validate":
        payload = validate_package_manifest(args.manifest_path)
        code = 0 if payload["ok"] else 1
    else:
        print("package: expected 'init' or 'validate'", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print(payload["summary"])
    return code


if __name__ == "__main__":
    raise SystemExit(main())

