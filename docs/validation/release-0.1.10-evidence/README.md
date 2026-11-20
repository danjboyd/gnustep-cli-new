# v0.1.10 release evidence

**Release under test:** stage-release run 44632748996.
- Channel `stable`, version `0.1.10`.
- **18 artifacts**, staged from `6d0bc99`.
- The package index, the 19th manifest entry, is added by the Release workflow.

**What v0.1.10 is:**
- **The Linux patch layer** (#96): an optional, signed layer for each of the five Linux targets (`gnustep setup --variant stock|patched`), carrying 11 patches. They are the two libs-gui fixes (GSTheme live switch, Command-modifier key bindings) and the X11 libs-back series (Motif hints, window types, borderless alpha, the focus-stacking fix, window shadows and rounded corners, popover shadows), on top of upstream's three no-wraster commits. It's for Invito Agent Workforce, by Dan's decisions on AIManager asks #8738 and #8806.
- **Host prerequisites** gain `unzip` and libXfixes (#97).
- **`gnustep doctor`** reports each GNUstep library's source (`managed.toolchain.sources`, #93).
- **The toolchains are v0.1.9's, unchanged.** The Windows patch layer carries the same 18 patches as v0.1.9.

> **Status: complete.** Every planned check has run and passed. The Windows checks ran on
> GitHub-hosted `windows-latest` runners, as a standard (non-admin) user where a user installs.
> Dan authorized building, staging and testing (no publishing) in AIManager ask #8942.
> This PR stays unmerged until the release is published.

## Artifacts and their sources

| Artifact | sha256 | Source |
|---|---|---|
| cli linux-amd64-clang | `9317a06e…` | run 44624812775 (6d0bc99) |
| toolchain linux-amd64-clang | `2188143b…` | run 44624812775: the **v0.1.9 toolchain, byte-identical** (`reuse_toolchain_tag=v0.1.9`) |
| carry-layer linux-amd64-clang | `69fd96b2…` | run 44624956105 (Linux Patch Layer, release `0.1.10`), requires toolchain `2188143b` |
| cli linux-ubuntu2404-amd64-clang | `de7e4550…` | run 44624837694 (6d0bc99) |
| toolchain linux-ubuntu2404-amd64-clang | `a6eb7a56…` | run 44624837694: the **v0.1.9 toolchain, byte-identical** (`reuse_toolchain_tag=v0.1.9`) |
| carry-layer linux-ubuntu2404-amd64-clang | `08e50471…` | run 44624956105 (Linux Patch Layer, release `0.1.10`), requires toolchain `a6eb7a56` |
| cli linux-ubuntu2604-amd64-clang | `454f76da…` | run 44624865246 (6d0bc99) |
| toolchain linux-ubuntu2604-amd64-clang | `99ed2d21…` | run 44624865246: the **v0.1.9 toolchain, byte-identical** (`reuse_toolchain_tag=v0.1.9`) |
| carry-layer linux-ubuntu2604-amd64-clang | `ae929400…` | run 44624956105 (Linux Patch Layer, release `0.1.10`), requires toolchain `99ed2d21` |
| cli linux-ubuntu2404-arm64-clang | `7576e227…` | run 44624850987 (6d0bc99) |
| toolchain linux-ubuntu2404-arm64-clang | `93f45413…` | run 44624850987: the **v0.1.9 toolchain, byte-identical** (`reuse_toolchain_tag=v0.1.9`) |
| carry-layer linux-ubuntu2404-arm64-clang | `1a0e4a37…` | run 44624956105 (Linux Patch Layer, release `0.1.10`), requires toolchain `93f45413` |
| cli linux-arm64-clang | `d6efdaa0…` | run 44624823276 (6d0bc99) |
| toolchain linux-arm64-clang | `548e08ba…` | run 44624823276: the **v0.1.9 toolchain, byte-identical** (`reuse_toolchain_tag=v0.1.9`) |
| carry-layer linux-arm64-clang | `72bdc6e9…` | run 44624956105 (Linux Patch Layer, release `0.1.10`), requires toolchain `548e08ba` |
| cli windows-amd64-msys2-clang64 | `7fda9ada…` | run 44624877960 (6d0bc99) |
| toolchain windows-amd64-msys2-clang64 | `017facad…` | run 44624877960: the **v0.1.9 toolchain, byte-identical** (`toolchain_source=existing-zip`) |
| carry-layer windows-amd64-msys2-clang64 | `903e555a…` | run 44626260360 (Windows Patch Layer, release `0.1.10`), requires toolchain `017facad` |

**Toolchains:** all six equal v0.1.9's published shas, so an update from v0.1.9 downloads no toolchain.

**Linux:** every Linux CLI and toolchain sha equals the sha its container qualification tested (`linux-smoke-report.json`, `evidence.derived_from`).

**Patch layers:** each has `requires_toolchain` = its target's toolchain, and staging and `verify-release` check every replaced file's `stock_sha256` against that toolchain.
- **Linux (5):** 4 files each (the back bundle and the three libgnustep-gui copies, because the packaged toolchain ships `.so`, `.so.0.32` and `.so.0.32.0` as copies). The patched bundle needs `libXfixes.so.3`.
- **Windows:** the same 18 patches and toolchain as v0.1.9, rebuilt under the 0.1.10 label. Its DLL bytes differ from v0.1.9's because the Windows builds aren't byte-reproducible. It passed the layer smoke test, the GSTheme live-switch test and the variant gate below.

## Bootstraps (stamped from `6d0bc99`, only line 6 differs)

| File | sha256 |
|---|---|
| `gnustep-bootstrap.sh` | `0d174cb23a4f2ec36c1b1305520d486fee090c0a710b820982499560e50dea7e` |
| `gnustep-bootstrap.ps1` | `b605a97cb18c5e074005175abf2dd0cda370244368b1e9bd6bc2fa2af5200cfb` (every Windows gate checks this digest) |

## Evidence files

| File | Source |
|---|---|
| `linux-*-container-qualification.json` (5) | The container-qualification artifact of each Linux run above. Each is `ok: true`, every step exits 0, and `tls_no_ca` exits 1 as expected. Tested in debian:13 (amd64, arm64), ubuntu:24.04 (amd64, arm64) and ubuntu:26.04. |
| `linux-smoke-report.json` | Derived from the five qualifications, listed with sha256 under `evidence.derived_from`. |
| `linux-carry-layer-tests.txt` | Run 44624956105: per target, the layer build and the carried patches' own tests on Xvfb. With the layer every test passes (0 failed, 0 skipped): liveSwitch 14, commandBindings 4, borderlessalpha 4, gdriverterm 1, motifhints 5, orderfocusroot 5, shadowdrawing 14, shadowmargin 23, windowterm 4, windowtype 5. The stock results show the bugs. |
| `linux-variant-gate.txt` | Run 44624956105, variant-gate job, in a clean debian:13 with exactly the bootstrap's host prerequisites: bootstrap `--variant patched`, stock ↔ patched round trips with a byte-identical toolchain after returning to stock, update keeping patched, doctor correct at every step. |
| `linux-update-rehearsal.txt` | A local rehearsal of release.yml with throwaway keys, serving the staged release on 127.0.0.1. See "Linux update rehearsal" below. Scratch paths are shown as `<scratch>`. |
| `windows-current-source-artifact.json` | Run 44624877960, byte-identical to the marker in the staged release (source revision `6d0bc99`). |
| `windows-full-tier1-core-report.json`, `windows-full-release-evidence.json` | Gate run 44634887348, tier1 job, as a standard user: 4/4 scenarios. Stored as compact UTF-8 JSON; the originals hash to `900761bc…` and `8a5eb41a…`. |
| `windows-arlen-check.txt` | The same job, right after tier1: Arlen install and remove, no leftovers. The original hashes to `8350f563…`. |
| `windows-toolchain-smoke-check.txt`, `windows-toolchain-post-checks.txt` | Gate run 44634887348, toolchain-smoke job, on a fresh staged install (gdnc, TLS, bundled authorities). The originals (the first is UTF-16) hash to `dceaf115…` and `3b979248…`. |
| `windows-update-gate-a.json`, `.txt` | Gate run 44634887348, gate A: **a v0.1.9 install upgraded to the staged 0.1.10 by its own 0.1.9 CLI**, with A0 (the candidate smoke) and C2/C (doctor). The originals hash to `7f089789…` and `6a6a1e64…`. |
| `windows-update-gates-bn.json`, `.txt` | Gate run 44634887348, gates B and N: a v0.1.5 install, using the staged CLI and default discovery, moves to production Latest 0.1.9; then `update cli` does nothing. The originals hash to `1ff3fe8e…` and `66013f14…`. |
| `windows-self-update-gate.json`, `.txt` | Gate run 44634887348, gate S: the staged 0.1.10 updates its own root to the same artifacts relabelled 0.1.11. The originals hash to `17b8c835…` and `622274e9…`. |
| `windows-variant-gate.json`, `.txt` | Gate run 44671389119, variant job, on the **staged** release: bootstrap `--variant patched`; stock → patched → stock using the install's own exe, with the stock tree back byte-identical; update keeps patched; doctor `ok` at every step. The originals hash to `0e490d00…` and `460f6076…`. |
| `openbsd-full-tier1-core-report.json` | **Carried forward** byte-identical, as in v0.1.2–v0.1.9. v0.1.10 ships no OpenBSD artifacts. |
| `update-all-production-like.json` | **Carried forward** byte-identical, as in v0.1.4–v0.1.9. |

## Linux update rehearsal

Run locally with a private `HOME` and GNUstep user dirs. The real `~/GNUstep` was checked unchanged.

The rehearsal replays release.yml's commands with throwaway keys: stage (including the layers), the filtered index (Arlen 0.3.2 + tools-xctest 0.8.1, identical to v0.1.9's apart from `generated_at`), the publication gate, signing and the controlled gate. `release-evidence-bundle`, `release-claim-consistency-gate` and `immediate-rc-blocker-status` report missing evidence before this directory exists, as they did for v0.1.9.

| Check | Result |
|---|---|
| R1: v0.1.9 install, its own CLI, `--manifest` = staged 0.1.10 | 0.1.9 → 0.1.10 |
| R3: `update --check` on it | no updates |
| R2: staged CLI, default discovery, production Latest | 0.1.5 → 0.1.9 |
| D: doctor on R1's install | `managed.install.integrity` ok, managed root recognised |
| K (#81): backups beside R1's root after the upgrade | exactly one |
| P (new): `setup --variant patched` on R1's install from the staged manifest | 11 carries, all 4 files patched, doctor `ok/patched`; `--variant stock` removes the record |
| RB (#85): `setup --rollback` on R1's install | back to 0.1.9, and the CLI runs |

## Windows: method

- **Runners:** GitHub-hosted `windows-latest`, through the temporary workflow `gate-v0110-windows.yml` on the unmerged branch `gate-v0110-windows`.
- **Inputs:** each job downloads stage-release run 44632748996's `gnustep-staged-release`, checks `SHA256SUMS`, and stamps `gnustep-bootstrap.ps1` from the git blob, checking the digest above. Installs from the staged manifest use a throwaway signing key with `RELEASE_TRUST_ROOT` (update and variant gates), or `GNUSTEP_BOOTSTRAP_ALLOW_UNSIGNED=1` for that one setup (tier1, toolchain smoke).
- **Standard user:** tier1, Arlen and the toolchain smoke run as a fresh local user that isn't in Administrators.
- **Harness fix during this run** (the product didn't change): the variant job first checked for 0.1.10 after updating to this branch's manifest Y, which is 0.1.11. Every step had passed; it was rerun to a pass on the same staged release (run 44671389119).

## Not covered

- **v0.1.9 → v0.1.10 by default discovery:** it needs v0.1.10 to be Latest, so it's checked after publishing.
- **Windows native unit tests:** CI runs the native suite on Linux.
- **tools-xctest:** unchanged (0.8.1, the same index entry and bytes as v0.1.9), so not requalified.
- **App-level evaluation of the Linux layer** (LinDirStat, Invito Agent Workforce screenshots): after publishing.
- **OpenBSD:** carried forward.
