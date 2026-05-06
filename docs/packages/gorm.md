# Gorm Package

Gorm is packaged as a GNUstep GUI application.

## Runtime Requirements

- Required runtime profile: `desktop`
- Required components: `org.gnustep.runtime.base`, `org.gnustep.runtime.gui`, `org.gnustep.runtime.back`
- Headless installs are not supported.

The package manager must reject Gorm for `server` and `ci` profiles unless those profiles explicitly provide GUI and Back runtime components.

## Install

```sh
gnustep install org.gnustep.gorm --profile desktop
```

## Validation Status

| Target | Status | Evidence |
| --- | --- | --- |
| Linux amd64 Clang | Published | `docs/validation/package-build-boundary-20260505/gorm-linux-amd64-clang-local-install-remove.json` |
| Linux Ubuntu 24.04 amd64 Clang | Built, pending publication | GitHub Actions run `25402506608` |
| OpenBSD amd64 Clang | Published | `docs/validation/package-install-remove-20260506/gorm-openbsd-amd64-clang-install-remove.json` |
| Windows amd64 MSYS2 clang64 | Built and install/remove validated; GUI publication blocked by model-load failure | `.artifacts/windows-gorm-gui-lease-20260506170706-iava3r/output/summary.json` |

The Windows Gorm package must remain unpublished until the `expected char and got object` model-load failure is fixed and a windows-2022 validation run captures a visible Gorm window.
