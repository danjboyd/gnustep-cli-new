# v0.1.4 release evidence

Published 2026-11-05 by Release run 42084994869, with Release Evidence run 42084692045.
After publication, Published Package Install Check run 42085743417 passed: index signature
and manifest digest, then a fresh bootstrap, `gnustep install arlen`, smoke and remove on
debian:13 and windows-latest.

Release under test: stage-release run 41900014828 (channel `stable`, version
`0.1.4`, 10 artifacts, source `101cfd0`). v0.1.4 rebuilds every CLI and reuses the
v0.1.3 toolchains byte for byte. It also publishes a signed stable package index
containing only Arlen 0.3.2 (Package Index run 41898623255).

## Artifacts and their sources

| Artifact | sha256 | Source |
|---|---|---|
| cli linux-amd64-clang | `0a636a67…` | run 41898627704 (101cfd0) |
| toolchain linux-amd64-clang | `41fd4b83…` | v0.1.3 asset, byte-identical (`reuse_toolchain_tag v0.1.3`, run 41898627704) |
| cli linux-ubuntu2404-amd64-clang | `7c89dbd3…` | run 41898632343 (101cfd0) |
| toolchain linux-ubuntu2404-amd64-clang | `e2430e58…` | v0.1.3 asset, byte-identical (`reuse_toolchain_tag v0.1.3`, run 41898632343) |
| cli linux-ubuntu2604-amd64-clang | `e0456853…` | run 41898636725 (101cfd0) |
| toolchain linux-ubuntu2604-amd64-clang | `1acde52f…` | v0.1.3 asset, byte-identical (`reuse_toolchain_tag v0.1.3`, run 41898636725) |
| cli linux-arm64-clang | `9b8a7dc4…` | run 41898641398 (101cfd0) |
| toolchain linux-arm64-clang | `0f8593f6…` | v0.1.3 asset, byte-identical (`reuse_toolchain_tag v0.1.3`, run 41898641398) |
| cli windows-amd64-msys2-clang64 | `48b7973e…` | run 41898646469 (101cfd0) |
| toolchain windows-amd64-msys2-clang64 | `00fee7b5…` | v0.1.3 asset, byte-identical (`existing-zip`, run 41898646469) |

Arlen 0.3.2 artifacts are the bytes the package manifest pins: amd64 `cfc3000b…`
(run 41725920745), Ubuntu 24.04 `70f0179d…` (41725924531), Ubuntu 26.04
`c4e4ae75…` (41725928717), arm64 `29368762…` (41725932816), Windows `fd39fb7d…`
(41724056057).

## What was requalified after the merges, and why not more

The CLIs and Arlen were qualified on 11-03 and 11-04 using `v0.1.4-candidate`. After
#35, #34, #32, #37 and #36 merged, the CLIs were rebuilt from master. Arlen was not
rebuilt: builds aren't byte-reproducible, and the manifest pins the digests, so a
rebuild would need a new manifest commit and would mean shipping bytes other than
the ones qualified.

- `src/` is identical between `v0.1.4-candidate` and master. The differences are
  `scripts/dev/activate-tools-xctest.sh`, `scripts/dev/run-native-tests.sh`, two test
  files and the new published-install workflow.
- Each Linux rebuild passed its own container qualification (files below).
- Arlen on the rebuilt master CLI was installed with the exact pinned bytes on Windows
  (below) and on Debian 13 amd64, the latter on a development host with throwaway signing keys and stubbed `sudo`,
  over localhost. A tampered index was refused, `gnustep install arlen` with no
  `--index` selected the right artifact, `arlen --help` exited 2 (usage), and removal
  left nothing behind.
- Release's evidence gates (claim consistency, Phase 26, 12 and 13, evidence bundle,
  immediate-RC blockers) were run locally against a throwaway-key rehearsal of these
  artifacts with these evidence files, and passed.
- The other Linux targets did not repeat the Arlen install on the rebuilt CLI; their
  Arlen results are from `v0.1.4-candidate`
  (`docs/validation/arlen-0.3.2-20261103/`). The post-publish check
  (`published-package-install-check.yml`) installs from the published release.

## Evidence files

