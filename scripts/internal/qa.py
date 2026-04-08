#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.qa import regression_suite


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--json", action="store_true")
    parser.parse_args()

    payload = regression_suite()
    if parser.parse_args().json:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print(payload["summary"])
        print(payload["stdout"], end="")
        if payload["stderr"]:
            print(payload["stderr"], file=sys.stderr, end="")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

