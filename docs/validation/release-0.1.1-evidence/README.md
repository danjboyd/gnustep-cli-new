# v0.1.1 release evidence

Release under test: stage-release run 38988612393 (channel `stable`, version
`0.1.1`, 8 artifacts). Evidence sources were chosen by Dan on 2026-10-16.

| File | Source |
|---|---|
| `windows-full-tier1-core-report.json` | Arlen Windows VM run of `scripts/dev/windows-full-release-smoke.ps1` (b0363c6, `-SuiteId tier1-core`) against the v0.1.1-rc.2 assets, which are byte-identical to the staged Windows artifacts (CLI `14949f33…`, toolchain `07d57993…`). Pending. |
| `windows-current-source-artifact.json` | Windows Current Source Artifacts run 38988016879; identical to the marker in the staged release. |
| `linux-smoke-report.json` | Derived from the three 0.1.1 container qualifications in this directory (`linux-*-container-qualification.json`, listed with sha256 under `evidence.derived_from`). Their artifact sha256s match the staged manifest. |
| `openbsd-full-tier1-core-report.json` | **Carried forward from v0.1.0**, byte-identical to `../release-0.1.0-evidence/` (sha256 `67204aa2…`). v0.1.1 ships no OpenBSD artifacts; the gate still requires the report. |
| `update-all-production-like.json` | **Carried forward from v0.1.0**, byte-identical to `../release-0.1.0-evidence/` (sha256 `6b4003ee…`). Not rerun against v0.1.1. |

Linux toolchains in v0.1.1 are the v0.1.0 toolchain assets relabelled
byte-identically (`reuse_toolchain_version`); only the Linux CLIs were rebuilt.
