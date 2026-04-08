#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.lifecycle import apply_upgrade_state, load_cli_state, plan_upgrade, repair_managed_root


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--json", action="store_true")
    subparsers = parser.add_subparsers(dest="subcommand")

    status_parser = subparsers.add_parser("status", add_help=False)
    status_parser.add_argument("--root", required=True)

    plan_parser = subparsers.add_parser("upgrade-plan", add_help=False)
    plan_parser.add_argument("--root", required=True)
    plan_parser.add_argument("--target-cli-version", required=True)
    plan_parser.add_argument("--target-toolchain-version")

    apply_parser = subparsers.add_parser("upgrade-apply", add_help=False)
    apply_parser.add_argument("--root", required=True)
    apply_parser.add_argument("--cli-version", required=True)
    apply_parser.add_argument("--toolchain-version")

    repair_parser = subparsers.add_parser("repair", add_help=False)
    repair_parser.add_argument("--root", required=True)

    args = parser.parse_args()
    if args.subcommand == "status":
        payload = load_cli_state(args.root)
        code = 0
    elif args.subcommand == "upgrade-plan":
        current = load_cli_state(args.root)
        payload = plan_upgrade(
            args.root,
            current_cli_version=current.get("cli_version"),
            target_cli_version=args.target_cli_version,
            current_toolchain_version=current.get("toolchain_version"),
            target_toolchain_version=args.target_toolchain_version,
        )
        code = 0
    elif args.subcommand == "upgrade-apply":
        payload = apply_upgrade_state(args.root, cli_version=args.cli_version, toolchain_version=args.toolchain_version)
        code = 0
    elif args.subcommand == "repair":
        payload = repair_managed_root(args.root)
        code = 0
    else:
        print("lifecycle: expected subcommand", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print(payload.get("summary", "Lifecycle operation completed."))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

