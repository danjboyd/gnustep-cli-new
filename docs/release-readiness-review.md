# Release Readiness Review

Current date: 2026-05-04.

## Release-Candidate Position

The project has reached a local v0.1.x RC1-style validation point for the deliberately small command set: `setup`, `doctor`, `build`, `run`, `new`, `install`, and `remove`. The native Objective-C full CLI and Python/shared support tooling are green, POSIX bootstrap no longer depends on Python, native setup now has pointer-driven activation plus rollback, the corrected staged candidates pass local release/security gates with ephemeral signing, Debian clean-machine dogfood passed end-to-end through bootstrap, managed toolchain, project workflow, package install/remove, upgrade, and rollback, and the refreshed Windows staged-release bootstrap/full-CLI smoke now passes on libvirt.

## Supported Claims For v0.1.x

- OpenBSD `amd64` packaged Clang/libobjc2 GNUstep is validated as the preferred native path.
- Debian `amd64` managed Clang/libobjc2 is validated for controlled dogfood and public bootstrap/full-CLI/package flows.
- Fedora and Arch packaged GNUstep are validated as GCC/libobjc interoperability paths, not preferred modern-runtime paths.
- Windows `amd64/msys2-clang64` is validated for managed-toolchain staging, native full-CLI build, package install/remove, public bootstrap setup, extracted-toolchain rebuild/doctor qualification, and staged-release bootstrap/full-CLI smoke from PowerShell plus `cmd.exe` help invocation.
- Windows `amd64/msvc` remains deferred for v0.1.x.

## Production Blockers

- Production release signing must use CI-held private keys or a signing service, not developer-local ad hoc keys. The workflow now requires release signing material and an explicit release trust root before publication; the release private/public/trust secrets are configured in GitHub.
- Production package-index signing must also use CI-held private keys or a signing service. The workflow now requires package-index signing material and an explicit package-index trust root before publication; the hosted producer is no longer blocked after rotating the package-index signing material to RSA and producing signed package-index artifact run `25021604641`.
- Release and package-index trust roots must be injected from an external trusted channel and verified by the release gate; local ephemeral signing is acceptable only as validation evidence. The controlled release gate no longer accepts a bundled package-index public key as production trust.
- Key rotation, revocation, expiry, rollback/freeze, and compromised-key drills must be automated before making production security claims; the local release key-rotation drill now exists and must be run with CI-held production trust roots before any production claim.
- Published-URL qualification now has a successful dogfood publication path and persisted hosted evidence for the provisional `v0.1.0-dev-hosted.1` release. Production still needs scheduled/CI live host evidence rather than replaying April 24 local smoke reports.
- Package artifact publication is now blocked by automation until package manifests carry real source provenance and artifact checksums. The current `tools-xctest` package remains intentionally non-publishable until controlled package builds rebuild every target from the declared upstream revision plus PR #5 patch and native install/smoke/remove evidence is recorded.
- The controlled `Release Inputs` workflow now supplies the hosted source-artifact handoff for Stage Release. The current dogfood release consumed run `25021838530`.
- The controlled `Release Evidence` workflow now supplies the hosted evidence handoff for release qualification. The current dogfood release consumed run `25022173894`.

## Next Gate

The next gate is productionizing cross-target release qualification: persist the Debian/OpenBSD/Windows OTVM evidence bundle from CI, enforce signed metadata with externally pinned production trust roots, add Fedora/Arch interop lanes where appropriate, and rebuild Windows artifacts from the current source tree before claiming a production Windows refresh. The April 19/20 signatures are local-development evidence, not a production signing claim.



## April 20 Lifecycle Gate Results

- Native Objective-C `tools-xctest` passed with 50 tests after adding failed-smoke activation coverage.
- Python/shared regression passed with 138 tests after adding controlled trust-root, release-claim consistency, package transaction, and package upgrade coverage.
- `controlled-release-gate` now requires an explicit release trust root; local bundled keys are no longer sufficient for production-style controlled release approval.
- `release-claim-consistency-gate` now checks staged artifacts against Debian/OpenBSD/Windows OTVM smoke evidence and can require a current-source Windows artifact marker.
- Debian upgrade dogfood now includes `setup --rollback`; the April 20 run passed on lease `lease-20260420121832-7kqkxe`, guest `172.17.2.121`, with final result `{"ok":true,"summary":"Debian upgrade and rollback dogfood validation passed."}`.
- A combined staged release under `/tmp/gnustep-combined-otvm-stage/stable/0.1.2` passed ephemeral signing, controlled release gate, release-claim consistency gate with stale-Windows override, Debian staged-release smoke, OpenBSD native packaged smoke, and Windows bootstrap/full-CLI smoke.
- Release tooling now has explicit `windows-current-source-marker`, `release-evidence-bundle`, and `release-key-rotation-drill` commands. CI release publication also fails nonzero when a JSON gate returns `ok:false`, so failed production gates cannot be hidden by successful JSON printing.
- Package tooling now supports signed-index package upgrades and stale package transaction recovery/audit, closing the next package lifecycle safety gap before broader package update claims.
- Final OTVM cleanup check reported `active_count 0`.

