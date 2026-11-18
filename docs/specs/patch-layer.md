# Patch layer: stock or patched GNUstep libraries

Status: **being built for v0.1.9.** Dan chose this design (option B) on 2026-11-17, and put the layer in v0.1.9 the same day.

## Goal

Ship the carried GNUstep fixes that Dan's apps need ([../carried-patches/inventory.md](../carried-patches/inventory.md)) once, in the managed toolchain, and let each user choose:
- **stock:** the toolchain exactly as qualified and published today. This stays the default.
- **patched:** stock plus a signed *patch layer*, which replaces a few library files with builds carrying the patches.

Not goals: changing the stock toolchain; sending anything upstream (see the protocol); patched builds of libobjc2 or libdispatch (nothing carries any today).

## The layer artifact

One per target that has carried patches. A release with nothing carried for a target ships no layer for it.

- **Name:** `gnustep-carry-<target>-<release>.zip`, kind `carry-layer` in the release manifest.
- It holds the replacement files only (DLLs or shared objects, plus any headers whose content changed) and `carry-layer.json`:

```json
{
  "schema_version": 1,
  "target": "windows-amd64-msys2-clang64",
  "release": "0.2.0",
  "requires_toolchain_sha256": "<sha256 of the stock toolchain artifact this layer patches>",
  "patches": ["win32pbs-images", "win32-client-caption", "..."],
  "files": [
    {"path": "clang64/bin/gnustep-back-032.dll",
     "stock_sha256": "<the stock file's sha256>",
     "sha256": "<the patched file's sha256>"}
  ]
}
```

- **Staging:** `stage-release --carry-input <target>=<zip>` (the multi-run path finds `gnustep-carry-<target>-<version>.zip`) stages the layer only if every replaced file's `stock_sha256` matches the staged toolchain archive's copy, and its recorded toolchain sha256 matches. `verify-release` repeats the check.
- **In the release manifest:** the layer is an ordinary artifact, `carry-layer-<target>`. It has a `requires_toolchain` that pins the stock toolchain's sha256, as the CLI already does for the CLI artifact, and it's signed and checksummed like every other artifact.
- **The patch set** comes from `toolchains/carry/carry.json` and the patch files under `toolchains/carry/<library>/<base>/` ([protocol](../carried-patches/README.md)).

No binary diffs: the layer ships whole files. The `stock_sha256` checks give the same guarantee that it only applies to the exact stock files, without new tooling in the CLI and both bootstraps.

## Building the layer (CI)

- **Windows** (`windows-carry-layer.yml`): build gnustep-base (our stock recipe, which applies `CARRY_PATCH_DIR`'s patches only when it is set), gnustep-gui and gnustep-back (MSYS2's recipes in `toolchains/carry/windows/`) with the carried patches, inside the locked MSYS2 root.
  - First check that the root's libraries are the stock zip's.
  - Each base in `carry.json` declares its `outputs`, glob patterns for the installed files the layer takes (the base, gui and backend DLLs, and gpbs.exe). Each output must differ from stock. Every other file the rebuild changes, such as a rebuilt tool's timestamp, is reported and not shipped.
- **Linux:** rebuild libs-back, libs-gui or libs-base from the pinned revision with the carried patches, in the same recipe and build environment as the stock toolchain, and take the files that differ.
- **ABI check:** compare the exported symbols of each replaced library against stock (`llvm-nm --defined-only --extern-only`, and the export table on Windows). Fail on any removed or changed symbol. Added symbols are listed in the layer's evidence.
- Layer builds are reproducible from the lock and the patch files, like toolchain builds.

## The CLI

- **Choosing:**
  - `gnustep setup --variant stock|patched` picks the variant at install time. Run on an existing install, it switches without reinstalling.
  - The bootstraps take the same flag. They install stock, then run the installed CLI's `setup --variant patched`, so the checks live in one place. Its JSON is folded into theirs as `carry_layer`, keeping `--json` a single document.
  - The choice is recorded in `state/cli-state.json` as `toolchain_variant`, with the layer's release and sha256.
- **Applying the layer,** as a transaction like a package install:
  1. Verify the layer's signature and checksum, and that `requires_toolchain_sha256` matches the installed toolchain.
  2. Verify every `stock_sha256`. If a file doesn't match, refuse and change nothing.
  3. Move each stock file to `state/carry/stock/<path>`, then copy the patched file into place.
     - On Windows a DLL loaded by a running process can't be overwritten, but it can be renamed: rename aside, then copy, the way #85's rollback swaps the root.
  4. Verify each patched file's sha256. On any failure, put the stock files back.
- **Switching to stock** restores the saved files and checks them against `stock_sha256`. No download is needed.
- **`update`:**
  - It keeps the variant.
  - If a new release has no layer for the target, it installs stock and says so: "patched variant unavailable in <release>; using stock".
  - A new toolchain sha always comes with a matching layer, or none.
- **`doctor`** (check `managed.toolchain.variant`, in both doctors) reports the variant, the layer release and its patch ids. It checks that every layer file matches either its stock or its patched sha256, and flags a mix of the two as an error, with the repair command.
- **`--json`:** `setup`, `update` and `doctor` include `toolchain_variant` and `carry_layer` (release, sha256, patches).

## Packages and gnustep-packager

- Packages (Arlen, tools-xctest, apps) are built against stock and must run on both. The ABI rule guarantees this. A package that needs a patched-only symbol declares `"requires_variant": "patched"`, and `install` refuses it on stock with a clear message.
- gnustep-packager builds against whichever variant the build machine has. Its workflow gains `toolchain-variant: patched`, which replaces the apps' `msys2-package-urls` workaround and their own patch files.

## Qualification per release

- **Stock:** unchanged from today.
- **Patched,** on each target with a layer:
  - tier1 (new project build/run, Gorm, self-update);
  - the package checks (Arlen, tools-xctest);
  - the ABI report;
  - the `verified_by` check of each new or changed patch;
  - one Dan app's packaged build (ScreenshotTool on Windows first).
- **Switching:** stock → patched → stock leaves a byte-identical toolchain. An update keeps the variant.

## Rollout

1. This design and the protocol, reviewed by Dan (this PR).
2. `toolchains/carry/` with the canonical backports for the Windows set (libs-back carry; ObjcMarkdown's libs-base and libs-gui patches), and the layer build in the Windows workflow, with the ABI check. No CLI change yet; the artifact isn't published.
3. CLI support (`--variant`, apply, restore, update, doctor, `--json`), with native tests including the Windows rename path. A Windows gate on GitHub runners: stock→patched→stock, update keeping the variant, and ScreenshotTool's MSI built on the patched variant.
4. The first release with a Windows layer, on Dan's go.
5. Then the Linux layer (the X11 libs-back series, merged from the three apps' drifted copies), when an app wants it from the managed toolchain rather than its own AppImage build.

## Open questions for Dan

- **Release:** does the layer go into its own release after v0.1.9 (suggested: v0.2.0, since it adds an artifact kind and a setup option), or into v0.1.9 itself? Suggested: after, so v0.1.9 (tools-xctest, #81, #85) isn't held up.
- **Patches already merged upstream but newer than our base** (libs-back#227, #246; libs-gui `3f5efad1`): carry them in the layer, or move the stock pin forward? Moving the pin is a stock change, with full requalification. Suggested: carry them in the layer for now.
- **Linux:** when should the Linux layer come? Suggested: after Windows, when an app asks for it.
