[CmdletBinding()]
param(
  [string]$Prefix = "C:\gnustep-cli\toolchain",
  [string]$CacheDir = "C:\gnustep-cli\cache",
  [string]$MsysRoot = "C:\msys64",
  [string]$InstallerUrl = "https://github.com/msys2/msys2-installer/releases/latest/download/msys2-x86_64-latest.exe"
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

New-Item -ItemType Directory -Force -Path $Prefix | Out-Null
New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null

$bash = Join-Path $MsysRoot 'usr\bin\bash.exe'
$installer = Join-Path $CacheDir 'msys2-x86_64-latest.exe'

if (-not (Test-Path $bash)) {
  Invoke-WebRequest -UseBasicParsing -Uri $InstallerUrl -OutFile $installer
  & $installer in --confirm-command --accept-messages --root ($MsysRoot -replace '\\', '/')
}

if (-not (Test-Path $bash)) {
  throw 'MSYS2 installation did not produce bash.exe at the expected path.'
}

$env:CHERE_INVOKING = '1'
& $bash -lc "true"
if ($LASTEXITCODE -ne 0) { throw 'MSYS2 shell bootstrap command failed.' }
& $bash -lc "pacman -Syuu --noconfirm || true"
if ($LASTEXITCODE -ne 0) { throw 'MSYS2 package database refresh failed.' }
& $bash -lc "pacman -S --noconfirm --needed make"
if ($LASTEXITCODE -ne 0) { throw 'MSYS2 host-package installation failed.' }
& $bash -lc "pacman -S --overwrite /clang64/include/Block.h --noconfirm --needed mingw-w64-clang-x86_64-clang mingw-w64-clang-x86_64-libobjc2 mingw-w64-clang-x86_64-libdispatch mingw-w64-clang-x86_64-gnustep-make mingw-w64-clang-x86_64-gnustep-base mingw-w64-clang-x86_64-gnustep-gui mingw-w64-clang-x86_64-gnustep-back"
if ($LASTEXITCODE -ne 0) { throw 'MSYS2 GNUstep package installation failed.' }

$clangRoot = Join-Path $MsysRoot 'clang64'
if (-not (Test-Path $clangRoot)) {
  throw 'MSYS2 clang64 root not found after package installation.'
}

$toolDirs = @('bin','etc','include','lib','libexec','share')
foreach ($entry in $toolDirs) {
  $source = Join-Path $clangRoot $entry
  if (Test-Path $source) {
    Copy-Item -Recurse -Force $source (Join-Path $Prefix $entry)
  }
}

Write-Host "MSYS2 managed toolchain assembly completed at $Prefix"
