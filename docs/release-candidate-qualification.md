# Release-Candidate Qualification

This document records the current qualification posture for a v1 release
candidate.

## Completed Artifact-Level Checks

- regression gate is green across Python/shared and native Objective-C suites
- bootstrap-to-full handoff qualification is implemented and passing
- installed full CLI qualification asserts:
  - installed launcher exists and is executable
  - runtime binary exists under `libexec/gnustep-cli/bin`
  - runtime bundle is present
  - `state/cli-state.json` exists and is valid
  - bundled Python runtime trees are absent
- package index generation is verified against the committed generated artifact
- package index trust-gate validation now runs against generated provenance in
  unsigned development mode, and release publication requires signed release
  metadata before upload

## Partial Checks

- package-flow smoke behavior is covered by Python and native regression tests
- Debian libvirt host package-flow smoke also passed on April 14, 2026 against
  freshly staged release artifacts using a runtime-only package fixture:
  bootstrap `setup`, package `install`, and package `remove` all completed
  successfully on a clean lease
- Debian libvirt host package-flow smoke also passed on the same date with a
  compiler-family-constrained `clang` package fixture against a fresh staged
  release. The managed artifact exposed `clang --version` successfully on the
  clean lease, and package policy accepted the environment as `clang` for
  install/remove validation.
- The same Debian lease path now also passes a direct managed-toolchain
  `clang` compile-link-run probe on a clean host, so the current managed Linux
  artifact is no longer only a package-policy-validating compiler slice.
- Debian dogfood validation was refreshed again on April 16, 2026 using
  `scripts/dev/debian-dogfood-validation.sh` and freshly staged local
  `linux/amd64/clang` artifacts. The latest run passed bootstrap `setup`,
  installed CLI `--version` / `--help`, `doctor --json`, managed Foundation
  compile-link-run, `gnustep new`, `gnustep build`, `gnustep run`, and package
  install/remove smoke on a clean libvirt lease (`lease-20260416222812-tbap3u`,
  guest `172.17.2.173`), then destroyed the lease.
- Windows libvirt host and release-artifact validation advanced again on April 17, 2026:
  - `windows-2022` libvirt preflight passed with the current `OracleTestVMs`
    readiness flow
  - lease `lease-20260417160327-z8fnih` validated the checked-in MSYS2 assembly
    path, rebuilt the full Objective-C CLI on-host, passed `--version` /
    `--help`, installed a staged Windows package fixture with native SHA-256
    verification, removed it successfully, and was destroyed after validation
  - lease `lease-20260417171734-djj1b9` rebuilt refreshed Windows release
    artifacts and then qualified the staged release ZIPs directly: extracted the
    refreshed CLI/toolchain artifacts, ran `gnustep.exe --version` and `--help`,
    installed a package fixture, removed it successfully, and printed
    `release-artifact-smoke-ok`
  - the `v0.1.0-dev` GitHub prerelease assets are published, digest-verified,
    and publicly reachable
  - Debian published-URL qualification passed on April 17, 2026: bootstrap
    fetched the public release manifest, installed the refreshed Linux CLI and
    toolchain, ran `--version`, `--help`, full `doctor --json`, and package
    install/remove smoke
  - release provenance plus OpenSSL-backed manifest/provenance signatures are
    now published and locally gate-verified for the prerelease
  - Windows published-URL bootstrap setup passed on April 17, 2026 in
    direct-process diagnostic mode with retained JSONL trace evidence; installed
    `--version` and `--help` passed, the native `doctor --json` hang was fixed,
    and the extracted toolchain rebuilt the Objective-C CLI and passed
    explicit-manifest `doctor --json` with `toolchain_compatible`
- Fedora and Arch libvirt host availability is no longer blocked as of April 16,
  2026. Both profiles passed `otvm` preflight and acceptance-run. Fresh hosts
  also built the current full Objective-C CLI with distro GNUstep packages and
  passed `--version`, `--help`, and package install/remove smoke. Follow-up live
  checks confirmed both packaged stacks are GNUstep Make `gcc` / `libobjc.so.4`
  environments, so they are GCC interoperability targets rather than preferred
  Clang/libobjc2 native paths. Modern-runtime Fedora/Arch validation must use
  the managed Clang/libobjc2 toolchain.
