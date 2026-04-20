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

## Upstream And Patch Policy

- each package manifest must identify the upstream source of truth in `source`
  using an official upstream repository or release archive whenever practical
- `source` must also record `tracking_strategy`, `update_cadence`, and
  `channel_policy` so package updates are explicit review decisions rather than
  implicit rebuilds from whatever upstream state exists at build time
- official stable packages should normally track tagged upstream releases;
  branch snapshots and per-commit builds belong on dogfood or snapshot channels
  unless maintainers explicitly approve a package-specific exception
- downstream patches are first-class package metadata, not operator notes
- package-scoped patches live under `packages/<package-id>/patches/` and are
  declared in the package manifest `patches` array
- every declared patch must include a stable `id`, relative `path`, verified
  `sha256`, and optional `strip`, `applies_to`, `rationale`, and
  `upstream_status` fields
- package artifact builders must apply declared patches after fetching and
  verifying upstream source, before invoking `gnustep build` or another selected
  backend
- `scripts/internal/package_tool.py apply-patches <manifest> <source-dir>
  --target <artifact-id>` is the current repository-level patch application
  primitive; it verifies manifest and patch digests, selects target-applicable
  patches, and invokes the system `patch` tool with the declared strip level
- initial `tools-xctest` package targets are Linux `amd64/clang`, Debian Linux `arm64/clang`, OpenBSD `amd64/clang`, OpenBSD `arm64/clang`, and Windows `amd64/msys2-clang64`; planned targets remain `publish: false` until rebuilt with declared patches and host-validated
- generated package indexes and provenance records carry the package source and
  patch list at package level and artifact level so a published artifact can be
  traced back to both upstream source and project-maintained downstream changes
- production publication must fail if a publishable package references a missing
  patch, a placeholder patch digest, or a patch digest that does not match the
  reviewed patch file

Recommended patch entry shape:

```json
{
  "id": "fix-tools-xctest-openbsd-link-name",
  "path": "patches/fix-tools-xctest-openbsd-link-name.patch",
  "sha256": "...",
  "strip": 1,
  "applies_to": ["tools-xctest-openbsd-amd64-clang"],
  "rationale": "Carry a downstream OpenBSD linker-name fix until upstream accepts it.",
  "upstream_status": "submitted"
}
```
