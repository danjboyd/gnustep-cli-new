# Command Contract Draft

This document captures the current v1 command-line contract at a high level.

## Top-Level Form

```text
gnustep <command> [options] [args]
```

## Commands

- `setup`
- `doctor`
- `build`
- `clean`
- `run`
- `new`
- `install`
- `remove`
- `update`

## Global Options

- `--help`
- `--version`
- `--json`
- `--verbose`
- `--quiet`
- `--yes`

## Output Policy

- human-readable output is the default and is not a stability contract
- `--json` is the machine-readable stability contract

## Doctor Contract

- `gnustep doctor` exists in both bootstrap and full interfaces.
- bootstrap and full must use the same top-level command form, JSON envelope shape, status vocabulary, and check identifiers
- bootstrap `doctor` is limited to installer-oriented and setup-relevant diagnostics
- full `doctor` may run deeper toolchain and environment validation that is unavailable in bootstrap
- when a shared doctor check is defined but not executable in bootstrap, the result should be represented structurally rather than pretending the check was run
- `doctor` should identify when an existing platform-native toolchain is usable so `setup` can recommend reusing it instead of always steering the user toward a managed install
- on OpenBSD specifically, `doctor` should evaluate the packaged GNUstep environment as a first-class candidate and report clearly when it is supported for CLI use
- for the current release, `doctor` should support explicit native-toolchain discovery and classification work on OpenBSD, Fedora, Debian, and Arch
- `doctor` should make it possible to distinguish:
  - preferred packaged/native toolchain path
  - supported but not preferred native path
  - interoperability-only native path
  - incompatible native path that should use the managed toolchain instead


## Setup And Update Contract

- `setup` is the authoritative onboarding, configuration, repair, and recovery command for the full CLI and managed toolchain.
- Bootstrap remains a one-time onboarding and recovery interface; it should not become the normal update wrapper once the full CLI is installed.
- `gnustep update` is the canonical user-facing command for day-2 lifecycle updates after the full CLI is installed.
- `gnustep update --check` should be read-only and should return a structured plan describing installed CLI/toolchain versions, latest compatible release versions, package-index freshness, installed package update availability, selected channel, metadata identity, and whether any action is needed.
- `gnustep update cli` should apply compatible CLI/toolchain updates transactionally: fetch and verify signed metadata, download and verify artifacts, stage extraction, smoke-validate the candidate release, activate through the stable current pointer, preserve rollback state, and report the final active version.
- `gnustep update packages` should refresh and verify the package index, select compatible newer artifacts for installed packages, verify artifact integrity/signatures, and upgrade packages transactionally.
- `gnustep update all` should coordinate CLI/toolchain and package updates in dependency-safe order; `gnustep update` with no explicit scope should default to `all` and require confirmation unless `--yes` is supplied.
- CLI/toolchain update JSON must include stable fields for current version, available version, selected artifacts, manifest digest, compatibility blockers, transaction state, previous release path, active release path, and next actions.
- Package update JSON must include stable fields for package id, current version, available version, selected artifact, compatibility blockers, transaction state, and next actions.
- `setup --check-updates` and `setup --upgrade` are compatibility/internal lifecycle hooks only and should not be the documented user-facing update syntax.
- `setup` must not grow a `--update` option.
- `gnustep setup --rollback` should restore the preserved previous managed release when an upgrade has completed but must be backed out; it may remain the explicit rollback command until a separate rollback UX is designed.
- `gnustep setup --repair` should recover interrupted installs/upgrades and normalize managed state before another update is attempted.

## Build, Clean, And Run Contract

- `gnustep build` and `gnustep run` are GNUstep project commands, not GNUstep-Make-only commands.
- `gnustep build --help` should describe "Build the current GNUstep project."
- `gnustep run --help` should describe "Run the current GNUstep project."
- Backend selection should be available through `--build-system <id>`.
- Stable backend IDs are `gnustep-make`, `cmake`, and `xcode-buildtool`.
- The user-facing selector `xcode` may be accepted as an alias for `xcode-buildtool`.
- Auto-detection should select a backend only when exactly one supported marker is present.
- Ambiguous backend detection should fail with exit code `2` and structured JSON explaining the candidate backends.
- Backend unavailability, such as missing `cmake` or `buildtool`, should fail with exit code `3` when the project marker is otherwise supported.
- GNUstep Make aggregate projects are valid build projects and must not be rejected because the top-level `GNUmakefile` lacks direct `TOOL_NAME`, `APP_NAME`, or `LIBRARY_NAME` assignments.
- `gnustep clean` is the canonical clean-only command. `gnustep build --clean` should not be the primary documented UX because users reasonably read it as "clean, then build".
- `gnustep clean` should use the selected backend clean operation and should report backend, invocation, and exit status in JSON.
- `gnustep shell` is a Windows-only full-CLI diagnostic escape hatch for opening the managed private MSYS2 `CLANG64` environment; it is intentionally outside the portable v1 core workflow and should not drive general product documentation or support claims.
- `run` may apply stricter target detection than `build`, but run-specific ambiguity must not be reported as an unsupported build project.

## Exit Codes

- `0`: success
- `1`: operational failure
- `2`: usage error
- `3`: environment failure or command unavailable in bootstrap
- `4`: compatibility mismatch
- `5`: internal error

## Setup Contract

- `setup` should not assume that managed installation is always preferred when a compatible existing toolchain is already present.
- When `doctor` has established that an existing external toolchain is supported for the requested workflow, `setup` should be able to recommend or adopt that environment rather than forcing a managed toolchain install.
- In structured output, that decision should be visible through `plan.install_mode`
  and `plan.disposition`.
- On OpenBSD, a validated packaged GNUstep environment should be considered a supported installation path and a candidate for the preferred path.
- Fedora and Arch are currently treated as supported native-toolchain candidates
  when the packaged environment matches the Clang plus `libobjc2` runtime model.
- Debian remains under current-release evaluation, but the stock GCC-oriented
  packaged path is currently treated primarily as interoperability evidence.
- If `setup` selects a managed toolchain instead of a compatible packaged OpenBSD environment, it should explain why.
