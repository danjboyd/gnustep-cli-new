# v0.1.2 release evidence

Release under test: stage-release run 39463710637 (channel `stable`, version
`0.1.2`, 10 artifacts). v0.1.2 adds Ubuntu 24.04 amd64
(`linux-ubuntu2404-amd64-clang`, ICU 74, glibc 2.39) and rebuilds every other
CLI stamped 0.1.2. All other toolchains are the v0.1.1 assets, unchanged.

## Artifacts and their sources

| Artifact | sha256 | Source |
|---|---|---|
| cli linux-amd64-clang | `247b21b2…` | Linux Managed Artifacts run 39461501521 (f44b4f2) |
| toolchain linux-amd64-clang | `41fd4b83…` | v0.1.1 asset relabelled byte-identically (`reuse_toolchain_version`) |
| cli linux-arm64-clang | `4bdb7d94…` | run 39461505705 (f44b4f2) |
| toolchain linux-arm64-clang | `0f8593f6…` | v0.1.1 asset, byte-identical |
| cli linux-ubuntu2604-amd64-clang | `c6f0e948…` | run 39461510853 (f44b4f2) |
| toolchain linux-ubuntu2604-amd64-clang | `1acde52f…` | v0.1.1 asset, byte-identical |
| cli linux-ubuntu2404-amd64-clang | `13a1b019…` | run 39324146937 (0dd149b) |
| toolchain linux-ubuntu2404-amd64-clang | `e2430e58…` | run 39324146937 (0dd149b), new target |
| cli windows-amd64-msys2-clang64 | `be98f9c6…` | Windows Current Source Artifacts run 39462285990 (fbb5817) |
| toolchain windows-amd64-msys2-clang64 | `07d57993…` | v0.1.1 asset, byte-identical (`existing-zip`, kept unchanged since PR #17) |

The 0dd149b..fbb5817 changes touch only the Windows release smoke script
(PR #16) and the Windows existing-zip packaging (PR #17), not the Linux CLI or
toolchain sources.

## Evidence files

| File | Source |
|---|---|
| `linux-*-container-qualification.json` | The container-qualification artifact of each Linux run above (debian:13 for amd64/arm64, ubuntu:26.04, ubuntu:24.04). |
| `linux-smoke-report.json` | Derived from the four container qualifications (listed with sha256 under `evidence.derived_from`); their artifact sha256s match the staged manifest. |
| `windows-current-source-artifact.json` | Run 39462285990; identical to the marker in the staged release. |
| `windows-full-tier1-core-report.json`, `windows-full-release-evidence.json` | OCI Windows Server 2022 lease `lease-20261020174817-tso6nw` via otvm-gate, run by the Markdown Viewer Windows session at ReleaseCoordinator's request with Dan's approval: `scripts/dev/windows-full-release-smoke.ps1` at fbb5817 (sha256 `40523126…`), `-ReleaseSource v0.1.2-stage-39463710637 -SuiteId tier1-core -RunnerId otvm-lease-lease-20261020174817-tso6nw`, non-elevated (scheduled task, RunLevel Limited, interactive session 1), 2026-10-20 17:58:21Z–18:17:27Z, exit 0, all four scenarios passed. Inputs: staged artifact from run 39463710637 (CLI `be98f9c6…`, toolchain `07d57993…`), stamped 0.1.2 `gnustep-bootstrap.ps1` (`16118ec3…`), Gorm patch `53a07e0f…`; `release-old` was a copy of `release-new`. JSON as relayed (compact form; the pretty-printed UTF-8-BOM originals hash to `e42ad3b1…` and `1ab57398…`). |
| `openbsd-full-tier1-core-report.json` | **Carried forward from v0.1.0**, byte-identical (sha256 `67204aa2…`). v0.1.2 ships no OpenBSD artifacts; the gate still requires the report. |
| `update-all-production-like.json` | **Carried forward from v0.1.0**, byte-identical (sha256 `6b4003ee…`). Not rerun against v0.1.2. |

## Pre-publication gate dry run (local, unsigned staged dir)

- `verify-release`: ok.
- `release-claim-consistency-gate`: ok.
- `run-smoke-tests.py --release-gate release-candidate` (OpenBSD + Windows reports): ok.
- `validate-update-all-evidence`: ok.

## Notes on the Windows run (not gate failures)

- `doctor_status` is `error` after the bootstrap install ("A GNUstep toolchain was
  detected, but it is incompatible with the selected managed artifacts";
  `toolchain.probe` not run). v0.1.1's run on the Arlen VM reported `ok`. No CLI,
  bootstrap or Windows toolchain bytes changed between the two (`git diff
  d66adff fbb5817 -- src/ scripts/bootstrap/` is empty; toolchain `07d57993…` in
  both), so the difference is the host: a fresh lease, with the smoke's PATH
  update skipped, versus a VM with a persistent GNUstep environment. To follow up
  as a doctor issue; the smoke asserts only the doctor JSON envelope.
- The self-update summary reads "CLI and toolchain update completed." although the
  plan was `cli_only`. v0.1.1's evidence has the same text; cosmetic.
