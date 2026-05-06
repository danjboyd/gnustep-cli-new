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
| Windows amd64 MSYS2 clang64 | Built, install/remove validated, and GUI launch validated; pending publication | `.artifacts/windows-gorm-gui-lease-20260506193205-xdf6dm/output-interactive-ci-25458527191/summary.json` |

The Windows package omits the toolbar and formatter palettes for now because those archived resources fail under the managed Windows GNUstep runtime. The CI-produced package from run `25458527191` has passed windows-2022 interactive GUI validation with a visible Gorm window.
