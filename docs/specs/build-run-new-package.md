# Build, Run, New, And Package Tooling

This document records the current Phase 7-9 implementation baseline.

## Build

- `build` currently detects GNUstep Make projects by looking for `GNUmakefile`.
- Supported initial project markers are:
- `TOOL_NAME`
- `APP_NAME`
- `LIBRARY_NAME`
- The initial backend remains `make`.

## Run

- `run` currently plans execution for:
- tools via direct execution from `./obj/<tool-name>`
- apps via `openapp <AppName>.app`
- unsupported or ambiguous project states fail clearly.

## New

- `new` currently supports:
- `gui-app`
- `cli-tool`
- `library`
- generated projects include a minimal `package.json` placeholder to support later packaging work.

## Package Tooling

- `gnustep package init` creates a package manifest skeleton.
- `gnustep package validate` checks required core fields and kind-specific requirements.
- validation currently enforces the basic policy shape already defined in `AGENTS.md`.