- Fedora and Arch managed Linux artifact validation was rerun on April 16, 2026
  against the refreshed Debian-built artifact. Both proved the artifact is not
  portable across those distro families: Fedora fails to launch on missing
  `libcurl-gnutls.so.4`, and Arch fails to launch on missing `libxml2.so.2`.
  The current `linux-amd64-clang` artifact is Debian-scoped in metadata and
  selection policy; Ubuntu now has its own Docker-built and dogfooded `linux-ubuntu2404-amd64-clang`
  target because Ubuntu base images can have different ICU/runtime SONAMEs.
- The Debian managed Linux release gap for normal project workflows is now
  closed for the current staged artifact: `gnustep new`, `gnustep build`, and
  `gnustep run` passed on a fresh Debian libvirt lease after explicit host
  prerequisite installation of `clang` and `make`.
- broader cross-target published-URL host package validation is now represented
  by `published-url-qualification-plan`; remaining work is automation and
  production trust-root/key handling, not unresolved Windows bootstrap or
  extracted-toolchain loader defects


## April 19/20, 2026 RC1 Refresh

- Fixed `stage-release` archive-input handling so prebuilt `.tar.gz` and `.zip`
  inputs are copied as release artifacts instead of being wrapped inside a new
  archive.
- Rebuilt the Windows Objective-C full CLI on a `windows-2022` libvirt guest
  after the stale RC artifact emitted `{}` for `doctor --json`; replaced the
  Windows CLI zip input, restaged RC1, and regenerated checksums/signatures.
- Fixed `toolchains/windows-amd64-msys2-clang64/assemble-toolchain.ps1` runtime
  copy logic: PowerShell now enumerates `usr\bin\*` explicitly and copies
  MSYS2 developer/runtime files with `-LiteralPath`, which handles tools such
  as `[.exe`.
- Refreshed gates passed: `verify-release`, `release-trust-gate`,
  `controlled-release-gate`, and `qualify-release`.
- Refreshed Windows staged-release OTVM smoke passed bootstrap setup, installed
  `gnustep.exe`, PowerShell invocation, `cmd.exe` help invocation, and
  `doctor --json`; the lease was destroyed after validation.
- Regression gates are green: Python/shared unittest discovery ran 134 tests;
  native Objective-C tools-xctest ran 39 tests.

## Host Qualification

- May 4, 2026 hosted RC refresh:
  `v0.1.0-dev-hosted.31` was the first qualified dogfood candidate from the
  May 4 RC refresh. Commit
  `5273786c17bcd6acc7dd518d56d9acc8c6514e8b` fixed the Windows bootstrap
  installer so flat CLI archives with `bin/gnustep.exe` are not unwrapped into
  an invalid release root. The fix passed targeted PowerShell bootstrap
  regression, combined POSIX/PowerShell bootstrap regression, build-infra tests,
  full Python unittest discovery with 258 tests, and the native Objective-C
  suite.
- Hosted qualification for `.31` passed:
  Linux Current Source Artifacts `25329957149`, Windows Current Source
  Artifacts `25329956930`, Stage Release `25330301665`, Published URL
  Qualification `25331121271`, Release Evidence `25331598383`, and
  consolidated Release `25331629057`. The consolidated Release run passed the
  full regression suite, package readiness, signed package-index verification,
  staged release verification, release key-rotation drill, controlled release
  gate, release-claim consistency gate, Phase 26 RC smoke gate, Phase 12/13
  hardening gates, immediate RC blocker gate, evidence upload, and GitHub
  publication without `allow_stale_windows_artifact`.
- The generated `.31` release qualification summary is `ok:true` and records:
  release manifest SHA-256
  `78e38eab7c0f117170ab8e8c644d08e3aa17a03fa036546bfcc5e1e25472737e`,
  release evidence bundle SHA-256
  `59d3afef28002e686c4f3524fa967aec1161f0f22147ee5a509f08613bc30cb5`,
  Linux smoke evidence SHA-256
  `41efc94904b01a2897d0d82cc917ec8397c44e038e4540e6df60d21be246adcc`,
  OpenBSD structured evidence SHA-256
  `f28167b11bace7ebe1aa0f086f880772e68318ac108f1f197ff2875e68d36025`,
  Windows structured evidence SHA-256
  `1ee4b0e2cfc5bea1af2dc721318f1a07a07b678668d57a58435f2ca0a732d4f9`,
  Windows current-source marker SHA-256
  `10bccd3087c082bdfcbd0df419ce59bc27e182887c81f7819a2a29acf05d7104`,
  and production-like update-all evidence SHA-256
  `6b4003eee5de8265e1bae54158264571b24916e71cb8f214c4bcdf749aed9704`.
