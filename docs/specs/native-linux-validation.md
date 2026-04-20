# Native Linux Validation

This document records the current validation intent for the Linux distributions
we are actively targeting in this push.

## OpenBSD

- treat the packaged `pkg_add` GNUstep/Clang environment as the preferred
  native path when compatibility checks pass
- keep OpenBSD follow-up validation centered on the packaged path rather than a
  managed OpenBSD toolchain by default
- validate `doctor` and `setup` evidence showing that the packaged native path
  remains preferred
- validate package install/remove behavior on that packaged native path once
  the relevant reviewed package artifacts exist

## Fedora

- treat the packaged Clang/libobjc2 GNUstep environment as a supported native
  toolchain candidate
- capture `doctor --json` evidence proving `native_toolchain_assessment` is
  `supported`
- capture `setup --json` evidence proving `install_mode` is `native`
- validate package install/remove behavior from a generated package index

## Arch

- treat the packaged Clang/libobjc2 GNUstep environment as a supported native
  toolchain candidate
- capture `doctor --json` evidence proving `native_toolchain_assessment` is
  `supported`
- capture `setup --json` evidence proving `install_mode` is `native`
- validate package install/remove behavior from a generated package index

## Debian

- continue treating stock GCC-oriented packaged environments primarily as
  interoperability evidence unless and until a distro-packaged Clang/libobjc2
  path is validated to the same standard
- keep the Debian GCC interoperability plan distinct from Fedora/Arch native
  validation
- for the current OpenBSD and Debian libvirt refresh path, use the dedicated
  `otvm` libvirt config documented in
  [openbsd-debian-libvirt-refresh.md](/home/danboyd/gnustep-cli-new/docs/validation/openbsd-debian-libvirt-refresh.md)
  rather than the default provider config

## Evidence Minimum

- exact package versions for GNUstep and compiler inputs
- `clang --version` or `gcc --version` output as applicable
- `doctor --json` output
- `setup --json` output
- package install/remove JSON output
- cleanup confirmation for any disposable validation host
