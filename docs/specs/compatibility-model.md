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

## GCC Policy

- GCC environments are detected and classified.
- GCC is not rejected ideologically.
- v1 managed artifacts are not promised for GCC unless validated GCC artifacts are actually published.

