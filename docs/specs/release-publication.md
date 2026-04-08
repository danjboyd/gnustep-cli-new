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
- The staged payload includes:
  - the built full GNUstep CLI archive
  - the managed Linux toolchain archive
  - a manifest with real file checksums
  - `SHA256SUMS`
- Release qualification can verify checksums and extract staged artifacts into a
  disposable install root for validation.

## Current Blockers

- No Git remote is configured for this repository yet.
- No GitHub repository currently exists at `danjboyd/gnustep-cli-new`.
- Because of that, the GitHub publication tooling can currently produce an
  exact `gh release create` plan but cannot complete live publication.

## Immediate Follow-Up

- create or connect the canonical GitHub repository
- push this repository to that remote
- run the staged GitHub publication command against the real repo
- extend staged release generation and qualification beyond Linux once the
  remaining Tier 1 artifacts are publishable
