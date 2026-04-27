# Release Publication

This document records the current Phase 19 implementation status.

## Current Publication Model

- GitHub Releases is the intended official artifact store.
- Release discovery still flows through `release-manifest.json`, not through
  GitHub page scraping.
- The same signed release manifest is the authoritative source for initial install, update checks, and full CLI/toolchain upgrades.
- Published managed runtime artifacts must be produced from explicit locked
  inputs, preferably pinned upstream source built by project-controlled
  automation for targets where this project compiles the component.
- Distro-derived or host-copied GNUstep runtime trees may be used during
  bring-up only when clearly marked provisional; they must not be promoted as
  official managed artifacts without source/input locks, provenance, and
  release qualification evidence.
- A staged release directory currently contains:
  - CLI archives
  - managed toolchain archives
  - `release-manifest.json`
  - `SHA256SUMS`

## Implemented Tooling

The current release pipeline is implemented through
[`build_infra.py`](/home/danboyd/gnustep-cli-new/src/gnustep_cli_shared/build_infra.py)
and
[`scripts/internal/build_infra.py`](/home/danboyd/gnustep-cli-new/scripts/internal/build_infra.py).

Implemented subcommands include:

- `stage-release`
- `verify-release`
- `otvm-release-host-validation-plan`
- `qualify-release`
- `qualify-full-cli-handoff`
- `github-release-plan`
- `github-release-publish`
- `prepare-github-release`
- `controlled-release-gate`
- `release-trust-gate`
- `sign-release-metadata`
- `refresh-local-release-metadata`
- `build-linux-cli-against-managed-toolchain`
- `linux-cli-abi-audit`

`prepare-github-release` is the current controlled orchestration path for:

- staging release assets
- verifying checksums and manifest consistency
- extracting artifacts into a qualification root
- optionally running bootstrap-to-full handoff qualification
- generating a release-scoped `otvm` host-validation plan for Debian, OpenBSD,
  and Windows libvirt targets
- emitting the exact GitHub publish plan that would be executed next
- emitting a package-artifact build plan from the reviewed `packages/` tree so package publication inputs are explicit before release publication

The GitHub release workflow now treats the staged release directory as a
workflow-owned input. Its default `release_source` is `staged-artifact`, which
downloads a named artifact from a specified workflow run into
`dist/<channel>/<version>` before signing, gating, evidence bundling, and
publication. The legacy `checked-in` source remains available for bring-up, but
release-candidate and production runs should use staged artifacts from
controlled build/prep jobs. The `Release Inputs` workflow is the controlled
handoff for externally produced release input bytes: it accepts explicit URLs
and SHA256 values, verifies them in GitHub Actions, and uploads
`gnustep-input-*` workflow artifacts. The `Stage Release` workflow then
downloads CLI/toolchain artifacts from a specified workflow run, stages a
release directory through `stage-release`, verifies the release directory, and
uploads `gnustep-staged-release`. Release-claim consistency is enforced later
by the release workflow after hosted smoke and update evidence inputs are
available.

Package-index custody can follow the same artifact handoff model. The default
`package_index_source` is `signed-artifact`: the release workflow downloads a
signed package-index metadata artifact, verifies it against
`GNUSTEP_CLI_PACKAGE_INDEX_TRUST_ROOT`, and diffs the signed index against the
index generated from the reviewed `packages/` tree. `sign-in-workflow` remains
available when a repository explicitly chooses to hold the package-index private
key in Actions secrets. The `Package Index` workflow is the controlled producer
for the signed package-index handoff and uploads `gnustep-signed-package-index`.

Release evidence custody follows the same pattern. The `Release Evidence`
workflow accepts explicit report URLs and SHA256 values, verifies the evidence
bytes in GitHub Actions, and uploads `gnustep-release-evidence-inputs`. The
release workflow can download that artifact before running Phase 26 and Phase
12/13 gates, so release qualification does not depend on operator-local
`.artifacts/` paths.

## Current Verified State

- A real staged prerelease payload now exists under `dist/stable/0.1.0-dev`.
- The first private GitHub prerelease has been published at
  `v0.1.0-dev`.
