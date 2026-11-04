# v0.1.4 release evidence

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
- Arlen on the rebuilt master CLI was installed with the exact pinned bytes on Debian 13
  amd64 only, on a development host with throwaway signing keys and stubbed `sudo`,
  over localhost. A tampered index was refused, `gnustep install arlen` with no
  `--index` selected the right artifact, `arlen --help` exited 2 (usage), and removal
  left nothing behind.
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
| `windows-full-tier1-core-report.json`, `windows-full-release-evidence.json` | WINDOWS-PENDING |
| `openbsd-full-tier1-core-report.json` | **Carried forward from v0.1.0 via v0.1.2 and v0.1.3**, byte-identical. v0.1.4 ships no OpenBSD artifacts; the gate still requires the report. |
| `update-all-production-like.json` | **Carried forward from v0.1.0 via v0.1.2 and v0.1.3**, byte-identical. Not rerun against v0.1.4. |

### Windows tier1-core run

WINDOWS-PENDING

## Known issues recorded for this release

- The package index's `generated_at` is the literal `TBD`
  (`package_repository.py`, hardcoded). It is inside the signed bytes and clients
  don't read it. To be fixed in a later release.
- `gnustep install arlen` fails with "Package manifest not found" when the current
  directory has an entry named `arlen`: the CLI prefers a local path over the index.
  v0.1.3 behaves the same. Workaround: `gnustep install io.github.danjboyd.arlen`.
- Windows `.cmd` shims drop `^` in unquoted arguments and expand `%VAR%`.
- `release.yml`'s new advertise and filtered-index steps have only been rehearsed
  locally; this release is their first real run.
