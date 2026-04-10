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
