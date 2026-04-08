# Phase 17 Tier 1 Toolchain Work

This document records the current repository state for the remaining Tier 1
managed toolchain targets after the Linux reference build.

## OpenBSD `amd64/clang`

The repository now contains concrete OpenBSD source-build inputs and a generated
build script:

- [source-lock.json](/home/danboyd/gnustep-cli-new/toolchains/openbsd-amd64-clang/source-lock.json)
- [toolchain-manifest.json](/home/danboyd/gnustep-cli-new/toolchains/openbsd-amd64-clang/toolchain-manifest.json)
- [component-inventory.json](/home/danboyd/gnustep-cli-new/toolchains/openbsd-amd64-clang/component-inventory.json)
- [build-toolchain.sh](/home/danboyd/gnustep-cli-new/toolchains/openbsd-amd64-clang/build-toolchain.sh)

The OpenBSD build path currently reuses the pinned GNUstep core component set
from the Linux reference target while adding OpenBSD-specific host assumptions:

- `gmake`
- `pkg-config`
- explicit `AUTOCONF_VERSION`
- explicit `AUTOMAKE_VERSION`

Current validation status:

- the generated script is shell-valid
- repository unit coverage now exercises the OpenBSD build-script path
- live OpenBSD validation was exercised using a temporary `otvm` config that
  pointed at the latest available OpenBSD 7.8 custom image
- `otvm preflight openbsd-7.8-fvwm` passes with that temporary config
- the leased OpenBSD image opens TCP 22 but does not reach the profile's ready
  state, and the current operator key cannot log in as `oracleadmin`
- a follow-up `otvm openbsd78-build-image --preserve-failed-instance` run
  re-used the existing base image and launched an OpenBSD builder instance
- direct SSH to that builder as `root` with the current operator key also fails
  with `Permission denied (publickey,password,keyboard-interactive)`
- that means the remaining OpenBSD blocker is image hygiene rather than the
  GNUstep toolchain scripts: the current custom/base images are not aligned with
  the current operator key material and must be rebuilt or revalidated through
  the OpenBSD image pipeline before Phase 17 can be considered complete
- the failing OpenBSD lease and builder instance were explicitly terminated to
  avoid idle OCI cost

## Windows `amd64/msys2-clang64`

The repository now contains concrete Windows MSYS2 assembly inputs and generated
artifacts:

- [input-manifest.json](/home/danboyd/gnustep-cli-new/toolchains/windows-amd64-msys2-clang64/input-manifest.json)
- [toolchain-manifest.json](/home/danboyd/gnustep-cli-new/toolchains/windows-amd64-msys2-clang64/toolchain-manifest.json)
- [component-inventory.json](/home/danboyd/gnustep-cli-new/toolchains/windows-amd64-msys2-clang64/component-inventory.json)
- [assemble-toolchain.ps1](/home/danboyd/gnustep-cli-new/toolchains/windows-amd64-msys2-clang64/assemble-toolchain.ps1)

The PowerShell assembly script:

- expects an MSYS2 installation rooted at `C:\msys64`
- updates the package database
- installs required MSYS2 host tooling such as `make`
- installs the Clang compiler package itself in addition to the GNUstep runtime packages
- installs the pinned GNUstep-related `clang64` package set
- copies the `clang64` runtime directories into the managed prefix

Current validation status:

- the generated PowerShell script parses cleanly under `pwsh`
- `otvm preflight windows-2022` is ready in this environment
- live Windows validation was executed on a short-lived `windows-2022` `otvm`
  lease
- the generated assembly script was copied to the blank Windows host and run
  under `powershell.exe`
- the script now bootstraps MSYS2 automatically from the official installer
  before assembling the managed prefix
- the first end-to-end run exposed a real package conflict between
  `mingw-w64-clang-x86_64-libobjc2` and
  `mingw-w64-clang-x86_64-libblocksruntime-swift` over
  `/clang64/include/Block.h`
- the overlap rule was then added explicitly to the manifest and assembly
  script via `--overwrite /clang64/include/Block.h`
- the updated script completed successfully on a fresh Windows lease and
  assembled the managed toolchain under `C:\gnustep-cli\toolchain`
- follow-up full-CLI validation on the same lease exposed a real Windows source/toolchain
  integration blocker rather than a packaging gap:
  Foundation plus the current MSYS2 `libdispatch` stack fails to compile the
  full CLI due to a `mode_t` typedef conflict between
  `os/generic_win_base.h` and `sys/types.h`
- that means the Windows `msys2-clang64` managed toolchain assembly path is now
  materially working, but the full GNUstep CLI is not yet confirmed buildable
  there without either an upstream fix or a project-local workaround for that
  header conflict
- the validation lease was explicitly destroyed afterward and followed by
  `otvm reap`

## Windows `amd64/msvc`

MSVC is now tracked explicitly as a go/no-go target with a non-published state:

- [windows-amd64-msvc-status.json](/home/danboyd/gnustep-cli-new/toolchains/windows-amd64-msvc-status.json)

Current status:

- `publish` remains `false`
- the target is still treated as not ready
- the repository records the blocking areas instead of implying silent support

## Test Coverage

Phase 17 repo coverage now includes:

- per-target build and assembly plan coverage
- OpenBSD build-script generation checks
- Windows MSYS2 assembly-script generation checks
- explicit MSVC status checks
