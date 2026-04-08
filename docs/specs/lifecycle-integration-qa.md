# Lifecycle, Integration, And QA Baseline

This document records the current Phase 13-15 baseline.

## Lifecycle

- managed CLI state is stored under `<managed-root>/state/cli-state.json`
- upgrade planning is explicit rather than implicit
- repair scans ensure required managed directories exist and clear stale staging data

## Integration Polish

- Linux desktop-entry generation is standardized through shared metadata helpers
- Windows shortcut metadata generation is standardized through shared metadata helpers
- GUI package integration validation is enforced through shared checks

## Hardening And QA

- package extraction now uses the `tarfile` data filter for safer extraction behavior
- a regression-suite helper exists to run the repo's automated tests as a release-gating action
- the project now has explicit lifecycle, integration, and QA helpers rather than relying solely on roadmap prose