- The staged payload includes:
  - the built full GNUstep CLI archives for Linux and Windows MSYS2 `clang64`
  - the managed toolchain archives for Linux and Windows MSYS2 `clang64`
  - a manifest with real file checksums
  - `SHA256SUMS`
- Release qualification can verify checksums and extract staged artifacts into a
  disposable install root for validation.
- Release preparation now also emits `otvm-host-validation-plan.json` alongside
  the staged release so host-backed Debian/OpenBSD/Windows validation uses a
  release-specific contract rather than ad hoc operator notes.
- The shared `setup` backend can now install from a staged release manifest into
  a managed root with checksum verification and PATH guidance.
- Manifest-driven update planning and transactional upgrade activation are now exposed through native `gnustep update` for staged releases, including smoke validation, current-pointer activation, rollback state, and frozen-metadata rejection. Debian upgrade/rollback dogfood passed again on April 20, 2026 using this path. Production signing/key-rotation remains the release-claim blocker.
- Linux CLI release artifacts must be built against the managed source-built GNUstep/libobjc2 prefix, not the host GNUstep Make environment. `build-linux-cli-against-managed-toolchain` is now a shared build-infra command, with a dev wrapper at `scripts/dev/build-linux-cli-against-managed-toolchain.sh`; it produces the artifact, refreshes local release metadata when requested, and runs `linux-cli-abi-audit` to reject legacy GCC Objective-C class symbols before staging.
- Host-backed validation on April 20, 2026 passed fresh Debian setup/package/project dogfood, Debian update/rollback dogfood, Windows bootstrap/full-CLI smoke, and OpenBSD smoke against libvirt leases. The OpenBSD lane also produced and dogfooded a real patched `tools-xctest` package artifact for the package publication gate.
- The shell bootstrap has been live-qualified from the private GitHub Release
  assets on Linux outside the repository tree.
- A live libvirt-backed Windows `otvm` lease successfully assembled the MSYS2
  managed toolchain, built the full GNUstep CLI with an explicit `HAVE_MODE_T`
  define, and produced publishable Windows prerelease artifacts.

## Current Blockers

- Windows public-manifest setup has now passed from the public GitHub
  prerelease endpoint with durable JSONL trace evidence. The SSH/session-loss
  failure mode is no longer the active setup blocker; keep `--trace` and
  `GNUSTEP_BOOTSTRAP_KEEP_TEMP=1` in the runbook for future live diagnostics.
- The Windows MSYS2 extracted-toolchain rebuild blocker is resolved for the
  current `msys2-clang64` path: the managed archive must preserve `clang64/bin`
  and include the MSYS `usr/bin` executable/DLL runtime closure so the extracted
  toolchain can run `bash`, `make`, and checksum tooling without relying on the
  original `C:\msys64` installation.
- Windows libvirt readiness is now working on the farm with the published
  `oracletestvms-windows2022-eval-libvirt-20260414153225.qcow2` image and the
  current `OracleTestVMs` readiness flow, and the staged `0.1.0-dev` bootstrap
  path is no longer blocked on PowerShell zip extraction.
- broader cross-target host validation is still incomplete as production CI
  evidence production and published-URL qualification are not yet fully wired,
  even though the release publication workflow can now consume a staged release
  directory artifact from another workflow run and the current Linux managed
  toolchain assembly and managed-prefix CLI artifact now pass Debian lease-side
  setup/project/package and update/rollback dogfood against freshly staged
  release artifacts
- `prepare-github-release` still generates the host-validation plan but does not
  itself execute live `otvm` farm actions; live validation remains an explicit
  follow-up step so local release staging is not coupled directly to farm
  availability
