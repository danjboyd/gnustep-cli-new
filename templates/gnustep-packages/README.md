# gnustep-packages Template

This directory is a template for the future separate `gnustep-packages` repository.

Recommended top-level structure:

- `packages/<package-id>/package.json`
- optional `packages/<package-id>/README.md`
- optional `packages/<package-id>/assets/`
- optional `packages/<package-id>/patches/`
- optional `packages/<package-id>/tests/`
- `schemas/`
- `docs/`

The canonical published package index should be generated from `packages/`, not maintained by hand.

Recommended generated artifact:

- `packages/package-index.json`
