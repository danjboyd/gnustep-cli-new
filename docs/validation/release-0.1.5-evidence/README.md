# v0.1.5 release evidence

Release under test: stage-release run 42270705980 (channel `stable`, version `0.1.5`,
10 artifacts, staged from `84c6add`). v0.1.5 picks up upstream libs-base's strict TLS host
verification on every target, rebuilds every toolchain and CLI, and carries the
Arlen-only package index forward. On Windows, gnustep-base also trusts a current Mozilla CA
bundle alongside the Windows store (see below).

This replaces the first staging (run 42122520629, source `9a40812`): its Windows lease smoke
found the Windows root-store gap described below. The Linux artifacts are the same four build
runs, byte-identical; only Windows was rebuilt.

## Artifacts and their sources

| Artifact | sha256 | Source |
|---|---|---|
| cli linux-amd64-clang | `34037e88…` | run 42121506379 (9a40812) |
| toolchain linux-amd64-clang | `f672faba…` | run 42121506379, built from source with the libs-base patches |
| cli linux-ubuntu2404-amd64-clang | `9a1179d2…` | run 42121517396 (9a40812) |
| toolchain linux-ubuntu2404-amd64-clang | `dbdafa71…` | run 42121517396, built from source with the libs-base patches |
| cli linux-ubuntu2604-amd64-clang | `a046413b…` | run 42121527775 (9a40812) |
| toolchain linux-ubuntu2604-amd64-clang | `8f54d84f…` | run 42121527775, built from source with the libs-base patches |
| cli linux-arm64-clang | `0e41dc40…` | run 42121538804 (9a40812) |
| toolchain linux-arm64-clang | `edb4465d…` | run 42121538804, built from source with the libs-base patches |
| cli windows-amd64-msys2-clang64 | `5b88e539…` | run 42269703643 (84c6add) |
| toolchain windows-amd64-msys2-clang64 | `8d9ecb29…` | run 42269703643, assembled from the lock with gnustep-base 1.31.1-10.4 (msys2-inputs-2026-11-06) |

The package index (Package Index run 42269701172) still lists Arlen 0.3.2 only, pointing at
the artifacts published on v0.1.4, which stay where they are.

## What changed in the toolchains

- libs-base: eight upstream commits applied as patches: 586eba532, 09b7efcb3, 0b5205854,
  193da175c, 02f2958f1, f28c9996a, a29f803ff and d80ae7406 (ChangeLog hunks removed). Linux
  applies them to the existing `d898f70` pin. Windows rebuilds MSYS2's gnustep-base 1.31.1-10
  recipe with them (the 7th without its test-file hunk) as package 1.31.1-10.4, published as
  the pinned input `msys2-inputs-2026-11-06`.
- Windows trust: Windows adds many trusted roots to its store only on demand, the first time
  its own chain building needs one, and gnutls reads the store as it stands. The first
  staging's lease therefore refused `https://1.1.1.1` (root SSL.com Root Certification
  Authority ECC) on a fresh machine. Our Windows-only patch 0009 makes gnustep-base also load
  its bundled `GSTLS/ca-certificates.crt` after the store; the package replaces that file
  (2016 in the source tree) with the Mozilla set from `mingw-w64-clang-x86_64-ca-certificates`
  20260816-1. Roots in the store, including ones an organisation installs, are still trusted.
  The toolchain smoke proves both sources offline and refuses a bundle older than 365 days.