- Fresh May 4 OTVM live-host refresh also passed outside the formal hosted
  Release artifact: OpenBSD `openbsd-7.8-fvwm` packaged GNUstep compile/run
  smoke and Windows `windows-2022` bootstrap/full-CLI smoke both returned
  `ok:true`, and the final OTVM lease check reported zero active leases. These
  refreshes supplement the accepted structured April 24 Phase 26 reports that
  are still used by the hosted Release gate.
- May 4, 2026 completion-pass refresh:
  `v0.1.0-dev-hosted.32` supersedes `.31` as the current qualified dogfood RC
  baseline. Fresh Linux Current Source Artifacts run `25333123033`, Windows
  Current Source Artifacts run `25333122890`, Package Index run `25333124065`,
  and Stage Release run `25333443740` produced and staged the release inputs.
  Published URL Qualification run `25334200978`, Release Evidence run
  `25334309869`, CI run `25334650310`, and consolidated Release run
  `25334690351` all passed.
- The generated `.32` release qualification summary is `ok:true` on source
  revision `e09f90545d71d48fe37f115f975b5418ce364050` with
  `stale_windows_allowed:false`. It records release manifest SHA-256
  `dbcf51e726b2db700c378c5c6dc9e798683998c801eb6269979cdd108a9ba564`,
  release evidence bundle SHA-256
  `3f1126d3e32a5674286fc739b4bb875749a83e24c7de83eb5012b5d6e0974e74`,
  Linux published-URL smoke SHA-256
  `07b7702a7f1a12892ce94defef135c85268a6a0589946ad5fbc3c0b0371a347a`,
  OpenBSD structured evidence SHA-256
  `f28167b11bace7ebe1aa0f086f880772e68318ac108f1f197ff2875e68d36025`,
  Windows structured evidence SHA-256
  `1ee4b0e2cfc5bea1af2dc721318f1a07a07b678668d57a58435f2ca0a732d4f9`,
  OpenBSD supplemental live-host refresh SHA-256
  `9cf07d6c0c903ea49602e34c208527bb0c935ac26eaf1690bdb3b5e3d8dced18`,
  Windows supplemental live-host refresh SHA-256
  `306936aecfe6be8dfbc72b0913e05f924a1b9763addb1e8ebb6052e7f20fbcd3`,
  Windows current-source marker SHA-256
  `155152c0894f5d0b6d08d4f4b0d7713786e4a6c2a6dc34c40fed149f03808fed`,
  and production-like update-all evidence SHA-256
  `6b4003eee5de8265e1bae54158264571b24916e71cb8f214c4bcdf749aed9704`.
- The first consolidated Release attempt for `.32` exposed a GitHub asset
  upload 504 after the release already existed. Commit
  `e09f90545d71d48fe37f115f975b5418ce364050` hardened publication by editing
  existing releases and retrying `gh release upload --clobber` one asset at a
  time; the rerun passed and published the dogfood release.
- May 4, 2026 production-rehearsal execution:
  the repository now has a non-published stable-channel rehearsal path. Package
  Index run `25337125505` passed with CI-held package-index signing material;
  Linux Current Source Artifacts run `25337124179` and Windows Current Source
  Artifacts run `25337124379` passed; `tools-xctest` package run `25337124709`
  rebuilt the hosted Linux package artifact; Stage Release run `25337451712`
  staged and verified `0.1.0-stable-rehearsal.1` on the `stable` channel; and
  Release Signing Smoke run `25337594897` signed and verified release metadata
  with CI-held release trust material and ran the release key-rotation drill.
  This is production-cutover proof without public stable publication.
- Stable publication remains intentionally unexecuted pending final stable
  version/tag selection and fresh hosted structured OpenBSD/Windows Tier 1
  reports. The accepted April 24 structured reports and May 4 supplemental
  refreshes remain sufficient for dogfood RC proof, but not for replacing the
  final hosted stable evidence requirement.
- May 4, 2026 final-evidence workflow execution:
  `Structured Smoke Evidence` was added as the hosted checksum-pinned handoff
  for OpenBSD and Windows structured reports. Run `25338906779` passed using
  the accepted existing `.32` structured reports against the
  `release-candidate` gate, which validates the ingestion path but is not fresh
  stable evidence. `Package tools-xctest Hosted Linux` was also added and run
  `25338857779` passed for `linux-amd64-clang` and
  `linux-ubuntu2404-amd64-clang`.
