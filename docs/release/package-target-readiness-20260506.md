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
| Gorm | windows-amd64-msys2-clang64 | yes | yes | no | no | promote validated artifact after release publication decision |

## Cleared RC Blocker

Windows Gorm now builds with the required support DLLs and the declared Windows palette-exclusion patch. The earlier `expected char and got object` model-load failure was isolated to the toolbar palette; the Windows package now omits both toolbar and formatter palettes pending an upstream/runtime-compatible fix.

- Build evidence: GitHub Actions Windows Package App Artifact run `25458527191`
- Artifact SHA-256: `7b1e26a2d94620b82d926f95dc98f5f01765d2dc4d3fc1652bf7cb18b1e686c5`
- GUI evidence: `.artifacts/windows-gorm-gui-lease-20260506193205-xdf6dm/output-interactive-ci-25458527191/summary.json`
- GUI result: `ok`; visible window title `Controls`; stderr empty
- Package-manager install/remove evidence: `docs/validation/package-install-remove-20260506/gorm-windows-amd64-msys2-clang64-install-remove.json`

`gorm-windows-amd64-msys2-clang64` is no longer an RC blocker. It remains unpublished only because release asset promotion has not been performed for this newly validated artifact.
