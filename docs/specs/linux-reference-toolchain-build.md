# Linux Reference Toolchain Build

This document records the current reference implementation path for the first
real managed toolchain target:

- `linux-amd64-clang` for Debian-scoped amd64 artifacts
- `linux-ubuntu2404-amd64-clang` for Ubuntu-scoped amd64 artifacts

## Current State

The repository now contains concrete tracked build inputs for the Linux managed
toolchain:

- a pinned source lock at
  [toolchains/linux-amd64-clang/source-lock.json](/home/danboyd/gnustep-cli-new/toolchains/linux-amd64-clang/source-lock.json)
- a generated managed toolchain manifest at
  [toolchains/linux-amd64-clang/toolchain-manifest.json](/home/danboyd/gnustep-cli-new/toolchains/linux-amd64-clang/toolchain-manifest.json)
- a generated reference build script at
  [toolchains/linux-amd64-clang/build-toolchain.sh](/home/danboyd/gnustep-cli-new/toolchains/linux-amd64-clang/build-toolchain.sh)
- an Ubuntu 24.04 Docker-oriented target at
  [toolchains/linux-ubuntu2404-amd64-clang/build-toolchain.sh](/home/danboyd/gnustep-cli-new/toolchains/linux-ubuntu2404-amd64-clang/build-toolchain.sh)
- an Ubuntu 24.04 build container definition at
  [toolchains/linux-ubuntu2404-amd64-clang/Dockerfile](/home/danboyd/gnustep-cli-new/toolchains/linux-ubuntu2404-amd64-clang/Dockerfile)

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
- a promoted shared build-infra command, `build-linux-cli-against-managed-toolchain`, plus the dev wrapper `scripts/dev/build-linux-cli-against-managed-toolchain.sh`, for producing managed-prefix CLI release artifacts
- an ABI audit command, `linux-cli-abi-audit`, that rejects Linux CLI binaries carrying legacy GCC Objective-C runtime symbols such as `__objc_class_name_NSAutoreleasePool`
- unit coverage confirming the build-script, ABI audit, local metadata refresh, and repository contracts still pass after the Linux reference build updates

What is not yet in place:

- production archive publication to GitHub Releases
- direct integration of managed-prefix CLI artifact production into `prepare-github-release` so release preparation cannot accidentally consume a host-built GNUstep Make binary

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
successfully against that staged managed toolchain through the shared
`build-linux-cli-against-managed-toolchain` command. The resulting binary was
smoke-tested with `--help`, then archived as a full CLI bundle and checked with
`linux-cli-abi-audit` before local release metadata was refreshed. This is now
the required model for Linux release CLI artifacts; host GNUstep Make builds are
only developer convenience builds and must not be promoted as managed-release
artifacts.

The generated Linux build script was revalidated with `bash -n`, and the
repository unit suite passed with:

```sh
python3 -m unittest discover -s tests
```

## Related Commands

Examples:

```sh
python3 scripts/internal/build_infra.py --json source-lock --target linux-amd64-clang
python3 scripts/internal/build_infra.py --json source-lock --target linux-ubuntu2404-amd64-clang
# Build the Ubuntu target in its distro-scoped container:
docker build -t gnustep-cli-toolchain:ubuntu2404 toolchains/linux-ubuntu2404-amd64-clang
docker run --rm -v /tmp/gnustep-cli-ubuntu2404-toolchain:/tmp/gnustep-cli-ubuntu2404-toolchain gnustep-cli-toolchain:ubuntu2404
python3 scripts/internal/build_infra.py --json toolchain-manifest --target linux-amd64-clang --toolchain-version 2026.04.0
python3 scripts/internal/build_infra.py --json toolchain-manifest --target linux-ubuntu2404-amd64-clang --toolchain-version 2026.04.0
python3 scripts/internal/build_infra.py linux-build-script \
  --target linux-ubuntu2404-amd64-clang \
  --prefix /tmp/gnustep-cli-linux-toolchain/install \
  --sources-dir /tmp/gnustep-cli-linux-toolchain/sources \
  --build-root /tmp/gnustep-cli-linux-toolchain/build
python3 scripts/internal/build_infra.py --json build-linux-cli-against-managed-toolchain \
  --toolchain-archive dist/stable/0.1.0-dev/gnustep-toolchain-linux-amd64-clang-0.1.0-dev.tar.gz \
  --output-dir dist/dogfood/linux-cli \
  --version 0.1.1-dev \
  --release-dir dist/stable/0.1.0-dev \
  --private-key /path/to/dev-release-private.pem
python3 scripts/internal/build_infra.py --json linux-cli-abi-audit \
  --binary /path/to/staged/full-cli/bin/gnustep
```
