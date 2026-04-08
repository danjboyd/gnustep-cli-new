#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.build_run_engine import execute_build, plan_build, render_build_human


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("project_dir", nargs="?", default=".")
    args = parser.parse_args()
    payload, exit_code = execute_build(args.project_dir) if args.execute else (plan_build(args.project_dir), 0)
    if args.json:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print(render_build_human(payload))
    return exit_code if args.execute or not payload.get("ok", False) else 0


if __name__ == "__main__":
    raise SystemExit(main())

