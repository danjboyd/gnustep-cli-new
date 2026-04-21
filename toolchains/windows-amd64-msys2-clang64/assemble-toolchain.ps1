[CmdletBinding()]
param(
  [string]$Prefix = "C:\gnustep-cli\toolchain",
  [string]$CacheDir = "C:\gnustep-cli\cache",
  [string]$MsysRoot = "",
  [string]$InstallerUrl = "https://github.com/msys2/msys2-installer/releases/latest/download/msys2-x86_64-latest.exe"
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

New-Item -ItemType Directory -Force -Path $Prefix | Out-Null
New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
if (-not $MsysRoot) {
  $MsysRoot = $Prefix
}
$prefixFull = [System.IO.Path]::GetFullPath($Prefix).TrimEnd('\')
$msysRootFull = [System.IO.Path]::GetFullPath($MsysRoot).TrimEnd('\')
$installingIntoManagedRoot = [string]::Equals($prefixFull, $msysRootFull, [System.StringComparison]::OrdinalIgnoreCase)

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
$pacmanLock = Join-Path $MsysRoot 'var\lib\pacman\db.lck'
if (Test-Path $pacmanLock) {
  Remove-Item -Force $pacmanLock -ErrorAction SilentlyContinue
}

& $bash -lc "true"
if ($LASTEXITCODE -ne 0) { throw 'MSYS2 shell bootstrap command failed.' }
& $bash -lc "pacman -Syuu --noconfirm || true"
if ($LASTEXITCODE -ne 0) { throw 'MSYS2 package database refresh failed.' }
& $bash -lc "pacman -S --noconfirm --needed make"
if ($LASTEXITCODE -ne 0) { throw 'MSYS2 host-package installation failed.' }
& $bash -lc "pacman -S --overwrite /clang64/include/Block.h --noconfirm --needed mingw-w64-clang-x86_64-clang mingw-w64-clang-x86_64-libobjc2 mingw-w64-clang-x86_64-libdispatch mingw-w64-clang-x86_64-gnustep-make mingw-w64-clang-x86_64-gnustep-base mingw-w64-clang-x86_64-gnustep-gui mingw-w64-clang-x86_64-gnustep-back mingw-w64-clang-x86_64-cairo mingw-w64-clang-x86_64-fontconfig mingw-w64-clang-x86_64-freetype mingw-w64-clang-x86_64-harfbuzz mingw-w64-clang-x86_64-icu mingw-w64-clang-x86_64-libjpeg-turbo mingw-w64-clang-x86_64-libpng mingw-w64-clang-x86_64-libtiff mingw-w64-clang-x86_64-pixman mingw-w64-clang-x86_64-pkgconf"
if ($LASTEXITCODE -ne 0) { throw 'MSYS2 GNUstep package installation failed.' }
& $bash -lc "pacman -Qkk"
if ($LASTEXITCODE -ne 0) { throw 'MSYS2 local package database integrity check failed.' }

$clangRoot = Join-Path $MsysRoot 'clang64'
if (-not (Test-Path $clangRoot)) {
  throw 'MSYS2 clang64 root not found after package installation.'
}

$toolDirs = @('bin','etc','include','lib','libexec','share')
if (-not $installingIntoManagedRoot) {
  $clangPrefix = Join-Path $Prefix 'clang64'
  New-Item -ItemType Directory -Force -Path $clangPrefix | Out-Null
  foreach ($entry in $toolDirs) {
    $source = Join-Path $clangRoot $entry
    if (Test-Path $source) {
      Copy-Item -Recurse -Force $source (Join-Path $clangPrefix $entry)
    }
  }

  $msysRootDirs = @('usr','etc','var')
  foreach ($entry in $msysRootDirs) {
    $source = Join-Path $MsysRoot $entry
    if (Test-Path $source) {
      Copy-Item -Recurse -Force $source (Join-Path $Prefix $entry)
    }
  }
}

# Compatibility links for older activation code. The canonical MSYS2 layout is
# <prefix>\clang64 plus <prefix>\usr, but these root-level directories keep
# existing release smoke scripts working while callers move to clang64 paths.
foreach ($entry in $toolDirs) {
  $source = Join-Path $clangRoot $entry
  if (Test-Path $source) {
    $destination = Join-Path $Prefix $entry
    if (-not [string]::Equals([System.IO.Path]::GetFullPath($source).TrimEnd('\'), [System.IO.Path]::GetFullPath($destination).TrimEnd('\'), [System.StringComparison]::OrdinalIgnoreCase)) {
      Copy-Item -Recurse -Force $source $destination
    }
  }
}

$developerBin = Join-Path $Prefix 'usr\bin'
New-Item -ItemType Directory -Force -Path $developerBin | Out-Null
$developerTools = @('bash.exe', 'sh.exe', 'make.exe', 'sha256sum.exe')
foreach ($tool in $developerTools) {
  $source = Join-Path $MsysRoot ('usr\\bin\\' + $tool)
  if (-not (Test-Path $source)) {
    throw ('Required MSYS2 developer tool is missing: ' + $source)
  }
  $destination = Join-Path $developerBin $tool
  if (-not [string]::Equals([System.IO.Path]::GetFullPath($source), [System.IO.Path]::GetFullPath($destination), [System.StringComparison]::OrdinalIgnoreCase)) {
    Copy-Item -Force -LiteralPath $source -Destination $destination
  }
}
$developerRuntimeFiles = Get-ChildItem -Path (Join-Path $MsysRoot 'usr\bin') -File | Where-Object { $_.Extension -in @('.exe', '.dll') }
if ($developerRuntimeFiles.Count -eq 0) {
  throw 'No MSYS2 usr\bin executable/DLL runtime files were found for developer tools.'
}
foreach ($runtimeFile in $developerRuntimeFiles) {
  $destination = Join-Path $developerBin $runtimeFile.Name
  if (-not [string]::Equals([System.IO.Path]::GetFullPath($runtimeFile.FullName), [System.IO.Path]::GetFullPath($destination), [System.StringComparison]::OrdinalIgnoreCase)) {
    Copy-Item -Force -LiteralPath $runtimeFile.FullName -Destination $destination
  }
}

$activateBat = @(
  '@echo off',
  'set GNUSTEP_MAKEFILES=%~dp0clang64\share\GNUstep\Makefiles',
  'set GNUSTEP_CONFIG_FILE=%~dp0clang64\etc\GNUstep\GNUstep.conf',
  'set PATH=%~dp0clang64\bin;%~dp0bin;%~dp0usr\bin;%PATH%'
)
Set-Content -Path (Join-Path $Prefix 'GNUstep.bat') -Value $activateBat -Encoding ASCII

$activatePs1 = @(
  '$prefix = Split-Path -Parent $MyInvocation.MyCommand.Path',
  '$env:GNUSTEP_MAKEFILES = Join-Path $prefix ''clang64\share\GNUstep\Makefiles''',
  '$env:GNUSTEP_CONFIG_FILE = Join-Path $prefix ''clang64\etc\GNUstep\GNUstep.conf''',
  '$env:PATH = (Join-Path $prefix ''clang64\bin'') + '';'' + (Join-Path $prefix ''bin'') + '';'' + (Join-Path $prefix ''usr\bin'') + '';'' + $env:PATH'
)
Set-Content -Path (Join-Path $Prefix 'GNUstep.ps1') -Value $activatePs1 -Encoding ASCII

Write-Host "MSYS2 managed toolchain assembly completed at $Prefix"

