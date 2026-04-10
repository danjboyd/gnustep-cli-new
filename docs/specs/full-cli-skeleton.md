# Full CLI Skeleton

The full CLI is scaffolded as a GNUstep Objective-C tool under `src/full-cli/`.

Current implementation goals:

- establish a GNUstep Make entry point
- centralize command dispatch in Objective-C
- keep command names and global help aligned with the bootstrap interface
- execute the shipped command set natively in Objective-C/GNUstep

This implementation is intentionally conservative so it can remain compatible with the broader GCC/Clang policy discussed for the project.

## Current Runtime Shape

The full CLI now has a small Objective-C runtime structure rather than a single
hard-coded command switch:

- [GSCommandContext.h](/home/danboyd/gnustep-cli-new/src/full-cli/GSCommandContext.h)
- [GSCommandContext.m](/home/danboyd/gnustep-cli-new/src/full-cli/GSCommandContext.m)
- [GSCommandRunner.h](/home/danboyd/gnustep-cli-new/src/full-cli/GSCommandRunner.h)
- [GSCommandRunner.m](/home/danboyd/gnustep-cli-new/src/full-cli/GSCommandRunner.m)

Current responsibilities are split this way:

- `GSCommandContext` parses global options and normalizes the command invocation
- `GSCommandRunner` owns help/version behavior, JSON envelope handling, command
  validation, repository-root discovery, and command dispatch

## Native Command Runtime

The full CLI now implements its shipped command set directly in Objective-C.

Current native command coverage:

- `doctor`
- `setup`
- `build`
- `run`
- `new`
- `install`
- `remove`

The Objective-C runtime now owns:

- command dispatch
- JSON envelope generation
- release-manifest loading for `doctor` and `setup`
- GNUstep Make project detection for `build` and `run`
- template generation for `new`
- managed package state handling for `install` and `remove`

## Current Verified State

The current full GNUstep CLI is no longer compile-only. Repository verification currently covers:

- print top-level help and version output
- emit structured JSON envelopes
- native command dispatch for the shipped command set
- native `doctor` and `setup` payload generation
- native template generation and package-state operations

Live validation now also covers a real Linux managed-toolchain build of the
native Objective-C CLI plus smoke execution of `doctor`, `setup`, `new`,
`build`, `run`, `install`, and `remove`.

The repository test suite no longer treats the full CLI as a Python-backed
dispatcher. Remaining validation work is now cross-target host coverage rather
than removal of a transitional Python runtime path.
