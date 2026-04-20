from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
NATIVE_TEST_RUNNER = ROOT / "scripts" / "dev" / "run-native-tests.sh"


def _run_python_suite() -> dict[str, Any]:
    proc = subprocess.run(
        ["python3", "-m", "unittest", "discover", "-s", str(ROOT / "tests")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        env={**os.environ, "GNUSTEP_CLI_QA_NESTED": "1"},
    )
    return {
        "id": "python",
        "ok": proc.returncode == 0,
        "status": "ok" if proc.returncode == 0 else "error",
        "summary": "Python/shared regression suite passed." if proc.returncode == 0 else "Python/shared regression suite failed.",
        "exit_status": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _run_native_suite() -> dict[str, Any]:
    if not NATIVE_TEST_RUNNER.exists():
        return {
            "id": "native-full-cli",
            "ok": False,
            "status": "error",
            "summary": "Native Objective-C test runner script is missing.",
            "exit_status": 1,
            "stdout": "",
            "stderr": "",
        }
    proc = subprocess.run(
        [str(NATIVE_TEST_RUNNER)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        cwd=str(ROOT),
        env=os.environ.copy(),
    )
    return {
        "id": "native-full-cli",
        "ok": proc.returncode == 0,
        "status": "ok" if proc.returncode == 0 else "error",
        "summary": "Native full CLI xctest suite passed." if proc.returncode == 0 else "Native full CLI xctest suite failed.",
        "exit_status": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


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
    stages = [_run_python_suite(), _run_native_suite()]
    ok = all(stage["ok"] for stage in stages)
    return {
        "schema_version": 1,
        "command": "qa-regression",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": "Regression suite passed." if ok else "Regression suite failed.",
        "exit_status": 0 if ok else 1,
        "stages": stages,
        "stdout": "\n".join(stage["stdout"] for stage in stages if stage["stdout"]),
        "stderr": "\n".join(stage["stderr"] for stage in stages if stage["stderr"]),
    }
