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
- package manifests may distinguish runtime components such as
  `org.gnustep.runtime.base`, `org.gnustep.runtime.gui`, and
  `org.gnustep.runtime.back`; headless packages should be allowed to require
  only Base when they do not need AppKit or display backends
- component requirements are currently recorded under package `requirements`
  and artifact-level runtime profile metadata rather than enforced through the
  `dependencies` array; `dependencies` is still interpreted by the native
  installer as already-installed package IDs
- before runtime components become automatic install dependencies, the package
  manager needs a virtual/provided-package model so a managed toolchain,
  platform package set, or future split runtime package can satisfy
  `org.gnustep.runtime.base` without forcing `org.gnustep.runtime.gui` and
  `org.gnustep.runtime.back`

## Runtime Component Policy

- Support installing GNUstep Base without GNUstep GUI or Back.
- Treat `org.gnustep.runtime.base` as the minimum runtime component for
  headless services, command-line tools, frameworks, and server workloads.
- Treat `org.gnustep.runtime.gui` and `org.gnustep.runtime.back` as explicit
  GUI/runtime-display requirements, not as implicit dependencies of every
  GNUstep package.
- GUI applications such as Gorm should require `org.gnustep.runtime.base`,
  `org.gnustep.runtime.gui`, and `org.gnustep.runtime.back`.
- Server-side packages such as the initial Arlen package should default to a
  headless Base-only runtime profile. GUI adapters or tooling can be modeled as
  optional features or separate packages that add GUI/Back requirements.

## Build Infrastructure

- the initial build matrix is explicit and matches the Tier 1 target policy
- official package binaries should be produced by project-controlled builds
  from reviewed source provenance and package metadata, not accepted as opaque
  maintainer-provided binaries by default
- package artifact publication should record source identity, build identity,
  checksums, signatures, and target compatibility in the generated index or
  associated release metadata
- the first Arlen and Gorm Linux `amd64/clang` artifacts are now hosted on the
  `v0.1.0` release, recorded with verified SHA-256 digests, and marked
  publishable in the generated package index after source-built OTVM package
  builds plus local install/remove validation
- signed `package-index.json` and `package-index-provenance.json` assets are
  hosted on the `v0.1.0` release; the package-index CI signing lane passed on
  `master`, and the matching `package-index-signing-public.pem` is also hosted
  as explicit release trust material so consumers can verify package-index
  signatures without downloading workflow artifacts
- the release workflow now promotes the package-index signing public key beside
  the signed package-index assets, and `verify-release` rejects promoted
  package-index metadata when it cannot verify with that bundled public key
- Linux arm64 VM access is available through the OTVM OCI
  `ubuntu-24.04-aarch64` profile; May 5, 2026 acceptance lease
  `lease-20260505191156-s29xph` validated SSH access and `aarch64`
  architecture and destroyed successfully
- release manifests can be generated from that matrix
- the `Package App Artifact` workflow is the controlled CI entrypoint for
  managed Unix-style Arlen/Gorm package artifact builds from explicit toolchain
  URLs and SHA256s, or from a prior workflow artifact containing
  `gnustep-toolchain-*.tar.gz`; Windows/MSYS2 package artifacts still require a
  separate Windows target workflow because Gorm publication needs GUI
  launch/screenshot evidence
- the `Linux Managed Artifacts` workflow is the controlled CI entrypoint for
  source-built Linux managed toolchain plus full CLI artifact production. It
  supports Linux amd64, Ubuntu 24.04 amd64, and Linux arm64 target ids, enforces
  runner architecture before building, and uploads the managed toolchain, full
  CLI, SHA256SUMS, and build reports for downstream package builds.
- `scripts/internal/admin.py` is the internal operator control plane for this
  build infrastructure. It can inventory the current package/toolchain/release
  metadata, compare pinned upstream sources against explicit freshness data,
  report remaining release gaps, generate GitHub Actions/OTVM build plans, and
  dry-run or apply unblocked `gh workflow run` dispatches. Package artifact
  dispatches stay blocked until the operator supplies either a managed
  toolchain URL plus SHA256 or a workflow artifact run id, matching the
  controlled workflow contracts.

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
- initial `tools-xctest` package targets are Debian Linux `amd64/clang`, Ubuntu Linux `amd64/clang`, Debian Linux `arm64/clang`, OpenBSD `amd64/clang`, OpenBSD `arm64/clang`, and Windows `amd64/msys2-clang64`; all targets remain `publish: false` until rebuilt with declared patches and host-validated
- `scripts/internal/build_infra.py --json tools-xctest-release-gate --packages-dir packages --evidence-dir <evidence-dir>` is the Phase 24 package lifecycle gate; it blocks release claims while artifacts predate declared patches, planned artifacts lack verified digests, or native install/smoke/remove evidence has not been collected
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
