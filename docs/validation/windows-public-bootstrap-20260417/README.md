# Windows Public Bootstrap Validation - 2026-04-17

Validation host: OTVM `windows-2022` libvirt lease `lease-20260417195907-fnazf6` (`172.17.2.176`).

Results:

- Public GitHub prerelease bootstrap setup passed in direct-process diagnostic mode.
- Setup trace evidence is retained in `setup-trace.jsonl`; stdout/stderr logs are retained beside it.
- The installed prerelease CLI passed `--version` and `--help` smoke checks.
- The previous installed `doctor --json` hang was reproduced, then isolated to native path handling rather than bootstrap setup.
- Native fixes now bound Windows repository-root walks, avoid repository-root scans in managed-install integrity checks, recognize MSYS `/c/...` managed roots and preserved `clang64/bin`, and treat Windows active probe deferral as deferred rather than broken.
- With those fixes and the hardened extracted toolchain layout, the rebuilt Objective-C CLI returned `0` for `doctor --json --manifest C:\Windows\Temp\minimal-release-manifest.json` with `environment_classification: toolchain_compatible` and `native_toolchain_assessment: supported`.

Remaining release-work item: convert this manual live evidence into an automated release qualification lane with destroy-on-exit lease cleanup.
