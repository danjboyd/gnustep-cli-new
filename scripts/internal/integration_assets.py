#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.integration import generate_desktop_entry, generate_windows_shortcut_metadata


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--json", action="store_true")
    subparsers = parser.add_subparsers(dest="subcommand")

    desktop = subparsers.add_parser("desktop-entry", add_help=False)
    desktop.add_argument("--app-id", required=True)
    desktop.add_argument("--display-name", required=True)
    desktop.add_argument("--exec-path", required=True)
    desktop.add_argument("--icon-name", required=True)
    desktop.add_argument("--categories", nargs="+", required=True)

    shortcut = subparsers.add_parser("windows-shortcut", add_help=False)
    shortcut.add_argument("--app-id", required=True)
    shortcut.add_argument("--display-name", required=True)
    shortcut.add_argument("--executable", required=True)
    shortcut.add_argument("--icon-path", required=True)
    shortcut.add_argument("--start-menu-group", default="GNUstep")

    args = parser.parse_args()
    if args.subcommand == "desktop-entry":
        payload = {
            "schema_version": 1,
            "command": "desktop-entry",
            "ok": True,
            "status": "ok",
            "content": generate_desktop_entry(
                app_id=args.app_id,
                display_name=args.display_name,
                exec_path=args.exec_path,
                icon_name=args.icon_name,
                categories=args.categories,
            ),
        }
    elif args.subcommand == "windows-shortcut":
        payload = {
            "schema_version": 1,
            "command": "windows-shortcut",
            "ok": True,
            "status": "ok",
            "metadata": generate_windows_shortcut_metadata(
                app_id=args.app_id,
                display_name=args.display_name,
                executable=args.executable,
                icon_path=args.icon_path,
                start_menu_group=args.start_menu_group,
            ),
        }
    else:
        print("integration-assets: expected subcommand", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print(payload.get("content", payload.get("metadata")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

