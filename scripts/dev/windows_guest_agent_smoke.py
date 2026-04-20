#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GUEST_KEY = "/home/danboyd/.ssh/otvm/id_rsa"


def guest_ssh(guest_host: str, remote: str, *, retries: int = 2, delay_seconds: int = 5) -> str:
    last = ""
    for attempt in range(retries + 1):
        result = subprocess.run(
            [
                "ssh",
                "-i",
                GUEST_KEY,
                "-o",
                "StrictHostKeyChecking=no",
                f"otvmbootstrap@{guest_host}",
                remote,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout
        last = result.stderr.strip() or result.stdout.strip()
        if attempt < retries:
            time.sleep(delay_seconds)
    raise RuntimeError(last or f"guest ssh failed: {remote}")


def stage_files(guest_host: str, files: list[Path]) -> None:
    subprocess.run(
        [
            "scp",
            "-i",
            GUEST_KEY,
            "-o",
            "StrictHostKeyChecking=no",
            *[str(path) for path in files],
            f"otvmbootstrap@{guest_host}:/C:/Users/otvmbootstrap/",
        ],
        check=True,
    )


def launch_detached(guest_host: str) -> None:
    remote = (
        'cmd /c start "" /B powershell -NoProfile -ExecutionPolicy Bypass '
        '-File C:\\Users\\otvmbootstrap\\windows-refresh-build-and-smoke.ps1'
    )
    guest_ssh(guest_host, remote, retries=6, delay_seconds=5)


def file_exists(guest_host: str, path: str) -> bool:
    try:
        output = guest_ssh(guest_host, f'cmd /c if exist "{path}" echo FOUND', retries=1, delay_seconds=5)
        return "FOUND" in output
    except RuntimeError:
        return False


def read_file(guest_host: str, path: str) -> str:
    return guest_ssh(guest_host, f'cmd /c type "{path}"', retries=6, delay_seconds=5)


def wait_for_results(guest_host: str, results_path: str, *, timeout_seconds: int = 1800) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if file_exists(guest_host, results_path):
            text = read_file(guest_host, results_path)
            return json.loads(text.lstrip("\ufeff"))
        time.sleep(10)
    raise TimeoutError(f"Timed out waiting for {results_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Windows refresh/build/package smoke via detached SSH and result-file polling.")
    parser.add_argument("--guest-host", required=True)
    parser.add_argument(
        "--script",
        default=str(REPO_ROOT / "scripts/dev/windows-refresh-build-and-smoke.ps1"),
    )
    parser.add_argument("--tarball", default="/tmp/full-cli-src.tar.gz")
    args = parser.parse_args()

    script = Path(args.script)
    tarball = Path(args.tarball)
    assemble = REPO_ROOT / "toolchains/windows-amd64-msys2-clang64/assemble-toolchain.ps1"
    stage_files(args.guest_host, [assemble, script, tarball])
    launch_detached(args.guest_host)
    results = wait_for_results(args.guest_host, r"C:\Users\otvmbootstrap\refresh-run\results.json")
    print(json.dumps(results, indent=2))
    return 0 if results.get("exe_exists") else 1


if __name__ == "__main__":
    raise SystemExit(main())