- `scripts/internal/build_infra.py --json package-artifact-build-plan --packages-dir packages` now exposes the reviewed package publication inputs explicitly, and `package-artifact-publication-gate` fails release publication while source or artifact digest placeholders remain. `tools-xctest-release-gate` is the stricter Phase 24 lifecycle gate: Debian amd64, Ubuntu amd64, and OpenBSD amd64 now have patched, published-in-metadata, validated artifacts with native install/smoke/minimal-bundle/remove evidence; Linux arm64, OpenBSD arm64, and Windows/MSYS2 remain non-publishable: Linux arm64 is blocked on the Phase 16.B2 managed Clang/libobjc2 toolchain after Ubuntu/aarch64 live validation exposed a GCC/libobjc runtime mismatch; Windows/MSYS2 is blocked on refreshing the toolchain artifact to include the MSYS runtime closure needed by GNUstep Make; OpenBSD arm64 is blocked on host/profile access.
- production signing policy is documented in `docs/security-production-signing.md`; release and package-index signing keys must remain distinct, release publication now requires package-index signing material, and production gates must verify against externally pinned trust roots
- update safety now has native downgrade, expiry, revocation, freeze, smoke-validation, rollback, and live upgrade/rollback dogfood coverage; release tooling now includes a key-rotation drill, evidence bundle generation, and a Windows current-source marker, while production signing keys, externally pinned trust roots, current-source Windows artifact evidence, and CI persistence remain required before production update claims
- MSVC remains explicitly deferred and unpublished for the v0.1.x line.

## Immediate Follow-Up

- wire `build-linux-cli-against-managed-toolchain` into the main controlled release-prep entrypoint so `prepare-github-release` consumes managed-prefix CLI artifacts by default instead of requiring a separate dev-wrapper invocation
- fold the refreshed Windows MSYS2 assembly and extracted-toolchain rebuild
  evidence into the normal release qualification job, then refresh the staged
  Windows CLI/toolchain release artifacts from that path
- rerun Windows host-backed package install/remove validation with the refreshed
  binary and refreshed toolchain artifact, then extend
  the current installed CLI smoke into broader package install/remove validation
  using the libvirt-backed `otvm` path
- keep the Windows bootstrap extraction path covered by regression tests so
  staged Windows releases continue to install from local or published manifests
- keep OpenBSD host-side package validation on the native packaged `pkg_add`
  path rather than shifting it to managed-toolchain work by default
- use the now-working Debian/OpenBSD libvirt path to extend host-side release
  artifact smoke validation as stronger artifacts become available
- use the generated `otvm-host-validation-plan.json` as the canonical input for
  Debian/OpenBSD/Windows host-backed release qualification
- keep update-check, `gnustep update cli`, package-update planning/application, and rollback coverage in the signed staged old/new release gate before public update claims; setup lifecycle hooks remain compatibility/internal recovery coverage only
- require `release-evidence-bundle`, `release-key-rotation-drill`, `controlled-release-gate`, and `release-claim-consistency-gate` to pass in CI before publication
- decide when to make releases public versus keeping them private during bring-up

## Local Staged Release Refresh

When a developer rebuilds a local staged artifact after `release-manifest.json` has already been generated, they must refresh the manifest artifact digests, `SHA256SUMS`, provenance, and signatures before running bootstrap or OTVM dogfood validation. Use:

```sh
scripts/dev/refresh-local-release-metadata.sh dist/stable/0.1.0-dev --private-key /path/to/dev-release-private.pem
```

This helper is for local/dev-channel staging only. It delegates to the shared build-infra `refresh-local-release-metadata` command so local dogfood uses the same digest/signature refresh logic as tests. It must not be used to bypass the production release workflow, trusted release signing keys, source-built toolchain requirements, or published-URL qualification gates. Development signing keys should be generated outside the repository, passed with `--private-key`, and deleted or stored according to local operator policy; production release and package-index keys remain separate trust roots.

## Managed-Prefix CLI Artifact Build

Linux release CLI archives must be produced from the managed GNUstep/libobjc2 prefix that will run them. The supported local/dev command is:

```sh
PRIVATE_KEY=/path/to/dev-release-private.pem \
VERSION=0.1.1-dev \
scripts/dev/build-linux-cli-against-managed-toolchain.sh
```

The wrapper calls the shared `build-linux-cli-against-managed-toolchain` build-infra command, runs the ABI audit, smoke-tests the installed binary against the extracted managed runtime, archives the CLI bundle, and optionally refreshes release metadata/signatures. Production release jobs must use the same managed-prefix build model with production signing keys and externally pinned trust roots.
