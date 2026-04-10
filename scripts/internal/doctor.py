#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.doctor_engine import build_doctor_payload, render_human


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--manifest")
    parser.add_argument("--interface", choices=["bootstrap", "full"], default="full")
    args = parser.parse_args()

    payload = build_doctor_payload(Path(args.manifest) if args.manifest else None, interface=args.interface)
    if args.json:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print(render_human(payload))
    return 0 if payload["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
