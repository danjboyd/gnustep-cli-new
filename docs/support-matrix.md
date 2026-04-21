# Support Matrix

This document records the current release-candidate support position for the
targets the project is actively discussing.

## Current Snapshot

- `openbsd-amd64-clang`
  status: `validated_native_preferred`
  notes: packaged OpenBSD GNUstep is currently treated as the preferred native
  path when compatibility checks pass; fresh libvirt host evidence was rerun on
  April 14, 2026 using the `~/.ssh/otvm` operator keypair; a fresh lease also
  proved the native `pkg_add` path by installing `gnustep-make`,
  `gnustep-base`, `gnustep-libobjc2`, and `gmake`, then compiling, linking, and
  running a Foundation probe. On April 17, 2026 another fresh lease built the
  current full CLI, ran version/help/doctor, and passed package install/remove
  smoke after native OpenBSD OS detection was fixed.
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
  security claim.
- `debian-arm64-managed-clang`
  status: `planned_build_target`
  notes: planned Debian/aarch64 managed target for the full CLI and official
  package artifacts. Target metadata uses canonical `arch = arm64`; build and
  validation should use `../OracleTestVMs` local libvirt/mac capacity first and
  fall back to OCI only when local capacity is unavailable. No release artifact
  or installability claim exists until the managed toolchain, full CLI, and
  `tools-xctest` package artifacts are built and host-validated.
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
  status: `planned_build_target`
  notes: planned OpenBSD/arm64 target for the full CLI and official package
  artifacts. Initial evidence should come from an OTVM OpenBSD arm64 profile
  or scripted access to the available OpenBSD arm64 server before publication
  is enabled; this remains blocked as of April 21, 2026.
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
  into an automated release qualification lane.
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
- Policy decision for the current release candidate: do not advertise the
  Debian-built `linux/amd64/clang` artifact as portable across all Linux distro
  families. Either publish it as Debian-qualified only, add per-distro managed
  artifacts, or close the dependency bundle before claiming Fedora/Arch managed
  Clang/libobjc2 support.

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
