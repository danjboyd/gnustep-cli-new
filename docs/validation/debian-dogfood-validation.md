# Debian Dogfood Validation

This runbook records the repeatable Debian managed-toolchain dogfood gate.

## Command

```bash
RELEASE_DIR=/tmp/gnustep-release-stage/stable/0.1.0-dev \
OTVM_CONFIG=/tmp/oracletestvms-libvirt-otvmkey.toml \
./scripts/dev/debian-dogfood-validation.sh
```

The script provisions a short-lived `debian-13-gnome-wayland` lease through
OracleTestVMs, stages the selected release directory and the POSIX bootstrap
script, validates the installed full CLI, and destroys the lease through a shell
trap.

## Coverage

- `otvm preflight debian-13-gnome-wayland`
- `otvm create debian-13-gnome-wayland`
- bootstrap `setup --json --root ... --manifest ...`
- installed `gnustep --version`
- installed `gnustep --help`
- installed `gnustep doctor --json --manifest ...`
- managed Foundation compile-link-run using the staged Clang/libobjc2 runtime
- `gnustep new`, `gnustep build`, and `gnustep run` against a generated CLI-tool project
- package `install --json --index ...`
- package `remove --json`
- lease destroy after success or failure

## Current Evidence

The gate passed on April 16, 2026 against freshly staged local
`linux/amd64/clang` artifacts.

- lease: `lease-20260416222812-tbap3u`
- guest: `172.17.2.173`
- result: `{"ok":true,"summary":"Debian dogfood validation passed."}`
- post-run active lease check: `active_count 0`

## Remaining Gap

This gate now proves controlled Debian dogfood for setup, doctor, a direct
managed Foundation compile-link-run probe, normal GNUstep Make project workflows
through `gnustep new` / `gnustep build` / `gnustep run`, and package flows.

The remaining managed Linux hardening is portability beyond Debian: Ubuntu now
requires its own Docker-built amd64 target because ICU/runtime SONAMEs can differ
from Debian, while Fedora and Arch reruns against the refreshed Debian-built
artifact still fail on distro library soname differences (`libcurl-gnutls.so.4`
on Fedora and `libxml2.so.2` on Arch).
