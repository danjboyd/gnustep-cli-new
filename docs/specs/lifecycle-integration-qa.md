# Lifecycle, Integration, And QA Baseline

This document records the current Phase 13-15 baseline.

## Lifecycle

- managed CLI state is stored under `<managed-root>/state/cli-state.json`
- upgrade planning is explicit rather than implicit
- update checks are read-only and compare installed state against the signed release manifest
- update checks reject downgrade, expired, revoked-artifact, and frozen older-metadata manifests using persisted lifecycle state
- CLI/toolchain upgrades are staged, verified, smoke-validated, rollback-capable lifecycle operations exposed through full `gnustep update cli`
- `setup --rollback` currently restores the preserved previous managed release after an upgrade when rollback state is available; this remains a lifecycle recovery command while `update` becomes the normal update UX
- repair scans ensure required managed directories exist and clear stale staging data
- versioned install layouts with a stable `current` pointer are used instead of activating by mutating the root launcher in place

## Integration Polish

- Linux desktop-entry generation is standardized through shared metadata helpers
- Windows shortcut metadata generation is standardized through shared metadata helpers
- GUI package integration validation is enforced through shared checks

## Hardening And QA

- package extraction now uses the `tarfile` data filter for safer extraction behavior
- a regression-suite helper exists to run the repo's automated tests as a release-gating action
- the project now has explicit lifecycle, integration, and QA helpers rather than relying solely on roadmap prose
- the regression gate now has two required layers:
  - the Python/shared test suite under `tests/`
  - the native Objective-C `tools-xctest` suite for `src/full-cli`
- Objective-C unit and regression coverage should be added to the native
  `tools-xctest` suite rather than being represented only by Python source-text
  assertions
- upgrade tests should cover stale manifests, downgrade attempts, frozen older
  metadata, interrupted staging, failed activation, update planning, package upgrades, rollback, repair, and
  successful old-to-new RC transitions in isolated prefixes

## Comprehensive Coverage Requirement

- Lifecycle features are not complete until their read-only plan, successful apply, no-op/idempotent, usage-error, compatibility-error, and rollback/error paths have automated coverage.
- Native full-CLI lifecycle behavior must be covered in `tools-xctest`, including direct Objective-C unit tests for state transitions and built-executable smoke tests before release qualification.
- `gnustep update` coverage must include all scopes and modes: default `all` planning, `--check`, `cli`, `packages`, and coordinated `all` application.
- Every lifecycle bug found during dogfood or host-backed validation must add a regression test or carry an explicit automation blocker in the roadmap.
