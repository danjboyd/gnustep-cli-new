# Package Target Readiness

Readiness states are intentionally separate:

- Built: controlled builder produced an archive.
- Validated: build evidence plus launch or install/remove evidence exists as appropriate for package kind.
- Published: archive is hosted at the package manifest URL and `publish` is true.
- Installable: package index metadata is regenerated, signed, trust-gated, and compatible with runtime-component checks.

| Package | Target | Built | Validated | Published | Installable Through Package Manager | Next Action |
| --- | --- | --- | --- | --- | --- | --- |
| Arlen | linux-amd64-clang-headless | yes | yes | yes | yes | none |
| Arlen | linux-ubuntu2404-amd64-clang-headless | yes | build only | no | no | publish after release promotion |
| Arlen | linux-arm64-clang-headless | yes | build only | no | no | publish after release promotion |
| Arlen | openbsd-amd64-clang-headless | yes | yes | yes | yes | none |
| Arlen | windows-amd64-msys2-clang64-headless | yes | yes | yes | yes | none |
| Gorm | linux-amd64-clang | yes | yes | yes | yes | none |
| Gorm | linux-ubuntu2404-amd64-clang | yes | build only | no | no | add GUI launch/install-remove evidence, then promote |
| Gorm | openbsd-amd64-clang | yes | yes | yes | yes | none |
| Gorm | windows-amd64-msys2-clang64 | yes | install/remove only; GUI blocked | no | no | fix Windows Gorm model-load failure, then rerun GUI validation |

## Remaining RC Blocker

Windows Gorm now builds with the required support DLLs and starts far enough to use the managed GNUstep Back runtime. GUI qualification still fails before a visible window appears:

- Evidence: `.artifacts/windows-gorm-gui-lease-20260506170706-iava3r/output/summary.json`
- stderr: `Exception occurred while loading model: expected char and got object`; `Failed to load Gorm`
- Package-manager install/remove evidence: `docs/validation/package-install-remove-20260506/gorm-windows-amd64-msys2-clang64-install-remove.json`

Do not publish `gorm-windows-amd64-msys2-clang64` until the model-load failure is patched and a windows-2022 GUI validation run records a visible Gorm window.
