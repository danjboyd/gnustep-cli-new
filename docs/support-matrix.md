# Support Matrix

This document records the current support position for the targets the
project is actively discussing.

## Current Snapshot

`v0.1.0` is published as the stable GitHub release (first published May 5,
2026; release evidence in `docs/validation/release-0.1.0-evidence/`). On June 3,
2026 Debian 13 trixie `arm64` CLI and toolchain artifacts were added to it. The
signed stable manifest scopes the Linux artifacts to Debian with an ICU 76 /
glibc 2.41 runtime gate. Ubuntu 26.04 amd64 was added on October 13, 2026 (see its entry below); Ubuntu
24.04 is not covered by the stable manifest.
Per-target notes below that describe `v0.1.0` as a candidate are historical.

On October 13, 2026 the stable `amd64` CLI and toolchain were replaced with
Debian 13 builds and the release metadata was re-signed. The previous `amd64`
toolchain (sha256 `cad89e63…`) was a mislabeled Debian 12 bookworm build: it
bundled glibc 2.36 and ICU 72 and crashed on Debian 13. The stable install
command is the release-asset bootstrap
`https://github.com/danjboyd/gnustep-cli-new/releases/download/v0.1.0/gnustep-bootstrap.sh`,
which selects the `v0.1.0` manifest and verifies it with the production trust
root. Evidence:
`docs/validation/linux-amd64-debian13-stable-republish-20261013.json`.

- `openbsd-amd64-clang`
  status: `validated_native_preferred`
  notes: packaged OpenBSD GNUstep is currently treated as the preferred native
  path when compatibility checks pass; fresh libvirt host evidence was rerun on
  April 14, 2026 using the `~/.ssh/otvm` operator keypair; a fresh lease also
  proved the native `pkg_add` path by installing `gnustep-make`,
  `gnustep-base`, `gnustep-libobjc2`, and `gmake`, then compiling, linking, and
  running a Foundation probe. On April 17, 2026 another fresh lease built the
  current full CLI, ran version/help/doctor, and passed package install/remove
  smoke after native OpenBSD OS detection was fixed. The April 27, 2026 Phase
  26 release-candidate gate also accepted the full OpenBSD Tier 1 report
  covering bootstrap install, generated project build/run, Gorm build/run, and
  CLI-only self-update. This is a native packaged release claim, not evidence
  that a managed OpenBSD toolchain artifact is published or release-blocking.
  A managed OpenBSD artifact may remain useful later, but it is optional while
  the packaged path satisfies the supported workflows. A May 4, 2026 live-host
  refresh also passed the OpenBSD packaged GNUstep compile/run smoke and is
  now persisted in the `.32` dogfood release evidence bundle as supplemental
  evidence; the full formal Tier 1 scenario claim remains backed by the
  accepted structured April 24 report until the hosted lane emits a fresh
  structured replacement.
- `fedora-amd64-gcc`
  status: `interoperability_only`
  notes: Fedora libvirt preflight and acceptance passed on April 16, 2026 using
  `oracletestvms-fedora-gnome-libvirt-20260415194036.qcow2`; a fresh host
  installed distro GNUstep packages, built the full Objective-C CLI, passed
  `--version` and `--help`, and passed package install/remove smoke. The
  packaged GNUstep Make configuration uses `/usr/bin/gcc`, and the built binary
  links against Fedora `libgnustep-base.so.1.30` plus `libobjc.so.4`, so Fedora
  distro GNUstep is a GCC/libobjc interoperability path, not the preferred
  Clang/libobjc2 runtime. Fedora Tier 1 modern-runtime workflows require the
  managed Clang/libobjc2 toolchain unless Fedora later ships a validated modern
  GNUstep stack.
- `debian-amd64-gcc`
  status: `interoperability_only`
  notes: Debian packaged GNUstep remains a GCC/libobjc interoperability target
  unless a validated packaged Clang plus `libobjc2` path is proven; fresh
  libvirt host evidence was rerun on April 14, 2026 using the same operator
  keypair
  GCC fixture: a `debian:13` container with `apt-get install gobjc
  libgnustep-base-dev gnustep-make` is a cheap GCC/legacy-runtime environment
  for exercising `doctor`'s GCC classification and the GCC guidance messages
  (used by Performance Dashboard, October 2026). Keep it separate from managed
  roots: Debian's GCC `libobjc` and the managed `libobjc2` both use the SONAME
  `libobjc.so.4`, so a process that can see both library directories may load
  the wrong runtime.
