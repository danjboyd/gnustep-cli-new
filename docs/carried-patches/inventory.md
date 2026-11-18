# Carried GNUstep patches: inventory (2026-11-17)

Every change to a GNUstep library that our toolchain or one of Dan's apps ships ahead of
upstream, as of the default branch of each repository on 2026-11-17:
- gnustep-cli-new: `0a3293d`;
- ScreenshotTool: `main` `5f26db3`;
- ObjcMarkdown (Markdown Viewer): `main` `f025f90`;
- LinDirStat: `main` `a5da5e9`.

This is the starting point for the patch layer ([../specs/patch-layer.md](../specs/patch-layer.md)).
From now on new carried patches come in through [README.md](README.md).

## The stock bases

| Target | libs-base | libs-gui | libs-back |
|---|---|---|---|
| Linux toolchains (all five) | `d898f703` + our 8 TLS patches | `7892137b` (master) | `bf3b3ced` (master) |
| Windows msys2-clang64 | MSYS2 `gnustep-base 1.31.1`, rebuilt by us as `1.31.1-10.5` with 4 patches | MSYS2 `gnustep-gui 0.32.0-7` | MSYS2 `gnustep-back 0.32.0-6` |

The apps' own Linux builds use different bases:
- LinDirStat patches `bf3b3ced`, the same libs-back our Linux toolchain builds.
- ScreenshotTool builds its own toolchain from the `base-1_31_1`, `gui-0_32_0` and `back-0_32_0` release tags.
- ObjcMarkdown builds from the commits its CI image pins.

So the same change exists as several backports.

## Already in the managed toolchain (gnustep-cli-new)

