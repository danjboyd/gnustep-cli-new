# Windows Public Release Smoke - 2026-04-21

This directory captures a public GitHub Releases bootstrap smoke for the
`v0.1.0-dev` Windows MSYS2 clang64 artifacts.

Validation target:
- OTVM profile: `windows-2022`
- Lease: `lease-20260421202009-zkzbh8`
- Install root: `C:\gnustep-cli-public-refresh`
- Manifest URL: `https://github.com/danjboyd/gnustep-cli-new/releases/download/v0.1.0-dev/release-manifest.json`
- Selected CLI artifact: `cli-windows-amd64-msys2-clang64`
- Selected toolchain artifact: `toolchain-windows-amd64-msys2-clang64`

Result:
- Bootstrap setup exited with status `0`.
- The public release manifest selected the refreshed Windows CLI artifact.
- The CLI ZIP and toolchain ZIP downloaded from GitHub Releases.
- Bootstrap verified artifact checksums before extraction.
- The installed `gnustep.exe --version` returned `0.1.0-dev`.
- The installed `gnustep.exe --help` rendered the full interface help.

Evidence:
- `public-setup.txt`: human-readable bootstrap setup transcript.
- `public-trace.jsonl`: structured bootstrap trace from manifest download through install cleanup.