| File | Source |
|---|---|
| `linux-*-container-qualification.json` | The container-qualification artifact of each Linux run above (debian:13 for amd64 and arm64, ubuntu:24.04, ubuntu:26.04). All steps passed; every CLI reports 0.1.4. Evidence tier: clean distro container on a GitHub runner, not a VM. |
| `linux-smoke-report.json` | Derived from the four container qualifications, listed with sha256 under `evidence.derived_from`. Their artifact digests were checked against the staged manifest. |
| `windows-current-source-artifact.json` | Run 41898646469; identical to the marker in the staged release. |
| `windows-full-tier1-core-report.json`, `windows-full-release-evidence.json` | See the next section. Stored as compact UTF-8 JSON; the pretty-printed UTF-8-BOM originals hash to `7ed2a8e8…` and `81d31cc6…`. |
| `windows-gnutar-first-check.txt` | The GNU-tar-first check on the same lease. |
| `windows-arlen-check.txt` | The Windows Arlen install check on the same lease. |
| `openbsd-full-tier1-core-report.json` | **Carried forward from v0.1.0 via v0.1.2 and v0.1.3**, byte-identical. v0.1.4 ships no OpenBSD artifacts; the gate still requires the report. |
| `update-all-production-like.json` | **Carried forward from v0.1.0 via v0.1.2 and v0.1.3**, byte-identical. Not rerun against v0.1.4. |

### Windows tier1-core run

- Host: OCI Windows Server 2022 lease `lease-20261105172531-2opbdx` via otvm-gate
  (owner windows-agent), destroyed afterwards; instance TERMINATED in OCI.
- Shell: Windows PowerShell 5.1.20348, scheduled task with S4U and RunLevel Limited.
  **Not necessarily a non-elevated token:** a check run the same way reported
  membership in Administrators as active (`elevated: True` in
  `windows-arlen-check.txt`). The v0.1.3 README called its identical setup
  non-elevated, which is unverified. Unelevated use with Developer Mode off was
  tested separately on Windows 11 on 2026-11-03 (see PR #34).
- Time: 2026-11-05, starting 17:32Z. Exit 0, all four scenarios passed.
- Command: `scripts/dev/windows-full-release-smoke.ps1` at 101cfd0 (sha256
  `b81aecd7…`), `-ReleaseSource v0.1.4-stage-41900014828 -SuiteId tier1-core`.
- Inputs: the staged Windows CLI `48b7973e…` and toolchain `00fee7b5…`, the stamped
  0.1.4 `gnustep-bootstrap.ps1` (`c75cdc9e…`), and the Gorm patch `53a07e0f…`.
  `release-old` was a copy of `release-new`.
- What the scenarios showed: doctor `ok` / `toolchain_compatible`, the CLI reports
  0.1.4, new/build/run, Gorm build and run with the pinned fixture patch, and a CLI-only
  self-update ("CLI update completed; the managed toolchain was unchanged.").
- GNU-tar-first check: with the managed root's `usr\bin` first on PATH, bare `tar`
  resolved to GNU tar 1.35. The bootstrap still verified the manifest signature, extracted
  both zips and installed. perl 5.42.3 runs, and neither installed root contains
  `etc\pacman.d\gnupg`.
- Arlen on the rebuilt CLI: in the smoke's installed root (its `gnustep.exe` sha256
  `531ec402…` matches the staged zip), with the pinned `fd39fb7d…` bytes served from local
  files and a throwaway signed manifest: a tampered index was refused, `gnustep install
  arlen` with no `--index` selected the Windows artifact, `arlen.cmd --help` exited 2
  and `boomhauer.cmd --help` exited 0, and removal left nothing behind.

## Known issues recorded for this release

- The package index's `generated_at` is the literal `TBD`
  (`package_repository.py`, hardcoded). It is inside the signed bytes and clients
  don't read it. To be fixed in a later release.
- `gnustep install arlen` fails with "Package manifest not found" when the current
  directory has an entry named `arlen`: the CLI prefers a local path over the index.
  v0.1.3 behaves the same. Workaround: `gnustep install io.github.danjboyd.arlen`.
- Windows `.cmd` shims drop `^` in unquoted arguments and expand `%VAR%`.
- `gnustep update` on an installed release reads that release's own manifest, so it
  doesn't find newer releases. Confirmed after publication: a v0.1.3 install reports
  "Everything is already current". Existing installs run the new bootstrap to move to 0.1.4.
- `release.yml`'s new advertise and filtered-index steps have only been rehearsed
  locally; this release is their first real run.
