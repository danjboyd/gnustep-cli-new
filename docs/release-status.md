# Release Status

Detailed release, validation, and known-gap notes for maintainers. The
user-facing overview is in the [README](../README.md).

## Release Asset Policy

Published release assets are immutable (see "Immutable Release Assets" in
[AGENTS.md](../AGENTS.md); adopted October 22, 2026). A fix ships as a new
version, or as a new asset name, never by overwriting a published file.
`github-release-publish` enforces this: it skips assets already published with
identical bytes and refuses the whole publish if any existing asset would
change. The October 13 and 15, 2026 replacements on `v0.1.0` listed below
predate the policy.

## Current Status

The repository currently contains:

- project requirements and architectural policy in [AGENTS.md](../AGENTS.md)
- an implementation roadmap in [docs/implementation-roadmap.md](implementation-roadmap.md)
- bootstrap scripts under `scripts/bootstrap/`
- the Objective-C full CLI under `src/full-cli`
- a generated package repository under `packages/`
- schema drafts under `schemas/`
- automated regression coverage under `tests/` and `src/full-cli/Tests`
- a project requirement that new features, bug fixes, and roadmap subphases include automated unit/regression coverage before being considered complete

### Shipped In Repo

- native `doctor`, `setup`, `build`, `run`, `new`, `install`, `remove`, and `update` command implementations exist in the full Objective-C CLI
- package installation now supports package IDs resolved through a package index
- package safety checks include compatibility-aware artifact selection,
  dependency rejection, reinstall/idempotent behavior, and removal blocking for
  dependents
- the installed full CLI bundle is qualified without bundled Python runtime
  trees

### Validated Now

- the Python/shared regression suite
- the native Objective-C `tools-xctest` suite
- bootstrap-to-full handoff qualification for staged release artifacts
- package index generation determinism in CI
- fresh OpenBSD packaged-path host evidence on libvirt, including native
  package install/remove smoke after fixing OpenBSD OS detection
- fresh Debian host evidence for managed-toolchain compile-link-run,
  release-artifact package smoke, and public published-URL bootstrap/full-CLI
  qualification on libvirt
- Fedora and Arch native packaged-path qualification on disposable libvirt hosts,
  classified as GCC/libobjc interoperability paths rather than preferred modern
  Clang/libobjc2 stacks
- Windows libvirt readiness, MSYS2 assembly, native full-CLI build,
  `--version` / `--help`, package install/remove smoke on a fresh lease, and
  package-flow qualification against refreshed staged Windows release artifacts

### Published Stable Release

- `v0.1.0` is published as the stable GitHub release (first published
  May 5, 2026). Its release evidence bundle, including the OpenBSD and Windows
  Tier 1 reports, is in `docs/validation/release-0.1.0-evidence/`.
- Install on Debian 13 (trixie) `amd64` or `arm64`, or Ubuntu 26.04 LTS `amd64`:

  ```sh
  curl -fsSL https://github.com/danjboyd/gnustep-cli-new/releases/download/v0.1.0/gnustep-bootstrap.sh | sh -s -- setup --user
  ```

  The release-asset bootstrap is stamped `CLI_VERSION="0.1.0"`, selects the
  stable `v0.1.0` manifest, and verifies it against the pinned production
  release trust root. The raw `scripts/bootstrap/gnustep-bootstrap.sh`, on
  `master` or at the `v0.1.0` tag, reports `0.1.0-dev` and installs from the
  `v0.1.0-dev` prerelease instead.
- The signed stable manifest scopes the Debian Linux artifacts to Debian with an
  ICU 76 / glibc 2.41 runtime gate, and the Ubuntu artifacts to Ubuntu 26.04 with
  an ICU 78 / glibc 2.43 gate. Debian 12 and Ubuntu 24.04 are not covered by the
  stable manifest.
- On June 3, 2026 Debian 13 `arm64` CLI and toolchain artifacts were added to
  `v0.1.0` (evidence:
  `docs/validation/linux-arm64-debian13-stable-publish-20260603.json`).
- On October 13, 2026 the `amd64` CLI and toolchain on `v0.1.0` were replaced
  with Debian 13 builds and the release metadata was re-signed. The previous
  `amd64` toolchain was a mislabeled Debian 12 bookworm build that bundled
  glibc 2.36 and ICU 72 and crashed on Debian 13. Evidence, including the old
  and new checksums:
  `docs/validation/linux-amd64-debian13-stable-republish-20261013.json`.
- On October 13, 2026 Ubuntu 26.04 LTS `amd64` CLI and toolchain artifacts
  (built in `ubuntu:26.04`, clang 21) were added to `v0.1.0`. Their evidence tier
  is a clean `ubuntu:26.04` container on a GitHub-hosted runner, not a VM:
  `docs/validation/linux-ubuntu2604-amd64-stable-publish-20261013/`.
- On October 13, 2026 the Debian 13 `amd64` and `arm64` CLIs were rebuilt with
  version stamping against the unchanged published toolchains and re-signed;
  both now report `0.1.0`. Stable `arm64` was validated through the published
  bootstrap for the first time (container tier). Evidence:
  `docs/validation/linux-debian13-cli-version-stamp-20261013/`.
