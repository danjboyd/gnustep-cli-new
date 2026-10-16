# Plan: a stable package index for v0.1.0

Status: proposal, 2026-10-15. Nothing here has been executed.

## Where things stand

The signed stable `v0.1.0` release manifest does not advertise a
`package-index` artifact. On a clean stable install, `gnustep list`,
`search`, `install`, and `remove` stop with "No package index is configured"
unless the user passes `--index`. This is the safe state for now, and the
README says so.

`package-index.json` and its signature are attached to the `v0.1.0` release,
but that index should not be advertised as it is:

| Problem | Detail |
| --- | --- |
| amd64 packages built against the wrong toolchain | The Arlen and Gorm `linux-amd64-clang` snapshots (May 5) were built against the old amd64 toolchain, which was a mislabeled Debian 12 build (glibc 2.36, ICU 72). The amd64 toolchain was replaced on Oct 13 and patched on Oct 15. These packages have never been validated on Debian 13. |
| tools-xctest built against distro GNUstep | `package-tools-xctest.yml` and `package-tools-xctest-hosted-linux.yml` install Ubuntu's `gnustep-devel` (GCC / gcc_libobjc) on `ubuntu-latest` and label the output `linux-amd64-clang`. That doesn't match the managed Clang/libobjc2 ABI, and it violates the managed-artifact source policy in `AGENTS.md`. |
| Dogfood URLs | Several `tools-xctest` artifact URLs point at the `dogfood` release, not `v0.1.0`. |
| Missing targets | There are no Ubuntu 26.04 artifacts. The index carries `ubuntu2404` artifacts, but the stable manifest doesn't support Ubuntu 24.04. Gorm has no Windows artifact URL. |
| Snapshot sources | Gorm and Arlen are pinned to reviewed commit snapshots. Gorm's own `source.channel_policy` says stable should track an upstream tag or an approved exception. |
| Hand-made manifest entry | The `v0.1.0-dev` manifest's `package-index` entry was added by hand. No code in `scripts/` or `src/gnustep_cli_shared/` generates a `package-index` artifact entry. |

## Proposed steps

1. **Run package builds in the target distro (code + tests).** Add a
   `container` input to `package-app-artifact.yml`, for example `debian:13` or
   `ubuntu:26.04`. Today the job runs directly on `ubuntu-latest` (glibc 2.39),
   which can't run the Debian 13 (glibc 2.41) or Ubuntu 26.04 (glibc 2.43)
   toolchains. Follow the container pattern already in
   `linux-managed-artifacts.yml` and `published-url-qualification.yml`. Use
   `ubuntu-24.04-arm` plus `debian:13` for arm64.
2. **Build tools-xctest with the managed toolchain (code + tests).** Change the
   tools-xctest packaging to take the same `toolchain_url`/`toolchain_sha256`
   or `toolchain_artifact_run_id` inputs as `package-app-artifact.yml`, and to
   build with the managed toolchain instead of distro `gnustep-devel`. Then
   retire `package-tools-xctest-hosted-linux.yml`.
3. **Rebuild the packages.** For each of Arlen, Gorm, and tools-xctest, and
   each target (`linux-amd64-clang` = Debian 13, `linux-arm64-clang` =
   Debian 13, `linux-ubuntu2604-amd64-clang`), build against the published
   `v0.1.0` toolchain URL and sha256. That's 9 workflow runs.
4. **Add Ubuntu 26.04 to the package manifests, and handle Ubuntu 24.04.** Add
   `linux-ubuntu2604-amd64-clang` artifacts to each `packages/*/package.json`.
   Then either drop the `ubuntu2404` artifacts from the stable index or keep
   them but exclude them from stable (decision below).
5. **Qualify before publishing.** In clean `debian:13` (amd64, arm64) and
   `ubuntu:26.04` containers: install the CLI through the published bootstrap,
   run `gnustep install <pkg> --index <staged index>` for each package, run a
   smoke test, run `gnustep remove`, and check cleanup. Record evidence under
   `docs/validation/`.
6. **Generate the manifest entry (code + tests).** Add generation of the
   `package-index` release-manifest artifact (id, url, sha256, size,
   provenance) to the staging and release tooling, so it is no longer
   hand-edited. Cover it with a test.
7. **Publish (needs Dan).** Attach the rebuilt package artifacts and the
   re-signed index to `v0.1.0`, add the `package-index` entry to the stable
   manifest, re-sign the manifest through Stage Release and Release, then rerun
   published-URL qualification. This is the same republish path used on
   Oct 13 and Oct 15.
8. **Docs.** Update the README package section and `docs/release-status.md`.

Steps 1, 2, and 6 are code changes that can land as ordinary reviewed PRs
without touching the published release. Steps 3 and 5 only produce workflow
artifacts and evidence. Only step 7 changes the published release.

## Decisions needed

- **Gorm and Arlen sources:** ship the current reviewed commit snapshots in
  stable as an explicit approved exception, or wait for or pick upstream tags.
  Recommendation: an approved exception for v0.1.0, recorded in each
  `package.json`, because Gorm's latest tag predates fixes the snapshot
  depends on. Verify that before deciding.
- **Ubuntu 24.04 package artifacts:** drop them from the stable index, or keep
  them for users who pass `--index`. Recommendation: drop them from stable,
  since the stable manifest doesn't support 24.04.
- **Windows and OpenBSD packages:** include them in the first stable index or
  defer. Recommendation: defer. Windows is in preview, and the OpenBSD
  artifacts target native packaged GNUstep, which needs its own
  qualification.
- **Approval to republish `v0.1.0` (step 7)**, or to put packages in a later
  release such as `v0.1.1`. Recommendation: republish `v0.1.0`. The Arlen docs
  link to the `v0.1.0` bootstrap URL, and earlier republishes used the same
  path.
