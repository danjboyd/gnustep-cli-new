# Debian Upgrade Dogfood Validation

This runbook records the old-to-new managed release upgrade dogfood gate.

## Command

```bash
OLD_RELEASE_DIR=/tmp/gnustep-release-stage/stable/0.1.0-old \
NEW_RELEASE_DIR=/tmp/gnustep-release-stage/stable/0.1.0-dev \
OTVM_CONFIG=/tmp/oracletestvms-libvirt-otvmkey.toml \
./scripts/dev/debian-upgrade-dogfood-validation.sh
```

The script provisions a short-lived `debian-13-gnome-wayland` lease through
OracleTestVMs, stages both release directories, installs the older release via
the POSIX bootstrap script, checks for updates against the newer manifest, runs
`gnustep update cli`, verifies lifecycle state, performs post-upgrade
`--version` and `doctor --json` smoke checks, runs `setup --rollback`, verifies
rollback state and post-rollback smoke checks, and destroys the lease through a
shell trap.

## Coverage

- `otvm preflight debian-13-gnome-wayland`
- `otvm create debian-13-gnome-wayland`
- bootstrap install from the old release manifest
- installed full CLI `update --check --json` against the new manifest
- installed full CLI `update cli --yes --json` against the new manifest
- lifecycle state validation for `last_action = upgrade` or `last_action = update_cli`, active release path, current-pointer activation, and preserved previous-release path
- post-upgrade `gnustep --version`
- post-upgrade `gnustep doctor --json`
- installed full CLI `setup --rollback --json`
- lifecycle state validation for `last_action = rollback` and `status = healthy`
- post-rollback `gnustep --version`
- post-rollback `gnustep doctor --json`
- lease destroy after success or failure

## Current Status

The automation hook is present and now installs the same Debian host prerequisites
(`clang` and `make`) used by the fresh Debian dogfood lane before bootstrap.

April 19/20 live execution exposed and drove fixes for three release-upgrade
issues:

- previously staged `0.1.0-dev` artifacts predated the native update command, so
  upgrade dogfood requires an old release that already contains update support
- locally built development binaries linked against the host Objective-C runtime
  are not valid managed-release artifacts; upgrade dogfood must use binaries
  built against the managed GNUstep/libobjc2 toolchain
- full CLI runtime bundles must not be double-wrapped by native setup because
  they already contain `bin/gnustep` and `libexec/gnustep-cli/bin/gnustep`
- native setup now smoke-validates versioned releases before activation and uses
  a root launcher that follows the stable `current` pointer

The current validation method stages synthetic managed-built `0.1.1` and `0.1.2`
release directories from the current Objective-C CLI plus the existing
Debian-qualified managed toolchain artifact, then runs the old-to-new VM lane.

## Current Evidence

The old-to-new managed upgrade gate passed on April 19/20, 2026 against a
synthetic managed-built update pair staged from the current Objective-C CLI and
the existing Debian-qualified managed toolchain artifact.

- old release: `/tmp/gnustep-upgrade-dogfood-stage/stable/0.1.1`
- new release: `/tmp/gnustep-upgrade-dogfood-stage/stable/0.1.2`
- lease: `lease-20260420024618-dt6zgo`
- guest: `172.17.2.144`
- result: `{"ok":true,"summary":"Debian upgrade dogfood validation passed."}`

The gate was rerun successfully on April 20, 2026 after current-pointer
activation and explicit rollback work:

- old release: `/tmp/gnustep-upgrade-dogfood-stage/stable/0.1.1`
- new release: `/tmp/gnustep-upgrade-dogfood-stage/stable/0.1.2`
- lease: `lease-20260420113227-frxel7`
- guest: `172.17.2.129`
- result: `{"ok":true,"summary":"Debian upgrade and rollback dogfood validation passed."}`

The lane covered bootstrap install of the old release, installed full-CLI
`update --check`, installed full-CLI `update cli --yes`, lifecycle state
validation for `last_action = upgrade` or `last_action = update_cli`, active
release path, current-pointer activation, preserved previous-release path,
post-upgrade `--version`, post-upgrade `doctor --json`, rollback, and
post-rollback smoke checks.

The gate was rerun again on April 20, 2026 after rebuilding the Linux CLI
artifact against the managed GNUstep/libobjc2 prefix and adding the ABI audit
gate:

- old release: local staged previous release under `dist/stable/previous`
- new release: local staged release under `dist/stable/0.1.0-dev`
- lease: `lease-20260420175845-1hcsgo`
- guest: `172.17.2.125`
- result: `{"ok":true,"summary":"Debian upgrade and rollback dogfood validation passed."}`
