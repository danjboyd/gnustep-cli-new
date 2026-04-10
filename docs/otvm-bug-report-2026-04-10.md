# OTVM Bug Report: Libvirt Farm Drift And Guest Readiness Regressions

Date: 2026-04-10

This note captures the concrete `OracleTestVMs` issues discovered while executing Phase 18E and 18F live validation for `gnustep-cli-new`.

## Summary

Two real problems were found:

1. The documented/example libvirt farm inventory is stale enough to fail `otvm preflight` out of the box on the current farm.
2. The repo currently overstates Debian libvirt readiness: the control plane can launch the guest and reach network and SSH readiness, but the advertised GUI path is still not reliably usable end to end for operator review.

The second issue is no longer the originally observed SSH-key acceptance failure. That earlier problem was worked around by promoting new manual goldens and updating the libvirt control-plane path. The remaining product issue is that the repo now documents Debian libvirt as validated/current while the actual Debian GUI experience is still unstable enough to block reliable external use.

## Environment

- Operator host: Debian 13
- `otvm` source tree: `/home/danboyd/OracleTestVMs`
- Live farm hosts exercised:
  - `iep-vm2`
  - `iep-ocr01`

## Issue 1: Documented Libvirt Inventory Does Not Match The Current Farm

### What the repo currently says

The current `otvm` docs and example config describe a libvirt setup using:

- hosts: `iep-vm1`, `iep-vm2`, `iep-ocr01`
- `ssh_user = "otvm"`
- `storage_pool = "otvm-images"`
- `network_name = "br0"` on every listed host

Relevant files in `OracleTestVMs`:

- `config/config.toml.example`
- `docs/runtime-configuration.md`
- `docs/libvirt-operations-runbook.md`
- `docs/libvirt-external-usage.md`

### What is actually true on the current farm

The live farm state observed on 2026-04-10 was:

- SSH/libvirt access works as `danboyd`, not as `otvm`
- `iep-vm1` does not match the documented ready shape for these profiles
  - no `br0` libvirt network
  - no `otvm-images` storage pool
- `iep-vm2` and `iep-ocr01` are the viable current hosts
- the viable storage pool is `default`
- the viable network is `br0`
- the current usable image references are:
  - `debian13-wayland.qcow2`
  - `openbsd78-fvwm.qcow2`

### User-visible failure

Using the documented/example inventory causes `otvm preflight` to fail with errors like:

- permission denied to `otvm@<host>`
- storage pool not found: `otvm-images`
- host/network assumptions that do not hold on `iep-vm1`

### Expected

The example config and runbooks should describe a config that can pass preflight on the current intended farm, or they should be clearly marked as illustrative only and not as the active farm inventory.

### Actual

The documented inventory is stale enough to mislead the operator into a broken configuration.

## Issue 2: Debian Libvirt GUI Readiness Is Still Not Acceptance-Ready

### Current state

The original SSH-readiness failure observed earlier on 2026-04-10 is no longer the best description of the problem. Since that first run:

- manual OpenBSD and Debian goldens were promoted
- the libvirt control-plane path was updated
- SSH readiness and guest IP discovery were proven again from those goldens
- Debian's documented GUI contract was changed from GNOME headless RDP on Wayland to direct RDP via `xrdp` on X11

### What the repo currently says

`OracleTestVMs` now describes the Debian libvirt path as current and live-validated. In particular, the current tree says:

- `debian-13-gnome-wayland` is validated live on the current farm
- Debian is modeled as direct RDP to `xrdp`
- Debian returns GUI metadata like:
  - `service = xrdp`
  - `session_model = on-demand-tester-desktop`
  - `session_type = x11`

### What is actually true right now

The current Debian libvirt path is still not reliable enough to count as validated for external operator use. The live state observed on 2026-04-10 was:

- `otvm` can launch the Debian guest on libvirt
- guest IP discovery works
- SSH readiness works
- `xrdp` can be installed and the guest can accept RDP connections
- but the visible GUI session remains unstable and client-sensitive
- Remmina repeatedly rendered only blank white/black canvases even when the remote X tree contained visible windows
- manual debugging on the guest showed that the generated `xrdp` startup contract in the repo was also not yet correct as written

In other words: the Debian libvirt story is beyond the original SSH-key failure, but it is still not actually done.

### User-visible failure

An external project following the current repo docs will reasonably conclude that Debian-on-libvirt is ready for interactive GUI review through the documented RDP path. In practice, the current operator experience is still unreliable enough that:

- the connection may succeed but render only a blank canvas
- the session startup contract may require live debugging or manual repair
- the advertised "validated live" status overstates the actual readiness level

### Expected

One of these needs to be true:

- the Debian libvirt path should be made genuinely reliable end to end for the documented RDP/Remmina workflow, or
- the docs should be downgraded so Debian libvirt is presented as experimental/in-progress rather than validated/current

### Actual

- Debian libvirt is documented as current and validated
- Debian libvirt still requires live debugging to get to a usable GUI session
- the current repo state does not justify the current documentation claims

### Assessment

This is still an `otvm` product bug, but it has changed shape:

- Issue 1 is still a stale-farm-inventory documentation/config bug
- Issue 2 is now a Debian GUI-readiness and product-positioning bug
- OpenBSD should no longer be grouped into this issue unless a fresh reproducible failure is observed there again

## What Did Work

These parts of `otvm` behaved correctly during the investigation:

- libvirt dependency checks
- libvirt SSH connectivity with the corrected farm user
- libvirt storage-pool visibility with corrected pool names
- image presence checks
- guest launch
- guest IP discovery
- TCP readiness checks
- lease destroy cleanup

So the failure boundary appears to be after guest boot and before SSH-based readiness/configuration completes.

## Suggested Fixes

1. Update the `OracleTestVMs` docs and example config to match the current farm reality.
2. Decide whether `ssh_user = "otvm"` is still a real supported operator model. If not, remove it from the active examples.
3. Either finish the Debian libvirt GUI path so the documented RDP workflow is genuinely reliable, or downgrade the docs so Debian libvirt is clearly marked as experimental/in-progress.
4. Rerun live Debian libvirt acceptance once the GUI path is stable and record fresh evidence that matches the current contract.
5. Keep OpenBSD tracked separately unless a new reproducible regression is found there.
6. Consider surfacing the last SSH or GUI-session startup failure more directly in human progress output before the full timeout expires.
