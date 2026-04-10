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
- `run`
- `new`
- `install`
- `remove`

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
- On OpenBSD, a validated packaged GNUstep environment should be considered a supported installation path and a candidate for the preferred path.
- If `setup` selects a managed toolchain instead of a compatible packaged OpenBSD environment, it should explain why.