- `debian-amd64-managed-clang`
  status: `dogfood_ready_partial`
  notes: Debian libvirt dogfood validation passed on April 16, 2026 against
  freshly staged local `linux/amd64/clang` artifacts using
  `scripts/dev/debian-dogfood-validation.sh`. The run completed bootstrap
  `setup`, installed full CLI `--version` / `--help`, `doctor --json` against
  the staged manifest, a managed Foundation compile-link-run probe with the
  bundled Clang/libobjc2 runtime, and package install/remove smoke. This is
  enough for controlled Debian dogfood of setup/doctor/package flows. The
  current regenerated artifact no longer exposes the previously observed
  host-origin GNUstep Make paths in the archive audit. April 17, 2026 public
  Debian release qualification passed end-to-end from the public GitHub release
  manifest after rebuilding the Linux CLI against the managed source-built
  toolchain, adding runtime SONAME aliases, and adding full-CLI HTTPS manifest
  downloader fallback. Signing/provenance remains pending before any production
  security claim. The managed Linux build base is now pinned to Debian 13 trixie
  (glibc 2.41, ICU 76) via `toolchains/linux-amd64-clang/Dockerfile`; Debian 12
  bookworm is deprecated. The previously published `v0.1.0` / `.32` artifacts
  were built on Debian 12 bookworm (ICU 72) and do not load on Debian 13 because
  GNUstep base links the versioned ICU SONAMEs and ICU has no cross-major ABI
  compatibility. The artifact must be rebuilt on the trixie base, the Linux CLI
  rebuilt against that managed prefix, then restaged, re-signed, and re-validated
  on a Debian 13 host before the trixie support claim is evidence-backed.
  October 13, 2026: done. The trixie amd64 CLI and toolchain are on stable
  `v0.1.0`, and a native Debian 13 amd64 host completed bootstrap `setup
  --user`, `doctor`, `new`/`build`/`run`, and a Foundation compile-link-run
  probe through the published stable bootstrap. Evidence:
  `docs/validation/linux-amd64-debian13-stable-republish-20261013.json`.
- `debian-arm64-managed-clang`
  status: `published_stable_debian13`
  notes: June 3, 2026: Debian 13 arm64 CLI and toolchain artifacts were
  published on the stable `v0.1.0` release and validated on a native Debian 13
  aarch64 host (toolchain libraries resolve against ICU 76 / glibc 2.41, and a
  Foundation program compiled with the published toolchain ran); evidence in
  `docs/validation/linux-arm64-debian13-stable-publish-20260603.json`. That
  validation used direct artifact download. October 13, 2026: the arm64 CLI
  was rebuilt with version stamping (reports `0.1.0`) and validated through
  the published stable bootstrap in a clean `debian:13` arm64 container
  (container tier; evidence in
  `docs/validation/linux-debian13-cli-version-stamp-20261013/`). Earlier
  history: planned Debian/aarch64 managed target for the full CLI and official
  package artifacts. Target metadata uses canonical `arch = arm64`; build and
  validation should use `../OracleTestVMs` local libvirt/mac capacity first and
  fall back to OCI only when local capacity is unavailable. No release artifact
  or installability claim exists until the managed toolchain, full CLI, and
  `tools-xctest` package artifacts are built and host-validated. The build base
  is pinned to Debian 13 trixie (glibc 2.41, ICU 76) via
  `toolchains/linux-arm64-clang/Dockerfile`; Debian 12 bookworm is deprecated.
- `ubuntu2604-amd64-managed-clang`
  status: `published_stable_container_qualified`
  notes: October 13, 2026: Ubuntu 26.04 LTS amd64 CLI and toolchain built from
  source in `ubuntu:26.04` (glibc 2.43, ICU 78, clang 21.1; libs-base,
  libs-corebase, libs-gui, and libs-back build without patches) and added to
  stable `v0.1.0` with an `ubuntu-26.04` / ICU 78 / glibc 2.43 manifest gate.
  Qualified through the published bootstrap in a clean `ubuntu:26.04.1`
  container on a GitHub-hosted runner: bundled SONAME check, setup as an
  unprivileged user, `doctor` (`toolchain_compatible`), `new`/`build`/`run`, a
  Foundation/blocks/ARC/libdispatch probe, and package install/remove with a
  fixture package. The evidence tier is a container, not a VM; Dan accepted it
  for this target. Evidence:
  `docs/validation/linux-ubuntu2604-amd64-stable-publish-20261013/`. No
  official package has a 26.04 artifact yet. arm64 is not planned for now.