- The stable tag candidate is `v0.1.0`. The support claim set for that tag is
  frozen pending final evidence: Debian/Ubuntu managed Linux, Windows MSYS2
  clang64 managed, OpenBSD native packaged, Fedora/Arch GCC interoperability,
  with Windows MSVC, OpenBSD arm64, Debian arm64, and broader Linux managed
  portability deferred.
- May 4, 2026 final `0.1.0` staging execution:
  Stage Release run `25342971361` passed for `stable/0.1.0` using the latest
  successful current-source Linux and Windows producer artifacts. Release
  Signing Smoke run `25343116683` then passed against that exact staged
  `0.1.0` artifact. The final staged payload is therefore built, verified, and
  signing-gate proven, but not published. Release Evidence and stable Release
  remain blocked on fresh structured OpenBSD and Windows reports for `v0.1.0`.

- Phase 26 release-candidate smoke gate:
  on April 27, 2026, `scripts/dev/run-smoke-tests.py --release-gate release-candidate`
  passed with the accepted OpenBSD and Windows Tier 1 reports:
  `.artifacts/phase26-openbsd-tier1-20260424/openbsd-tier1-report.json` and
  `.artifacts/phase26-windows-gorm-patched-20260424/windows-tier1-report-patched-gorm.json`.
  The companion `--phase26-exit-status` check also passed with those reports.
  The Windows dogfood full-CLI artifact was rebuilt from the current tree,
  smoke-tested on a short-lived `windows-2022` lease, and republished to the
  `dogfood` GitHub release as
  `gnustep-cli-windows-amd64-msys2-clang64-0.1.0-dev-dogfood.20260427T162104Z.g31c1872c5dfd.28.zip`
  with SHA-256
  `2e7be6c43e75be52fcb53402f4b131b461eede81d5796418abb4bdd41b08a753`.
  Refreshed dogfood release metadata was re-uploaded after local provenance
  digest verification.
- OpenBSD:
  preflight and live libvirt refresh passed on April 14, 2026 using the
  `~/.ssh/otvm` operator keypair; on the same date a fresh OpenBSD lease also
  used `pkg_add` to install `gnustep-make`, `gnustep-base`, `gnustep-libobjc2`,
  and `gmake`, and then passed a native packaged GNUstep Foundation
  compile-link-run probe. A fresh April 17, 2026 lease also built the current
  full CLI, ran version/help/doctor, and passed package install/remove smoke
  after fixing native OpenBSD OS detection; on April 20, 2026 a fresh OpenBSD
  7.8 amd64 lease rebuilt patched `tools-xctest`, installed it through the native
  full CLI, ran `xctest --help`, ran a minimal XCTest bundle, removed the
  package, and destroyed the lease. See the evidence in
  [openbsd-debian-libvirt-refresh.md](/home/danboyd/gnustep-cli-new/docs/validation/openbsd-debian-libvirt-refresh.md) and
  [tools-xctest-openbsd-78-20260420](/home/danboyd/gnustep-cli-new/docs/validation/tools-xctest-openbsd-78-20260420/tools-xctest-openbsd-amd64-clang.json)
- Debian:
  preflight and live libvirt refresh passed on April 14, 2026 using the same
  `~/.ssh/otvm` operator keypair; see the same libvirt refresh evidence
- Fedora:
  preflight and acceptance passed on April 16, 2026 using
  `oracletestvms-fedora-gnome-libvirt-20260415194036.qcow2`; a fresh lease then
  installed packaged GNUstep prerequisites, built the full CLI, passed
  `--version` / `--help`, and passed package install/remove smoke. Follow-up
  detector validation confirmed GNUstep Make uses `/usr/bin/gcc` and links
  Fedora `libobjc.so.4`; package selection now follows the GCC artifact path.
- Arch:
  preflight and acceptance passed on April 16, 2026 using
  `oracletestvms-arch-gnome-libvirt-20260415214102.qcow2`; a fresh lease then
  installed `clang`, `gcc`, `gcc-objc`, `gnustep-base`, and `gnustep-make`,
  built the full CLI, passed `--version` / `--help`, emitted `doctor --json`,
  and passed package install/remove smoke. Follow-up detector validation
  confirmed GNUstep Make uses `/usr/bin/gcc` and links Arch `libobjc.so.4`;
  package selection now follows the GCC artifact path, and setup correctly keeps
  managed installation as the preferred modern-runtime path.