- On October 15, 2026 the three Linux toolchains (Debian 13 `amd64`/`arm64`,
  Ubuntu 26.04 `amd64`) were rebuilt from the same pins so their `GNUstep.sh`
  prepends `<root>/lib` (libobjc2, libdispatch, BlocksRuntime) to
  `LD_LIBRARY_PATH`, then republished and re-signed; the CLIs are unchanged.
  Evidence: `docs/validation/linux-toolchain-runtime-lib-republish-20261015/`.
- The stable manifest also carries the Windows `amd64` MSYS2 `clang64` CLI and
  toolchain. OpenBSD `amd64` is a native packaged-GNUstep path, not a managed
  artifact.

### Still Blocked Or Pending

- release builds stamp the CLI version (`GNUSTEP_CLI_VERSION`), so the stable
  Linux CLIs (Debian 13 `amd64`/`arm64`, Ubuntu 26.04 `amd64`) report `0.1.0`
  and check the `v0.1.0` manifest for updates; the Windows MSYS2 CLI has not
  been rebuilt and still reports `0.1.0-dev`
- no official package has an Ubuntu 26.04 artifact yet
- the `amd64` official package artifacts on `v0.1.0` (Arlen, Gorm,
  `tools-xctest` snapshots from May 5, 2026) were built against the previous
  bookworm toolchain and have not been rebuilt or revalidated on Debian 13
- managed GNUstep shared libraries have no RUNPATH, and upstream GNUstep
  Make's `GNUstep.sh` does not add `<root>/lib` (libobjc2, libdispatch,
  BlocksRuntime) to the loader path. The Linux toolchains on `v0.1.0` patch the
  managed `GNUstep.sh` to prepend it since October 15, 2026. Installs made
  before then keep the old `GNUstep.sh`, and `gnustep update` reports them as
  current because the version did not change; re-running the bootstrap `setup`
  command refreshes them. Because the patched `GNUstep.sh` prepends
  `<root>/lib`, libraries there take precedence over system libraries for
  every process started from that shell
- the managed toolchains' libobjc2 has the `@synchronized` first-lock race
  (gnustep/libobjc2#424); it is fixed upstream but not in a tagged release, and
  the managed toolchains will pick it up with the next libobjc2 tag. See
  "Known Runtime Issues" in `docs/support-matrix.md`
- finish native Objective-C `doctor` deep-detection parity with the shared model
  before claiming the full CLI as the authoritative diagnostic implementation
- repaired Linux managed artifact portability beyond the explicitly scoped
  Debian and Ubuntu managed targets remains deferred; Fedora and Arch are
  currently GCC/libobjc interoperability paths unless per-distro managed
  Clang/libobjc2 artifacts are built and validated
- package-index trust metadata, provenance generation, signing, trust-gate
  validation, and signed-index enforcement in package-index consumer paths are
  implemented for the official package repository path; hosted Linux
  `tools-xctest` rebuilds pass, while target-native package rebuilds for
  OpenBSD, Windows, and arm64 remain to be completed or explicitly deferred
- OpenBSD `amd64` release claims are native packaged GNUstep claims; managed
  OpenBSD artifact publication is optional future work, not a current
  release-candidate blocker

### otvm Libvirt Note

For current `otvm`-backed validation, use libvirt rather than the default OCI
config. This now applies to the VM-backed GNUstep CLI validation path
generally, including Windows work as `OracleTestVMs` rolls out libvirt-backed
Windows leases. Use a dedicated libvirt config based on
[otvm-libvirt.example.toml](validation/otvm-libvirt.example.toml)
and the refresh procedure in
[openbsd-debian-libvirt-refresh.md](validation/openbsd-debian-libvirt-refresh.md).
Release preparation also emits `otvm-host-validation-plan.json`, and
`scripts/internal/build_infra.py otvm-release-host-validation-plan` can
regenerate that release-scoped Debian/OpenBSD/Windows libvirt validation plan
for any staged release directory.

## Planned Scope

Initial commands:

- `setup`
- `doctor`
- `build`
- `run`
- `new`
- `install`
- `remove`
- `update`

Bootstrap only supports `setup` and `doctor`, but should expose the full CLI surface in help output. Bootstrap is an onboarding and recovery tool, not the normal updater after the full CLI is installed.

Update scope:

- `gnustep update --check` should compare installed CLI/toolchain and package state against signed release/package metadata without mutating the install.
- `gnustep update cli` should update the full CLI and managed toolchain through staged, verified, rollback-capable activation.
- `gnustep update packages` should upgrade installed packages through the signed package index and package transaction model.
- `gnustep update` / `gnustep update all` should coordinate CLI/toolchain and package updates through one coherent plan.
- `setup --check-updates` and `setup --upgrade` are compatibility/internal lifecycle hooks only; user-facing documentation should not present setup as the update command, and there should be no `setup --update` syntax.
- `gnustep setup --repair` should remain the recovery path for interrupted or corrupted lifecycle operations.

Build backend scope:

- `gnustep-make` is the first implemented backend and uses `GNUmakefile` / `make`.
- `cmake` is a core planned backend using `CMakeLists.txt` / `cmake`.
- `xcode-buildtool` is a core planned backend using libs-xcode `buildtool` and `*.xcodeproj`.
- Help and diagnostics should say `GNUstep project` unless the message is specifically backend-specific.

The current release goal is not "managed toolchain only". `doctor` and `setup`
should be able to distinguish among:

- preferred native packaged toolchain paths
- supported but not preferred native paths
- interoperability-only native paths
- incompatible native paths that should use the managed toolchain instead

