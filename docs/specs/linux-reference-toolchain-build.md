# Linux Reference Toolchain Build

This document records the current reference implementation path for the first
real managed toolchain target:

- `linux-amd64-clang`

## Current State

The repository now contains concrete tracked build inputs for the Linux managed
toolchain:

- a pinned source lock at
  [toolchains/linux-amd64-clang/source-lock.json](/home/danboyd/gnustep-cli-new/toolchains/linux-amd64-clang/source-lock.json)
- a generated managed toolchain manifest at
  [toolchains/linux-amd64-clang/toolchain-manifest.json](/home/danboyd/gnustep-cli-new/toolchains/linux-amd64-clang/toolchain-manifest.json)
- a generated reference build script at
  [toolchains/linux-amd64-clang/build-toolchain.sh](/home/danboyd/gnustep-cli-new/toolchains/linux-amd64-clang/build-toolchain.sh)

## Pinned Component Set

The Linux reference build currently pins:

- `libobjc2`
- `libdispatch`
- `tools-make`
- `libs-base`
- `libs-corebase`
- `libs-gui`
- `libs-back`

The source revisions were resolved from the official upstream repositories and
recorded in the source lock.

## Build Strategy

The generated script implements this sequence:

1. clone or update each pinned upstream repository
2. check out the pinned detached revision
3. build and install `libobjc2`
4. build and install `libdispatch`
5. build and install `tools-make`
6. source the GNUstep Make environment from the managed prefix
7. build and install `libs-base`, `libs-corebase`, `libs-gui`, and `libs-back`

The script is intentionally explicit and readable. It is not yet a full release
pipeline with caching, retries, archive publication, or artifact verification.

## Scope Boundary

This is currently a reference build path, not yet a production release builder.

What is in place:

- pinned Linux source inputs
- generated shell-valid build script
- build-infra commands to emit the source lock, toolchain manifest, component
  inventory, and script
- automated tests that verify the contract and script generation
- a locally validated build path that successfully built and installed:
  - `libobjc2`
  - `libdispatch`
  - `tools-make`
  - `libs-base`
  - `libs-corebase`
  - `libs-gui`
  - `libs-back`
- a locally validated build of the Objective-C full CLI against that staged
  managed Linux toolchain
- unit coverage confirming the build-script and repository contracts still pass
  after the Linux reference build updates

What is not yet in place:

- archive publication to GitHub Releases
- end-to-end bootstrap `setup` downloading and installing this produced
  toolchain artifact

## Local Validation Notes

The Linux reference build has now been exercised on this host through the full
core managed stack. The managed prefix successfully staged:

- `libobjc2`
- `libdispatch`
- `tools-make`
- `libs-base`
- `libs-corebase`
- `libs-gui`
- `libs-back`

The Objective-C full CLI under
[src/full-cli](/home/danboyd/gnustep-cli-new/src/full-cli) also built
successfully against that staged managed toolchain, and the resulting binary
was smoke-tested with:

- `--help`
- `--json --version`

The generated Linux build script was revalidated with `bash -n`, and the
repository unit suite passed with:

```sh
python3 -m unittest discover -s tests
```

## Related Commands

Examples:

```sh
python3 scripts/internal/build_infra.py --json source-lock --target linux-amd64-clang
python3 scripts/internal/build_infra.py --json toolchain-manifest --target linux-amd64-clang --toolchain-version 2026.04.0
python3 scripts/internal/build_infra.py linux-build-script \
  --target linux-amd64-clang \
  --prefix /tmp/gnustep-cli-linux-toolchain/install \
  --sources-dir /tmp/gnustep-cli-linux-toolchain/sources \
  --build-root /tmp/gnustep-cli-linux-toolchain/build
```