- Windows:
  libvirt readiness, MSYS2 assembly, native full-CLI build, `--version` /
  `--help`, package install/remove smoke, refreshed staged release-artifact
  package-flow qualification, public-manifest bootstrap setup with trace
  evidence, and extracted-toolchain rebuild plus explicit-manifest `doctor`
  qualification passed on April 17, 2026 against `windows-2022` libvirt leases.
  The April 19/20 refreshed RC1 staged-release lane also passed PowerShell bootstrap setup from the local release manifest, installed `gnustep.exe`, invoked help through `cmd.exe`, and validated `doctor --json` after replacing a stale Windows CLI artifact with a freshly rebuilt Objective-C binary. The remaining Windows gap is production trust-root handling and CI persistence of the evidence bundle, not bootstrap/full-CLI behavior.

## otvm Libvirt Operator Shape

- use a dedicated libvirt config file rather than the default provider config
- use `danboyd@iep-vm1`, `danboyd@iep-vm2`, and `danboyd@iep-ocr01`
- use `qemu+ssh://danboyd@<host>/system`
- use `guest_access_mode = "direct-lan"`
- use the published farm images:
  - Windows: `oracletestvms-windows2022-eval-libvirt-20260414153225.qcow2`
  - Debian: `oracletestvms-debian13-wayland-libvirt-20260414181129.qcow2`
  - OpenBSD: `openbsd78-fvwm.qcow2`
  - Fedora: `oracletestvms-fedora-gnome-libvirt-20260415194036.qcow2`
  - Arch: `oracletestvms-arch-gnome-libvirt-20260415214102.qcow2`
- use the checked-in config template:
  - [otvm-libvirt.example.toml](/home/danboyd/gnustep-cli-new/docs/validation/otvm-libvirt.example.toml)
- use the release-generated validation plan when preparing a staged release:
  - `otvm-host-validation-plan.json`
  - `python3 scripts/internal/build_infra.py --json otvm-release-host-validation-plan --release-dir <release-dir>`
- use the checked-in runner to regenerate the plan and summarize target checks:
  - `scripts/dev/run-otvm-release-validation.sh dist/stable/<version> ~/oracletestvms-libvirt.toml`
- every live validation run must use short TTLs and explicit `destroy` cleanup;
  `otvm list` should show zero active leases before closing the release gate

## Phase Status

- Phase `23.D` now has fresh live evidence for:
  - OpenBSD
  - Debian
  - Fedora
  - Arch
- Fedora and Arch are no longer blocked on external host availability through
  `otvm`; their distro GNUstep stacks are classified as GCC interoperability
  targets, while preferred modern-runtime validation must use managed
  Clang/libobjc2 artifacts.
- Phase `23.E` is complete because:
  - release gates are green
  - release-candidate docs now match the current validation evidence
  - OpenBSD and Debian claims are backed by fresh live evidence
  - Windows evidence now reflects successful host setup, native CLI build,
    package install/remove smoke, and refreshed staged release-artifact
    qualification
  - Fedora and Arch are described accurately as live-validated GCC
    interoperability targets that require managed Clang/libobjc2 for preferred
    modern-runtime workflows


## April 19, 2026 RC1 Execution Update

The next release-candidate milestone was executed locally as `dist/stable/0.1.0-dev-rc1` using the known-good `0.1.0-dev` artifact bytes with refreshed release metadata. The first attempt to restage RC artifacts through `stage-release` exposed an important packaging hazard: archive inputs were treated as bundle directories, producing a CLI tarball that contained the prior tarball instead of an installable `bin/gnustep` tree. That release-tooling bug is now fixed with regression coverage, and the final RC1 candidate was regenerated through the fixed `stage-release` path.

Completed April 19 gates:

