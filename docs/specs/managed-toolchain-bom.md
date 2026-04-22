# Managed Toolchain Bill Of Materials

This document defines the recommended v1 bill of materials and acquisition
strategy for the managed GNUstep toolchains installed by `gnustep setup`.

It answers a simple question:

- where do the managed GNUstep libraries come from

The short answer is:

- Unix-like Clang targets should be built by project-controlled automation from
  pinned upstream GNUstep source revisions
- Windows `msys2-clang64` should initially be assembled from curated MSYS2
  packages rather than rebuilt entirely from source
- Windows `msvc` should remain a separate managed target with its own build
  pipeline and must not be conflated with the MSYS2 target

## Core Source Policy

Official managed toolchain artifacts must be assembled from explicit, locked,
reviewable inputs. For source-built targets, that means pinned upstream source
revisions built by project-controlled automation. Distro-installed GNUstep
trees, distro-generated GNUstep Makefiles, and ad hoc host library copies are
acceptable only as native packaged execution paths, interoperability validation
inputs, or clearly marked provisional staging inputs. They are not the canonical
source of truth for an official managed artifact.

Every managed artifact should be explainable from metadata: upstream URLs, exact
revisions or package identities, checksums, applied patches, configure/build
flags, target applicability, and build identity. Any exception to this policy
needs to be visible in the roadmap, release qualification notes, and artifact
metadata.

## Goals

- keep managed toolchains reproducible
- keep support claims artifact-backed
- make the source of each managed library explicit
- avoid depending on host distro packages for the managed install path
- leave room for target-specific implementation where the ecosystems differ
- use a simple initial publication channel for official artifacts

## Product Layers

The managed install should be thought of as three independently versioned
products:

1. the full `gnustep` CLI
2. the managed toolchain
3. installable packages

This document is about product layer 2.

## Managed Toolchain Definition

In v1, a managed GNUstep toolchain means a curated install root containing at
least:

- an Objective-C runtime compatible with the target
- GNUstep Make
- GNUstep Base
- GNUstep GUI
- GNUstep Back when the target supports GUI execution through the managed stack
- the metadata needed for `doctor`, `build`, and `run` to identify the
  toolchain reliably

The compiler itself is part of the target descriptor, but not every managed
toolchain needs to ship its own compiler binaries in v1. On Unix-like targets,
it is acceptable for the managed toolchain to rely on a compatible host Clang
while shipping the GNUstep runtime and library stack in the managed prefix.

## Source Of Truth

For source-built targets, the managed toolchain should be built from a pinned
source lock rather than from floating branches or distro packages.

The source lock should eventually record, at minimum:

- component name
- canonical upstream URL
- exact revision, tag, or release archive digest
- any downstream patch identifiers applied by this project
- target applicability when a patch is platform-specific

The source lock should be versioned separately from the release manifest.

## Publication Channel

For v1, the recommended official publication channel for managed toolchain
artifacts is GitHub Releases.

That means:

- toolchain archives should be uploaded as GitHub Release assets
- checksums and any signing material should be published alongside them
- the release manifest should point at those published assets

GitHub Releases is the storage and distribution layer.

The release manifest remains the discovery and compatibility layer.

Bootstrap and `setup` should therefore consume the release manifest first and
should not scrape GitHub release pages directly.

## Required Components By Target Family

### Unix-like Clang Targets

For Linux `amd64/clang`, Linux `arm64/clang` on Debian/aarch64, OpenBSD `amd64/clang`, and OpenBSD `arm64/clang`, the recommended managed
toolchain source set is:

The GNUstep Make input for this source set should come from the upstream
`gnustep/tools-make` repository. Copying a distro-installed `gnustep-config`,
Makefiles tree, or generated filesystem configuration into a managed artifact is
only a temporary bring-up shortcut unless it has been rebuilt from the locked
upstream source into the managed prefix.

- `libobjc2`
- `libdispatch`
- `tools-make`
- `libs-base`
- `libs-corebase`
- `libs-gui`
- `libs-back`

These should be built by project-controlled automation from pinned upstream
GNUstep revisions.

This is the core v1 GNUstep library BOM for Unix-like managed installs.

### Optional Unix-like Components

These may be required by specific revisions, backends, or integration choices,
but should be treated as explicit conditional dependencies rather than implicit
host assumptions:

