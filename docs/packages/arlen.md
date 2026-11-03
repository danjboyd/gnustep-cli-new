# Arlen Package

Arlen is packaged as a headless GNUstep framework/tool package.

## Runtime Requirements

- Required runtime profile: `headless-base`
- Required components: `org.gnustep.runtime.base`
- Not required by default: `org.gnustep.runtime.gui`, `org.gnustep.runtime.back`

This package is suitable for headless server deployment. Installing Arlen with the `server` or `ci` profile should not pull GUI or Back runtime components unless a later optional GUI adapter is requested explicitly.

## Install

No stable release (v0.1.0 through v0.1.3) advertises a package index, so
`gnustep install arlen` doesn't work against a stable install. It works only
with an index you pass explicitly:

```sh
gnustep install arlen --profile server --index <path-or-url>
```

Canonical package ID: `io.github.danjboyd.arlen`

To install Arlen today, use Arlen's own installer (`tools/install.sh` or
`tools/install.ps1` in the Arlen repository):

- On Linux, it builds Arlen's patched runtime (libobjc2, libdispatch,
  libs-base, tools-make) from its own per-target locks. It does this with this
  repository's `build_infra.py build-custom-toolchain`, pinned by commit and
  sha256 (see [custom-toolchains.md](../custom-toolchains.md)).
- On Windows, it uses the managed MSYS2 CLANG64 toolchain from a pinned
  gnustep-cli release.

## Validation Status

"Attached to v0.1.0" below means the `0.1.0-snapshot` artifact is a release
asset on `v0.1.0`, next to an unadvertised `package-index.json`. The signed
`v0.1.0` release manifest doesn't point at that index, so a stable install
never sees these artifacts. They were built in May 2026, against the previous
(bookworm) toolchain, and haven't been rebuilt for Debian 13 or the later
stable releases; see [release-status.md](../release-status.md).

| Target | Status | Evidence |
| --- | --- | --- |
| Linux amd64 Clang headless | Attached to v0.1.0 (snapshot 20260505); not advertised | `docs/validation/package-build-boundary-20260505/arlen-linux-amd64-clang-headless-local-install-remove.json` |
| Linux Ubuntu 24.04 amd64 Clang headless | Built, never published | GitHub Actions run `25402322391` |
| Linux arm64 Clang headless | Attached to v0.1.0 (snapshot 20260507.1); not advertised | GitHub Actions run `25402206815` |
| OpenBSD amd64 Clang headless | Attached to v0.1.0 (snapshot 20260505); not advertised | `docs/validation/package-install-remove-20260506/arlen-openbsd-amd64-clang-headless-install-remove.json` |
| Windows amd64 MSYS2 clang64 headless | Attached to v0.1.0 (snapshot 20260505); not advertised | `docs/validation/package-install-remove-20260506/arlen-windows-amd64-msys2-clang64-headless-install-remove.json` |