- `ubuntu2404-amd64-managed-clang`
  status: `dogfood_ready_partial`
  notes: Ubuntu 24.04/amd64 now has distro-scoped managed CLI and toolchain
  artifacts built in a base Ubuntu Docker environment and published to the
  `v0.1.0-dev` prerelease. April 20, 2026 evidence covers setup from the local
  release manifest, runtime dependency closure, full `doctor --json`, and
  `tools-xctest` package install/help/minimal-bundle/remove dogfood. Production
  signing/trust-root qualification and repeatable CI/farm automation remain
  pending before a public support claim.
- `arch-amd64-gcc`
  status: `interoperability_only`
  notes: Arch libvirt preflight and acceptance passed on April 16, 2026 using
  `oracletestvms-arch-gnome-libvirt-20260415214102.qcow2`; a fresh host
  installed distro GNUstep packages, built the full Objective-C CLI, passed
  `--version` and `--help`, emitted `doctor --json`, and passed package
  install/remove smoke. The packaged GNUstep Make configuration uses
  `/usr/bin/gcc`, and the built binary links against Arch
  `libgnustep-base.so.1.31` plus `libobjc.so.4`, so Arch distro GNUstep is a
  GCC/libobjc interoperability path, not the preferred Clang/libobjc2 runtime.
  Arch Tier 1 modern-runtime workflows require the managed Clang/libobjc2
  toolchain unless Arch later ships a validated modern GNUstep stack.
- `openbsd-arm64-clang`
  status: `package_lifecycle_validated_managed_toolchain_deferred`
  notes: planned OpenBSD/arm64 target for the full CLI and official package
  artifacts. The latest OracleTestVMs exposes accepted profile
  `openbsd-7.8-arm64`, and May 7, 2026 acceptance passed with the accepted image
  when using `/home/danboyd/.ssh/otvm/id_rsa.pub`. OTVM lease
  `lease-20260507215030-3q6vbf` built the native full CLI, built patched
  `tools-xctest`, installed it by simple alias, ran `xctest --help`, ran a
  minimal XCTest bundle, and removed it by simple alias. Managed toolchain
  publication remains disabled until a source-built OpenBSD arm64 toolchain is
  produced and smoked.
- `windows-amd64-msys2-clang64`
  status: `managed_target_staged_artifacts_validated`
  notes: planned Tier 1 managed target with live host and staged release-artifact
  evidence for the current implementation; on April 17, 2026 lease
  `lease-20260417160327-z8fnih` assembled the checked-in MSYS2 `clang64`
  toolchain path including `sha256sum.exe`, rebuilt the full Objective-C CLI,
  passed `--version` / `--help`, installed a staged Windows package with native
  SHA-256 verification, and removed it successfully. Lease
  `lease-20260417171734-djj1b9` then qualified the refreshed staged Windows
  release ZIPs directly: extracted the CLI/toolchain artifacts, ran
  `gnustep.exe --version` and `--help`, installed a package fixture, and removed
  it successfully. The GitHub prerelease assets have since been published and
  digest-verified, and signed/provenance metadata is published. Follow-up
  direct-process diagnostics on lease `lease-20260417195907-fnazf6` passed
  public-manifest setup from the GitHub prerelease endpoint, retained setup
  trace evidence, and isolated the installed `doctor --json` hang to native path
  handling. The native fix bounds Windows repository-root walks, makes
  managed-install integrity state detection install-root based, recognizes MSYS
  `/c/...` managed roots and preserved `clang64/bin`, and treats deferred
  Windows active probes as deferred rather than broken. The extracted toolchain
  then rebuilt the Objective-C CLI and
  `doctor --json --manifest C:\Windows\Temp\minimal-release-manifest.json`
  exited `0` with `toolchain_compatible`. The remaining gap is production
  signing/trust-root management and turning this published-URL/runtime evidence
  into an automated release qualification lane. On April 27, 2026 the dogfood
  Windows full-CLI artifact was rebuilt from the current tree, smoke-tested on a
  short-lived Windows lease, republished to the `dogfood` GitHub release, and
  accepted by the Phase 26 release-candidate gate with the Windows MSYS2
  `clang64` Tier 1 report. A May 4, 2026 live-host refresh then proved
  PowerShell bootstrap and installed full-CLI smoke against the fixed flat
  `bin/gnustep.exe` CLI archive path, and that summary is now persisted in the
  `.32` dogfood release evidence bundle. That refresh supplements the accepted
  structured Tier 1 report; it does not replace the formal scenario report
  until the hosted evidence lane emits a new structured Windows report.
- `windows-amd64-msvc`
  status: `deferred`
  notes: explicitly deferred for the v0.1.x line