- Windows: the gnustep-base package is built with `-mllvm -enable-dfa-jump-thread=false` on
  every file. That is upstream libs-base 7c81d0c83's workaround for clang 23 miscompiling
  `GSPrivateFormat` (llvm/llvm-project#231864), which made every `NSLog` crash. Upstream applies
  it to GSFormat.m only; a small speed cost from applying it everywhere is possible and was not
  measured.
- OpenBSD: the patches are in both OpenBSD locks but were not built or tested. v0.1.5 ships no
  OpenBSD artifacts.

## Evidence files

| File | Source |
|---|---|
| `linux-*-container-qualification.json` | The container-qualification artifact of each Linux run above (debian:13 for amd64 and arm64, ubuntu:24.04, ubuntu:26.04). All steps passed, including TLS: a trusted site loads; expired, wrong-host, self-signed and untrusted-root certificates are refused; `GS_TLS_VERIFY_S=NO` overrides; `https://1.1.1.1` (certificate names that address) loads and a GitHub address (certificate names only github.com) is refused. Evidence tier: clean distro container on a GitHub runner. |
| `linux-smoke-report.json` | Derived from the four container qualifications, listed with sha256 under `evidence.derived_from`; their artifact digests were checked against the staged manifest. |
| `windows-current-source-artifact.json` | Run 42269703643; identical to the marker in the staged release. That run's toolchain smoke and PowerShell check passed with the same TLS cases (address cases in the bash smoke), with gdnc started by the library itself, plus the offline trust checks: a local site whose root is only in the bundled file loads, and one whose root is only in the machine store loads. The same check failed on the 10.3 package (run 42257098217), as intended. |
| `windows-full-tier1-core-report.json`, `windows-full-release-evidence.json` | See the next section. Stored as compact UTF-8 JSON; the pretty-printed UTF-8-BOM originals hash to `9daf800a…` and `273262cc…`. |
| `windows-root-store-survey.json` | The root-store survey on the same lease, run first; see the next section. |
| `windows-toolchain-smoke-check.txt`, `windows-arlen-check.txt` | The toolchain smoke (gdnc and HTTPS) and the Arlen check on the same lease. |
| `openbsd-full-tier1-core-report.json` | **Carried forward from v0.1.0 via v0.1.2, v0.1.3 and v0.1.4**, byte-identical. v0.1.5 ships no OpenBSD artifacts, and the libs-base patches are untested on OpenBSD. |
| `update-all-production-like.json` | **Carried forward**, byte-identical, as in v0.1.4. |

## Other checks before publication

- **libs-base's own test suite** at `d898f70`, on a Debian 13 development host (not the pinned
  build container): unpatched 11794 passed, 41 dashed hopes, 0 failed; patched (7 commits)
  11789 passed, 43 dashed hopes, 4 failed. The 4 failures are tests expecting the old
  `-[NSURL description]` output (NSURL/mystep.m and NSJSONSerialization/tests00.m): a29f803ff
  deliberately hides URL passwords there, and upstream's test-only follow-ups 64b5db6f2 and
  de5bf97d0, applied for the check, make them pass. The 2 new dashed hopes (NSURLConnection
  test03 and test05, HTTPS redirect to a local test server) are the strict refusal of that
  server's self-signed certificate: both pass with `GS_TLS_VERIFY_S=NO`. With d80ae7406
  added, its addressTLS.m tests pass (11/11), as do NSStream, NSFileHandle and NSURLHandle.
- **Arlen 0.3.2** (the published v0.1.4 artifact, `cfc3000b…`) installed on the staged
  linux-amd64 release on a Debian 13 development host, with throwaway signing keys over
  localhost: a tampered index was refused, `gnustep install arlen` with no `--index`
  selected the right artifact, `arlen --help` exited 2 (usage), removal left nothing behind.
  Other targets were not repeated before publication.
- Release's evidence gates (claim consistency, Phase 26, 12 and 13, update-all, evidence
  bundle, release qualification summary and immediate-RC blockers) were run locally against
  a throwaway-key rehearsal of stage-release run 42270705980's artifacts with these evidence
  files, in release.yml's order, and passed. The rehearsal's own steps (stage, verify, index
  generate/sign/trust gate, publication gate, signed-artifact check, advertise, key-rotation
  drill, sign, controlled gate) passed too.

### Windows lease (root-store survey, tier1-core, HTTPS, Arlen)

- Host: OCI Windows Server 2022 lease `lease-20261106184237-xz5by6` via otvm-gate
  (owner windows-agent), a fresh machine, 2026-11-06 18:47–20:22Z. Destroyed afterwards;
  the instance is TERMINATED in OCI. Operator on the office network.
- Shell: Windows PowerShell 5.1.20348, scheduled tasks with S4U and RunLevel Limited
  (`elevated: True`, as in v0.1.4).
- Inputs: the staged Windows CLI `5b88e539…` and toolchain `8d9ecb29…` (both checked on
  the host), the stamped 0.1.5 `gnustep-bootstrap.ps1` (`bea03e78…`), the Gorm patch
  `53a07e0f…`, and `smoke-toolchain.sh` from `84c6add`. `release-old` was a copy of
  `release-new`.