## April 19 RC1 Gate Results

- `dist/stable/0.1.0-dev-rc1` was staged through the fixed `stage-release` path from known-good `0.1.0-dev` artifact archives.
- Full Python/shared regression passed with 134 tests, including archive-input release staging regression coverage.
- Native Objective-C tools-xctest regression passed.
- Release verification, signed release trust gate, controlled release gate, package index trust gate, and local extraction qualification passed for the corrected RC1 candidate.
- Debian dogfood validation passed on a fresh libvirt OTVM lease and destroyed the lease afterwards.
- OpenBSD staged-release native packaged smoke passed on a fresh libvirt lease: `pkg_add` installed packaged GNUstep components and a Foundation compile/run probe succeeded.
- Windows staged-release bootstrap/full-CLI smoke initially exposed a stale CLI artifact that emitted `{}` for `doctor --json`; rebuilding the Objective-C CLI on Windows, replacing the RC Windows CLI zip, restaging, and resigning fixed the issue. The refreshed smoke passed bootstrap setup, installed `gnustep.exe`, PowerShell invocation, `cmd.exe` help invocation, and `doctor --json`.
- Final OTVM lease cleanup destroyed the validation and rebuild leases.

The main remaining release-engineering issue is productionizing evidence and trust, not unresolved Debian/OpenBSD/Windows staged-release behavior. The first attempted RC staging caught that `stage-release` could misuse prebuilt archive inputs as directory inputs; that immediate bug is fixed by copying supported archive inputs directly and adding regression coverage. The Windows refresh also caught `assemble-toolchain.ps1` wildcard handling defects for `usr\bin` runtime files, including MSYS2 `[`-named tools; those are fixed with explicit wildcard enumeration and `Copy-Item -LiteralPath`.

## April 27 Hosted CI, Producer, And Release Status

- Hosted CI passed on `master` at commit `f67a390a`: Python/shared, native
  Objective-C, and package-artifacts jobs are green.
- The Python/shared job now installs `tools-xctest` because the QA regression
  test executes the native suite inside the shared regression runner.
- `Package Index` producer run `25021604641` passed and uploaded
  `gnustep-signed-package-index` with digest
  `sha256:39814e18490372ecbf0803de40206aa41d88f29254d5fcd024735dde777ee97e`.
- `Release Inputs` run `25021838530` passed and uploaded the four hosted input
  artifacts consumed by `Stage Release`.
- `Stage Release` run `25021894289` passed and uploaded `gnustep-staged-release`
  for version `0.1.0-dev-hosted.1`.
- `Release Evidence` run `25022173894` passed and uploaded
  `gnustep-release-evidence-inputs`.
- `Release` run `25022880046` passed and published prerelease
  `v0.1.0-dev-hosted.1`:
  `https://github.com/danjboyd/gnustep-cli-new/releases/tag/v0.1.0-dev-hosted.1`.
  The run evidence artifact `gnustep-release-evidence-dogfood-0.1.0-dev-hosted.1`
  has digest
  `sha256:6b3033c148a0ad5a83e24da75fde4fc730f9698c8d36c857afe6021c239edf88`.
- Published asset digests include Linux CLI
  `sha256:15190139967c202fee652301bdca8fb7e6d833cafe5447a34c55562f22fac682`,
  Linux toolchain
  `sha256:d9ce78d16d28842f7bedd24dbd2de64e16f67c064fbeb1d6ab1b372780ddff1b`,
  Windows CLI
  `sha256:8a1b0cf6f8db2f79ecc0c478532a213650131584baf4e2f7184c3b3364aa271e`,
  and Windows toolchain
  `sha256:1c07368c338c47502409fb996463ec53ff33324a6ede9cc29339fcda944a11a3`.
- The release passed with the explicit `allow_stale_windows_artifact=true`
  exception. This is acceptable for the dogfood hosted-path proof, but a
  production Windows refresh still requires a current-source hosted Windows
  artifact and live smoke evidence.

## April 28 Execution Update

- Added hosted producer workflows for current-source Windows artifacts,
  published-URL Linux qualification, and controlled `tools-xctest` package
  artifact production.
- Tightened Release so stale Windows artifacts are dogfood-only and Linux smoke
  evidence is a required hosted evidence input.
- Added `release-qualification-summary.json` generation to Release so each
  publication carries a compact index of producer run IDs, asset digests,
  evidence digests, source revision, and exceptions.