- Python/shared regression: `python3 -m unittest discover -s tests` passed with 134 tests after adding archive-input staging regression coverage.
- Native Objective-C regression: `scripts/dev/run-native-tests.sh` passed through tools-xctest.
- Bootstrap no-Python regression is now covered by `tests/test_bootstrap_sh.py`; the POSIX bootstrap contains no `python3` or `scripts/internal/*.py` references.
- Existing `dist/stable/0.1.0-dev` artifact verification passed, but its manifest predates the current `metadata_version` trust-gate requirement.
- Corrected `dist/stable/0.1.0-dev-rc1` verification passed.
- Corrected `dist/stable/0.1.0-dev-rc1` signed release trust gate passed using the bundled local development public key.
- Corrected `dist/stable/0.1.0-dev-rc1` controlled release gate passed with the generated package index in unsigned development mode.
- Corrected `dist/stable/0.1.0-dev-rc1` local extraction qualification passed for Linux and Windows CLI/toolchain artifacts after restaging through the fixed `stage-release` command.
- Debian clean-machine dogfood passed on lease `lease-20260419230951-mb6y20` (`172.17.2.190`): bootstrap setup, installed CLI version/help, `doctor --json`, managed Foundation compile/run, `gnustep new`, `gnustep build`, `gnustep run`, and package install/remove all completed successfully. The cleanup trap destroyed the lease. After the `stage-release` fix, local bootstrap setup against the restaged RC1 manifest also passed and produced `toolchain_compatible` from installed `doctor --json`.
- Release-scoped OTVM plan generation passed for Debian, OpenBSD, and Windows.
- OpenBSD `openbsd-7.8-fvwm` lease readiness passed on lease `lease-20260419231454-fcy9ew` and the runner destroyed the lease.
- Windows `windows-2022` lease readiness passed on lease `lease-20260419231557-mguj9c` and the runner destroyed the lease.
- Final OTVM list reported zero active leases after the run.

April 19/20 upgrade-lifecycle follow-up:

- Native setup now has regression coverage for downgrade rejection, expired metadata rejection, revoked selected artifacts, runtime-bundle double-wrap prevention, package conflict rejection, and versioned `releases/<version>` snapshot materialization.
- Debian old-to-new upgrade dogfood was exercised with synthetic managed-built `0.1.1` -> `0.1.2` release directories because the previously staged `0.1.0-dev` old artifact predates update-command support. The live lane verified update planning and upgrade execution and exposed policy/runtime issues that were fixed in native setup and the dogfood script.


April 20 lifecycle and staged-release validation refresh:

- Native setup now smoke-validates versioned managed releases before switching the `current` pointer and installs the root `bin/gnustep` as a current-pointer launcher.
- `setup --rollback` is implemented and covered by native regression tests for preserved previous-release restoration.
- Update checks now persist and enforce accepted manifest metadata freshness: downgrade, expired metadata, revoked selected artifacts, and frozen older generated metadata are rejected before upgrade.
- Debian old-to-new upgrade dogfood passed again against current managed-built synthetic `0.1.1` -> `0.1.2` releases staged under `/tmp/gnustep-upgrade-dogfood-stage`; lease `lease-20260420113227-frxel7`, guest `172.17.2.129`, result `{"ok":true,"summary":"Debian upgrade dogfood validation passed."}`.
- Staged-release OTVM smoke passed for Debian, OpenBSD, and Windows against `/tmp/gnustep-combined-otvm-stage/stable/0.1.2`; Debian lease `lease-20260420113557-ivc8kd`, OpenBSD lease `lease-20260420113851-i0f0xy`, Windows lease `lease-20260420114127-2ltr8j`. Final OTVM list reported zero active leases.
- The combined validation release used the current Linux CLI bundle plus existing Windows prerelease artifacts from `dist/stable/0.1.0-dev`; this is valid smoke evidence for the host lanes, but not a production Windows artifact refresh.

Remaining RC follow-up from this execution:

- Continue hardening release staging by requiring explicit input modes and preserving toolchain metadata sidecars for archive-input releases. The immediate archive-wrapping bug is fixed and covered by regression tests.
- Use production signing keys or CI-held signing material for any production claim; the April 19 RC1 signatures are local-development evidence only.
- Refresh Windows release artifacts from the current source tree before making a production Windows claim; the April 20 Windows smoke reused the existing prerelease Windows artifacts.
- Keep the existing published `0.1.0-dev` manifest classified as prerelease evidence unless it is republished with current `metadata_version` metadata and signatures.

## Exit Condition For Follow-Up Validation

The remaining external follow-up is:

- artifact-level qualification remains green
- OpenBSD and Debian release-candidate acceptance remains repeatable against
  the current farm images and `~/.ssh/otvm` operator key material; Debian amd64
  and OpenBSD amd64 `tools-xctest` package dogfood evidence is now recorded
- Windows libvirt host validation should use the same release-generated
  `otvm` plan rather than a separate OCI-oriented workflow
- Windows libvirt validation currently requires local `mtools` support for the
  current `OracleTestVMs` path; guest readiness, MSYS2 assembly, native CLI
  build, package install/remove host validation, and refreshed staged release
  artifact qualification now pass on the current Windows qcow2 image
