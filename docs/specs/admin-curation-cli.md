# Admin Curation CLI

The repository now has an internal operator CLI at
`scripts/internal/admin.py`. It is not part of the user-facing `gnustep`
command contract. Its job is to keep binary curation, upstream freshness,
package artifact planning, release evidence, and scheduled checks in one
machine-readable control surface.

## Goals

- inventory the binaries and metadata currently served for each supported
  platform, architecture, toolchain flavor, and package
- compare pinned upstream package/toolchain sources against explicit
  comparison data, or against upstream Git `HEAD` when the operator requests a
  network fetch
- report the remaining release gaps that matter to the project goals:
  production trust, final hosted evidence, source/package freshness, and
  build-operation automation
- produce build plans that map publishable targets to the existing GitHub
  Actions workflows or to OTVM-backed lanes
- produce dry-run or applied `gh workflow run` dispatches without inventing
  workflow inputs that the workflows do not accept
- emit scheduler templates suitable for a cron job or systemd timer

## Commands

- `inventory`
  Reads package manifests, `packages/package-index.json`, optional release
  manifests, toolchain metadata, and the build matrix.
- `upstream-check`
  Compares package `source` records and toolchain `source-lock.json`
  components against an operator-supplied JSON cache. `--fetch` may use
  `git ls-remote` for sources with `upstream_url`, `upstream`, or `url`.
  Unknown comparison data is reported as `status: warning`; it is not treated
  as proof that a pin is current.
- `upstream-sources`
  Lists every package and toolchain source pin that needs upstream comparison
  data. Use this output to build or review the upstream freshness cache.
- `gap-report`
  Emits the current primary release/project gaps and the next operator actions.
  Missing proof is an actionable blocker: production trust requires a release
  directory, package index, release trust root, and package-index trust root;
  final hosted evidence requires release/evidence inputs; scheduling and native
  doctor parity require explicit evidence JSON.
- `build-plan`
  Maps source-built Linux and Windows targets to workflow dispatch records and
  maps OpenBSD targets to OTVM-backed build requirements. Package artifacts are
  included, but Unix package builds are marked blocked until the operator
  supplies either a managed toolchain URL/checksum or a workflow artifact run
  id. This prevents invalid workflow dispatches.
- `dispatch-builds`
  Produces the exact `gh workflow run` commands in dry-run mode by default.
  `--apply` executes only unblocked dispatches.
- `doctor-parity`
  Compares captured native and shared `doctor --json` payloads and writes the
  `ok:true` evidence expected by `gap-report --doctor-parity-evidence`.
- `schedule-template`
  Emits systemd service/timer and cron templates for recurring checks.

## JSON Contract

Every command emits a shared envelope:

```json
{
  "schema_version": 1,
  "command": "build-plan",
  "ok": true,
  "status": "ok",
  "summary": "...",
  "inputs": {},
  "findings": [],
  "actions": []
}
```

Human-readable output is only an operator convenience. Automation should use
`--json` and consume the structured fields directly.

## Scheduling

The intended recurring check is:

```sh
scripts/internal/admin.py --json gap-report
```

The first production scheduler is `.github/workflows/admin-curation.yml`. It
runs daily and by manual dispatch, uploads inventory/upstream/gap JSON reports,
and fails when `gap-report` still has actionable errors. It also writes
`scheduler-evidence.json`, which is the proof input used to clear
`admin_automation_not_scheduled`. Scheduled runs fetch upstream Git HEAD
revisions by default; manual dispatch can disable that fetch when reviewing
only local metadata.

Final closure should call `gap-report` with the same proof inputs used by the
release workflow:

```sh
scripts/internal/admin.py --json gap-report \
  --release-dir dist/stable/0.1.0 \
  --evidence-dir .artifacts/hosted-release-evidence \
  --package-index packages/package-index.json \
  --release-trust-root /path/to/release-trust-root.pem \
  --package-index-trust-root /path/to/package-index-trust-root.pem \
  --smoke-report .artifacts/hosted-release-evidence/openbsd-full-tier1-core-report.json \
  --smoke-report .artifacts/hosted-release-evidence/windows-full-tier1-core-report.json \
  --update-all-evidence .artifacts/hosted-release-evidence/update-all-production-like.json \
  --scheduler-evidence .artifacts/admin-curation/scheduler-evidence.json \
  --doctor-parity-evidence .artifacts/hosted-release-evidence/doctor-parity.json
```

Build dispatch should normally remain dry-run until the operator has reviewed
the generated action list and supplied any required toolchain artifact inputs.
For Unix package builds, pass either `--toolchain-artifact-run-id` or
`--toolchain-url` plus `--toolchain-sha256` so the package workflow can build
against the exact managed toolchain artifact being promoted.
