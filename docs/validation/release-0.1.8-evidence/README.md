# v0.1.8 release evidence

Release under test: stage-release run 43976939079 (channel `stable`, version `0.1.8`,
**12 artifacts**, staged from `5e9612f`). v0.1.8 is a CLI release: Windows upgrades work
(#77), `doctor` no longer flags every upgraded install (#76), copy and extraction errors say
why (#66, #68), and the README gains a verified install path (#70, #73). Toolchains are
rebuilt at this commit with no source changes. The Arlen-only package index is carried
forward (Package Index run 43975573558, identical to v0.1.7's apart from `generated_at`).

This replaces two earlier stagings that were never published:
- `c9abfd6` (run 43938713957): the Linux rehearsal showed `doctor` calling every upgraded
  install broken, because of the empty `.staging` that each upgrade leaves behind. Fixed by #76.
- `573b2c8` (run 43958855345): the Windows update gate showed `gnustep update` couldn't
  upgrade Windows at all when the toolchain changes, and every release so far has changed it.
  Fixed by #77.

> **Status: complete.** Every planned check has run and passed. The Windows checks ran on
> GitHub-hosted `windows-latest` runners as a standard (non-admin) local user, not on an OTVM
> lease as in v0.1.3–v0.1.7. See "Windows: method" below. This PR stays unmerged until the
> release is published.

## Artifacts and their sources

| Artifact | sha256 | Source |
|---|---|---|
| cli linux-amd64-clang | `25441125…` | run 43975597249 (5e9612f) |
| toolchain linux-amd64-clang | `ce420e28…` | run 43975597249 |
| cli linux-ubuntu2404-amd64-clang | `e377af35…` | run 43975646395 (5e9612f) |
| toolchain linux-ubuntu2404-amd64-clang | `a14c4746…` | run 43975646395 |
| cli linux-ubuntu2604-amd64-clang | `6524e046…` | run 43975668934 (5e9612f) |
| toolchain linux-ubuntu2604-amd64-clang | `a19074c9…` | run 43975668934 |
| cli linux-ubuntu2404-arm64-clang | `ec9c1777…` | run 43975691218 (5e9612f) |
| toolchain linux-ubuntu2404-arm64-clang | `77da5614…` | run 43975691218 |
| cli linux-arm64-clang | `bd889cf6…` | run 43975621080 (5e9612f) |
| toolchain linux-arm64-clang | `dc301435…` | run 43975621080 |
| cli windows-amd64-msys2-clang64 | `c48d85bd…` | run 43975713568 (5e9612f) |
| toolchain windows-amd64-msys2-clang64 | `7c18cce6…` | run 43975713568, assembled from the lock (`toolchain_source=assemble-msys2`) |

The sha256 of every Linux artifact equals the sha its container qualification tested
(cross-checked in `linux-smoke-report.json`'s `derived_from`, and against the staged manifest).
The Windows marker names the same two Windows shas.

## What changed

- **Windows upgrades (#77):** the upgrade moved the install aside, then smoke-ran the new CLI
  before the new toolchain was in place. The smoke run failed and the upgrade rolled back. This
  happened on every Windows upgrade to a release with a new toolchain, and v0.1.7's gate A
  failure was this bug. The CLI is now installed after the other layers. A reused toolchain is
  kept only when the root wasn't moved.
- **Doctor (#76):** an empty `.staging` is no longer reported as an interrupted install. Both
  the native and Python doctors.
- **Errors (#66, #68):** a failed copy reports the path, the OS reason and whether removing the
  old file failed. A failed extraction lists each extractor's error.
- Also: `gnustep run`'s reported Linux invocation (#73), manifests fetched once per update (#59),
  native integrity reads the recorded status (#58), patches listed in `source-lock.json` (#63),
  the release index guard (#69, #72, #74), and tools-xctest pinned but not in the index (#71).

## Evidence files

| File | Source |
|---|---|
| `linux-*-container-qualification.json` (5) | The container-qualification artifact of each Linux run above. All 9 steps passed in each, including SONAME checks, package install/remove and TLS. Evidence tier: a clean distro container on a GitHub runner. |
| `linux-smoke-report.json` | Derived from the five container qualifications, which are listed with sha256 under `evidence.derived_from`. |
| `windows-current-source-artifact.json` | Run 43975713568, byte-identical to the marker in the staged release (source revision `5e9612f`). |
| `windows-full-tier1-core-report.json`, `windows-full-release-evidence.json` | Gate run 44009065051, tier1 job. Stored as compact UTF-8 JSON; the UTF-8-BOM originals hash to `9a464a69…` and `8fe6370a…`. |
| `windows-arlen-check.txt` | The same job, right after tier1, on the same install. Converted to plain UTF-8; the original hashes to `077ca7a9…`. |
| `windows-toolchain-smoke-check.txt` | Gate run 44007544196, toolchain-smoke job. Converted to plain UTF-8; the original hashes to `ddaa7227…`. |
| `windows-update-gates.json`, `windows-update-gates.txt` | Gate run 43977236695, gates B and N. Converted to UTF-8 (compact JSON); the originals hash to `3fbe6a3c…` and `10eadb24…`. |
| `windows-self-update-gate.json`, `windows-self-update-gate.txt` | Gate run 43977236695, gate S on the final stage. Converted the same way; the originals hash to `70f24e79…` and `f0a77ed2…`. |
| `openbsd-full-tier1-core-report.json` | **Carried forward** byte-identical, as in v0.1.2–v0.1.7. v0.1.8 ships no OpenBSD artifacts. |
| `update-all-production-like.json` | **Carried forward** byte-identical, as in v0.1.4–v0.1.7. |

## Windows: method

- **Runners:** GitHub-hosted `windows-latest` (Windows Server 2025, image `windows-2025-vs2026` 20261103.629; not an OTVM
  lease), workflow `gate-v018-windows-update.yml` on the unmerged branch
  `gate-v018-windows-update`. It used no lease, as agreed for this release. A full lease run
  of tier1, Arlen and the update gates doesn't fit on the lease's disk.
- **Inputs:** each job downloads stage-release run 43976939079's `gnustep-staged-release`
  artifact. It stamps `gnustep-bootstrap.ps1` from the git blob at `5e9612f` and checks it
  against the digest that ships (`4bd3e6bf…`). The staged manifest isn't production-signed
  before Release. Installs from it use either a throwaway signing key with
  `RELEASE_TRUST_ROOT` (update gates) or the bootstrap's `GNUSTEP_BOOTSTRAP_ALLOW_UNSIGNED=1`
  for that one setup (tier1, toolchain smoke).
- **Standard user:** tier1, Arlen and the toolchain smoke run as a fresh local user created for
  the job. The user is not in Administrators, so its token runs at medium integrity, and
  `elevated: False` is recorded. The scheduled tasks run with `-RunLevel Limited`. To get "Log on as a batch job" for a
  scheduled task with a stored password, the user is in `Performance Log Users`, which holds
  that right by default and grants no admin rights. v0.1.7's lease checks ran elevated. This
  is the stricter setting, and closer to a real user installing with `--user`.
- **Not covered** (as before): a physical or interactive desktop session, ARM64 Windows.

## Windows results

- **tier1-core** (`windows-full-tier1-core-report.json`): overall_ok. bootstrap-install-usable-cli,
  new-cli-project-build-run, gorm-build-run and self-update-cli-only all passed, with the
  staged 0.1.8 CLI.
- **Arlen check** (`windows-arlen-check.txt`), not elevated, with the 0.1.8 CLI:
  - a tampered package list is refused (exit 1);
  - `install` picks `arlen-windows-amd64-msys2-clang64-headless` 0.3.2, whose zip hashes to
    `fd39fb7d…`, the digest in the index;
  - `arlen.cmd` and `boomhauer.cmd` are installed as plain files; `boomhauer --help` exits 0 and
    `arlen --help` exits 2, the same as v0.1.4–v0.1.7;
  - `remove` exits 0 and leaves no package directory or shims.
- **Toolchain smoke** (`windows-toolchain-smoke-check.txt`), not elevated, on a fresh install
  of the staged release:
  - `smoke-toolchain` exit 0: Foundation with blocks, pthread, pyexpat, curl with SSL, perl and
    NSLog;
  - TLS host verification (expired, wrong-host, self-signed and untrusted-root are refused; the
    override works; address URLs are checked against the certificate);
  - trust on a store missing the root;
  - bundled authorities 93 days old; gdnc was not left running;
  - from outside the toolchain's bash: github.com 0, expired 1, 1.1.1.1 0.
- **Gate B** (`windows-update-gates.*`): the staged 0.1.8 CLI with plain `update --yes`, no
  `--manifest` and no trust override, on a 0.1.5 install, against production Latest (v0.1.7).
  It exited 0 and the install is at 0.1.7. **N:** `update cli --yes` afterwards is a no-op
  (exit 0, `current` unchanged, no new snapshot).
- **Gate S** (`windows-self-update-gate.*`), the #77 bug: a 0.1.8 install from the staged
  manifest self-updates to the staged artifacts relabelled 0.1.9 and re-signed with a throwaway
  key. It exited 0, `current\release.txt` is 0.1.9, the new CLI's smoke passed, the launcher works,
  and doctor reports integrity ok with the managed root.
  - Control: the same gate with the v0.1.7-era updater (run 43971737455, `control`) exits 1,
    stays at 0.1.8 and fails the smoke, which is the bug. The fixed build in that run passed.
- **Gate A** (v0.1.7 → 0.1.8 by `gnustep update`): not run as a pass/fail gate. The v0.1.7
  updater has the #77 bug, so it rolls back by design. The release notes tell v0.1.7 Windows
  users to re-run the 0.1.8 bootstrap. From 0.1.8 on, gate S shows the updater works.

## Harness fixes during this run (no product change)

- The first standard-user run (43979530103) hung: a plain local user lacks batch logon, so the
  scheduled task never started. The fix was adding the user to `Performance Log Users`, plus a
  `whoami /groups` probe that fails fast.
- In run 44007544196 the Arlen check refused the package index, correctly: `actions/checkout`
  had converted the fixture to CRLF, so its sha256 (`c6351903…`) no longer matched the one the
  manifest pins (`dcdf2258…`). The fixtures are now checked out byte-exact
  (`.gitattributes: * -text`), and 44009065051 passed. Tier1 passed in both runs.

## Other checks before publication

- **Linux update rehearsals** (isolated scratch installs, staged manifest served locally, private
  HOME; `~/GNUstep` unchanged):
  - R1: the 0.1.7 CLI with plain `update --yes` moved 0.1.7 to 0.1.8;
  - R2: the staged CLI moved 0.1.5 to 0.1.7 against the real Latest;
  - R3: 0.1.8 then reported no updates;
  - D: `doctor` reported the upgraded install as managed at its root.
- **Release-path rehearsal** (release.yml's commands, throwaway keys, nothing published): passed,
  apart from the evidence gates that need this bundle, as in v0.1.7.
- **Package index:** Package Index run 43975573558 (`packages=io.github.danjboyd.arlen`,
  `published_only=true`) is identical to v0.1.7's published index apart from `generated_at`;
  `allow_new_index_packages` stays empty.
- The real check against `releases/latest` runs after publication.