- Advanced native `doctor` parity by adding a structured `toolchain.features`
  check that exposes normalized Objective-C feature flags as first-class check
  evidence.
- `Windows Current Source Artifacts` run `25069092549` passed with fresh
  `assemble-msys2`, built and smoked the Objective-C full CLI from current
  source, and uploaded `gnustep-windows-current-source-artifacts` as artifact
  `6691317171`.
- `Package tools-xctest` run `25069093408` passed and uploaded
  `gnustep-package-tools-xctest-linux-amd64-clang` as artifact `6691217427`.
- Published-URL qualification run `25068782043` failed for the existing
  `v0.1.0-dev-hosted.1` release because its manifest points artifact URLs at
  `/releases/download/dogfood/download/v...`. Commit `7444b101` fixes future
  staged GitHub release URLs and keeps package workflow failure diagnostics as
  uploaded artifacts.
- Remaining production blockers are now candidate-publication and live-host
  evidence blockers: stage/publish a fresh dogfood candidate from the fixed
  manifest generator and current-source Windows artifacts, run published-URL
  Linux qualification against it, collect fresh Windows/OpenBSD live smoke
  reports, and rerun Release without `allow_stale_windows_artifact`.

## May 4 Hosted RC Gate Update

- Immediate RC blockers from the April 28 list are cleared for the current
  dogfood candidate. Commit `5273786c17bcd6acc7dd518d56d9acc8c6514e8b`
  fixed Windows PowerShell bootstrap installation from flat CLI archives by
  preserving known install-layout roots such as `bin/`.
- Local verification passed after the fix: targeted PowerShell bootstrap
  regression, POSIX and PowerShell bootstrap regressions, build-infra tests,
  full Python unittest discovery with 258 tests, and the native Objective-C
  suite through `scripts/dev/run-native-tests.sh`.
- Fresh OTVM live-host reruns passed on May 4, 2026:
  OpenBSD `openbsd-7.8-fvwm` packaged GNUstep compile/run smoke and Windows
  `windows-2022` bootstrap/full-CLI smoke both returned `ok:true`; the final
  OTVM cleanup check reported zero active leases.
- Current-source hosted producers passed for `.31`: Linux Current Source
  Artifacts run `25329957149`, Windows Current Source Artifacts run
  `25329956930`, and Stage Release run `25330301665`.
- Published-URL Linux qualification passed for
  `v0.1.0-dev-hosted.31` in run `25331121271`.
- Corrected hosted Release Evidence run `25331598383` passed using structured
  Phase 26 OpenBSD and Windows reports with SHA-256
  `f28167b11bace7ebe1aa0f086f880772e68318ac108f1f197ff2875e68d36025` and
  `1ee4b0e2cfc5bea1af2dc721318f1a07a07b678668d57a58435f2ca0a732d4f9`.
- Consolidated Release run `25331629057` passed end-to-end without the stale
  Windows exception and published prerelease
  `https://github.com/danjboyd/gnustep-cli-new/releases/tag/v0.1.0-dev-hosted.31`.
  The generated `release-qualification-summary.json` is `ok:true`, records the
  source revision above, records `stale_windows_allowed:false`, and includes
  release evidence bundle SHA-256
  `59d3afef28002e686c4f3524fa967aec1161f0f22147ee5a509f08613bc30cb5`.
- Remaining caution: the full Release gate still uses the accepted structured
  April 24 Phase 26 OpenBSD/Windows reports for the formal scenario evidence.
  The May 4 fresh OTVM reruns are simpler live-host smoke refreshes that prove
  the immediate Windows bootstrap fix and OpenBSD packaged compile/run lane.

## May 4 Completion-Pass Update

- `Release Evidence` now accepts optional fresh OpenBSD and Windows live-host
  smoke summary URLs and checksums, downloads them into the hosted evidence
  artifact, and preserves them as supplemental evidence rather than pretending
  they are full structured Phase 26 scenario reports.
- The consolidated `Release` workflow now builds `release-evidence-bundle.json`
  with `.artifacts/hosted-release-evidence` as the evidence root and uploads
  all hosted evidence JSON files with the release evidence artifact. This
  removes the previous gap where fresh simple OTVM reruns could be proven
  locally but not persisted in the hosted release evidence bundle.
- Package artifact source-build closure is now stricter: publishable package
  artifacts must carry materialized build evidence and validation evidence
  paths. The `tools-xctest` package manifest now points build evidence at
  committed records under `docs/validation/tools-xctest-build-evidence/`, and
  `package-artifact-publication-gate` passes with those records present.
- Production trust and stable cutover remain gated by the final operator
  decision to run a stable-channel release with final CI-held signing material
  or a signing service. The repository now enforces the trust-root path in the
  Release workflow, but this document should not claim stable production
  publication until that final run exists.
