# Release Readiness Review

Current date: 2026-04-27.

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
- Production package-index signing must also use CI-held private keys or a signing service. The workflow now requires package-index signing material and an explicit package-index trust root before publication; the hosted producer is currently blocked because `GNUSTEP_CLI_PACKAGE_INDEX_SIGNING_PRIVATE_KEY` is not configured.
- Release and package-index trust roots must be injected from an external trusted channel and verified by the release gate; local ephemeral signing is acceptable only as validation evidence. The controlled release gate no longer accepts a bundled package-index public key as production trust.
- Key rotation, revocation, expiry, rollback/freeze, and compromised-key drills must be automated before making production security claims; the local release key-rotation drill now exists and must be run with CI-held production trust roots before any production claim.
- Published-URL qualification still needs production persisted evidence and scheduled/CI execution; the staged-release OTVM lanes now have destroy-on-exit cleanup for Debian, OpenBSD, and Windows smoke coverage, and release evidence can now be bundled as `release-evidence-bundle.json`.
- Package artifact publication is now blocked by automation until package manifests carry real source provenance and artifact checksums. The current `tools-xctest` package remains intentionally non-publishable until controlled package builds rebuild every target from the declared upstream revision plus PR #5 patch and native install/smoke/remove evidence is recorded.
- The controlled `Release Inputs` workflow now supplies the hosted source-artifact handoff for Stage Release. Current hosted CI is green but publishes no release input artifacts, so Stage Release should consume a `Release Inputs` workflow run rather than a CI run.

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

## April 27 Hosted CI And Producer Status

- Hosted CI passed on `master` at commit `4d649e68`: Python/shared, native
  Objective-C, and package-artifacts jobs are green.
- The Python/shared job now installs `tools-xctest` because the QA regression
  test executes the native suite inside the shared regression runner.
- `Package Index` producer run `25020740853` failed at the signing step because
  the private package-index signing secret is missing.
- CI run `25020575778` has no Actions artifacts, so it cannot be used as a
  `Stage Release` source run. The `Release Inputs` workflow now exists for that
  handoff and verifies explicit URLs against supplied SHA256 values before
  uploading Actions artifacts.
