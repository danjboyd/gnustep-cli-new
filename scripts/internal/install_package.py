#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.package_manager import install_package
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
    parser.add_argument("manifest_path")
    args = parser.parse_args()

    root = args.root or _default_user_root(_host_os())
    payload, exit_code = install_package(args.manifest_path, root)
    if args.json:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print(payload["summary"])
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
