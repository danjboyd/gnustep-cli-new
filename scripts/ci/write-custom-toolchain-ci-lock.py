#!/usr/bin/env python3
"""Write the custom toolchain lock that CI builds with the container wrapper.

The lock starts from the official linux-amd64-clang pins and adds the kinds of
changes consuming applications make: libs-gui configure flags that drop optional
features, and a verified patch (the libobjc2 @synchronized first-lock fix).

Usage: write-custom-toolchain-ci-lock.py <output-dir>
Writes <output-dir>/gnustep-toolchain.lock.json plus its patches.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.custom_toolchain import custom_toolchain_lock_from_source_lock  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "custom-toolchain-ci"
LIBOBJC2_PATCH = "patches/libobjc2/0001-Move-hidden-class-lock-initialisation-earlier.patch"
LIBS_GUI_ARGS = [
    "--disable-movie",
    "--disable-sound",
    "--disable-imagemagick",
    "--disable-aspell",
    "--disable-speech",
    "--disable-speech-recognizer",
    "--disable-cups",
]


def write_ci_lock(output_dir: Path) -> Path:
    source_lock = json.loads((ROOT / "toolchains" / "linux-amd64-clang" / "source-lock.json").read_text())
    lock = custom_toolchain_lock_from_source_lock(source_lock, "gnustep-cli-ci")
    lock["container"] = {"recipe": "linux-amd64-clang", "apt_packages": []}
    patch_target = output_dir / LIBOBJC2_PATCH
    patch_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(FIXTURES / LIBOBJC2_PATCH, patch_target)
    digest = hashlib.sha256(patch_target.read_bytes()).hexdigest()
    for component in lock["components"]:
        if component["name"] == "libobjc2":
            component["patches"] = [{"path": LIBOBJC2_PATCH, "sha256": digest}]
        elif component["name"] == "libs-gui":
            component["configure_args"] = component["configure_args"] + LIBS_GUI_ARGS
    lock_path = output_dir / "gnustep-toolchain.lock.json"
    lock_path.write_text(json.dumps(lock, indent=2) + "\n")
    return lock_path


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <output-dir>", file=sys.stderr)
        return 2
    output_dir = Path(argv[1]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    print(write_ci_lock(output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