- blocks runtime support when not fully satisfied by the chosen `libobjc2`
  configuration
- backend-specific graphics or window-system dependencies

If any of these become required, they should be named explicitly in the source
lock and build plan rather than smuggled in through ambient host state.

### Windows MSYS2 `clang64`

For Windows `amd64/msys2-clang64`, the recommended v1 strategy is not a full
from-source GNUstep stack rebuild.

Instead, the managed toolchain should initially be assembled by running the
official MSYS2 installer into a private project-controlled root, installing a
curated set of project-approved MSYS2 packages into that root, capturing the
result in project-controlled metadata, and repacking it into managed artifacts.

The expected component set includes equivalents of:

- `libobjc2`
- `libdispatch` when the curated MSYS2-based assembly supports it cleanly
- GNUstep Make
- GNUstep Base
- GNUstep CoreBase when available in a validated form for this target
- GNUstep GUI
- GNUstep Back

The important policy point is:

- the project should still publish a managed artifact
- but that artifact may be produced by curating and repackaging approved MSYS2
  package inputs rather than rebuilding the entire stack from source in v1

This keeps the user-facing product artifact-backed and reproducible while
respecting the practical reality of the MSYS2 ecosystem.

The package input manifest for this target should record:

- the MSYS2 installer URL, version/channel, checksum, and source channel
- package names
- exact package versions
- exact package repository snapshots or package digests
- any file-overwrite or conflict-resolution rules required during assembly
- the private-root layout policy, including preservation of `clang64`, `usr`,
  `etc`, and `var\lib\pacman\local`

The Windows managed artifact should initially preserve the MSYS2 package layout
closely enough that applications behave like they do under a normal
`C:\msys64\clang64` shell. In practical terms, the managed ZIP should contain a
private MSYS2-style root with `clang64`, `usr`, `etc`, and pacman local package
metadata under `var\lib\pacman\local`. A smaller hand-copied DLL subset is not
a sufficient v1 runtime target for GUI support.

Before publication, Windows `msys2-clang64` assembly must run `pacman -Qkk`
against the private root and fail the artifact if pacman reports local package
database or installed-file integrity errors. The archive audit must also reject
`var\lib\pacman\local\<package>` entries that are missing their required `desc`
metadata file.

For GUI applications, managed launch should use GNUstep's own environment
initialization and app launcher:

- managed `usr\bin\bash.exe`
- `/clang64/share/GNUstep/Makefiles/GNUstep.sh`
- `/clang64/bin/openapp`

Directly starting `Foo.app\Foo.exe` is only a fallback/debug path because it can
skip runtime setup that GNUstep GUI applications depend on.

Gorm is the release-qualification application for this target. A Windows
`msys2-clang64` managed artifact is not GUI-ready until it can build Gorm,
launch it through managed `openapp`, and produce a screenshot with the Gorm
menu, Inspector, and at least one palette window visible.

### Windows MSVC

Windows `amd64/msvc` must be treated as a genuinely separate toolchain family.

Do not model it as a minor variant of the MSYS2 target.

The recommended long-term approach is:

- a separate project-controlled build pipeline
- a separate source/input lock
- a separate managed artifact family

In v1 planning, the MSVC toolchain should remain first-class in the support
matrix, but it is acceptable for it to mature behind the Unix-like Clang and
MSYS2 `clang64` paths as long as support claims stay honest.

If the MSVC target is not yet production-ready, release policy should say so
explicitly rather than silently degrading into best-effort support.

## Recommended Component Roles

### `libobjc2`

- provides the modern Objective-C runtime for the Clang-oriented managed stack
- should be pinned explicitly
- should be probed explicitly by `doctor`
- should be treated as a hard compatibility boundary for packages that require
  modern Objective-C features

### `tools-make`

- provides the build system integration required for the v1 `build` command
- should be installed into the managed prefix
- should be treated as required for a toolchain to count as managed and usable

### `libs-base`

- required for basic Foundation-level GNUstep development
- should be treated as part of the minimum managed stack

### `libdispatch`

- should be part of the core managed install wherever it builds successfully
- should be pinned explicitly on source-built targets
- should not be treated as an incidental ambient host dependency

### `libs-corebase`

