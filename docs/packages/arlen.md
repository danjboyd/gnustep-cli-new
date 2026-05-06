# Arlen Package

Arlen is packaged as a headless GNUstep framework/tool package.

## Runtime Requirements

- Required runtime profile: `headless-base`
- Required components: `org.gnustep.runtime.base`
- Not required by default: `org.gnustep.runtime.gui`, `org.gnustep.runtime.back`

This package is suitable for headless server deployment. Installing Arlen with the `server` or `ci` profile should not pull GUI or Back runtime components unless a later optional GUI adapter is requested explicitly.

## Install

```sh
gnustep install io.github.danjboyd.arlen --profile server
```

## Validation Status

| Target | Status | Evidence |
| --- | --- | --- |
| Linux amd64 Clang headless | Published | `docs/validation/package-build-boundary-20260505/arlen-linux-amd64-clang-headless-local-install-remove.json` |
| Linux Ubuntu 24.04 amd64 Clang headless | Built, pending publication | GitHub Actions run `25402322391` |
| Linux arm64 Clang headless | Built, pending publication | GitHub Actions run `25402206815` |
| OpenBSD amd64 Clang headless | Published | `docs/validation/package-install-remove-20260506/arlen-openbsd-amd64-clang-headless-install-remove.json` |
| Windows amd64 MSYS2 clang64 headless | Published | `docs/validation/package-install-remove-20260506/arlen-windows-amd64-msys2-clang64-headless-install-remove.json` |
