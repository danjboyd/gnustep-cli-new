# Production-Like Update All Evidence

This runbook defines the evidence file required by the Phase 13 hardening gate
for a production-like `gnustep update all --yes` run.

## Required Evidence Shape

The evidence JSON must report a real managed install that exercised all update
scopes: CLI, toolchain, and packages. The Phase 13 gate rejects a bare
`{"ok": true}` payload.

```json
{
  "schema_version": 1,
  "ok": true,
  "summary": "gnustep update all --yes passed on a production-like managed install.",
  "production_like": true,
  "command": "gnustep update all --yes",
  "target": "windows-amd64-msys2-clang64",
  "lease_id": "lease-...",
  "started_at": "2026-04-27T00:00:00Z",
  "completed_at": "2026-04-27T00:00:00Z",
  "scopes": {
    "cli": true,
    "toolchain": true,
    "packages": true
  },
  "release_transition": {
    "from_version": "0.1.0-dev-dogfood.previous",
    "to_version": "0.1.0-dev-dogfood.current"
  },
  "package_updates": [
    {
      "id": "org.gnustep.tools-xctest",
      "from_version": "0.1.0-dev.previous",
      "to_version": "0.1.0-dev.current",
      "ok": true
    }
  ],
  "result": {
    "ok": true,
    "exit_code": 0
  },
  "artifacts": {
    "stdout": "update-all.stdout.log",
    "stderr": "update-all.stderr.log",
    "state_before": "cli-state-before.json",
    "state_after": "cli-state-after.json"
  }
}
```

## Gate Command

Run the Phase 13 gate with the update evidence and the accepted Tier 1 smoke
reports:

```sh
python3 scripts/internal/build_infra.py --json phase13-update-hardening-status \
  --release-dir .artifacts/local-dogfood-refresh/dogfood/0.1.0-dev-dogfood.20260427T162104Z.g31c1872c5dfd.28 \
  --smoke-report .artifacts/phase26-openbsd-tier1-20260424/openbsd-tier1-report.json \
  --smoke-report .artifacts/phase26-windows-gorm-patched-20260424/windows-tier1-report-patched-gorm.json \
  --update-all-evidence path/to/update-all-production-like.json
```

## Acceptance Notes

- The run must use a managed install with published or production-like signed
  metadata.
- The package update must install or update at least one real package entry;
  `org.gnustep.tools-xctest` is the current preferred package fixture.
- Record the install state before and after the command so rollback and
  pointer-state regressions can be diagnosed later.
- Keep stdout, stderr, command exit code, lease metadata, and release/package
  versions with the evidence bundle.
