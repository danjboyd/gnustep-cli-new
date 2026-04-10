from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tarfile
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from .setup_planner import execute_setup


UNIX_CORE_COMPONENTS = [
    "libobjc2",
    "libdispatch",
    "tools-make",
    "libs-base",
    "libs-corebase",
    "libs-gui",
    "libs-back",
]

TIER1_TARGETS = [
    {
        "id": "linux-amd64-clang",
        "os": "linux",
        "arch": "amd64",
        "compiler_family": "clang",
        "toolchain_flavor": "clang",
        "strategy": "source-build",
        "publish": True,
        "core_components": UNIX_CORE_COMPONENTS,
    },
    {
        "id": "openbsd-amd64-clang",
        "os": "openbsd",
        "arch": "amd64",
        "compiler_family": "clang",
        "toolchain_flavor": "clang",
        "strategy": "source-build",
        "publish": True,
        "core_components": UNIX_CORE_COMPONENTS,
    },
    {
        "id": "windows-amd64-msys2-clang64",
        "os": "windows",
        "arch": "amd64",
        "compiler_family": "clang",
        "toolchain_flavor": "msys2-clang64",
        "strategy": "msys2-assembly",
        "publish": True,
        "core_components": [
            "libobjc2",
            "libdispatch",
            "tools-make",
            "libs-base",
            "libs-gui",
            "libs-back",
        ],
    },
    {
        "id": "windows-amd64-msvc",
        "os": "windows",
        "arch": "amd64",
        "compiler_family": "msvc",
        "toolchain_flavor": "msvc",
        "strategy": "source-build",
        "publish": False,
        "core_components": [
            "libobjc2",
            "tools-make",
            "libs-base",
            "libs-gui",
            "libs-back",
        ],
    },
]

SOURCE_COMPONENT_URLS = {
    "libobjc2": "https://github.com/gnustep/libobjc2.git",
    "libdispatch": "https://github.com/swiftlang/swift-corelibs-libdispatch.git",
    "tools-make": "https://github.com/gnustep/tools-make.git",
    "libs-base": "https://github.com/gnustep/libs-base.git",
    "libs-corebase": "https://github.com/gnustep/libs-corebase.git",
    "libs-gui": "https://github.com/gnustep/libs-gui.git",
    "libs-back": "https://github.com/gnustep/libs-back.git",
}

PINNED_SOURCE_REVISIONS = {
    "libobjc2": "b67709ad7851973fde127022d8ac6a710c82b1d5",
    "libdispatch": "4ce40128f607a6eb7b58077a06b7464c1518a30d",
    "tools-make": "50cf9619e672fb2ff6825f239b5a172c5dc55630",
    "libs-base": "d898f703e618b86f9b7ecb0f05a257cb6ed3ffac",
    "libs-corebase": "e5983493d5ddf9c5b7e562f166855d9517a3f179",
    "libs-gui": "7892137bdedd007eba8425f766e41481ddb4fda6",
    "libs-back": "bf3b3ced525f08415a20d109f05be1f91492414c",
}

MSYS2_PACKAGE_INPUTS = [
    "mingw-w64-clang-x86_64-clang",
    "mingw-w64-clang-x86_64-libobjc2",
    "mingw-w64-clang-x86_64-libdispatch",
    "mingw-w64-clang-x86_64-gnustep-make",
    "mingw-w64-clang-x86_64-gnustep-base",
    "mingw-w64-clang-x86_64-gnustep-gui",
    "mingw-w64-clang-x86_64-gnustep-back",
]

MSYS2_HOST_PACKAGES = [
    "make",
]


def tier1_targets() -> list[dict[str, Any]]:
    return deepcopy(TIER1_TARGETS)


def target_by_id(target_id: str) -> dict[str, Any]:
    for target in TIER1_TARGETS:
        if target["id"] == target_id:
            return deepcopy(target)
    raise ValueError(f"unknown target id: {target_id}")


def build_matrix() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "targets": tier1_targets(),
    }


def release_manifest_from_matrix(version: str, base_url: str) -> dict[str, Any]:
    artifacts: list[dict[str, Any]] = []
    for target in TIER1_TARGETS:
        cli_id = f"cli-{target['id']}"
        artifacts.append(
            {
                "id": cli_id,
                "kind": "cli",
                "version": version,
                "os": target["os"],
                "arch": target["arch"],
                "compiler_family": target["compiler_family"],
                "toolchain_flavor": target["toolchain_flavor"],
                "objc_runtime": "libobjc2" if target["compiler_family"] != "msvc" else "unknown",
                "objc_abi": "modern" if target["compiler_family"] != "msvc" else "unknown",
                "required_features": [],
                "format": "tar.gz" if target["os"] != "windows" else "zip",
                "url": f"{base_url.rstrip('/')}/{version}/{cli_id}",
                "sha256": "TBD",
            }
        )
        artifacts.append(
            {
                "id": f"toolchain-{target['id']}",
                "kind": "toolchain",
                "version": version,
                "os": target["os"],
                "arch": target["arch"],
                "compiler_family": target["compiler_family"],
                "toolchain_flavor": target["toolchain_flavor"],
                "objc_runtime": "libobjc2" if target["compiler_family"] != "msvc" else "unknown",
                "objc_abi": "modern" if target["compiler_family"] != "msvc" else "unknown",
                "required_features": ["blocks"] if target["compiler_family"] != "msvc" else [],
                "format": "tar.gz" if target["os"] != "windows" else "zip",
                "url": f"{base_url.rstrip('/')}/{version}/toolchain-{target['id']}",
                "sha256": "TBD",
                "published": target["publish"],
            }
        )
    return {
        "schema_version": 1,
        "channel": "stable",
        "generated_at": "TBD",
        "releases": [
            {
                "version": version,
                "status": "active",
                "artifacts": artifacts,
            }
        ],
    }


