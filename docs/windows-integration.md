# Windows Integration

Windows bootstrap is PowerShell. The installed full CLI is `gnustep.exe` and must be invokable from both PowerShell and `cmd.exe`. Under the hood, the managed `msys2-clang64` target may use MSYS2 shell tools for build/package operations, but that detail must not force the user to manually start an MSYS2 shell for ordinary CLI invocation.

## Activation Contract

The managed Windows toolchain publishes both activation helpers:

- `GNUstep.ps1` for PowerShell
- `GNUstep.bat` for `cmd.exe`

Both helpers must set:

- `GNUSTEP_MAKEFILES` to the managed `share\GNUstep\Makefiles` tree
- `GNUSTEP_CONFIG_FILE` to the managed `etc\GNUstep\GNUstep.conf` file
- `PATH` with `clang64\bin`, then `bin`, then `usr\bin`, before the inherited user PATH

The `clang64\bin` prefix is required because GNUstep Make shell builds expect the MSYS2 `/clang64` layout. The `usr\bin` prefix is required because developer tools such as `bash.exe`, `make.exe`, and `sha256sum.exe` depend on the MSYS runtime DLL closure.

## Validation Contract

Windows release qualification must prove these flows on a disposable `windows-2022` OTVM lease:

- PowerShell bootstrap setup from a public release manifest
- installed `gnustep.exe --version` and `--help` from PowerShell
- installed `gnustep.exe --version` and `--help` from `cmd.exe`
- installed `gnustep.exe doctor --json` with a matching Windows manifest
- package install/remove smoke
- extracted-toolchain rebuild smoke using only the managed toolchain layout
