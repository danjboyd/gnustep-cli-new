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

- A real local Linux release payload has been staged under `dist/stable/`.
- The first private GitHub prerelease has been published at
  `v0.1.0-dev`.
- The staged payload includes:
  - the built full GNUstep CLI archive
  - the managed Linux toolchain archive
  - a manifest with real file checksums
  - `SHA256SUMS`
- Release qualification can verify checksums and extract staged artifacts into a
  disposable install root for validation.
- The shared `setup` backend can now install from a staged release manifest into
  a managed root with checksum verification and PATH guidance.

## Current Blockers

- Publication is currently Linux-only.
- `setup` is implemented in the shared helper path, but bootstrap-native
  `setup` remains a thinner path and is not yet using the same full install
  execution flow.
- Fresh-host qualification against the live GitHub Release assets still needs to
  be run end to end.

## Immediate Follow-Up

- run fresh-host qualification against the live private GitHub Release assets
- decide when to make releases public versus keeping them private during bring-up
- extend staged release generation and qualification beyond Linux once the
  remaining Tier 1 artifacts are publishable