def source_lock_template(target_id: str) -> dict[str, Any]:
    target = target_by_id(target_id)
    if target["strategy"] != "source-build":
        raise ValueError(f"target does not use a source lock: {target_id}")
    sources = []
    for component in target["core_components"]:
        if component not in SOURCE_COMPONENT_URLS:
            continue
        sources.append(
            {
                "name": component,
                "url": SOURCE_COMPONENT_URLS[component],
                "revision": PINNED_SOURCE_REVISIONS.get(component, "TBD"),
                "patches": [],
            }
        )
    return {
        "schema_version": 1,
        "target": {
            "id": target["id"],
            "os": target["os"],
            "arch": target["arch"],
            "compiler_family": target["compiler_family"],
            "toolchain_flavor": target["toolchain_flavor"],
        },
        "strategy": target["strategy"],
        "runtime": {
            "objc_runtime": "libobjc2" if target["compiler_family"] != "msvc" else "unknown",
            "objc_abi": "modern" if target["compiler_family"] != "msvc" else "unknown",
        },
        "components": sources,
    }


def msys2_input_manifest_template() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "target": {
            "id": "windows-amd64-msys2-clang64",
            "os": "windows",
            "arch": "amd64",
            "compiler_family": "clang",
            "toolchain_flavor": "msys2-clang64",
        },
        "strategy": "msys2-assembly",
        "repository_snapshot": "TBD",
        "host_packages": [
            {
                "name": name,
                "version": "TBD",
                "sha256": "TBD",
            }
            for name in MSYS2_HOST_PACKAGES
        ],
        "packages": [
            {
                "name": name,
                "version": "TBD",
                "sha256": "TBD",
            }
            for name in MSYS2_PACKAGE_INPUTS
        ],
        "conflict_rules": [
            {
                "path": "clang64/include/Block.h",
                "policy": "allow-managed-overwrite",
                "reason": "Known overlap between libobjc2 and blocks runtime packaging.",
            },
            {
                "path": "clang64/include/objc/blocks_runtime.h",
                "policy": "allow-managed-overwrite",
                "reason": "Known overlap between libobjc2 and blocks runtime packaging.",
            }
        ],
    }


def toolchain_manifest(target_id: str, toolchain_version: str) -> dict[str, Any]:
    target = target_by_id(target_id)
    return {
        "schema_version": 1,
        "kind": "managed-toolchain",
        "toolchain_version": toolchain_version,
        "target": {
            "id": target["id"],
            "os": target["os"],
            "arch": target["arch"],
            "compiler_family": target["compiler_family"],
            "toolchain_flavor": target["toolchain_flavor"],
        },
        "runtime": {
            "objc_runtime": "libobjc2" if target["compiler_family"] != "msvc" else "unknown",
            "objc_abi": "modern" if target["compiler_family"] != "msvc" else "unknown",
            "required_features": ["blocks"] if target["compiler_family"] != "msvc" else [],
        },
        "components": target["core_components"],
        "published": target["publish"],
    }


def component_inventory(target_id: str, toolchain_version: str) -> dict[str, Any]:
    target = target_by_id(target_id)
    components = []
    for name in target["core_components"]:
        components.append(
            {
                "name": name,
                "version": "TBD",
                "source": "upstream-source" if target["strategy"] == "source-build" else "curated-binary-input",
            }
        )
    return {
        "schema_version": 1,
        "target": {
            "id": target["id"],
            "os": target["os"],
            "arch": target["arch"],
            "compiler_family": target["compiler_family"],
            "toolchain_flavor": target["toolchain_flavor"],
        },
        "toolchain_version": toolchain_version,
        "components": components,
    }


