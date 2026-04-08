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

## Exit Codes

- `0`: success
- `1`: operational failure
- `2`: usage error
- `3`: environment failure or command unavailable in bootstrap
- `4`: compatibility mismatch
- `5`: internal error

