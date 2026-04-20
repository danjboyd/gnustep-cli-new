#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.package_repository import (
    generate_package_index,
    package_index_trust_gate,
    sign_package_index_metadata,
    write_package_index,
    write_package_index_provenance,
)


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--channel", default="stable")
    parser.add_argument("--output")
    parser.add_argument("--provenance", action="store_true")
    parser.add_argument("--sign-private-key")
    parser.add_argument("--sign-public-key")
    parser.add_argument("--trust-gate", action="store_true")
    parser.add_argument("--allow-unsigned", action="store_true")
    parser.add_argument("--trusted-public-key")
    parser.add_argument("packages_root")
    args = parser.parse_args()

    if args.trust_gate:
        payload = package_index_trust_gate(args.packages_root, require_signatures=not args.allow_unsigned, trusted_public_key_path=args.trusted_public_key)
    elif args.sign_private_key:
        payload = sign_package_index_metadata(args.packages_root, args.sign_private_key, public_key_path=args.sign_public_key)
    elif args.provenance:
        path = write_package_index_provenance(args.packages_root)
        payload = {"schema_version": 1, "command": "package-index-provenance", "ok": True, "status": "ok", "provenance_path": str(path)}
    elif args.output:
        output = write_package_index(args.packages_root, args.output, channel=args.channel)
        payload = {"schema_version": 1, "command": "package-repo", "ok": True, "status": "ok", "output": str(output)}
    else:
        payload = generate_package_index(args.packages_root, channel=args.channel)

    if args.json:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print("Package index generated.")
    if isinstance(payload, dict) and payload.get("ok") is False:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