def _unix_source_build_script(target_id: str, prefix: str, sources_dir: str, build_root: str, *, host_os: str) -> str:
    target = target_by_id(target_id)
    if target["strategy"] != "source-build":
        raise ValueError(f"target does not use a source build strategy: {target_id}")
    source_lock = source_lock_template(target_id)
    jobs_expr = '$(getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)'
    lines = [
        "#!/bin/sh",
        "set -eu",
        "",
        f'PREFIX="{prefix}"',
        f'SOURCES_DIR="{sources_dir}"',
        f'BUILD_ROOT="{build_root}"',
        f'HOST_OS="{host_os}"',
        f'JOBS="{jobs_expr}"',
        "",
        'mkdir -p "$PREFIX" "$SOURCES_DIR" "$BUILD_ROOT"',
        "",
    ]
    for component in source_lock["components"]:
        lines.extend(
            [
                f'if [ ! -d "$SOURCES_DIR/{component["name"]}/.git" ]; then',
                f'  git clone "{component["url"]}" "$SOURCES_DIR/{component["name"]}"',
                "fi",
                f'git -C "$SOURCES_DIR/{component["name"]}" fetch --tags origin',
                f'git -C "$SOURCES_DIR/{component["name"]}" checkout --detach "{component["revision"]}"',
                "",
            ]
        )
    lines.extend(
        [
            'case "$HOST_OS" in',
            '  linux)',
            '    export MAKE=gmake',
            '    ;;',
            '  openbsd)',
            '    export MAKE=gmake',
            '    export PKG_CONFIG=pkg-config',
            '    export AUTOCONF_VERSION=${AUTOCONF_VERSION:-2.72}',
            '    export AUTOMAKE_VERSION=${AUTOMAKE_VERSION:-1.17}',
            '    ;;',
            'esac',
            "",
            'cd "$SOURCES_DIR/libobjc2"',
            'rm -rf build',
            'cmake -S . -B build \\',
            '  -DCMAKE_BUILD_TYPE=RelWithDebInfo \\',
            '  -DCMAKE_INSTALL_PREFIX="$PREFIX" \\',
            '  -DCMAKE_C_COMPILER=clang \\',
            '  -DCMAKE_CXX_COMPILER=clang++ \\',
            '  -DCMAKE_OBJC_COMPILER=clang \\',
            '  -DCMAKE_OBJCXX_COMPILER=clang++ \\',
            '  -DGNUSTEP_INSTALL_TYPE=NONE \\',
            '  -DEMBEDDED_BLOCKS_RUNTIME=ON',
            'cmake --build build -j"$JOBS"',
            'cmake --install build',
            "",
            'cd "$SOURCES_DIR/libdispatch"',
            'rm -rf build',
            'cmake -S . -B build -G Ninja \\',
            '  -DCMAKE_BUILD_TYPE=RelWithDebInfo \\',
            '  -DCMAKE_INSTALL_PREFIX="$PREFIX" \\',
            '  -DCMAKE_C_COMPILER=clang \\',
            '  -DCMAKE_CXX_COMPILER=clang++ \\',
            '  -DCMAKE_PREFIX_PATH="$PREFIX" \\',
            '  -DBUILD_TESTING=OFF',
            'cmake --build build -j"$JOBS"',
            'cmake --install build',
            "",
            'export CC=clang',
            'export CXX=clang++',
            'export OBJC=clang',
            'export OBJCXX=clang++',
            'export PATH="$PREFIX/System/Tools:$PREFIX/bin:$PATH"',
            'export LD_LIBRARY_PATH="$PREFIX/lib:$PREFIX/lib64:${LD_LIBRARY_PATH:-}"',
            'export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:$PREFIX/lib64/pkgconfig:${PKG_CONFIG_PATH:-}"',
            'export CPPFLAGS="-I$PREFIX/include ${CPPFLAGS:-}"',
            'export CFLAGS="-I$PREFIX/include ${CFLAGS:-}"',
            'export CXXFLAGS="-I$PREFIX/include ${CXXFLAGS:-}"',
            'export OBJCFLAGS="-I$PREFIX/include ${OBJCFLAGS:-}"',
            'export OBJCXXFLAGS="-I$PREFIX/include ${OBJCXXFLAGS:-}"',
            'export LDFLAGS="-L$PREFIX/lib -L$PREFIX/lib64 ${LDFLAGS:-}"',
            "",
            'cd "$SOURCES_DIR/tools-make"',
            './configure --prefix="$PREFIX" --with-layout=gnustep --enable-native-objc-exceptions --enable-objc-arc --with-library-combo=ng-gnu-gnu',
            '"${MAKE:-make}" -j"$JOBS"',
            '"${MAKE:-make}" install',
            "",
            'export GNUSTEP_SYSTEM_ROOT="$PREFIX/System"',
            'export GNUSTEP_LOCAL_ROOT="$PREFIX/Local"',
            'export GNUSTEP_NETWORK_ROOT="$PREFIX/Network"',
            'export GNUSTEP_MAKEFILES="$PREFIX/System/Library/Makefiles"',
            'set +u',
            '. "$GNUSTEP_MAKEFILES/GNUstep.sh"',
            'set -u',
            'unset GNUSTEP_SYSTEM_ROOT GNUSTEP_LOCAL_ROOT GNUSTEP_NETWORK_ROOT',
            "",
            '# Expose the managed Objective-C runtime headers through the GNUstep header domain.',
            'ln -sfn "$PREFIX/include/objc" "$PREFIX/Local/Library/Headers/objc"',
            'cp -f "$PREFIX/include/Block.h" "$PREFIX/Local/Library/Headers/Block.h"',
            'cp -f "$PREFIX/include/Block_private.h" "$PREFIX/Local/Library/Headers/Block_private.h"',
            "",
            'for lib in libs-base libs-corebase libs-gui libs-back; do',
            '  cd "$SOURCES_DIR/$lib"',
            '  "${MAKE:-make}" distclean >/dev/null 2>&1 || true',
            '  ./configure --prefix="$PREFIX"',
            '  "${MAKE:-make}" -j"$JOBS"',
            '  "${MAKE:-make}" install',
            'done',
            "",
            'printf "%s\\n" "$HOST_OS managed toolchain build completed at $PREFIX"',
            "",
        ]
    )
    return "\n".join(lines)


