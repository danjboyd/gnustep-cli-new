# Carried GNUstep patches: how to submit one

Status: **draft for Dan's review.**

A *carried patch* is a change to a GNUstep library that an app needs before upstream GNUstep has it, or before the release our toolchain uses has it. Covered libraries: libobjc2, libdispatch, tools-make, libs-base, libs-gui and libs-back.

gnustep-cli-new ships carried patches in an optional **patch layer** on top of the stock toolchain ([../specs/patch-layer.md](../specs/patch-layer.md)). Users choose stock or patched; stock stays the default.

This page is the protocol for getting a patch into the layer, keeping it current and retiring it. The current set is in [inventory.md](inventory.md).

## Principles

1. **One canonical copy.** Each carried change lives here once per stock base it targets. Apps stop keeping their own copies of it. The only exception is a build outside the managed toolchain, such as a Flatpak; that build syncs from the canonical file and never edits a copy.
2. **The topic branch is the source of truth.** Every change has a topic branch on the `danjboyd/<library>` fork, based on upstream master: the form it would be sent upstream in. The patch files here are backports of that branch to our stock bases, and each records the branch commit it came from.
3. **Stock is never affected.** A carried patch changes nothing for a user who chooses stock. In the patched layer it must not change the library's binary interface (ABI): apps built against stock run on patched, and the other way round. Behaviour that would surprise an app that didn't ask for it is turned on by a default the app or its theme sets (as `GSBackWindowShadows` and `GSBackClientDrawsCaptions` already are).
4. **Carrying is temporary.** The goal for every patch is upstream. A patch leaves the layer when the stock base includes it.
5. **Upstream posts are separate.** Getting into the layer doesn't send anything upstream. That still follows each project's contribution policy and our UPSTREAM_POLICY.md, with Dan's sign-off on each post.

## Who does what

| Role | Who | Does |
|---|---|---|
| Requester | the agent of the app that needs the change (gnustep-tools-xctest, ScreenshotTool's, ObjcMarkdown's, LinDirStat's…), or a theme agent | writes the change on its topic branch and submits it here, then keeps it current |
| Layer maintainer | gnustep-cli-new (this repo's agent) | reviews submissions, makes the canonical backports, builds and qualifies the layer, retires patches |
| Approver | Dan | approves each release that changes the layer's contents, through an AIManager ask that lists the patches added, updated and dropped |

## Submitting a patch

Open a pull request on danjboyd/gnustep-cli-new. If you can't open one, mail `gnustep-cli-new` with the same contents, and I'll open it. The PR adds:

1. **The patch file:** `toolchains/carry/<library>/<base>/NNNN-<slug>.patch`, made with `git format-patch` (no signature).
   - `<base>` names the stock base it applies to, for example `linux-bf3b3ced` or `msys2-0.32.0`. Send one file for each base the change is wanted on.
   - It must apply with `git apply --check -p1` on that base, on top of the patches already listed for it.
2. **An entry in `toolchains/carry/carry.json`** (the schema is in the design doc). Fields:
   - `id`, `library`, `summary`;
   - `why`: links to the app issues it fixes;
   - `requested_by`: the apps that need it;
   - `platforms`;
   - `topic_branch` and `topic_commit` on `danjboyd/<library>`;
   - `upstream`: `not_sent`, a PR or issue URL with its state, or `merged <commit>`;
   - `defaults`: any defaults it reads, and what turns the behaviour on;
   - `abi`: `unchanged`, or the symbols added (removing or changing a symbol is never accepted);
   - `verified_by`: how it was tested (a GNUstep regression test where one is practical, otherwise the app check that shows the fix);
   - `owner`: the agent who keeps it current.
3. **Order, if it matters:** where it goes in the series for that base, and why (for example, the XDND changes go after the window-type series).

### What review checks

- The patch applies to every base it names, in series order, and the layer builds on each platform it targets.
- **ABI:** comparing exported symbols between stock and patched shows nothing removed or changed. Additions are allowed, but an app that uses an added symbol must declare that it needs the patched variant.
- **Defaults:** a stock app that sets none of the patch's defaults behaves as before. Any exception is stated in the entry and needs Dan's approval in the release ask.
- **Overlap:** if another app already carries the same change, the two are merged into one canonical version. The topic branch's latest revision wins, and both apps' checks must pass. This is the step that ends the drift described in the inventory.
- **Qualification:** the release checks run with stock and with stock plus the layer (tier1, Gorm, the package checks), plus the `verified_by` check of each patch that changed.

Accepted patches ship in the next release that carries a layer for that platform. The PR merges to master after review. The layer artifact is built and published only with a release, and only on Dan's go.

## Keeping a patch current

- **When the topic branch changes,** send an update the same way: a new backport, the new `topic_commit`, and a note on what changed.
- **When the stock base moves** (a new pin, or a new MSYS2 release), the layer maintainer rebases every patch onto the new base and asks the owner to check any that conflict. A patch whose owner doesn't answer before the release is dropped from that release, with notice. It can come back later.
- **When upstream changes state** (sent, merged, rejected), update the `upstream` field.

## Retiring a patch

A patch leaves the layer when the stock base includes the change (the upstream merge reaches our pin or the MSYS2 package), or when its owner withdraws it. The release notes list each patch retired. The topic branch stays on the fork.

## For apps, once the layer ships

- Build with the managed toolchain and the patched variant: `gnustep setup --variant patched`, or the gnustep-packager option. Drop your own patch files and side-installed packages, such as ScreenshotTool's `msys2-package-urls` for `carry-0.32.0.5`.
- A build that can't use the managed toolchain (Flatpak, a distro package) takes the canonical files from `toolchains/carry/` at a recorded gnustep-cli-new commit.
