# Fedora Native Validation Runbook

This runbook has live Fedora libvirt evidence from April 16, 2026 and remains
the repeatable procedure for follow-up qualification.

## Goal

Prove that the packaged Fedora GNUstep environment remains useful for GCC
interoperability validation, while preferred modern-runtime workflows use the
managed Clang/libobjc2 toolchain.

## Required Evidence

- exact Fedora package list for GNUstep-related packages; the April 16, 2026
  smoke required `clang`, `make`, `gnustep-base-devel`, `gnustep-make`,
  `libblocksruntime`, `libblocksruntime-devel`, `redhat-rpm-config`, and
  `gcc-objc`
- `clang --version`
- `gnustep doctor --json`
- `gnustep setup --json`
- package install/remove JSON using the generated `packages/package-index.json`
- cleanup confirmation for the disposable host

## Execution

1. Provision a disposable Fedora host through `otvm` or an equivalent runner.
2. Install packaged prerequisites:
   `dnf install clang make gnustep-base-devel gnustep-make libblocksruntime libblocksruntime-devel redhat-rpm-config gcc-objc tar gzip coreutils`
3. Run `gnustep doctor --json` and confirm the packaged stack is classified as
   GCC/libobjc interoperability rather than preferred Clang/libobjc2.
4. Run `gnustep setup --json` and confirm preferred modern-runtime setup uses
   managed artifacts unless a validated Clang/libobjc2 native stack is present.
5. Run a package flow against `packages/package-index.json`.
6. Record outputs and destroy the host.

## April 16, 2026 Evidence

- `otvm` preflight passed for `fedora-gnome-wayland`.
- `otvm` acceptance-run passed for `fedora-gnome-wayland` and destroyed the lease.
- A fresh Fedora lease built the full Objective-C CLI from `src/full-cli`.
- `gnustep --version` returned `0.1.0-dev`; `gnustep --help` displayed the full command surface.
- Package install/remove smoke passed with a local package-index fixture.
- Follow-up detector validation confirmed GNUstep Make uses `/usr/bin/gcc`, the built binary linked against Fedora `libgnustep-base.so.1.30` and `libobjc.so.4`, and package selection chose the GCC artifact path.