def linux_build_script(target_id: str, prefix: str, sources_dir: str, build_root: str) -> str:
    target = target_by_id(target_id)
    if target["os"] != "linux" or target["strategy"] != "source-build":
        raise ValueError(f"linux build script is only supported for source-built linux targets: {target_id}")
    return _unix_source_build_script(target_id, prefix, sources_dir, build_root, host_os="linux")


def openbsd_build_script(target_id: str, prefix: str, sources_dir: str, build_root: str) -> str:
    target = target_by_id(target_id)
    if target["os"] != "openbsd" or target["strategy"] != "source-build":
        raise ValueError(f"openbsd build script is only supported for source-built openbsd targets: {target_id}")
    return _unix_source_build_script(target_id, prefix, sources_dir, build_root, host_os="openbsd")


def msys2_assembly_script(prefix: str, cache_dir: str) -> str:
    packages = " ".join(MSYS2_PACKAGE_INPUTS)
    host_packages = " ".join(MSYS2_HOST_PACKAGES)
    lines = [
        "[CmdletBinding()]",
        "param(",
        f'  [string]$Prefix = "{prefix}",',
        f'  [string]$CacheDir = "{cache_dir}",',
        '  [string]$MsysRoot = "C:\\msys64",',
        '  [string]$InstallerUrl = "https://github.com/msys2/msys2-installer/releases/latest/download/msys2-x86_64-latest.exe"',
        ")",
        "",
        "$ErrorActionPreference = 'Stop'",
        "$ProgressPreference = 'SilentlyContinue'",
        "",
        "New-Item -ItemType Directory -Force -Path $Prefix | Out-Null",
        "New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null",
        "",
        "$bash = Join-Path $MsysRoot 'usr\\bin\\bash.exe'",
        "$installer = Join-Path $CacheDir 'msys2-x86_64-latest.exe'",
        "",
        "if (-not (Test-Path $bash)) {",
        "  Invoke-WebRequest -UseBasicParsing -Uri $InstallerUrl -OutFile $installer",
        "  & $installer in --confirm-command --accept-messages --root ($MsysRoot -replace '\\\\', '/')",
        "}",
        "",
        "if (-not (Test-Path $bash)) {",
        "  throw 'MSYS2 installation did not produce bash.exe at the expected path.'",
        "}",
        "",
        "$env:CHERE_INVOKING = '1'",
        "& $bash -lc \"true\"",
        "if ($LASTEXITCODE -ne 0) { throw 'MSYS2 shell bootstrap command failed.' }",
        "& $bash -lc \"pacman -Syuu --noconfirm || true\"",
        "if ($LASTEXITCODE -ne 0) { throw 'MSYS2 package database refresh failed.' }",
        f"& $bash -lc \"pacman -S --noconfirm --needed {host_packages}\"",
        "if ($LASTEXITCODE -ne 0) { throw 'MSYS2 host-package installation failed.' }",
        f"& $bash -lc \"pacman -S --overwrite /clang64/include/Block.h --noconfirm --needed {packages}\"",
        "if ($LASTEXITCODE -ne 0) { throw 'MSYS2 GNUstep package installation failed.' }",
        "",
        "$clangRoot = Join-Path $MsysRoot 'clang64'",
        "if (-not (Test-Path $clangRoot)) {",
        "  throw 'MSYS2 clang64 root not found after package installation.'",
        "}",
        "",
        "$toolDirs = @('bin','etc','include','lib','libexec','share')",
        "foreach ($entry in $toolDirs) {",
        "  $source = Join-Path $clangRoot $entry",
        "  if (Test-Path $source) {",
        "    Copy-Item -Recurse -Force $source (Join-Path $Prefix $entry)",
        "  }",
        "}",
        "",
        "Write-Host \"MSYS2 managed toolchain assembly completed at $Prefix\"",
    ]
    return "\n".join(lines) + "\n"


