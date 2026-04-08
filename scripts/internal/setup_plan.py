#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.setup_planner import build_setup_payload, render_setup_human


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--scope", choices=["user", "system"], default="user")
    parser.add_argument("--manifest")
    parser.add_argument("--root")
    args = parser.parse_args()

    payload, exit_code = build_setup_payload(scope=args.scope, manifest_path=args.manifest, install_root=args.root)
    if args.json:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print(render_setup_human(payload))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

