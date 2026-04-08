#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.template_engine import available_templates, create_template


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--list-templates", action="store_true")
    parser.add_argument("template", nargs="?")
    parser.add_argument("destination", nargs="?")
    parser.add_argument("--name")
    args = parser.parse_args()

    if args.list_templates:
        payload = {
            "schema_version": 1,
            "command": "new",
            "ok": True,
            "status": "ok",
            "templates": available_templates(),
        }
        if args.json:
            print(json.dumps(payload, separators=(",", ":")))
        else:
            print("\n".join(payload["templates"]))
        return 0

    if not args.template or not args.destination:
        print("new: template and destination are required", file=sys.stderr)
        return 2

    project_name = args.name or Path(args.destination).name
    payload = create_template(args.template, args.destination, project_name)
    if args.json:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print(payload["summary"])
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

