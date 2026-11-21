# v0.1.11 release evidence

**Release under test:** stage-release run 44836191930.
- Channel `stable`, version `0.1.11`.
- **18 artifacts**, staged from `229852c`.
- The package index, the 19th manifest entry, is added by the Release workflow.

**What v0.1.11 is** (Dan's decisions on AIManager asks #9133, #9153, #9159, #9171 and #9197):
- **Windows patch layer:** 24 carries (v0.1.10's 18, plus):
  - #94: Command-modifier key bindings, so Ctrl+arrow word moves work;
  - #99 (CocoaTerminal): NSOpenGLView child windows hide, clip and clean up;
  - #100 (CocoaTerminal): dead keys compose.
- **Linux patch layer:** 17 carries (v0.1.10's 11 plus #102 for CocoaTerminal): NSOpenGLView visibility on X11, and OpenGL loaded at run time. The back end doesn't link libGL; without libGL, apps still start and OpenGL reports unavailable.
- **Release tooling (#101):** SHA256SUMS now matches the re-signed provenance. It was stale since v0.1.8.
- **The toolchains are v0.1.9's/v0.1.10's, unchanged.** The package index is unchanged (Arlen 0.3.2, tools-xctest 0.8.1).

> **Status: complete.** Every planned check has run and passed. The Windows checks ran on
> GitHub-hosted `windows-latest` runners, as a standard (non-admin) user where a user installs.
> Dan authorized building, staging and testing (no publishing) in AIManager ask #9197.
> This PR stays unmerged until the release is published.

## Artifacts and their sources

| Artifact | sha256 | Source |
|---|---|---|
| cli linux-amd64-clang | `c2cc10d5…` | run 44826137722 (229852c) |
| toolchain linux-amd64-clang | `2188143b…` | run 44826137722: the **v0.1.9/v0.1.10 toolchain, byte-identical** (`reuse_toolchain_tag=v0.1.10`) |
| carry-layer linux-amd64-clang | `764d72f2…` | run 44826215228 (Linux Patch Layer, release `0.1.11`), requires toolchain `2188143b` |
| cli linux-ubuntu2404-amd64-clang | `b59defc7…` | run 44826158549 (229852c) |
| toolchain linux-ubuntu2404-amd64-clang | `a6eb7a56…` | run 44826158549: the **v0.1.9/v0.1.10 toolchain, byte-identical** (`reuse_toolchain_tag=v0.1.10`) |
| carry-layer linux-ubuntu2404-amd64-clang | `e39bf53a…` | run 44826215228 (Linux Patch Layer, release `0.1.11`), requires toolchain `a6eb7a56` |
| cli linux-ubuntu2604-amd64-clang | `bbc6ab9c…` | run 44826181254 (229852c) |
| toolchain linux-ubuntu2604-amd64-clang | `99ed2d21…` | run 44826181254: the **v0.1.9/v0.1.10 toolchain, byte-identical** (`reuse_toolchain_tag=v0.1.10`) |
| carry-layer linux-ubuntu2604-amd64-clang | `e76cf28f…` | run 44826215228 (Linux Patch Layer, release `0.1.11`), requires toolchain `99ed2d21` |
| cli linux-ubuntu2404-arm64-clang | `22c6825e…` | run 44826170059 (229852c) |
| toolchain linux-ubuntu2404-arm64-clang | `93f45413…` | run 44826170059: the **v0.1.9/v0.1.10 toolchain, byte-identical** (`reuse_toolchain_tag=v0.1.10`) |
| carry-layer linux-ubuntu2404-arm64-clang | `87d3e979…` | run 44826215228 (Linux Patch Layer, release `0.1.11`), requires toolchain `93f45413` |
| cli linux-arm64-clang | `93db2fac…` | run 44826147844 (229852c) |
| toolchain linux-arm64-clang | `548e08ba…` | run 44826147844: the **v0.1.9/v0.1.10 toolchain, byte-identical** (`reuse_toolchain_tag=v0.1.10`) |
| carry-layer linux-arm64-clang | `f7a268c4…` | run 44826215228 (Linux Patch Layer, release `0.1.11`), requires toolchain `548e08ba` |
| cli windows-amd64-msys2-clang64 | `81799e4e…` | run 44826190974 (229852c) |
| toolchain windows-amd64-msys2-clang64 | `017facad…` | run 44826190974: the **v0.1.9/v0.1.10 toolchain, byte-identical** (`toolchain_source=existing-zip`) |
| carry-layer windows-amd64-msys2-clang64 | `bace24a1…` | run 44830782884 (Windows Patch Layer, release `0.1.11`), requires toolchain `017facad` |

**Toolchains:** all six equal v0.1.9's and v0.1.10's published shas.

**Linux:** every Linux CLI and toolchain sha equals the sha its container qualification tested (`linux-smoke-report.json`, `evidence.derived_from`).

**Patch layers:** each requires its target's toolchain, and staging and `verify-release` check every replaced file's `stock_sha256`.
- **Linux:** 4 files each: the back bundle and the three libgnustep-gui copies.
- **Windows:** gnustep-base, gnustep-gui, the back bundle and gpbs.
- **Pre-merge verification:**
  - the Windows carries were built together before merging: runs 44796818647 (#94 + #99) and 44819766515 (+ #100);
  - cocoa-terminal's acceptance on those exact layers: COTGLCheck 12/14 (stock 8/14; 2 inherent child-window gaps), with dead keys composing é, ', 'x, a and ä (stock gives ''e);
  - #102's Linux layer runs: 44814445988 and 44817958900.

## Bootstraps (stamped from `229852c`, only line 6 differs)

| File | sha256 |
|---|---|
| `gnustep-bootstrap.sh` | `bbfe4e9451aaf5f1590ab843cd7856c83f3b44ca78414da570760deebb416b81` |
| `gnustep-bootstrap.ps1` | `9fe0a9fe2742f36cc3efd5c8e7a73528e4f325df78b1d54749a8336fdc5bf700` (every Windows gate checks this digest) |

## Evidence files

| File | Source |
|---|---|
| `linux-*-container-qualification.json` (5) | The container-qualification artifact of each Linux run above. Each is `ok: true`, every step exits 0, and `tls_no_ca` exits 1 as expected. |
| `linux-smoke-report.json` | Derived from the five qualifications (`evidence.derived_from`). |
| `linux-carry-layer-tests.txt` | Run 44826215228, per target: the carried tests on Xvfb, first on stock, then with the layer (all pass, 0 failed, 0 skipped: 15 tests, including openglSubwindow 29, openglLoad 7, visibility 6, shadowmargin 23), then with **libGL removed** (non-GL tests pass; GL tests skip with one "OpenGL is unavailable"). No libGL in the back bundle's NEEDED. |
| `linux-variant-gate.txt` | Run 44826215228, variant-gate job, in a clean debian:13 with exactly the bootstrap's host prerequisites: bootstrap `--variant patched`, round trips with a byte-identical stock tree, update keeping patched. The gate uses its own fixed X/Y labels. |
| `linux-update-rehearsal.txt` | The local release-path and update rehearsal. After signing, every SHA256SUMS line verifies (#101). |
| `windows-current-source-artifact.json` | Run 44826190974, byte-identical to the staged marker (source revision `229852c`). |
| `windows-full-tier1-core-report.json`, `windows-full-release-evidence.json` | Gate run 44836964191, tier1, as a standard user: 4/4. The originals hash to `eacd3329…` and `5c39d069…`. |
| `windows-arlen-check.txt` | The same job: Arlen install and remove, no leftovers (`f767f620…`). |
| `windows-toolchain-smoke-check.txt`, `windows-toolchain-post-checks.txt` | Gate run 44836964191, toolchain smoke on a fresh staged install. The originals (the first is UTF-16) hash to `fbbc42da…` and `33d6216d…`. |
| `windows-update-gate-a.json`, `.txt` | Gate A: **a v0.1.10 install upgraded to the staged 0.1.11 by its own CLI**, with A0, C2 and C (`4dfc1ea8…`, `cc6d4453…`). |
| `windows-update-gates-bn.json`, `.txt` | Gates B and N: v0.1.5 → production Latest 0.1.10 by the staged CLI; then `update cli` does nothing (`eabd8e32…`, `0d39d61b…`). |
| `windows-self-update-gate.json`, `.txt` | Gate S: the staged 0.1.11 updates its own root to the same artifacts as 0.1.12 (`e11470a3…`, `e4e468d2…`). |
| `windows-variant-gate.json`, `.txt` | The variant job on the staged release: bootstrap patched, round trips with a byte-identical stock tree, update keeping patched (`44659e50…`, `b8d13eeb…`). |
| `openbsd-full-tier1-core-report.json`, `update-all-production-like.json` | **Carried forward** byte-identical. |

## Linux update rehearsal

| Check | Result |
|---|---|
| R1: v0.1.10 install, its own CLI, `--manifest` = staged 0.1.11 | 0.1.10 → 0.1.11 |
| R3: `update --check` on it | no updates |
| R2: staged CLI, default discovery, production Latest | 0.1.5 → 0.1.10 |
| D: doctor on R1's install | integrity ok, managed root recognised |
| K: backups after the upgrade | exactly one |
| P: `--variant patched` from the staged manifest | 17 carries, all 4 files patched, doctor `ok/patched`; back to stock removes the record |
| RB: `setup --rollback` | back to 0.1.10 |

The real `~/GNUstep` was checked unchanged.

## Windows: method

Gate run 44836964191, on the unmerged branch `gate-v0111-windows` (workflow `gate-v0111-windows.yml`). Each job downloads stage-release run 44836191930, checks SHA256SUMS, and stamps the ps1 bootstrap from the git blob with the digest above. All six jobs passed on the first run.

## Not covered

- **v0.1.10 → v0.1.11 by default discovery:** checked after publishing.
- **Windows native unit tests:** CI runs the native suite on Linux.
- **tools-xctest:** unchanged, not requalified.
- **OpenBSD:** carried forward.
