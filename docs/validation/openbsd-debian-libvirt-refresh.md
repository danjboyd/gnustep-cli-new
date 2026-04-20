# OpenBSD And Debian Libvirt Refresh

This runbook records the currently validated `otvm` shape for refreshing the
OpenBSD and Debian release-candidate evidence on the libvirt farm.

## Current Working Model

- operator-to-hypervisor SSH uses:
  - `danboyd@iep-vm1`
  - `danboyd@iep-vm2`
  - `danboyd@iep-ocr01`
- libvirt URIs use `qemu+ssh://danboyd@<host>/system`
- guest access mode is `direct-lan`
- the machine running `otvm` must be able to reach the guest subnet directly

Do not assume the older `otvm@...` examples or `otvm-images` storage pool
model. Those were part of the stale farm shape that caused earlier confusion.

## Published Farm Images

- Debian:
  `oracletestvms-debian13-wayland-libvirt-20260414181129.qcow2`
- OpenBSD:
  `openbsd78-fvwm.qcow2`

## Ready Config

Use the checked-in template:

- [otvm-libvirt.example.toml](/home/danboyd/gnustep-cli-new/docs/validation/otvm-libvirt.example.toml)

The current operator shape on this workstation uses:

- `project.operator_public_key_file = "/home/danboyd/.ssh/otvm/id_rsa.pub"`
- matching private key:
  - `/home/danboyd/.ssh/otvm/id_rsa`

This keypair was confirmed on April 14, 2026 to work for:

- hypervisor SSH to `iep-vm1`, `iep-vm2`, and `iep-ocr01`
- Debian guest SSH as `debian`
- OpenBSD guest SSH as `oracleadmin`

Recommended operator path:

```bash
cp docs/validation/otvm-libvirt.example.toml ~/oracletestvms-libvirt.toml
```

## Preconditions

1. Working SSH access from the operator machine to:
   - `danboyd@iep-vm1`
   - `danboyd@iep-vm2`
   - `danboyd@iep-ocr01`
2. The operator machine can reach the guest LAN directly.
3. The current published farm images remain present on the hypervisors.

## Commands

```bash
PYTHONPATH=src python3 -m oracletestvms --config ~/oracletestvms-libvirt.toml preflight openbsd-7.8-fvwm
PYTHONPATH=src python3 -m oracletestvms --config ~/oracletestvms-libvirt.toml preflight debian-13-gnome-wayland
PYTHONPATH=src python3 -m oracletestvms --config ~/oracletestvms-libvirt.toml acceptance-run openbsd-7.8-fvwm debian-13-gnome-wayland
```

## What To Record

- exact config path used
- exact published image references
- preflight JSON output for both profiles
- acceptance-run JSON output
- selected host for each lease
- destroy/reap results after completion

## Current 2026-04-14 Refresh Result

- Hypervisor access and libvirt connectivity are working from this machine with:
  - `danboyd@iep-vm1`
  - `danboyd@iep-vm2`
  - `danboyd@iep-ocr01`
- `otvm preflight openbsd-7.8-fvwm` passed.
- `otvm preflight debian-13-gnome-wayland` passed.
- OpenBSD live acceptance created:
  - lease: `lease-20260414192540-hdpj4a`
  - host: `iep-vm2`
  - guest IP: `172.17.2.188`
- Debian live acceptance created:
  - lease: `lease-20260414192825-nckv9d`
  - host: `iep-vm2`
  - guest IP: `172.17.2.191`
- A first refresh attempt using older local key assumptions failed at guest SSH.
- After switching `otvm` to `/home/danboyd/.ssh/otvm/id_rsa.pub`, both profiles
  completed successfully:
  - Debian lease `lease-20260414194652-n3wr17`
  - Debian guest `172.17.2.197`
  - OpenBSD lease `lease-20260414194652-hma3eq`
  - OpenBSD guest `172.17.2.199`
- Both guests reached full `lease.ready`.
- Direct guest SSH also succeeded with `/home/danboyd/.ssh/otvm/id_rsa`.
- Both validation leases were destroyed cleanly after verification.
- OpenBSD packaged-path validation was then rerun on a fresh lease:
  - lease: `lease-20260414214055-3bbbdq`
  - host: `iep-vm2`
  - guest IP: `172.17.2.127`
  - `doas pkg_add -I gmake gnustep-make gnustep-base gnustep-libobjc2`
    completed successfully
  - `. /usr/local/share/GNUstep/Makefiles/GNUstep.sh`
  - `gnustep-config --objc-flags` and `gnustep-config --base-libs` both
    resolved correctly
  - a Foundation probe compiled, linked, and ran successfully with packaged
    OpenBSD Clang and GNUstep Base:

```text
2026-04-14 21:47:11.314 gsprobe[75850:14461399076424] probe-ok
```

- This confirms that the current OpenBSD `pkg_add` path is not only discoverable
  in policy but functionally usable for native GNUstep compile-link-run
  validation on the libvirt farm.

Current conclusion:

- The libvirt farm shape is usable from this machine.
- The current farm images are aligned with the `~/.ssh/otvm` keypair.
- The OpenBSD packaged GNUstep path is validated as a preferred native-path
  candidate through real `pkg_add` and compile-link-run evidence, not just
  image refresh success.
