# Windows Integration

Windows bootstrap is PowerShell. The installed full CLI is `gnustep.exe` and must be invokable from both PowerShell and `cmd.exe`. Under the hood, the managed `msys2-clang64` target may use MSYS2 shell tools for build/package operations, but that detail must not force the user to manually start an MSYS2 shell for ordinary CLI invocation.

The v1 managed `msys2-clang64` artifact is assembled by running the official
MSYS2 installer into a private GNUstep CLI root and installing the curated
package set there. End-user setup installs that prepared artifact; it should
not depend on, mutate, or discover a global `C:\msys64` installation.

Only the user-facing `<install-root>\bin` directory should be added to the
default PowerShell PATH for future sessions. The private MSYS2 directories are
used by activation helpers and by `gnustep.exe` internally.

## Activation Contract

The managed Windows toolchain publishes both activation helpers:

- `GNUstep.ps1` for PowerShell
- `GNUstep.bat` for `cmd.exe`

Both helpers must set:

- `GNUSTEP_MAKEFILES` to the managed `clang64\share\GNUstep\Makefiles` tree
- `GNUSTEP_CONFIG_FILE` to the managed `clang64\etc\GNUstep\GNUstep.conf` file
- `PATH` with `clang64\bin`, then `bin`, then `usr\bin`, before the inherited user PATH

The `clang64\bin` prefix is required because GNUstep Make shell builds expect the MSYS2 `/clang64` layout. The `usr\bin` prefix is required because developer tools such as `bash.exe`, `make.exe`, and `sha256sum.exe` depend on the MSYS runtime DLL closure.

The managed artifact should preserve a coherent private MSYS2-style root, not
only a hand-picked DLL subset. At minimum that root includes:

- `clang64\` from the curated MSYS2 clang64 package set
- `usr\` for the MSYS shell/runtime tools used by GNUstep Make and `openapp`
- `etc\` for MSYS configuration such as `profile`, `fstab`, and pacman config
- `var\lib\pacman\local` for package provenance/debuggability

Root-level `bin`, `etc`, `include`, `lib`, `libexec`, and `share` compatibility
copies may exist during the transition, but new code should prefer the
canonical `clang64\...` paths.

## GUI Launch Contract

For `.app` targets, `gnustep run` must launch through the managed GNUstep/MSYS
environment rather than invoking the app executable directly. The Windows
managed `msys2-clang64` launch path is:

```sh
. /clang64/share/GNUstep/Makefiles/GNUstep.sh
/clang64/bin/openapp ./Application.app
```

The full CLI may wrap that in managed `usr\bin\bash.exe`, but users should not
need to start an MSYS shell manually.

## Developer Shell

`gnustep shell` is currently a Windows-only full-CLI command. It opens the
managed private MSYS2 `CLANG64` shell using the installed GNUstep environment,
without exposing `pacman` as a GNUstep CLI package-management command.

This shell is an escape hatch for developers who need native MSYS2 tooling. If a
project requires an additional MSYS2 package during development, the recommended
manual path is to open `gnustep shell` and install it with MSYS2 tools inside
that managed root. Ordinary `gnustep build` and `gnustep run` workflows should
continue to work from PowerShell without entering this shell.

## Validation Contract

Windows release qualification must prove these flows on a disposable `windows-2022` OTVM lease:

- PowerShell bootstrap setup from a public release manifest
- installed `gnustep.exe --version` and `--help` from PowerShell
- installed `gnustep.exe --version` and `--help` from `cmd.exe`
- installed `gnustep.exe doctor --json` with a matching Windows manifest
- installed `gnustep.exe shell --print-command` from PowerShell
- package install/remove smoke
- extracted-toolchain rebuild smoke using only the managed toolchain layout
- GUI smoke: build and launch a minimal AppKit application, then verify a
  visible nonblank screenshot
- Gorm qualification: build Gorm, launch it through managed `openapp`, and
  verify a screenshot containing the Gorm menu, Inspector, and palette windows

The local helper for this lane is:

```powershell
scripts\dev\windows-gui-qualification.ps1 `
  -ManagedRoot "$env:LOCALAPPDATA\gnustep-cli" `
  -ReferenceMsysRoot C:\msys64 `
  -GormRoot C:\Users\Administrator\git\apps-gorm
```
