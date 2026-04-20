#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.package_manager import install_package, install_package_from_index, recover_package_transactions, upgrade_package, upgrade_package_from_index
from gnustep_cli_shared.setup_planner import _default_user_root


def _host_os() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform.startswith("openbsd"):
        return "openbsd"
    return "linux"


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--root")
    parser.add_argument("--index")
    parser.add_argument("--allow-unsigned-index", action="store_true")
    parser.add_argument("--trusted-public-key")
    parser.add_argument("--upgrade", action="store_true")
    parser.add_argument("--recover-transactions", action="store_true")
    parser.add_argument("--apply-recovery", action="store_true")
    parser.add_argument("manifest_path", nargs="?")
    args = parser.parse_args()

    root = args.root or _default_user_root(_host_os())
    if args.recover_transactions:
        payload, exit_code = recover_package_transactions(root, apply=args.apply_recovery)
    elif not args.manifest_path:
        payload, exit_code = {
            "schema_version": 1,
            "command": "install",
            "ok": False,
            "status": "error",
            "summary": "Package manifest path or package id is required.",
        }, 2
    elif args.index:
        if args.upgrade:
            payload, exit_code = upgrade_package_from_index(
                args.index,
                args.manifest_path,
                root,
                require_signed_index=not args.allow_unsigned_index,
                trusted_public_key_path=args.trusted_public_key,
            )
        else:
            payload, exit_code = install_package_from_index(
                args.index,
                args.manifest_path,
                root,
                require_signed_index=not args.allow_unsigned_index,
                trusted_public_key_path=args.trusted_public_key,
            )
    else:
        if args.upgrade:
            payload, exit_code = upgrade_package(args.manifest_path, root)
        else:
            payload, exit_code = install_package(args.manifest_path, root)
    if args.json:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print(payload["summary"])
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
