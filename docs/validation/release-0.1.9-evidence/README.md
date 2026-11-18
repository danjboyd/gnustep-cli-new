# v0.1.9 release evidence

**Release under test:** stage-release run 44386009191.
- Channel `stable`, version `0.1.9`.
- **13 artifacts**, staged from `314248b`.
- The package index, the 14th manifest entry, is added by the Release workflow.

**What v0.1.9 is:**
- **The patch layer:** a stock toolchain plus an optional, signed Windows patch layer, chosen with `gnustep setup --variant stock|patched` (#86, #88).
- **Rollback on Windows** works (#85).
- **One backup per upgrade:** each upgrade keeps a single backup (#81).
- **tools-xctest 0.8.1** enters the stable index (#79, #83, #89).

> **Status: complete.** Every planned check has run and passed. The Windows checks ran on
> GitHub-hosted `windows-latest` runners, as a standard (non-admin) user where a user installs.
> Dan authorized building, staging and testing (no publishing) in AIManager ask #8455.
> This PR stays unmerged until the release is published.

## Artifacts and their sources

| Artifact | sha256 | Source |
|---|---|---|
| cli linux-amd64-clang | `15e1125e…` | run 44377689462 (314248b) |
| toolchain linux-amd64-clang | `2188143b…` | run 44377689462 (314248b) |
| cli linux-ubuntu2404-amd64-clang | `2358346e…` | run 44377699418 (314248b) |
| toolchain linux-ubuntu2404-amd64-clang | `a6eb7a56…` | run 44377699418 (314248b) |
| cli linux-ubuntu2604-amd64-clang | `d5766fe1…` | run 44377705599 (314248b) |
| toolchain linux-ubuntu2604-amd64-clang | `99ed2d21…` | run 44377705599 (314248b) |
| cli linux-ubuntu2404-arm64-clang | `e8e189a0…` | run 44377710381 (314248b) |
| toolchain linux-ubuntu2404-arm64-clang | `93f45413…` | run 44377710381 (314248b) |
| cli linux-arm64-clang | `ee0b347e…` | run 44377694294 (314248b) |
| toolchain linux-arm64-clang | `548e08ba…` | run 44377694294 (314248b) |
| cli windows-amd64-msys2-clang64 | `0bf64714…` | run 44377715753 (314248b) |
| toolchain windows-amd64-msys2-clang64 | `017facad…` | run 44377715753 (314248b), assembled from the lock (`toolchain_source=assemble-msys2`) |
| carry-layer windows-amd64-msys2-clang64 | `7bd23d54…` | run 44379667597 (Windows Patch Layer, release `0.1.9`, built against toolchain `017facad`) |

**Linux:** the sha256 of every Linux artifact equals the sha its container qualification tested, cross-checked in `linux-smoke-report.json`'s `derived_from`.

**Windows:** the marker names the same two Windows shas.

**The patch layer** has `requires_toolchain` = `017facad…`. Its four files' `stock_sha256` match that toolchain, and staging and `verify-release` both check this.
- **Contents:** 18 carried patches:
  - 13 libs-back;
  - 4 libs-gui (including #88's GSTheme live-switch fix);
  - 1 libs-base.
- **ABI check:** no removed export. The added symbols are `GSThemeInstallBackendDefaults`, the `GSThemeMethod.types` ivar offset, and two WIN32Server ivar offsets.
- **GSTheme live-switch test** (`liveSwitch.m`): passes 14/14 on the patched root. Stock fails 10/14, which is the bug.

## Bootstraps (stamped from `314248b`, only line 6 differs)

| File | sha256 |
|---|---|
| `gnustep-bootstrap.sh` | `3fca82d1b20f58af3bd97ef84c7991e8d0061be80eddc613d3b3b47c6e6a6895` |
| `gnustep-bootstrap.ps1` | `4d39c0e45c618dd38dad533bdc6decd9a4b4cbd92b913084b1d75043298e7bf7` (every Windows gate checks this digest) |

## What changed

- **Patch layer (#86, #88), Windows only:**
  - **Choosing a variant:**
    - `gnustep setup --variant patched` swaps in rebuilt `gnustep-base`, `gnustep-gui`, the back bundle DLL and `gpbs.exe`, after checking every file's stock sha.
    - `--variant stock` restores the saved stock files.
    - Both work on an existing install without reinstalling.
  - **Other commands:**
    - the bootstraps take `--variant`;
    - `update` keeps the variant;
    - `doctor` reports it (`managed.toolchain.variant`) and flags a mixed install.
  - **Patch collection:** the patches ScreenshotTool, ObjcMarkdown and LinDirStat carried are collected under `toolchains/carry`, with a submission protocol (`docs/carried-patches`).
- **Rollback (#85):** on Windows, `setup --rollback` swaps the roots instead of deleting the running one, so it no longer fails with exit 1.
- **Backups (#81):** each upgrade keeps only the backup that rollback uses, and `doctor` lists older backups.
- **tools-xctest 0.8.1 (#89, merge before Release):** the six artifacts become v0.1.9 assets in the stable index. The package ships `xctest.make` and `xctest-bundle` (#83).

## Evidence files

| File | Source |
|---|---|
| `linux-*-container-qualification.json` (5) | The container-qualification artifact of each Linux run above. Each is `ok: true`, every step exits 0, and `tls_no_ca` exits 1 as expected (the same as v0.1.8). Tested in debian:13 (amd64 and arm64), ubuntu:24.04 (amd64 and arm64) and ubuntu:26.04. |
| `linux-smoke-report.json` | Derived from the five qualifications, listed with sha256 under `evidence.derived_from`. |
| `linux-update-rehearsal.txt` | A local rehearsal of release.yml with throwaway keys, serving the staged release on 127.0.0.1. See "Linux update rehearsal" below. Scratch paths are shown as `<scratch>`. |
| `windows-current-source-artifact.json` | Run 44377715753, byte-identical to the marker in the staged release (source revision `314248b`). |
| `windows-full-tier1-core-report.json`, `windows-full-release-evidence.json` | Gate run 44388080146, tier1 job, as a standard user. Stored as compact UTF-8 JSON; the UTF-8-BOM originals hash to `74ac877b…` and `4f0dbb76…`. |
| `windows-arlen-check.txt` | The same job, right after tier1, on the same install. Plain UTF-8; the original hashes to `1b9d1c36…`. |
| `windows-toolchain-smoke-check.txt`, `windows-toolchain-post-checks.txt` | Gate run 44388080146, toolchain-smoke job, on a fresh staged install (gdnc, TLS). The originals hash to `c51d6379…` and `88986557…`. |
| `windows-update-gate-a.json`, `.txt` | Gate run 44394563055, gate A: **a v0.1.8 install upgraded to the staged 0.1.9 by its own 0.1.8 CLI**, with A0 (the candidate smoke) and C2/C (doctor). The originals hash to `7e5e6bff…` and `39bb1688…`. |
| `windows-update-gates-bn.json`, `.txt` | Gate run 44394563055, gates B and N: a v0.1.5 install, using the staged CLI and default discovery, moves to production Latest 0.1.8; then `update cli` does nothing. The originals hash to `e28a63a1…` and `bddb97ff…`. |
| `windows-self-update-gate.json`, `.txt` | Gate run 44389069521, gate S: the staged 0.1.9 updates its own root to the same artifacts relabelled 0.1.10. The originals hash to `eca93876…` and `a31f02ea…`. |
| `windows-variant-gate.json`, `.txt` | Gate run 44388080146, variant job, on the **staged** release. The originals hash to `5d6cca3a…` and `7b174d0e…`. The job: <ul><li>bootstraps with `--variant patched`;</li><li>switches stock → patched → stock using the install's own exe, which has the patched DLL loaded, and the stock tree comes back byte-identical;</li><li>updates to 0.1.10 and keeps the patched variant;</li><li>runs doctor `ok` at every step.</li></ul> |
| `openbsd-full-tier1-core-report.json` | **Carried forward** byte-identical, as in v0.1.2–v0.1.8. v0.1.9 ships no OpenBSD artifacts. |
| `update-all-production-like.json` | **Carried forward** byte-identical, as in v0.1.4–v0.1.8. |

**tools-xctest:** the six package qualifications on the staged CLI and toolchain (run 44402406762) are in `docs/validation/tools-xctest-v0.8.1-on-v0.1.9-20261118/` (PR #89). All six pass 9/9.

## Linux update rehearsal

Run locally with a private `HOME` and GNUstep user dirs. The real `~/GNUstep` was checked unchanged.

The rehearsal replays release.yml's commands with throwaway keys:
- stage, including the layer;
- the filtered index;
- the publication gate;
- signing;
- the controlled gate.

`release-evidence-bundle`, `release-claim-consistency-gate` and `immediate-rc-blocker-status` report missing evidence before this directory exists, as they did for v0.1.8.

| Check | Result |
|---|---|
| R1: v0.1.8 install, its own CLI, `--manifest` = staged 0.1.9 | 0.1.8 → 0.1.9 |
| R3: `update --check` on it | no updates |
| R2: staged CLI, default discovery, production Latest | 0.1.5 → 0.1.8 |
| D: doctor on R1's install | `managed.install.integrity` ok, managed root recognised |
| K (#81): backups beside R1's root after the upgrade | exactly one |
| RB (#85): `setup --rollback` on R1's install | back to 0.1.8, and the CLI runs |

## Windows: method

- **Runners:** GitHub-hosted `windows-latest`, through the temporary workflows `gate-v019-windows.yml` and `gate-v019-tools-xctest.yml` on the unmerged branch `gate-v019-windows`.
- **Inputs:** each job downloads stage-release run 44386009191's `gnustep-staged-release` and checks `SHA256SUMS`.
  - It stamps `gnustep-bootstrap.ps1` from the git blob and checks the digest above.
  - The staged manifest isn't production-signed before Release. Installs from it use either a throwaway signing key with `RELEASE_TRUST_ROOT` (the update and variant gates), or `GNUSTEP_BOOTSTRAP_ALLOW_UNSIGNED=1` for that one setup (tier1, toolchain smoke).
- **Standard user:** tier1, Arlen, the toolchain smoke and tools-xctest run as a fresh local user that isn't in Administrators (medium integrity), as for v0.1.8.
- **Harness fixes during this run** (the product didn't change):
  - **Gate S** first failed because the gate stamped manifest Y with a fixed `generated_at` earlier than the staged manifest's. The CLI rightly refused Y as older.
  - **Gate A0** first compared the version with a pattern left at `0.1.8`. Gate A itself had passed.
  - **The Linux tools-xctest jobs** first read `package.json` from the wrong directory, then lacked the sudo rule the dogfood had for host prerequisites.
  
  Each was rerun to a pass on the same staged release.

## Not covered

- **v0.1.8 → v0.1.9 by default discovery:** it needs v0.1.9 to be Latest, so it's checked after publishing.
- **Windows native unit tests:** CI runs the native suite on Linux (100 tests passed on #86's final commit).
- **OpenBSD:** carried forward.
- **A Linux patch layer:** none ships in v0.1.9. LinDirStat is evaluating one afterwards.