## Managed Linux Artifact Status

- The current `linux/amd64/clang` managed artifacts install on Fedora and Arch
  through native `setup`, and setup correctly chooses managed mode when distro
  GNUstep is GCC/libobjc interoperability-only.
- The Unix launcher now stages the native runtime binary under
  `libexec/gnustep-cli/bin/gnustep` and sets managed runtime library paths
  before execution.
- Freshly staged April 16, 2026 Linux managed artifacts now include the
  transitive runtime libraries seen by `ldd`, a populated compiler sysroot C
  header tree, unversioned linker names for GNUstep Base and libobjc, and
  text-only setup relocation. This fixed the Debian dogfood path, including
  `doctor`, a managed Foundation compile-link-run probe, `gnustep new`,
  `gnustep build`, `gnustep run`, and package install/remove on a fresh Debian
  libvirt lease after installing host prerequisites `clang` and `make`.
- The checked-in `dist/stable/0.1.0-dev` artifacts were regenerated in-place on
  April 17, 2026, pass local manifest verification plus local release
  qualification, and match the digest-verified `v0.1.0-dev` GitHub prerelease
  assets.
- Fedora and Arch were rerun with the refreshed artifact on April 16, 2026 and
  remain blocked for managed Clang/libobjc2 support because the Debian-built
  artifact is not portable: Fedora lacks `libcurl-gnutls.so.4`; Arch lacks
  `libxml2.so.2`.
- The managed Linux build base is pinned to Debian 13 trixie (glibc 2.41, ICU
  76) through `toolchains/linux-amd64-clang/Dockerfile` and
  `toolchains/linux-arm64-clang/Dockerfile`, and the `debian:12` CI containers in
  `published-url-qualification.yml` and `linux-current-source-artifacts.yml` are
  retargeted to `debian:13`. Debian 12 bookworm is deprecated. This is a
  release-floor change: trixie-built artifacts (glibc 2.41 / ICU 76) will not run
  on bookworm, which is the intended trade. The durable follow-up is to bundle
  the transitive runtime closure (ICU, libxml2, libcurl-gnutls, libgnutls, libffi)
  into the managed prefix so the artifact stops being pinned to a single distro
  release; until then, each ICU major bump requires a rebuild.
- Policy decision for the current release candidate: do not advertise the
  Debian-built `linux/amd64/clang` artifact as portable across all Linux distro
  families. Either publish it as Debian-qualified only, add per-distro managed
  artifacts, or close the dependency bundle before claiming Fedora/Arch managed
  Clang/libobjc2 support.

## Known Runtime Issues

- libobjc2 `@synchronized` first-lock race
  ([gnustep/libobjc2#424](https://github.com/gnustep/libobjc2/issues/424)).
  The source-built managed toolchains pin libobjc2 at `b67709a`, which predates
  the upstream fix (`fab3df2`, PR #430, merged October 13, 2026 and not yet in
  a tagged release). The Windows MSYS2 `clang64` toolchain uses MSYS2's libobjc2
  package and is affected until MSYS2 ships the fix. When several threads
  race the first `@synchronized` on a fresh object, the process can hang, lose
  mutual exclusion, or abort. Associated objects share the same lock, so
  racing the first `objc_setAssociatedObject` on a fresh object is affected,
  as is libs-base KVO, which does `@synchronized(object)` when the first
  observer is added. Single-threaded first use, and `@synchronized` on class
  objects, are not affected.
  Policy: the managed toolchains move to the next upstream libobjc2 tag that
  contains the fix rather than carrying a backport. Until then, applications
  that need the fix can build a custom toolchain (`docs/custom-toolchains.md`)
  with a C backport of `fab3df2` in their lock's libobjc2 `patches`; the
  Custom Toolchain CI workflow builds with one
  (`tests/fixtures/custom-toolchain-ci/patches/libobjc2/`) and runs a race
  probe against it.

## Deferred Discovery Targets

- openSUSE
- RHEL-family distributions and clones
- Alpine

## Evidence Meaning

- `validated_native_preferred`: policy, tests, and host evidence currently
  support preferring the packaged native path
- `interoperability_only`: the environment is useful for interoperability and
  GCC reality checks, but not currently treated as the preferred runtime model
- `managed_target_incomplete`: the managed target remains part of the roadmap,
  but release-candidate validation is not complete
- `dogfood_ready_partial`: live validation supports controlled internal use for
  the named flows, but public release claims still have documented gaps
- `deferred`: tracked, but not part of the current v0.1.x release target
