# Full CLI Skeleton

The full CLI is scaffolded as a GNUstep Objective-C tool under `src/full-cli/`.

Current skeleton goals:

- establish a GNUstep Make entry point
- centralize command dispatch in Objective-C
- keep command names and global help aligned with the bootstrap interface
- leave `doctor` and `setup` as explicit stubs until deeper integration is implemented

This scaffold is intentionally conservative so it can remain compatible with the broader GCC/Clang policy discussed for the project.

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

## Transitional Backend

For now, the Objective-C full CLI dispatches command execution into the tracked
helper scripts under `scripts/internal/`:

- `doctor.py`
- `setup_plan.py`
- `build.py`
- `run.py`
- `new_project.py`
- `install_package.py`
- `remove_package.py`

This is an interim Phase 18 step so the full GNUstep-based command can act as
the real top-level interface while deeper GNUstep-native command bodies are
implemented.

Current full-CLI behavior differences from the raw helper scripts:

- `build` and `run` execute by default from the Objective-C CLI
- `install` and `remove` inject the default managed root automatically when the
  caller does not pass `--root`
- delegated backend commands run from the caller's current working directory
  rather than the repository root

## Current Verified State

The current full GNUstep CLI is no longer compile-only. It has been verified on
the managed Linux Clang toolchain to:

- print top-level help and version output
- emit structured JSON envelopes
- delegate `doctor` successfully through the Objective-C front end
- execute `setup` successfully through the Objective-C front end against a
  staged release manifest
- create new projects with `new`
- build a generated CLI-tool project with `build`
- run that generated project with `run`

The current implementation still uses the tracked Python helpers as a
transitional backend, but the installed Objective-C/GNUstep binary is now the
real command entry point for those flows.
