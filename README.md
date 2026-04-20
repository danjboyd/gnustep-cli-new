# gnustep-cli-new

This repository is a fresh start for a new GNUstep CLI.

The design is intentionally split into two interfaces:

- a bootstrap CLI for `setup` and `doctor`
- a full CLI implemented as an Objective-C/GNUstep application

The old repository at `../gnustep-cli` is reference material, not an architectural constraint.

## Project Goals

- Build one CLI with two interfaces:
  - a minimal bootstrap interface for installation and `doctor`
  - a full Objective-C/GNUstep interface for normal long-term use
- Prefer reusing a compatible platform-native GNUstep toolchain when that path is validated and compatible with the CLI's requirements, rather than forcing a managed install everywhere.
- Keep managed installs artifact-backed and reproducible when a native packaged path is not good enough or not yet supported.
- Treat updates as a first-class managed lifecycle responsibility of the installed full CLI: `gnustep update` should check, plan, and apply CLI/toolchain and package updates transactionally, while setup remains focused on onboarding, repair, and environment configuration.
- Treat `build` and `run` as GNUstep project commands with a backend model; GNUstep Make is first implemented, while CMake and libs-xcode/buildtool are core planned backends.
- Treat current-release native-toolchain discovery and validation as in scope for:
  - OpenBSD
  - Fedora
  - Debian
  - Arch
- Treat the following distro families as deferred future investigation targets rather than current-release requirements:
  - openSUSE
  - RHEL-family distributions and clones
  - Alpine

## Current Status

The repository currently contains:

- project requirements and architectural policy in [AGENTS.md](/home/danboyd/gnustep-cli-new/AGENTS.md)
- an implementation roadmap in [docs/implementation-roadmap.md](/home/danboyd/gnustep-cli-new/docs/implementation-roadmap.md)
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

### Still Blocked Or Pending

- repaired Linux managed artifact portability beyond Debian; until then the
  current `linux-amd64-clang` managed artifact is explicitly Debian-scoped
- Windows public-manifest bootstrap setup now passes from the public prerelease
  endpoint with retained JSONL trace evidence; follow-up native runtime work
  fixed the installed `doctor --json` hang and validated the managed
  `msys2-clang64` toolchain against an explicit local manifest
- release provenance and OpenSSL-backed metadata signatures are generated,
  published, locally gate-verified, and wired into the controlled release gate;
  production still requires CI-held trust roots and key rotation/revocation
  procedures before any production security claim
- package-index trust metadata, provenance generation, signing, trust-gate
  validation, and signed-index enforcement in package-index consumer paths are
  implemented for the official package repository path
- Windows bootstrap setup can now write JSONL trace logs with `--trace` and
  preserve temporary artifacts with `GNUSTEP_BOOTSTRAP_KEEP_TEMP=1` for live
  failure diagnosis
- Windows extracted-toolchain developer rebuild is no longer blocked by loader
  errors: the assembly now preserves the `clang64` prefix and includes the MSYS
  `usr/bin` executable/DLL runtime closure needed by `bash`, `make`, and
  checksum tooling

### otvm Libvirt Note

For current `otvm`-backed validation, use libvirt rather than the default OCI
config. This now applies to the VM-backed GNUstep CLI validation path
generally, including Windows work as `OracleTestVMs` rolls out libvirt-backed
Windows leases. Use a dedicated libvirt config based on
[otvm-libvirt.example.toml](/home/danboyd/gnustep-cli-new/docs/validation/otvm-libvirt.example.toml)
and the refresh procedure in
[openbsd-debian-libvirt-refresh.md](/home/danboyd/gnustep-cli-new/docs/validation/openbsd-debian-libvirt-refresh.md).
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

## Development

Run the baseline test suite with:

```bash
python3 -m unittest discover -s tests
```

The committed package index should stay in sync with the package manifests:

```bash
python3 scripts/internal/package_repo.py --json packages --output /tmp/package-index.json >/dev/null
diff -u packages/package-index.json /tmp/package-index.json
```


Testing policy: any new feature or bug fix should include the relevant automated tests in the same change set. Native Objective-C behavior belongs in the `tools-xctest` suite; Python tests should cover bootstrap, shared tooling, schemas, package repository generation, and cross-language contracts.

Run the full regression gate, including the native Objective-C `tools-xctest`
suite for the full CLI, with:

```bash
python3 -c 'import sys; sys.path.insert(0, "src"); from gnustep_cli_shared.qa import regression_suite; import json; print(json.dumps(regression_suite(), indent=2))'
```

Or run the native suite directly with:

```bash
. ./scripts/dev/activate-tools-xctest.sh
./scripts/dev/run-native-tests.sh
```

GitHub Actions now runs both the Python/shared suite and the native
Objective-C `tools-xctest` suite on every push and pull request.
