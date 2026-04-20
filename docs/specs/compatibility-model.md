# Compatibility Model Draft

The compatibility system is built around three record types:

- environment
- artifact
- requirement

Compatibility decisions answer:

- does this environment satisfy this requirement?
- does this artifact target this environment?

## Canonical Dimensions

- `os`
- `arch`
- `compiler_family`
- `toolchain_flavor`
- `objc_runtime`
- `objc_abi`
- `feature_flags`
- `can_compile`
- `can_link`
- `can_run`

## Primary v1 Managed Targets

- `linux/amd64/clang`
- `openbsd/amd64/clang`
- `windows/amd64/msys2-clang64`
- `windows/amd64/msvc`

## Current Release Native-Toolchain Discovery Goals

- The current release should explicitly investigate platform-native GNUstep package viability on:
  - OpenBSD
  - Fedora
  - Debian
  - Arch
- These investigations are not all expected to produce the same answer.
- The goal is to classify each ecosystem honestly:
  - preferred packaged toolchain path
  - supported but not preferred packaged path
  - interoperability-only path
  - incompatible path that should use the managed toolchain instead
- OpenBSD and Fedora are currently the most plausible packaged-toolchain candidates for a preferred or supported native-package path because they may ship a Clang plus `libobjc2`-oriented stack.
- Arch is also now treated as a supported native-package candidate when its packaged GNUstep environment matches the Clang plus `libobjc2` runtime model.
- Debian remains a current-release discovery target, but today it is primarily treated as a GCC interoperability path unless a validated packaged Clang plus `libobjc2` stack is proven.

## Deferred Native-Toolchain Discovery Targets

- The following distro families are explicitly deferred beyond the current release target set:
  - openSUSE
  - RHEL-family distributions and clones
  - Alpine
- They remain valid future investigation targets, but they should not expand the current release validation scope until the higher-leverage current-release targets are classified first.

## OpenBSD Packaged Toolchain Policy

- OpenBSD system packages should be treated as a first-class external toolchain path, not as an inherently inferior fallback.
- If the OpenBSD-packaged GNUstep stack satisfies the CLI's capability and compatibility requirements, it should be considered a supported environment.
- On OpenBSD, a compatible packaged Clang/GNUstep environment is a candidate for the preferred installation path because it reuses platform-native packages instead of forcing a managed toolchain build.
- Managed OpenBSD toolchains remain useful when the packaged environment is missing required capabilities, fails validation, or does not match the runtime assumptions of the requested workflow.
- Compatibility decisions for OpenBSD should remain capability-based:
  - compiler family
  - Objective-C runtime
  - Objective-C ABI
  - required feature flags
  - compile/link/run capability
  - required GNUstep components
- The CLI must not silently mix a system-packaged OpenBSD toolchain with incompatible managed artifacts.
- `doctor` should distinguish between:
  - compatible OpenBSD packaged toolchain available for use
  - packaged toolchain present but broken
  - packaged toolchain present but incompatible with the requested workflow
  - no usable packaged toolchain detected

## GCC Policy

- GCC environments are detected and classified.
- GCC is not rejected ideologically.
- v1 managed artifacts are not promised for GCC unless validated GCC artifacts are actually published.
- A distro may still be a current-release discovery target even when its packaged GNUstep stack is GCC-based.
- In those cases, the release goal is to determine whether the packaged path is:
  - sufficient for interoperability validation
  - sufficient for some supported workflows
  - or incompatible with the CLI's required runtime/capability model