| Library | Patch | Targets | Upstream |
|---|---|---|---|
| libs-base | 0001–0008 TLS series: strict host verification on by default, error message fix, TLS improvements, verify-failure notification, security improvement, host verification for address URLs | Linux (5) and OpenBSD recipes | upstream commits backported to our pin |
| libs-base | `bace6f54` clang workaround (#589) | Windows | upstream commit; MSYS2's own package applies it too |
| libs-base | 0007 security improvement, without its test hunk | Windows | upstream commit |
| libs-base | 0009 on Windows, also trust the bundled authorities | Windows | ours (#44); not sent |
| libs-base | 0010 clang 23 compile fix, without its CI hunk | Windows | upstream #856 |
| libs-gui | Command modifier in key bindings (`543628d9`) | Linux and OpenBSD, **PR #33 only, not merged** | danjboyd/libs-gui; not sent |

These stay in the stock toolchain: they're security or build fixes that every user needs. They are not candidates for the layer.

## Carried by the apps

### Windows (what the MSIs ship)

| Library | Change | Carried by | How | Upstream |
|---|---|---|---|---|
| libs-back | win32pbs: images between the Windows clipboard and gpbs | ScreenshotTool, ObjcMarkdown | danjboyd/libs-back `carry-0.32.0.5` MSYS2 package | gnustep/libs-back#246, **merged 2026-11-15** (`5e14866`), after 0.32.0; the carry release notes still say open |
| libs-back | win32: client-drawn captions (`GSBackClientDrawsCaptions`, Snap Layouts) | same | same | topic branch `win32-client-caption`; not sent |
| libs-back | win32: `-setmaxsize::` keeps the maximize box as the style says | same | same | `win32-setmaxsize`; not sent |
| libs-back | win32: DWM shadow and rounding for borderless windows | same | same | `win32-popup-shadows`; not sent |
| libs-back | win32: per-monitor DPI awareness (`GSBackDPIAware`) | same | same | `win32-per-monitor-dpi`; not sent |
| libs-back | win32: monitor frames flipped against the primary's height | same | same | `win32-monitor-frames`; not sent |
| libs-back | win32: timers and redisplay during a move or resize | **nobody yet**: only in `carry-0.32.0.6` (2026-11-11); both apps still pin `.5` | — | `win32-sizemove-timers`; not sent |
| libs-base | GSAttributedString: hash cached attribute dictionaries by content (ObjcMarkdown #94, quadratic text building) | ObjcMarkdown | rebuilt DLL in CI (`build-windows-gnustep-patches.sh`) | not sent |
| libs-gui | GSLayoutManager: compile out the glyph-run sanity check (#94, quadratic layout) | ObjcMarkdown | same | reported as gnustep/libs-gui#992 (issue); patch not sent |
| libs-gui | GSTheme: the theme sets `GSBackHandlesWindowDecorations` before the backend reads it | ObjcMarkdown | same | prepared in plugins-themes-Adwaita#13; not sent |
| libs-gui | `3f5efad1`: NSScrollView stops re-tiling without end with `autohidesScrollers` (#121) | ObjcMarkdown | same | upstream commit, newer than 0.32.0 |
| libs-base | `bace6f54` | ObjcMarkdown | same | identical to ours |

### Linux (AppImages, Flatpak, CI images)

All libs-back, X11 backend:

| Change | ScreenshotTool | ObjcMarkdown | LinDirStat | Upstream |
|---|---|---|---|---|
| Reject an all-zero `_NET_FRAME_EXTENTS` answer | ✓ | — | ✓ | gnustep/libs-back#227 (`170c643`), newer than both our pin and 0.32.0 |
| Keep the window manager functions (Motif hints) of windows the gui decorates | ✓ | ✓ | ✓ | gnustep/libs-back#244, open |
| Type menus, tool tips, drag images and modal panels as GTK does | ✓ | ✓ | ✓ | `x11-window-types`; not sent |
| Alpha channel for borderless windows when a theme asks | ✓ | ✓ | ✓ | `x11-borderless-alpha`; not sent |
| Window shadows and rounded corners (cairo) | ✓ | ✓ | ✓ | `x11-window-shadows`; not sent |
| Popover shadows for menus (cairo) | ✓ | ✓ | ✓ | `x11-popover-shadows`; not sent |
| List `WM_DELETE_WINDOW` on closable windows | ✓ | ✓ | ✓ | `x11-wm-delete-window`; not sent |
| XDND: answer `TARGETS` and `text/uri-list`, refuse other types | ✓ | ✓ | — | prepared (`danjboyd/libs-back-xdnd`); not sent |
| XDND: speak version 3, send what each version expects | ✓ | ✓ | — | prepared; not sent |
| xpbs: offer copied files as `text/uri-list` and `x-special/gnome-copied-files` | — | ✓ | — | prepared; not sent |

ObjcMarkdown also applies its libs-base and libs-gui patches above to its Linux builds.

## Drift between the copies

The same change is carried in up to three places, and the copies no longer match:
- **ScreenshotTool and ObjcMarkdown** match apart from 1–2 lines per patch, which is header and context noise.
- **LinDirStat carries an older, smaller version of the X11 series.** For example:
  - window shadows: 870 changed lines, against 1,651 in the other two;
  - window types: 171 against 480.
  
  Its patches date from before the `-v5`…`-v7` revisions on danjboyd/libs-back.
- **Windows:** both apps ship libs-back `carry-0.32.0.5`; `.6` adds the size-move timer fix, and neither has picked it up.
- **The topic branches are the reference.** danjboyd/libs-back holds them (`x11-*-v7`, `win32-*`, `carry`), but each app's patch files are hand-made backports with nothing that ties them to a branch revision. LinDirStat's lock file is the exception: it records the series commits.

This is the drift the layer and the protocol are meant to end: one canonical backport per base, built once and shipped to every app.

## Not in scope here

- danjboyd/libs-sharing: a separate library the apps vendor, not a patch to GNUstep.
- The `gnustep-swift*` carry branches on the forks: another project's carry set, not shipped by these apps.
- macOS builds: they use Cocoa.