def msvc_status() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "target": {
            "id": "windows-amd64-msvc",
            "os": "windows",
            "arch": "amd64",
            "compiler_family": "msvc",
            "toolchain_flavor": "msvc",
        },
        "publish": False,
        "status": "deferred_for_v1",
        "summary": "The MSVC managed toolchain remains tracked, but it is explicitly deferred for the v0.1.x line and is not validated or published.",
        "blocking_areas": [
            "libdispatch viability under the MSVC stack is not yet proven",
            "the GNUstep runtime and library build pipeline for MSVC is not implemented in this repository",
            "no validated managed artifact or live-validation evidence exists yet",
        ],
        "next_steps": [
            "keep MSVC documented as a deferred target until a dedicated build pipeline exists",
            "prototype libobjc2/tools-make/libs-base/libs-gui/libs-back builds under an MSVC-oriented environment",
            "add live-validation evidence before changing publish status",
        ],
    }


def toolchain_plan(target_id: str) -> dict[str, Any]:
    target = target_by_id(target_id)
    plan: dict[str, Any] = {
        "schema_version": 1,
        "target": target,
        "published": target["publish"],
        "steps": [],
        "validation": [],
    }
    if target["strategy"] == "source-build":
        plan["steps"] = [
            {"id": "prepare-host", "title": "Prepare bootstrap compiler and build host"},
            {"id": "fetch-sources", "title": "Fetch pinned upstream source set"},
            {"id": "build-components", "title": "Build managed GNUstep components into a staging prefix"},
            {"id": "archive-toolchain", "title": "Archive the staged managed toolchain"},
            {"id": "emit-metadata", "title": "Write source lock, component inventory, and checksums"},
        ]
    else:
        plan["steps"] = [
            {"id": "prepare-host", "title": "Prepare assembly host and package cache"},
            {"id": "fetch-packages", "title": "Fetch pinned MSYS2 package inputs"},
            {"id": "normalize-layout", "title": "Normalize package contents into the managed install layout"},
            {"id": "archive-toolchain", "title": "Archive the staged managed toolchain"},
            {"id": "emit-metadata", "title": "Write input manifest, component inventory, and checksums"},
        ]
    plan["validation"] = [
        {"id": "doctor", "title": "Run doctor against the staged managed toolchain"},
        {"id": "compile-probe", "title": "Compile and link a minimal Objective-C probe"},
        {"id": "build-fixture", "title": "Build a minimal GNUstep Make fixture project"},
    ]
    if target["os"] == "windows":
        plan["validation"].append({"id": "otvm-smoke", "title": "Validate bootstrap and install smoke path on an otvm Windows lease"})
    return plan


def debian_gcc_interop_plan() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "command": "debian-gcc-interop-plan",
        "ok": True,
        "status": "ok",
        "summary": "Debian GCC interoperability validation plan generated.",
        "host_requirements": {
            "provider": "otvm-or-equivalent",
            "os": "linux",
            "distribution": "debian",
            "toolchain_profile": "stock-gnu-gcc-gnustep",
            "lifetime": "disposable",
        },
        "goal": (
            "Verify that the Objective-C full CLI can still be built in a stock Debian GCC-based "
            "GNUstep environment as an interoperability check."
        ),
        "constraints": [
            "Treat this as GCC interoperability evidence, not as a managed Tier 1 artifact target.",
            "Use Debian-provided GNUstep packages rather than the managed Clang toolchain.",
            "Destroy the leased or disposable host after validation completes.",
        ],
        "steps": [
            {
                "id": "prepare-host",
                "title": "Provision disposable Debian host",
                "details": "Create a short-lived Debian lease or equivalent disposable VM with shell access.",
            },
            {
                "id": "install-packages",
                "title": "Install Debian GNUstep and build prerequisites",
                "details": (
                    "Install clang-free Debian packages needed to build the full CLI, such as gcc, gobjc, "
                    "gnustep-make, libgnustep-base-dev, libgnustep-gui-dev, libgnustep-back-dev, and make."
                ),
            },
            {
                "id": "source-gnu-environment",
                "title": "Load the GNUstep Make environment",
                "details": "Source the GNUstep environment script so GNUSTEP_MAKEFILES and related variables are available.",
            },
            {
                "id": "build-full-cli",
                "title": "Build the Objective-C full CLI",
                "details": "Run make in src/full-cli and capture stdout/stderr plus the compiler identity.",
            },
            {
                "id": "smoke-cli",
                "title": "Smoke-test the built CLI",
                "details": "Run the built gnustep binary with --help, --version, and doctor --json.",
            },
            {
                "id": "record-evidence",
                "title": "Record interoperability evidence",
                "details": "Persist package versions, compiler version, command output, and any known GCC-specific limitations.",
            },
        ],
        "evidence": [
            "dpkg package list for GNUstep-related packages",
            "gcc --version output",
            "make output from src/full-cli",
            "CLI smoke-test output",
        ],
    }


def _artifact_basename(kind: str, target_id: str, version: str) -> str:
    return f"gnustep-{kind}-{target_id}-{version}"


def _artifact_extension(target: dict[str, Any]) -> str:
    return ".zip" if target["os"] == "windows" else ".tar.gz"


def _artifact_filename(kind: str, target_id: str, version: str) -> str:
    target = target_by_id(target_id)
    return f"{_artifact_basename(kind, target_id, version)}{_artifact_extension(target)}"


