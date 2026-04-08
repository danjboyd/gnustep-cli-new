# Release Publication

This document records the current Phase 19 implementation status.

## Current Publication Model

- GitHub Releases is the intended official artifact store.
- Release discovery still flows through `release-manifest.json`, not through
  GitHub page scraping.
- A staged release directory currently contains:
  - CLI archives
  - managed toolchain archives
  - `release-manifest.json`
  - `SHA256SUMS`

## Implemented Tooling

The current release pipeline is implemented through
[`build_infra.py`](/home/danboyd/gnustep-cli-new/src/gnustep_cli_shared/build_infra.py)
and
[`scripts/internal/build_infra.py`](/home/danboyd/gnustep-cli-new/scripts/internal/build_infra.py).

Implemented subcommands include:

- `stage-release`
- `verify-release`
- `qualify-release`
- `github-release-plan`
- `github-release-publish`

## Current Verified State

- A real staged prerelease payload now exists under `dist/stable/0.1.0-dev`.
- The first private GitHub prerelease has been published at
  `v0.1.0-dev`.
- The staged payload includes:
  - the built full GNUstep CLI archives for Linux and Windows MSYS2 `clang64`
  - the managed toolchain archives for Linux and Windows MSYS2 `clang64`
  - a manifest with real file checksums
  - `SHA256SUMS`
- Release qualification can verify checksums and extract staged artifacts into a
  disposable install root for validation.
- The shared `setup` backend can now install from a staged release manifest into
  a managed root with checksum verification and PATH guidance.
- The shell bootstrap has been live-qualified from the private GitHub Release
  assets on Linux outside the repository tree.
- A live Windows `otvm` lease successfully assembled the MSYS2 managed toolchain,
  built the full GNUstep CLI with an explicit `HAVE_MODE_T` define, and
  produced publishable Windows prerelease artifacts.

## Current Blockers

- OpenBSD remains blocked on external `otvm` image hygiene rather than on this
  repository's build scripts.
- Debian GCC interoperability validation is currently blocked in this
  environment because `OracleTestVMs` does not yet have
  `debian13_wayland_image_ocid` configured.
- Windows fresh-host installation from the published prerelease assets still
  needs an end-to-end bootstrap qualification run against the updated release.
- MSVC remains explicitly deferred and unpublished for the v0.1.x line.

## Immediate Follow-Up

- run fresh-host qualification against the live private GitHub Release assets on
  Windows using the updated prerelease
- restore Debian otvm image availability, then run the GCC interoperability
  validation there
- decide when to make releases public versus keeping them private during bring-up
- complete OpenBSD once the external image blocker is resolved
