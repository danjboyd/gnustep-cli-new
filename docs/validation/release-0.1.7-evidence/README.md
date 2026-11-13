# v0.1.7 release evidence

Release under test: stage-release run 42914083161 (channel `stable`, version `0.1.7`,
**12 artifacts**, staged from `4acbb27`). v0.1.7 is a CLI release: `gnustep update --yes`
installs the newer release that discovery finds, a failed upgrade restores the previous
install, Windows toolchain extraction no longer times out, and `doctor` recognises a healthy
managed install. Toolchains are rebuilt at this commit with no source changes; the
Arlen-only package index is carried forward unchanged.

This replaces two earlier stagings that were never published: `4d5504b` (run 42856127250;
#53's doctor change had no effect on real installs, fixed by #62) and `939bf4a`
(run 42862187210; a Windows lease showed `update --yes` could leave an install without
`gnustep`, fixed by #64).

> **Status: complete.** Every planned check has run. The Windows update gates ran on a third
> lease (below); one gate failed on the test host's full disk and rolled back cleanly, and the same
> upgrade then completed. This PR stays a draft and unmerged until the release is published.

## Publication

- Release Evidence run 43518684372 (these five files at `d96adee`).
- First Release run 43518745235 (2026-11-13 22:26Z) published the full committed package index:
  Package Index run 42912655746 had been dispatched without `packages=io.github.danjboyd.arlen`
  and `published_only=true`. v0.1.6 was made Latest again, the v0.1.7 release and tag were
  deleted on Dan's go, and Release run 43522218499 republished v0.1.7 from the same staged files
  with Package Index run 43519836439 (Arlen only; identical to v0.1.6's apart from
  `generated_at`, sha256 `8d78e66a…`). Tag `v0.1.7` = `4acbb27`. The CLI and toolchain files are
  the staged ones every check above tested.

## Artifacts and their sources

| Artifact | sha256 | Source |
|---|---|---|
| cli linux-amd64-clang | `9cc006cd…` | run 42912659816 (4acbb27) |
| toolchain linux-amd64-clang | `589e467e…` | run 42912659816 |
| cli linux-ubuntu2404-amd64-clang | `49d56474…` | run 42912668437 (4acbb27) |
| toolchain linux-ubuntu2404-amd64-clang | `bc15985f…` | run 42912668437 |
| cli linux-ubuntu2604-amd64-clang | `670c0c27…` | run 42912672600 (4acbb27) |
| toolchain linux-ubuntu2604-amd64-clang | `5bd0d847…` | run 42912672600 |
| cli linux-ubuntu2404-arm64-clang | `f158b78c…` | run 42912676612 (4acbb27) |
| toolchain linux-ubuntu2404-arm64-clang | `be732cab…` | run 42912676612 |
| cli linux-arm64-clang | `1db44445…` | run 42912664267 (4acbb27) |
| toolchain linux-arm64-clang | `fb132ab2…` | run 42912664267 |
| cli windows-amd64-msys2-clang64 | `6671b208…` | run 42912680558 (4acbb27) |
| toolchain windows-amd64-msys2-clang64 | `849c7ca9…` | run 42912680558, assembled from the lock with gnustep-base 1.31.1-10.5 |

Every Linux artifact's sha256 equals the sha its container qualification tested
(cross-checked in `linux-smoke-report.json`'s `derived_from`, and against the staged manifest).
Package Index run 42912655746 lists the same Arlen 0.3.2 artifacts, digests and URLs as v0.1.6.

## What changed

- **Update (#57):** `update --yes` and `update cli --yes` without `--manifest` install the
  release that discovery found; v0.1.5 and v0.1.6 re-applied the recorded release and reported
  success. If the planned version isn't installed afterwards, the command fails.
- **Upgrade safety (#64):** archive extraction has a 30-minute limit (it was 15 s, which cut
  Windows toolchain extraction short); on Windows a timed-out command's process tree is killed;
  the rollback checks every step and says where the snapshot is if it can't restore; `update cli
  --yes` with nothing newer no longer reruns setup.
- **Doctor (#53, #62):** a healthy managed install, including one under `releases/<version>`,
  is reported as managed rather than native.
- **README (#65):** Windows users on v0.1.5/v0.1.6 update by running the bootstrap again.

## Evidence files

| File | Source |
|---|---|
| `linux-*-container-qualification.json` (5) | The container-qualification artifact of each Linux run above. Every step passed, including SONAME checks, package install/remove and TLS; `tls_no_ca` exits 1, the expected refusal with no CA bundle. Evidence tier: clean distro container on a GitHub runner. |
| `linux-smoke-report.json` | Derived from the five container qualifications, listed with sha256 under `evidence.derived_from`. |
| `windows-current-source-artifact.json` | Run 42912680558; identical to the marker in the staged release (source revision `4acbb27`). |
| `windows-full-tier1-core-report.json`, `windows-full-release-evidence.json` | The lease run below. Stored as compact UTF-8 JSON; the UTF-8-BOM originals hash to `c014aafa…` and `183e133e…`. |
| `windows-toolchain-smoke-check.txt` | The toolchain smoke (gdnc and HTTPS) on the same lease. |
| `windows-arlen-check.txt` | The rerun lease below. Converted to plain UTF-8; the original (a UTF-8-BOM line followed by UTF-16LE lines, from PowerShell 5.1 `Tee-Object -Append`) hashes to `670372ed…`. |
| `windows-update-gates.json`, `windows-update-gates.txt` | The update-gate lease below. Converted to UTF-8 (compact JSON); the originals hash to `bec3ffa1…` and `30c2efd0…`. |
| `openbsd-full-tier1-core-report.json` | **Carried forward** byte-identical, as in v0.1.2–v0.1.6. v0.1.7 ships no OpenBSD artifacts. |
| `update-all-production-like.json` | **Carried forward** byte-identical, as in v0.1.4–v0.1.6. |

## Windows lease

- Host: OCI Windows Server 2022 lease `lease-20261110223401-m0crty` via otvm-gate (owner
  windows-agent), a fresh machine, created 2026-11-10 22:34Z. Operator on the office network.
  Destroyed 2026-11-11 16:07Z; the instance is TERMINATED in OCI.
- Inputs checked on the host: the staged Windows CLI `6671b208…` and toolchain `849c7ca9…`, and
  the stamped 0.1.7 `gnustep-bootstrap.ps1`.
- **tier1-core:** overall_ok. bootstrap-install-usable-cli (doctor ok, toolchain_compatible,
  0.1.7), new-cli-project-build-run, gorm-build-run and self-update-cli-only all passed.
- **Toolchain smoke:** exit 0; TLS as on Linux (GitHub address `140.82.112.3` refused), trust on a
  store missing the root, the bundled authorities 86 days old; from outside the toolchain's
  bash: github.com 0, expired 1, 1.1.1.1 0.
- **Not retrieved:** the Arlen check and the update gates were still running when the session
  that owned the lease ended, and the host was unreachable afterwards.

## Windows rerun lease

- Host: OCI Windows Server 2022 lease `lease-20261112230721-36ydjg` via otvm-gate (owner
  windows-agent), a fresh machine, created 2026-11-12 23:07Z. Operator on the office network.
  Destroyed 2026-11-13 01:46Z; the instance is TERMINATED in OCI.
- Inputs checked on the host: the same staged CLI `6671b208…`, toolchain `849c7ca9…` and stamped
  0.1.7 bootstrap `867308a2…`.
- **tier1-core:** overall_ok again; all four steps passed (the 11-10 report above is kept).
- **Arlen check** (`windows-arlen-check.txt`), elevated, with the 0.1.7 CLI: a tampered package
  list is refused (exit 1); `install` picks `arlen-windows-amd64-msys2-clang64-headless` 0.3.2,
  whose zip hashes to `fd39fb7d…`, the digest in `packages/io.github.danjboyd.arlen/package.json`;
  `arlen.cmd` and `boomhauer.cmd` are installed as plain files (not symlinks), `boomhauer --help`
  exits 0 and `arlen --help` exits 2, the same as v0.1.4, v0.1.6 and the Arlen 0.3.2 qualification;
  `remove` exits 0 and leaves no package directory or shims.
- **Update gates: not run.** The driver's completion check for the Arlen step never matched
  (it read the last line of the mixed-encoding file, a stray NUL byte), so it waited until its
  own deadline and the update gates did not fit before the lease had to be destroyed.

## Windows update-gate lease

- Host: OCI Windows Server 2022 lease `lease-20261113202757-uc5yrx` via otvm-gate (owner
  windows-agent), a fresh machine, created 2026-11-13 20:28Z. Operator on the office network.
  Destroyed 22:19Z; the instance is TERMINATED in OCI.
- Inputs checked on the host: CLI `6671b208…`, toolchain `849c7ca9…`, bootstrap `867308a2…`.
- The staged 0.1.7 install came from the stamped 0.1.7 bootstrap and the staged manifest, signed
  with a throwaway key: exit 0, version 0.1.7. Gates ran in the smoke environment (the root's
  `usr\bin`, `bin` and `clang64\bin` on PATH, plus the unzip shim).
- **N, the 0.1.7 CLI upgrading Windows:** `update cli --yes` with the staged 0.1.7 CLI, no
  `--manifest` and no trust override, on a 0.1.5 install, against production Latest (v0.1.6):
  exit 0, "CLI and toolchain update completed", the install moved to 0.1.6. The trace shows
  the CLI staged and smoke-checked, the toolchain extracted (tar.exe, then the unzip fallback)
  and the release activated. This is the upgrade that on 11-10 timed out after 15 s and left
  the root without `gnustep` (#64). The gate script labels it a no-op check and marks it
  `ok=false` only because it expected B to have upgraded first, so it expected "No updates".
- **B, failed upgrade rolled back:** the same upgrade with plain `update --yes`, run first on the
  same root, failed with "Failed to copy bin/libclang.dll" in the toolchain copy. The rollback
  restored the install by move (`rollback.restored method=move`); afterwards the root holds
  `bin`, `state`, `current` and the toolchain, at 0.1.5. On 11-10 the same route left only
  `.staging` and `releases/0.1.6`.
  - Likely cause: the test host's disk. The run holds five managed installs plus setup backups on
    one volume, and the next bootstrap in the same run (B-bare) failed with "No space left on
    device". B's own bootstrap log was overwritten by B-bare's, so ENOSPC during B itself is
    inferred, not shown.
  - The copy routine (`copyTreeContentsFrom:`) removes and copies each file once, without a retry
    or a detailed error. A follow-up after v0.1.7 can make that error say why the copy failed.
- **A and B0 (old CLIs):** 0.1.6 with an explicit `--manifest` to staged 0.1.7, and 0.1.5 with plain
  `update --yes`. Both stop at "Candidate release failed post-upgrade smoke validation" and leave
  the install unchanged, as on 11-10. This is the release notes' "Upgrading from v0.1.5 or v0.1.6
  on Windows" case: run the 0.1.7 bootstrap.
- **C, doctor:** the staged 0.1.7 install is reported as managed at its root
  (`use_managed_toolchain`).
- **B-bare** (diagnostic, bare environment): its 0.1.5 bootstrap ran out of disk space; not meaningful.
- Not covered: 0.1.7 to a newer release by default discovery (none exists before v0.1.8).

## Other checks before publication

- **Release-path rehearsal** (release.yml's commands, throwaway keys, nothing published): passed,
  apart from the evidence gates that need this bundle.
- **Update rehearsals** (isolated scratch installs, staged manifest served locally):
  - the staged 0.1.7 CLI with plain `update --yes` against the real Latest moved 0.1.5 to 0.1.6
    (the #57 route);
  - the old 0.1.5 CLI reproduced the bug (stayed 0.1.5, reported success);
  - the old 0.1.6 CLI with an explicit `--manifest` reached 0.1.7;
  - 0.1.7 then reported no updates;
  - `update cli --yes` with nothing newer was a no-op (no setup, no new snapshot);
  - `doctor` reported the managed install at its root (`use_managed_toolchain`).
  The real check against `releases/latest` runs after publication.
