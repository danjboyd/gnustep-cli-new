# v0.1.1 release evidence

Release under test: stage-release run 38988612393 (channel `stable`, version
`0.1.1`, 8 artifacts). Evidence sources were chosen by Dan on 2026-10-16.

| File | Source |
|---|---|
| `windows-full-tier1-core-report.json`, `windows-full-release-evidence.json` | Arlen Windows VM (`arlen-windows-agent`, Windows Server 2022 10.0.20348, non-elevated) run of `scripts/dev/windows-full-release-smoke.ps1` at 12b7a07 (script sha256 `40523126…`), `-ReleaseSource v0.1.1-rc.2-run-38988016879 -SuiteId tier1-core -RunnerId arlen-windows-vm`, 2026-10-17 07:11:53Z–07:22:43Z, exit 0, all four scenarios passed. Inputs were the v0.1.1-rc.2 assets, byte-identical to the staged Windows artifacts (CLI `14949f33…`, toolchain `07d57993…`). JSON as relayed by the Arlen Windows session (compact form; not the on-disk bytes). Earlier runs at b0363c6 and 037278c failed only `self-update-cli-only`, on fixture defects fixed in PR #16. |
| `windows-current-source-artifact.json` | Windows Current Source Artifacts run 38988016879; identical to the marker in the staged release. |
| `linux-smoke-report.json` | Derived from the three 0.1.1 container qualifications in this directory (`linux-*-container-qualification.json`, listed with sha256 under `evidence.derived_from`). Their artifact sha256s match the staged manifest. |
| `openbsd-full-tier1-core-report.json` | **Carried forward from v0.1.0**, byte-identical to `../release-0.1.0-evidence/` (sha256 `67204aa2…`). v0.1.1 ships no OpenBSD artifacts; the gate still requires the report. |
| `update-all-production-like.json` | **Carried forward from v0.1.0**, byte-identical to `../release-0.1.0-evidence/` (sha256 `6b4003ee…`). Not rerun against v0.1.1. |

Linux toolchains in v0.1.1 are the v0.1.0 toolchain assets relabelled
byte-identically (`reuse_toolchain_version`); only the Linux CLIs were rebuilt.
