from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def regression_suite() -> dict[str, Any]:
    if os.environ.get("GNUSTEP_CLI_QA_NESTED") == "1":
        return {
            "schema_version": 1,
            "command": "qa-regression",
            "ok": True,
            "status": "ok",
            "summary": "Nested regression invocation skipped.",
            "exit_status": 0,
            "stdout": "",
            "stderr": "",
        }
    proc = subprocess.run(
        ["python3", "-m", "unittest", "discover", "-s", str(ROOT / "tests")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        env={**os.environ, "GNUSTEP_CLI_QA_NESTED": "1"},
    )
    return {
        "schema_version": 1,
        "command": "qa-regression",
        "ok": proc.returncode == 0,
        "status": "ok" if proc.returncode == 0 else "error",
        "summary": "Regression suite passed." if proc.returncode == 0 else "Regression suite failed.",
        "exit_status": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
