# v0.1.3 release evidence

Release under test: stage-release run 39863701167 (channel `stable`, version
`0.1.3`, 10 artifacts, source `0bd97f9`). v0.1.3 rebuilds the Windows
MSYS2 `clang64` toolchain (perl added; the pacman keyring is no longer
shipped) and rebuilds every CLI stamped 0.1.3. The Linux toolchains are the
v0.1.2 assets, unchanged.

## Artifacts and their sources

| Artifact | sha256 | Source |
|---|---|---|
| cli linux-amd64-clang | `a411d914…` | Linux Managed Artifacts run 39846402182 (999c39d) |
| toolchain linux-amd64-clang | `41fd4b83…` | v0.1.2 asset relabelled byte-identically (`reuse_toolchain_tag v0.1.2`) |
| cli linux-arm64-clang | `24b9378e…` | run 39846406521 (999c39d) |
| toolchain linux-arm64-clang | `0f8593f6…` | v0.1.2 asset, byte-identical |
| cli linux-ubuntu2404-amd64-clang | `a4f4dad8…` | run 39846410362 (999c39d) |
| toolchain linux-ubuntu2404-amd64-clang | `e2430e58…` | v0.1.2 asset, byte-identical |
| cli linux-ubuntu2604-amd64-clang | `c1fc731b…` | run 39846414193 (999c39d) |
| toolchain linux-ubuntu2604-amd64-clang | `1acde52f…` | v0.1.2 asset, byte-identical |
| cli windows-amd64-msys2-clang64 | `6ee7a7df…` | Windows Current Source Artifacts run 39862924821 (0bd97f9) |
| toolchain windows-amd64-msys2-clang64 | `00fee7b5…` | run 39862924821 (0bd97f9), `assemble-msys2` from the locked inputs |

999c39d..0bd97f9 changes only the Windows packaging step and a contract
test (PR #21), not the Linux CLI sources.

## Evidence files

| File | Source |
|---|---|
| `linux-*-container-qualification.json` | The container-qualification artifact of each Linux run above (debian:13 for amd64 and arm64, ubuntu:24.04, ubuntu:26.04). All steps passed, and every CLI reports 0.1.3. |
| `linux-smoke-report.json` | Derived from the four container qualifications, which are listed with their sha256 under `evidence.derived_from`. Their artifact sha256s match the staged manifest. |
| `windows-current-source-artifact.json` | Run 39862924821; identical to the marker in the staged release. |
| `windows-full-tier1-core-report.json`, `windows-full-release-evidence.json` | See the next section. The files are stored as compact UTF-8 JSON; the pretty-printed UTF-8-BOM originals hash to `26d7eb2f…` and `3e8ac9fe…`. |
| `windows-gnutar-first-check.txt` | The GNU-tar-first check on the same lease (see below). |
| `openbsd-full-tier1-core-report.json` | **Carried forward from v0.1.0 via v0.1.2**, byte-identical (sha256 `67204aa2…`). v0.1.3 ships no OpenBSD artifacts; the gate still requires the report. |
| `update-all-production-like.json` | **Carried forward from v0.1.0 via v0.1.2**, byte-identical (sha256 `6b4003ee…`). Not rerun against v0.1.3. |

### Windows tier1-core run

- Host: OCI Windows Server 2022 lease `lease-20261022222724-ns19za` via
  otvm-gate (owner windows-agent), destroyed afterwards.
- Shell: Windows PowerShell 5.1.20348, non-elevated (scheduled task, S4U,
  RunLevel Limited).
- Time: 2026-10-22, starting 22:33Z. Exit 0, all four scenarios passed.
- Command: `scripts/dev/windows-full-release-smoke.ps1` at 0bd97f9 (sha256
  `b81aecd7…`), `-ReleaseSource v0.1.3-stage-39863701167 -SuiteId tier1-core`.
- Inputs: the staged Windows CLI `6ee7a7df…` and toolchain `00fee7b5…`, the
  stamped 0.1.3 `gnustep-bootstrap.ps1` (`ef9159c6…`), and the Gorm patch
  `53a07e0f…`. `release-old` was a copy of `release-new`.
- What the scenarios showed:
  - The bootstrap refused a tampered fixture manifest (trust.verified=false)
    before the signed install.
  - Doctor in the fresh shell reported `ok` / `toolchain_compatible`.
  - The CLI reports 0.1.3.
  - The CLI-only self-update summary read "CLI update completed; the managed
    toolchain was unchanged."
- GNU-tar-first check: with the managed root's `usr\bin` first on PATH, bare
  `tar` resolved to GNU tar 1.35. The bootstrap still verified the manifest
  signature, extracted both zips and installed. perl 5.42.3 runs, and neither
  installed root contains `etc\pacman.d\gnupg`.
- The same sources and lock were also verified as 0.1.3-rc.1 (run 39830527904)
  on lease `lease-20261022193003-vgzvb5`. See PR #20.
