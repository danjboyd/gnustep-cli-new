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
  The current `linux-amd64-clang` artifact is now Debian-scoped in metadata and
  selection policy until dependency closure or per-distro artifacts exist.
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

- OpenBSD:
  preflight and live libvirt refresh passed on April 14, 2026 using the
  `~/.ssh/otvm` operator keypair; on the same date a fresh OpenBSD lease also
  used `pkg_add` to install `gnustep-make`, `gnustep-base`, `gnustep-libobjc2`,
  and `gmake`, and then passed a native packaged GNUstep Foundation
  compile-link-run probe. A fresh April 17, 2026 lease also built the current
  full CLI, ran version/help/doctor, and passed package install/remove smoke
  after fixing native OpenBSD OS detection; see the evidence in
  [openbsd-debian-libvirt-refresh.md](/home/danboyd/gnustep-cli-new/docs/validation/openbsd-debian-libvirt-refresh.md)
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
  the current farm images and `~/.ssh/otvm` operator key material
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
