# Package Repository, Installation, And Build Infrastructure

This document records the current Phase 10-12 baseline.

## Package Repository

- package definitions remain one-directory-per-package
- package indexes are generated, not edited by hand
- the current repository now carries a generated `packages/package-index.json`
  artifact that is verified in CI against the package manifests
- a template for the future `gnustep-packages` repository lives under `templates/gnustep-packages/`

## Package Installation

- package install/remove currently target a managed root
- installed package state is tracked under `<managed-root>/state/installed-packages.json`
- package installs are staged under `<managed-root>/.staging/` before being moved into `<managed-root>/packages/<package-id>/`
- installed files are recorded for later removal

## Build Infrastructure

- the initial build matrix is explicit and matches the Tier 1 target policy
- official package binaries should be produced by project-controlled builds
  from reviewed source provenance and package metadata, not accepted as opaque
  maintainer-provided binaries by default
- package artifact publication should record source identity, build identity,
  checksums, signatures, and target compatibility in the generated index or
  associated release metadata
- release manifests can be generated from that matrix
- the current helpers are scaffolding for controlled artifact publication workflows
