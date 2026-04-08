# gnustep-cli-new

This repository is a fresh start for a new GNUstep CLI.

The design is intentionally split into two interfaces:

- a bootstrap CLI for `setup` and `doctor`
- a full CLI implemented as an Objective-C/GNUstep application

The old repository at `../gnustep-cli` is reference material, not an architectural constraint.

## Current Status

The repository currently contains:

- project requirements and architectural policy in [AGENTS.md](/home/danboyd/gnustep-cli-new/AGENTS.md)
- an implementation roadmap in [docs/implementation-roadmap.md](/home/danboyd/gnustep-cli-new/docs/implementation-roadmap.md)
- initial Phase 1-3 scaffolding:
- schema drafts under `schemas/`
- bootstrap scripts under `scripts/bootstrap/`
- baseline tests under `tests/`

## Planned Scope

Initial commands:

- `setup`
- `doctor`
- `build`
- `run`
- `new`
- `install`
- `remove`

Bootstrap only supports `setup` and `doctor`, but should expose the full CLI surface in help output.

## Development

Run the baseline test suite with:

```bash
python3 -m unittest discover -s tests
```