- should be part of the core managed Unix-like Clang stack
- should be pinned and versioned like the rest of the managed GNUstep
  components
- should be treated as target-conditional only where the target-specific build
  or packaging story is not yet validated

### `libs-gui`

- required for GUI app support and therefore part of the managed GUI-capable
  stack

### `libs-back`

- required for managed GUI execution on platforms where the managed toolchain is
  expected to run GNUstep GUI apps
- backend flavor and transitive system requirements should be tracked
  explicitly per target

## Build And Assembly Strategy

### Linux `amd64/clang`

Recommended strategy:

- build from upstream pinned source in project-controlled CI
- use a host Clang toolchain as the bootstrap compiler
- install into a staging prefix
- package the staged prefix as the managed toolchain artifact

### OpenBSD `amd64/clang`

Recommended strategy:

- build from upstream pinned source in project-controlled CI or dedicated build
  infrastructure
- prefer explicit OpenBSD patches recorded in project metadata rather than
  undocumented ad hoc steps
- package the staged prefix as the managed toolchain artifact

### Windows `amd64/msys2-clang64`

Recommended strategy:

- assemble from pinned MSYS2 binary package inputs
- normalize the installed tree into the project-managed prefix layout
- publish the normalized result as the managed toolchain artifact

This should still include validation and smoke testing against a blank Windows
lease, but the input source is curated packages rather than direct source
builds.

### Windows `amd64/msvc`

Recommended strategy:

- treat as an explicit parallel workstream
- source-build or otherwise produce a dedicated MSVC-compatible GNUstep stack
- publish only once it has a repeatable project-controlled build and validation
  path

## Artifact Composition

The managed toolchain artifact should not be a mystery tarball.

For each published managed toolchain artifact, project metadata should be able
to answer:

- which target it is for
- which components it contains
- which component versions or revisions it contains
- which patches were applied
- which runtime and ABI it expects
- which feature flags it is intended to satisfy

At minimum, each managed toolchain artifact should ship or be accompanied by:

- a toolchain manifest
- a source or input lock
- a component inventory
- checksums and signing metadata

## Versioning Recommendation

The managed toolchain should have its own version independent of the full CLI
version.

For example:

- CLI `0.2.0`
- managed Linux Clang toolchain `2026.04.0`

This allows the CLI to evolve without pretending the underlying GNUstep stack
changed at the same cadence.

## What We Should Not Do

- do not treat distro packages as the managed source of truth on Linux or
  OpenBSD
- do not let floating upstream branch heads define reproducible managed
  artifacts
- do not hide target-specific differences behind vague labels like `windows`
- do not claim GCC managed support unless and until GCC-targeted managed
  artifacts are actually built and validated
- do not make the managed toolchain format so opaque that `doctor` cannot
  explain what is installed

## Recommended Initial BOM Decisions

The recommended initial BOM policy for this repository is:

1. Linux `amd64/clang`: source-build `libobjc2`, `tools-make`, `libs-base`,
   `libdispatch`, `libs-corebase`, `libs-gui`, and `libs-back` from pinned
   upstream revisions.
2. Linux `arm64/clang`: source-build the same GNUstep component set on
   Debian/aarch64, using `../OracleTestVMs` local VM capacity before OCI
   fallback.
3. OpenBSD `amd64/clang`: source-build the same GNUstep component set from
   pinned upstream revisions, with any required OpenBSD patches recorded
   explicitly.
4. OpenBSD `arm64/clang`: source-build the same GNUstep component set, using the available OpenBSD arm64 server for initial evidence.
5. Windows `amd64/msys2-clang64`: assemble a managed toolchain from pinned,
   curated MSYS2 packages, including `libdispatch` if supported cleanly, and
   publish that normalized result as the official managed artifact.
6. Windows `amd64/msvc`: keep as a first-class target in the support matrix,
   but do not publish production claims for `libdispatch`, `libs-corebase`, or
   the overall managed stack until a repeatable dedicated MSVC pipeline exists.

## Immediate Follow-Up Work

The next concrete design tasks after this BOM are:

1. define the source lock schema for source-built toolchains
2. define the MSYS2 input manifest schema for the Windows `clang64` target
3. define the per-target component inventory format shipped with each managed
   toolchain artifact
4. implement actual build or assembly pipelines for each Tier 1 managed
   toolchain target
