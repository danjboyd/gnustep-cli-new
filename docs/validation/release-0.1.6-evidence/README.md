# v0.1.6 release evidence

Release under test: stage-release run 42695178149 (channel `stable`, version `0.1.6`,
**12 artifacts**, staged from `5240863`). v0.1.6 adds Ubuntu 24.04 arm64 as a stable target,
builds the GNUstep toolchains with `-O2`, limits the Windows clang 23 workaround to
`GSFormat.m`, and changes the CLI: doctor reports the age of Windows' bundled CA set,
GNUstep.csh puts the toolchain's `lib` on the loader path, and `update --check` no longer
claims an install is current when that can't be shown. The Arlen-only package index is
carried forward unchanged.

This replaces the first staging (run 42690085410, source `34c5af0`), which silently dropped
Ubuntu 24.04 arm64 because the target was still marked unpublished in `build_infra`
(fixed by #54, with a Stage Release regression test). That candidate was never published.

## Artifacts and their sources

| Artifact | sha256 | Source |
|---|---|---|
| cli linux-amd64-clang | `c1ad7729…` | run 42693611857 (5240863) |
| toolchain linux-amd64-clang | `fb40eddb…` | run 42693611857, built from source with -O2 |
| cli linux-ubuntu2404-amd64-clang | `ef35c162…` | run 42693639871 (5240863) |
| toolchain linux-ubuntu2404-amd64-clang | `2450f07a…` | run 42693639871, built from source with -O2 |
| cli linux-ubuntu2604-amd64-clang | `3c2a18d4…` | run 42693653098 (5240863) |
| toolchain linux-ubuntu2604-amd64-clang | `0b3486cb…` | run 42693653098, built from source with -O2 |
| cli linux-ubuntu2404-arm64-clang | `ee45f056…` | run 42693667948 (5240863) |
| toolchain linux-ubuntu2404-arm64-clang | `a40ab3f4…` | run 42693667948, built from source with -O2 |
| cli linux-arm64-clang | `ecc05e55…` | run 42693626146 (5240863) |
| toolchain linux-arm64-clang | `eedc9fca…` | run 42693626146, built from source with -O2 |
| cli windows-amd64-msys2-clang64 | `55c8e06e…` | run 42693682068 (5240863) |
| toolchain windows-amd64-msys2-clang64 | `861e8576…` | run 42693682068, assembled from the lock with gnustep-base 1.31.1-10.5 (msys2-inputs-2026-11-09) |

Every Linux artifact's sha256 equals the sha its container qualification tested
(cross-checked in `linux-smoke-report.json`'s `derived_from`). The package index (Package
Index run 42693606832) lists the same Arlen 0.3.2 artifacts, digests and URLs as v0.1.5.

## What changed

- **Toolchains (#46):** GNUstep Make takes its default `OPTFLAG` from `CFLAGS` at configure time,
  so toolchain libraries had been built without optimisation. `CFLAGS` now carries `-g -O2` in
  every Linux and OpenBSD recipe (OpenBSD: static check only; no OpenBSD artifacts ship).
- **Windows gnustep-base 1.31.1-10.5 (#47):** upstream libs-base 7c81d0c83's clang 23 workaround
  now applies to `GSFormat.m` only, as upstream does; the build fails if the flag reaches any
  other file. A same-runner benchmark found no measurable difference from 10.4.
- **Ubuntu 24.04 arm64 (#48, #54):** new stable target, glibc 2.39, ICU 74.
- **CLI:** `doctor` check `tls.bundled-authorities` (#49); GNUstep.csh lib path (#50); honest
  `update --check` wording (#52); README installs from the latest stable bootstrap (#51).
- Unchanged by choice (Dan, ask #5100): libs-gui stays on upstream `7892137`; the first-click
  submenu fix and the scroller fix are not in this release.

## Evidence files

| File | Source |
|---|---|
| `linux-*-container-qualification.json` (5) | The container-qualification artifact of each Linux run above (debian:13 for amd64 and arm64, ubuntu:24.04 amd64 and arm64, ubuntu:26.04). All 12 steps passed, including SONAME checks and TLS (trusted site loads; expired, wrong-host, self-signed and untrusted-root refused; `GS_TLS_VERIFY_S=NO` overrides; `https://1.1.1.1` loads; a GitHub address is refused). `tls_no_ca` exits 1, the expected refusal with no CA bundle, as in v0.1.5. Evidence tier: clean distro container on a GitHub runner. |
| `linux-smoke-report.json` | Derived from the five container qualifications, listed with sha256 under `evidence.derived_from`; their artifact digests were checked against the staged manifest. |
| `windows-current-source-artifact.json` | Run 42693682068; identical to the marker in the staged release (source revision `5240863`). That run's toolchain smoke passed, including both offline trust checks and the bundled-authorities age check (85 days). |
| `windows-full-tier1-core-report.json`, `windows-full-release-evidence.json` | The lease run below. Stored as compact UTF-8 JSON; the UTF-8-BOM originals hash to `05915899…` and `6e051206…`. |
| `windows-toolchain-smoke-check.txt`, `windows-arlen-check.txt` | The toolchain smoke (gdnc and HTTPS) and the Arlen check on the same lease. |
| `openbsd-full-tier1-core-report.json` | **Carried forward from v0.1.0 via v0.1.2–v0.1.5**, byte-identical. v0.1.6 ships no OpenBSD artifacts. |
| `update-all-production-like.json` | **Carried forward**, byte-identical, as in v0.1.4 and v0.1.5. |

## Windows lease

- Host: OCI Windows Server 2022 lease `lease-20261109205712-3gglxu` via otvm-gate (owner
  windows-agent), a fresh machine, 2026-11-09 20:57–21:46Z. Destroyed afterwards; the instance is
  TERMINATED in OCI. Operator on the office network.
- Inputs checked on the host: the staged Windows CLI `55c8e06e…` and toolchain `861e8576…`, and
  the stamped 0.1.6 `gnustep-bootstrap.ps1` (`93054b44…`).
- **tier1-core:** overall_ok. bootstrap-install-usable-cli, new-cli-project-build-run,
  gorm-build-run and self-update-cli-only all passed.
- **Toolchain smoke:** exit 0; the TLS cases as on Linux (GitHub address `140.82.113.3`
  refused), trust on a store missing the root, the bundled authorities 85 days old; from
  outside the toolchain's bash: github.com 0, expired 1, 1.1.1.1 0.
- **Arlen 0.3.2:** a tampered index was refused; install, the `arlen` and `boomhauer` shims and
  remove behaved exactly as in v0.1.5.

## Other checks before publication

- **Release-path rehearsal** (release.yml's commands, throwaway keys, nothing published): stage,
  index generate/sign/trust gate, publication gate, signed-artifact check, advertise, verify,
  key rotation drill, sign and the controlled release gate passed. The evidence gates need this
  bundle.
- **Update-discovery rehearsal** (isolated scratch install; staged manifest served locally and
  verified with the rehearsal key): a v0.1.5 install saw 0.1.6 and upgraded; build and run worked
  afterwards; 0.1.6 then reported "No updates were found."; with the latest URL unreachable it
  reported "Could not check the latest stable release, so a newer version may exist". The real
  check against `releases/latest` runs after publication.