**Root-store survey, before anything else touched the certificate store**
(`windows-root-store-survey.json`). The toolchain zip was expanded, not installed, and
`tls.exe` from the toolchain smoke was built with it. Store counts were read through the
PowerShell `Cert:` drive, which installs nothing.

- The fresh store held 18 roots (LocalMachine\Root and CurrentUser\Root; 5 in AuthRoot).
  Of the 16 surveyed sites' roots, only DigiCert Global Root G2 was present.
- gnustep-base with the Windows store alone (its bundled file moved aside, as before
  the fix): 2 of 16 sites loaded (www.microsoft.com, www.amazon.com). `https://1.1.1.1` was
  refused.
- gnustep-base as shipped (store plus the bundled Mozilla set): 16 of 16 loaded:
  1.1.1.1, www.google.com, github.com, www.microsoft.com, letsencrypt.org,
  valid-isrgrootx2.letsencrypt.org, www.amazon.com, www.ssl.com, www.sectigo.com,
  www.godaddy.com, www.globalsign.com, www.identrust.com, www.buypass.no, www.certum.pl,
  www.actalis.it and www.swisssign.com.
- Proof that the bundled file is what's read: a local site was refused, then loaded once
  its root was added only to the toolchain's `GSTLS/ca-certificates.crt`. The file was then
  restored; its sha256 matches package 1.31.1-10.4. (The script's own restore check needed
  `cmp`, which the toolchain's bash lacks, and printed `restored=NO`; the sha256 check
  replaces it.)
- The store was unchanged after the gnustep-base runs.
- Only then did Windows' own client (`Invoke-WebRequest`) visit the same sites. The store
  grew to 33 roots and held 15 of the 16, and gnustep-base with the store alone then loaded
  16 of 16. Windows installs these roots on demand. Four of those requests ended with a
  PowerShell redirect error, because redirects were turned off, after the TLS handshake.

**tier1-core**: exit 0, all four scenarios passed (bootstrap-install-usable-cli,
new-cli-project-build-run, gorm-build-run, self-update-cli-only).
`scripts/dev/windows-full-release-smoke.ps1` (sha256 `b81aecd7…`, unchanged since v0.1.4),
`-ReleaseSource v0.1.5-stage-42270705980 -SuiteId tier1-core`.

**gdnc and HTTPS** (`windows-toolchain-smoke-check.txt`): `smoke-toolchain.sh` exited 0 on
the installed toolchain. No gdnc was running beforehand, and HTTPS worked, so the library
started it itself. github.com loaded. Expired, wrong-host, self-signed and untrusted-root
certificates were refused, and `GS_TLS_VERIFY_S=NO` overrides. `https://1.1.1.1` loaded and
a GitHub address (`https://140.82.113.4`) was refused. The offline bundle check and the age
check (82 days) passed. From PowerShell outside bash: github.com 0, expired 1, 1.1.1.1 0.
These checks ran after the survey had filled the store, so they test strict verification,
not the root gap; the survey covers the gap.

**Arlen 0.3.2** (`windows-arlen-check.txt`): in the smoke's installed root (its
`gnustep.exe` sha256 `867d029b…` matches the staged zip), with the pinned `fd39fb7d…`
bytes served from local files and a throwaway signed manifest: a tampered index was
refused, `gnustep install arlen` selected the Windows artifact, `arlen.cmd --help` exited
2 (usage) and `boomhauer.cmd --help` exited 0, as on v0.1.4, and removal left nothing
behind.

## Known issues recorded for this release

- `GS_TLS_VERIFY_S=NO` turns verification off per process, for endpoints that can't present a
  trusted certificate.
- `-[NSURL description]` hides the password in URLs that contain one; `-absoluteString` is
  unchanged.
- `gnustep update` finds newer stable releases only from 0.1.5 installs on; older installs run
  the new bootstrap.
- The Windows `gnustep-base` package is built with the clang 23 workaround on every file.
- On Windows, gnustep-base trusts the union of the Windows store and its bundled Mozilla set:
  a root distrusted by one but still listed by the other stays trusted. The bundled set is
  fixed per toolchain release and only refreshed by a new one.