def _artifact_url(base_url: str, version: str, filename: str) -> str:
    return f"{base_url.rstrip('/')}/download/v{version}/{filename}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _archive_directory(source_dir: Path, archive_path: Path, root_name: str) -> None:
    if archive_path.suffix == ".zip":
        with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
            for path in sorted(source_dir.rglob("*")):
                if path.is_dir():
                    continue
                relative = path.relative_to(source_dir)
                archive.write(path, arcname=str(Path(root_name) / relative))
        return

    with tarfile.open(archive_path, "w:gz", dereference=True) as archive:
        archive.add(source_dir, arcname=root_name)


def _archive_file(source_file: Path, archive_path: Path, root_name: str) -> None:
    if archive_path.suffix == ".zip":
        with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
            archive.write(source_file, arcname=str(Path(root_name) / source_file.name))
        return

    with tarfile.open(archive_path, "w:gz", dereference=True) as archive:
        archive.add(source_file, arcname=str(Path(root_name) / source_file.name))


def bundle_full_cli(
    binary_path: str | Path,
    output_dir: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    binary = Path(binary_path).resolve()
    if not binary.exists():
        raise FileNotFoundError(binary)
    root = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[2]
    bundle_root = Path(output_dir).resolve()
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    (bundle_root / "bin").mkdir(parents=True, exist_ok=True)
    runtime_root = bundle_root / "libexec" / "gnustep-cli"
    (runtime_root / "scripts").mkdir(parents=True, exist_ok=True)
    (runtime_root / "src").mkdir(parents=True, exist_ok=True)
    shutil.copytree(root / "scripts" / "internal", runtime_root / "scripts" / "internal", dirs_exist_ok=True)
    shutil.copytree(root / "src" / "gnustep_cli_shared", runtime_root / "src" / "gnustep_cli_shared", dirs_exist_ok=True)
    shutil.copytree(root / "examples", runtime_root / "examples", dirs_exist_ok=True)
    runtime_binary_dir = runtime_root / "bin"
    runtime_binary_dir.mkdir(parents=True, exist_ok=True)
    runtime_binary = runtime_binary_dir / binary.name
    shutil.copy2(binary, runtime_binary)
    os.chmod(runtime_binary, 0o755)

    if binary.suffix.lower() == ".exe":
        shutil.copy2(runtime_binary, bundle_root / "bin" / binary.name)
        os.chmod(bundle_root / "bin" / binary.name, 0o755)
    else:
        launcher = bundle_root / "bin" / binary.name
        launcher.write_text(
            "#!/usr/bin/env sh\n"
            "set -eu\n"
            'PROGRAM_PATH="$0"\n'
            'while [ -L "$PROGRAM_PATH" ]; do\n'
            '  PROGRAM_PATH="$(readlink "$PROGRAM_PATH")"\n'
            "done\n"
            'BIN_DIR=$(CDPATH= cd -- "$(dirname "$PROGRAM_PATH")" && pwd)\n'
            'INSTALL_ROOT=$(CDPATH= cd -- "$BIN_DIR/.." && pwd)\n'
            'RUNTIME_ROOT="$INSTALL_ROOT/libexec/gnustep-cli"\n'
            'RUNTIME_BIN="$RUNTIME_ROOT/bin/gnustep"\n'
            'export GNUSTEP_SYSTEM_ROOT="$INSTALL_ROOT/System"\n'
            'export GNUSTEP_LOCAL_ROOT="$INSTALL_ROOT/Local"\n'
            'export GNUSTEP_NETWORK_ROOT="$INSTALL_ROOT/Network"\n'
            'export GNUSTEP_MAKEFILES="$INSTALL_ROOT/System/Library/Makefiles"\n'
            'export PATH="$INSTALL_ROOT/bin:$INSTALL_ROOT/System/Tools:$INSTALL_ROOT/Local/Tools:$PATH"\n'
            'export LD_LIBRARY_PATH="$INSTALL_ROOT/Local/Library/Libraries:$INSTALL_ROOT/System/Library/Libraries:$INSTALL_ROOT/lib:$INSTALL_ROOT/lib64:${LD_LIBRARY_PATH:-}"\n'
            'if [ -f "$GNUSTEP_MAKEFILES/GNUstep.sh" ]; then\n'
            '  set +u\n'
            '  . "$GNUSTEP_MAKEFILES/GNUstep.sh"\n'
            '  set -u\n'
            "fi\n"
            'exec "$RUNTIME_BIN" "$@"\n',
            encoding="utf-8",
        )
        os.chmod(launcher, 0o755)
    return {
        "schema_version": 1,
        "command": "bundle-cli",
        "ok": True,
        "status": "ok",
        "summary": "Full CLI runtime bundle created.",
        "bundle_root": str(bundle_root),
    }


def stage_release_assets(
    version: str,
    output_dir: str | Path,
    base_url: str,
    *,
    cli_inputs: dict[str, str | Path] | None = None,
    toolchain_inputs: dict[str, str | Path] | None = None,
    channel: str = "stable",
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    release_dir = output_root / channel / version
    release_dir.mkdir(parents=True, exist_ok=True)

    cli_inputs = cli_inputs or {}
    toolchain_inputs = toolchain_inputs or {}
    artifacts: list[dict[str, Any]] = []
    checksums: list[dict[str, str]] = []

    for target in tier1_targets():
        if not target["publish"]:
            continue
        for kind, inputs in (("cli", cli_inputs), ("toolchain", toolchain_inputs)):
            input_value = inputs.get(target["id"])
            if input_value is None:
                continue
            source = Path(input_value).resolve()
            if not source.exists():
                raise FileNotFoundError(source)
            filename = _artifact_filename(kind, target["id"], version)
            archive_path = release_dir / filename
            root_name = _artifact_basename(kind, target["id"], version)
            if source.is_dir():
                _archive_directory(source, archive_path, root_name)
            else:
                _archive_file(source, archive_path, root_name)

            artifact = {
                "id": f"{kind}-{target['id']}",
                "kind": kind,
                "version": version,
                "os": target["os"],
                "arch": target["arch"],
                "compiler_family": target["compiler_family"],
                "toolchain_flavor": target["toolchain_flavor"],
                "objc_runtime": "libobjc2" if target["compiler_family"] != "msvc" else "unknown",
                "objc_abi": "modern" if target["compiler_family"] != "msvc" else "unknown",
                "required_features": [] if kind == "cli" else (["blocks"] if target["compiler_family"] != "msvc" else []),
                "format": "zip" if target["os"] == "windows" else "tar.gz",
                "url": _artifact_url(base_url, version, filename),
                "sha256": _sha256(archive_path),
                "size": archive_path.stat().st_size,
                "filename": filename,
            }
            artifacts.append(artifact)
            checksums.append({"filename": filename, "sha256": artifact["sha256"]})

    manifest = {
        "schema_version": 1,
        "channel": channel,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "releases": [
            {
                "version": version,
                "status": "active",
                "artifacts": artifacts,
            }
        ],
    }
    manifest_path = release_dir / "release-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    checksums_path = release_dir / "SHA256SUMS"
    checksums_path.write_text(
        "".join(f"{entry['sha256']}  {entry['filename']}\n" for entry in checksums),
        encoding="utf-8",
    )

    return {
        "schema_version": 1,
        "command": "stage-release",
        "ok": True,
        "status": "ok",
        "summary": "Release assets staged.",
        "release_dir": str(release_dir),
        "manifest_path": str(manifest_path),
        "checksums_path": str(checksums_path),
        "artifacts": artifacts,
    }


def verify_release_directory(release_dir: str | Path) -> dict[str, Any]:
    root = Path(release_dir).resolve()
    manifest_path = root / "release-manifest.json"
    checksums_path = root / "SHA256SUMS"
    if not manifest_path.exists():
        return {
            "schema_version": 1,
            "command": "verify-release",
            "ok": False,
            "status": "error",
            "summary": "Release manifest is missing.",
            "release_dir": str(root),
        }
    if not checksums_path.exists():
        return {
            "schema_version": 1,
            "command": "verify-release",
            "ok": False,
            "status": "error",
            "summary": "SHA256SUMS is missing.",
            "release_dir": str(root),
        }

    manifest = json.loads(manifest_path.read_text())
    artifacts = manifest["releases"][0]["artifacts"]
    checksum_map: dict[str, str] = {}
    for line in checksums_path.read_text().splitlines():
        if not line.strip():
            continue
        sha256, filename = line.split("  ", 1)
        checksum_map[filename] = sha256

    results: list[dict[str, Any]] = []
    ok = True
    for artifact in artifacts:
        filename = artifact["filename"]
        asset_path = root / filename
        exists = asset_path.exists()
        actual_sha = _sha256(asset_path) if exists else None
        checksum_ok = exists and checksum_map.get(filename) == actual_sha == artifact["sha256"]
        results.append(
            {
                "filename": filename,
                "exists": exists,
                "sha256_matches": checksum_ok,
            }
        )
        ok = ok and checksum_ok

    return {
        "schema_version": 1,
        "command": "verify-release",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": "Release directory verified." if ok else "Release directory verification failed.",
        "release_dir": str(root),
        "results": results,
    }


def _extract_archive(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if archive_path.suffix == ".zip":
        with ZipFile(archive_path) as archive:
            archive.extractall(destination)
        return
    with tarfile.open(archive_path, "r:gz") as archive:
        archive.extractall(destination, filter="data")


def qualify_release_install(release_dir: str | Path, install_root: str | Path) -> dict[str, Any]:
    verification = verify_release_directory(release_dir)
    if not verification["ok"]:
        return verification

    root = Path(release_dir).resolve()
    destination = Path(install_root).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((root / "release-manifest.json").read_text())
    installs: list[dict[str, Any]] = []
    for artifact in manifest["releases"][0]["artifacts"]:
        filename = artifact["filename"]
        asset_path = root / filename
        extract_root = destination / artifact["id"]
        if extract_root.exists():
            shutil.rmtree(extract_root)
        _extract_archive(asset_path, extract_root)
        installs.append(
            {
                "artifact_id": artifact["id"],
                "filename": filename,
                "install_path": str(extract_root),
            }
        )

    return {
        "schema_version": 1,
        "command": "qualify-release",
        "ok": True,
        "status": "ok",
        "summary": "Release assets verified and extracted into the qualification root.",
        "release_dir": str(root),
        "install_root": str(destination),
        "installs": installs,
    }


def qualify_full_cli_handoff(release_dir: str | Path, install_root: str | Path) -> dict[str, Any]:
    release_root = Path(release_dir).resolve()
    manifest_path = release_root / "release-manifest.json"
    install_path = Path(install_root).resolve()
    payload, exit_code = execute_setup(
        scope="user",
        manifest_path=str(manifest_path),
        install_root=str(install_path),
    )
    if exit_code != 0 or not payload.get("ok", False):
        return {
            "schema_version": 1,
            "command": "qualify-full-cli-handoff",
            "ok": False,
            "status": "error",
            "summary": "Bootstrap-to-full handoff qualification failed during setup.",
            "release_dir": str(release_root),
            "install_root": str(install_path),
            "setup_exit_code": exit_code,
            "setup_payload": payload,
        }

    binary_path = install_path / "bin" / "gnustep"
    runtime_root = install_path / "libexec" / "gnustep-cli"
    checks: list[dict[str, Any]] = []

    def add_check(check_id: str, ok: bool, message: str) -> None:
        checks.append(
            {
                "id": check_id,
                "ok": ok,
                "message": message,
            }
        )

    add_check("install.binary", binary_path.exists(), "Installed CLI binary is present.")
    add_check("install.binary_executable", os.access(binary_path, os.X_OK), "Installed CLI binary is executable.")
    add_check(
        "install.runtime_bundle",
        runtime_root.exists(),
        "Installed CLI runtime bundle is present under libexec/gnustep-cli.",
    )
    add_check(
        "install.runtime_examples",
        (runtime_root / "examples").exists(),
        "Installed CLI runtime bundle includes bundled example manifests.",
    )

    command_results: list[dict[str, Any]] = []
    for args, expected in (
        (["--version"], "0.1.0-dev"),
        (["--help"], "gnustep"),
    ):
        if not os.access(binary_path, os.X_OK):
            command_results.append(
                {
                    "args": args,
                    "ran": False,
                    "ok": False,
                    "stdout": "",
                    "stderr": "Installed CLI binary is not executable.",
                    "exit_status": None,
                }
            )
            continue
        proc = subprocess.run(
            [str(binary_path), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            cwd=str(install_path),
        )
        command_results.append(
            {
                "args": args,
                "ran": True,
                "ok": proc.returncode == 0 and expected in proc.stdout,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "exit_status": proc.returncode,
            }
        )

    ok = all(check["ok"] for check in checks) and all(result["ok"] for result in command_results)
    return {
        "schema_version": 1,
        "command": "qualify-full-cli-handoff",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": (
            "Bootstrap-to-full handoff qualification succeeded."
            if ok
            else "Bootstrap-to-full handoff qualification failed."
        ),
        "release_dir": str(release_root),
        "install_root": str(install_path),
        "setup_payload": payload,
        "checks": checks,
        "command_results": command_results,
    }


def github_release_plan(
    repo: str,
    version: str,
    release_dir: str | Path,
    *,
    channel: str = "stable",
    title: str | None = None,
) -> dict[str, Any]:
    root = Path(release_dir).resolve()
    tag = f"v{version}"
    title = title or f"GNUstep CLI {version}"
    asset_paths = sorted(str(path) for path in root.iterdir() if path.is_file())
    create_command = ["gh", "release", "create", tag, "--repo", repo, "--title", title]
    if channel != "stable":
        create_command.append("--prerelease")
    create_command.extend(asset_paths)
    return {
        "schema_version": 1,
        "command": "github-release-plan",
        "ok": True,
        "status": "ok",
        "repo": repo,
        "tag": tag,
        "release_dir": str(root),
        "assets": asset_paths,
        "command_line": create_command,
    }


def publish_github_release(
    repo: str,
    version: str,
    release_dir: str | Path,
    *,
    channel: str = "stable",
    title: str | None = None,
) -> dict[str, Any]:
    plan = github_release_plan(repo, version, release_dir, channel=channel, title=title)
    proc = subprocess.run(plan["command_line"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    plan["stdout"] = proc.stdout
    plan["stderr"] = proc.stderr
    plan["exit_status"] = proc.returncode
    plan["ok"] = proc.returncode == 0
    plan["status"] = "ok" if proc.returncode == 0 else "error"
    plan["summary"] = "GitHub Release published." if proc.returncode == 0 else "GitHub Release publication failed."
    return plan


def write_release_manifest(version: str, base_url: str, output_path: str | Path) -> Path:
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(release_manifest_from_matrix(version, base_url), indent=2) + "\n")
    return output
