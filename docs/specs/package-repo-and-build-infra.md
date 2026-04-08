# Package Repository, Installation, And Build Infrastructure

This document records the current Phase 10-12 baseline.

## Package Repository

- package definitions remain one-directory-per-package
- package indexes are generated, not edited by hand
- a template for the future `gnustep-packages` repository lives under `templates/gnustep-packages/`

## Package Installation

- package install/remove currently target a managed root
- installed package state is tracked under `<managed-root>/state/installed-packages.json`
- package installs are staged under `<managed-root>/.staging/` before being moved into `<managed-root>/packages/<package-id>/`
- installed files are recorded for later removal

## Build Infrastructure

- the initial build matrix is explicit and matches the Tier 1 target policy
- release manifests can be generated from that matrix
- the current helpers are scaffolding for controlled artifact publication workflows