- Fedora and Arch managed Clang/libobjc2 qualification should be run on fresh
  hosts now that the distro GNUstep packages are classified as GCC
  interoperability-only
- the recorded support claims in [support-matrix.md](/home/danboyd/gnustep-cli-new/docs/support-matrix.md)
  match the collected evidence

## April 21 Phase 12/13/14/18 Execution Update

Local execution for Phases 12, 13, 14, and 18 is now represented in the machine-readable release-candidate qualification snapshot returned by `release_candidate_qualification_status()`.

Completed or locally enforced:

- Phase 12: release trust gates, package-index trust gates, package artifact publication gates, `tools-xctest` release gates, no-bundled-Python handoff qualification, and key-rotation drill helpers are implemented and regression covered.
- Phase 13: native `gnustep update` owns CLI, package, and default all-scope update planning/application; rollback, stale transaction recovery, downgrade rejection, expired metadata rejection, revoked artifact rejection, and package-update rollback are covered.
- Phase 14: the current command surface runs through the native Objective-C CLI with aligned help, JSON envelopes, command dispatch, and staged cross-platform smoke evidence.
- Phase 18: Linux amd64 managed native CLI execution is validated, staged cross-platform artifacts have host-backed smoke evidence, and release qualification fails if bundled Python runtime trees reappear in the installed full CLI bundle.

Remaining external production blockers:

- Provision CI-owned production signing keys or a signing service for release and package-index metadata.
- Move host-backed qualification from operator-run lanes into automated release jobs.
- Promote package artifact build plans into controlled build jobs that produce signed artifacts.
- Run old-to-new update dogfood against two real published update-capable releases, including one `update all --yes` run that covers both CLI/toolchain and package updates.
- Finish native `doctor` deep-detection parity before claiming full native diagnostic replacement.
- Build every final Tier 1 full-CLI artifact from production build lanes rather than reusing staged or prerelease evidence.

May 4 completion-pass update:

- Hosted evidence persistence now covers supplemental live-host refreshes. The
  `Release Evidence` workflow accepts optional fresh OpenBSD and Windows OTVM
  smoke summary URLs and stores them as
  `otvm-openbsd-7.8-fvwm-smoke.json` and `otvm-windows-2022-smoke.json`.
  `release-evidence-bundle` includes those files as
  `openbsd-live-host-refresh` and `windows-live-host-refresh` entries when
  present, while keeping the formal Phase 26 gate tied to structured scenario
  reports.
- Package artifact publication now checks that publishable artifacts have both
  materialized build evidence and validation evidence. The committed
  `tools-xctest` build evidence records under
  `docs/validation/tools-xctest-build-evidence/` close the durable provenance
  gap for the current package manifest.
- The remaining production blockers are now final production operation
  blockers rather than dogfood RC blockers: run the final stable-channel
  release with final trust roots, production artifact producers, hosted
  structured live-host evidence, and post-release update/rollback validation.

## April 27 Phase 12/13 Production-Like Update

Local production-like hardening now passes the Phase 12 and Phase 13 gates with explicit release and package-index trust roots, signed metadata, the existing OpenBSD and Windows Tier 1 smoke reports, and `gnustep update all --yes` evidence at `.artifacts/phase13-local-production-like/evidence/update-all-production-like.json`.

The update-all run covered a CLI/toolchain transition plus a package update. It also found and fixed a native state-preservation bug: package state could disappear after the CLI/toolchain update, and the Phase 13 evidence validator did not previously reject failed raw package update entries.

Remaining production blockers:

- Keep the controlled `Package Index`, `Release Inputs`, `Stage Release`, and
  `Release Evidence` producer chain green and repeatable for each new release
  candidate.
- Re-run the signed metadata and `update all --yes` path on clean Windows/OpenBSD/Linux Tier 1 hosts from the release lanes.
- Keep the new native `update all --yes` regression and raw-package evidence checks in the release gate before RC sign-off.

April 27 hosted workflow update:

- GitHub Actions CI is green on `master` at commit `f67a390a`.
- `Package Index` run `25021604641` passed and produced
  `gnustep-signed-package-index` with digest
  `sha256:39814e18490372ecbf0803de40206aa41d88f29254d5fcd024735dde777ee97e`.
- `Release Inputs` run `25021838530` passed and produced the hosted CLI and
  toolchain input artifacts consumed by `Stage Release`.
- `Stage Release` run `25021894289` passed and produced
  `gnustep-staged-release` for `0.1.0-dev-hosted.1`.
