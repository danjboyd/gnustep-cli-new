# Session Handoff: 2026-04-10

This note captures where `gnustep-cli-new` was left at the end of the April 10, 2026 session.

## Repo State

- The `gnustep-cli-new` worktree is dirty with active implementation and roadmap updates.
- No git cleanup or history rewriting was performed.
- The main roadmap status for Phase 18 was updated to reflect the live `otvm` evidence from today.
- An inline `otvm` bug report was added in this repo so the separate `OracleTestVMs` Codex session can consume it directly.

Relevant files changed in this repo during or before this session:

- `docs/implementation-roadmap.md`
- `docs/specs/compatibility-model.md`
- `docs/specs/command-contract.md`
- `src/gnustep_cli_shared/build_infra.py`
- `scripts/internal/build_infra.py`
- `tests/test_build_infra.py`
- `docs/otvm-bug-report-2026-04-10.md`

## GNUstep CLI Status

The previously completed local work remains true:

- Linux managed-toolchain full CLI build path is working locally.
- Bootstrap-to-full staged handoff qualification exists and passes locally.
- The full CLI bundle now installs a runtime-aware launcher.
- Debian GCC interoperability planning exists in `build_infra.py`.

The current blocking work is no longer local Linux execution. It is the remaining live-validation evidence for Phase 18.

## Phase 18 Status After This Session

### What was completed

- Phase 18E libvirt-backed preflight was exercised successfully against the real KVM farm for:
  - `openbsd-7.8-fvwm`
  - `debian-13-gnome-wayland`
- The working farm subset was identified as:
  - `iep-vm2`
  - `iep-ocr01`
- The working farm shape for these profiles is currently:
  - `ssh_user = "danboyd"`
  - `storage_pool = "default"`
  - `network_name = "br0"`
  - image references:
    - `openbsd78-fvwm.qcow2`
    - `debian13-wayland.qcow2`

### What failed

Live acceptance did not complete for either profile.

OpenBSD:

- lease id: `lease-20260410212940-vu2p3e`
- launched on `iep-vm2`
- IP discovered: `172.17.2.115`
- TCP/22 readiness passed
- stalled in the `oracleadmin` SSH readiness probe

Debian:

- lease id: `lease-20260410213335-0zitc1`
- launched on `iep-vm2`
- IP discovered: `172.17.2.171`
- TCP/22 readiness passed
- TCP/3389 readiness passed
- stalled in the `debian` SSH readiness probe

Both leases were destroyed cleanly after evidence capture.

### Current interpretation

The libvirt route itself is now proven enough to say:

- host reachability works
- `virsh`/libvirt connectivity works
- image presence checks work
- guest launch works
- guest network/IP discovery works
- destroy cleanup works

The remaining failure is guest SSH readiness/image hygiene:

- both current guest images reject both locally available operator keys
  - `~/.ssh/id_rsa`
  - `~/.ssh/oracletestvms_ed25519`
- this blocks `otvm` acceptance from reaching `ready`

That means:

- Phase 18E is partially executed, but still open
- Phase 18F is still open

## OTVM Findings

The `otvm` findings were written up here:

- `docs/otvm-bug-report-2026-04-10.md`

The two core issues are:

1. The documented/example libvirt inventory is stale and does not match the current working farm.
2. The current Debian and OpenBSD libvirt images are not acceptance-ready with the configured operator key.

## Temporary Runtime Configs Used

These temporary configs were used outside this repo during investigation:

- `/tmp/otvm-libvirt-phase18-min.toml`
- `/tmp/otvm-libvirt-phase18-dan.toml`
- `/tmp/otvm-libvirt-phase18-ready.toml`
- `/tmp/otvm-libvirt-phase18-debian.toml`

Only `/tmp/otvm-libvirt-phase18-ready.toml` and `/tmp/otvm-libvirt-phase18-debian.toml` represent the corrected farm shape that actually passed preflight.

## Commands That Matter For Resume

From `OracleTestVMs`, the useful validated commands are:

```bash
otvm --config /tmp/otvm-libvirt-phase18-ready.toml preflight openbsd-7.8-fvwm
otvm --config /tmp/otvm-libvirt-phase18-ready.toml preflight debian-13-gnome-wayland
```

The acceptance commands that reproduced the current readiness failures were:

```bash
otvm --config /tmp/otvm-libvirt-phase18-ready.toml acceptance-run openbsd-7.8-fvwm
otvm --config /tmp/otvm-libvirt-phase18-debian.toml acceptance-run debian-13-gnome-wayland
```

The farm itself was directly validated with:

```bash
virsh -c qemu+ssh://danboyd@iep-vm2/system uri
virsh -c qemu+ssh://danboyd@iep-ocr01/system uri
virsh -c qemu+ssh://danboyd@iep-vm2/system pool-list --all
virsh -c qemu+ssh://danboyd@iep-vm2/system net-list --all
virsh -c qemu+ssh://danboyd@iep-ocr01/system pool-list --all
virsh -c qemu+ssh://danboyd@iep-ocr01/system net-list --all
```

## Next Session Resume Plan

1. Hand the inline bug report to the `OracleTestVMs` session:
   - `docs/otvm-bug-report-2026-04-10.md`
2. In `OracleTestVMs`, fix one or both of:
   - stale libvirt docs/example inventory
   - Debian/OpenBSD image SSH-key/bootstrap hygiene
3. Rebuild or repair:
   - `openbsd78-fvwm.qcow2`
   - `debian13-wayland.qcow2`
4. Rerun:
   - libvirt preflight for OpenBSD and Debian
   - acceptance for OpenBSD and Debian
5. If those reach `ready`, update `docs/implementation-roadmap.md` again and close the remaining Phase 18E/18F gap.
6. After Phase 18 is truly closed, proceed to Phase 19 publication and end-to-end consumption.

## Current Best Understanding

Do not spend the next session re-debugging libvirt connectivity first. That part is now understood.

The actual current blocker is:

- guest image readiness and operator-key alignment on the libvirt-backed Debian and OpenBSD images

The farm route is usable once those guest images are corrected.