- `Release Evidence` run `25022173894` passed and produced
  `gnustep-release-evidence-inputs`.
- `Release` run `25022880046` passed and published prerelease
  `v0.1.0-dev-hosted.1`:
  `https://github.com/danjboyd/gnustep-cli-new/releases/tag/v0.1.0-dev-hosted.1`.
  Its release evidence artifact digest is
  `sha256:6b3033c148a0ad5a83e24da75fde4fc730f9698c8d36c857afe6021c239edf88`.
- Published release asset digests include Linux CLI
  `sha256:15190139967c202fee652301bdca8fb7e6d833cafe5447a34c55562f22fac682`,
  Linux toolchain
  `sha256:d9ce78d16d28842f7bedd24dbd2de64e16f67c064fbeb1d6ab1b372780ddff1b`,
  Windows CLI
  `sha256:8a1b0cf6f8db2f79ecc0c478532a213650131584baf4e2f7184c3b3364aa271e`,
  and Windows toolchain
  `sha256:1c07368c338c47502409fb996463ec53ff33324a6ede9cc29339fcda944a11a3`.
- This dogfood release passed with `allow_stale_windows_artifact=true`, using
  the approved April 24 Windows smoke artifact as hosted evidence. Production
  Windows refresh remains blocked until a current-source hosted Windows build
  and live smoke run replace that exception.

April 28 execution update:

- Added a `Windows Current Source Artifacts` workflow to produce hosted Windows
  CLI/toolchain artifacts plus `windows-current-source-artifact.json` from the
  workflow source revision.
- Added a `Published URL Qualification` workflow to produce hosted Linux smoke
  evidence from a published release manifest URL.
- Added a `Package tools-xctest` workflow to generate controlled package
  artifacts from declared source provenance in CI.
- Release now requires Linux smoke evidence, writes
  `release-qualification-summary.json`, and refuses stale Windows artifacts
  outside the `dogfood` channel.
- Native `doctor` now includes a structured `toolchain.features` check for
  normalized Objective-C feature flags.
- April 28 follow-up: CI passed at commit `7444b101` in run `25069081363`.
  `Windows Current Source Artifacts` run `25069092549` passed with fresh
  `assemble-msys2`, current-source full-CLI build, workflow smoke, and uploaded
  artifact `gnustep-windows-current-source-artifacts` (`6691317171`).
  `Package tools-xctest` run `25069093408` passed and uploaded
  `gnustep-package-tools-xctest-linux-amd64-clang` (`6691217427`).
- Published-URL qualification against `v0.1.0-dev-hosted.1` failed in run
  `25068782043` because that immutable dogfood manifest contains malformed
  GitHub asset URLs. The generator and Stage Release workflow are fixed in
  `7444b101`; the published-URL lane should be rerun against the next candidate,
  not counted as a pass for `v0.1.0-dev-hosted.1`.
- Remaining RC blocker: stage/publish a new dogfood candidate with fixed
  manifest URLs and the current-source Windows artifact, then collect
  published-URL Linux, Windows live, and OpenBSD live smoke evidence before
  rerunning release without the stale Windows exception.

## April 30 Roadmap Audit Result

The remaining release plan is still the right shape, but the short critical
path now supersedes the older phase sequence. The project is not blocked on
command skeleton work; it is blocked on candidate freshness, production trust
material, release-lane evidence, and native `doctor` parity.

Immediate RC sequence:

- Stage and publish a new candidate from the fixed manifest URL generator.
- Use current-source Windows artifacts; do not carry
  `allow_stale_windows_artifact=true` into a release-candidate or stable claim.
- Run published-URL Linux qualification against the new candidate.
- Collect fresh Windows and OpenBSD live smoke reports for the same candidate.
- Feed Linux, Windows, OpenBSD, and update-all evidence through `Release
  Evidence`.
- Rerun `Release` without the stale-Windows exception.

The release workflow now has an aggregate machine-check for this list:
`python3 scripts/internal/build_infra.py --json immediate-rc-blocker-status`.
The gate composes Phase 12, Phase 13, release-claim consistency, controlled
package artifact readiness, Linux published-URL evidence, Windows
current-source evidence, and release qualification summary checks. It is
expected to fail until the exact candidate has all required evidence and no
stale-Windows exception.

Support-claim note: OpenBSD `amd64` remains a native packaged GNUstep claim for
the current release. Managed OpenBSD artifact publication is optional future
work unless the roadmap is explicitly revised to require it.
