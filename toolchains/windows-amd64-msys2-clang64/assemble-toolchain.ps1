[CmdletBinding()]
param(
  [string]$Prefix = "C:\gnustep-cli\toolchain",
  [string]$CacheDir = "C:\gnustep-cli\cache",
  [string]$MsysRoot = "",
  [string]$InputManifest = "",
  # Resolve mode: install the current MSYS2 packages instead of the locked set
  # and write the resolve record (pacman -Q plus sync databases) to this
  # directory. scripts/dev/msys2_lock.py turns that record into the lock.
  [string]$ResolveOut = ""
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# Windows PowerShell 5.1 leaves $PSScriptRoot empty in parameter defaults.
if (-not $InputManifest) {
  $InputManifest = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'input-manifest.json'
}
$inputs = Get-Content -Raw -Path $InputManifest | ConvertFrom-Json
$lockedPackages = @($inputs.locked_packages | Where-Object { $_ })
$resolveMode = [bool]$ResolveOut
if (-not $resolveMode -and $lockedPackages.Count -eq 0) {
  throw "$InputManifest has no locked_packages. Run a resolve (-ResolveOut) and lock it with scripts/dev/msys2_lock.py first."
}

function Get-VerifiedDownload {
  param([string]$Url, [string]$Sha256, [string]$Destination)
  if (Test-Path $Destination) {
    if ((Get-FileHash -Algorithm SHA256 -Path $Destination).Hash.ToLowerInvariant() -eq $Sha256.ToLowerInvariant()) {
      return
    }
    Remove-Item -Force $Destination
  }
  Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Destination
  $actual = (Get-FileHash -Algorithm SHA256 -Path $Destination).Hash.ToLowerInvariant()
  if ($actual -ne $Sha256.ToLowerInvariant()) {
    Remove-Item -Force $Destination
    throw "Checksum mismatch for ${Url}: expected $Sha256, got $actual"
  }
}

function Get-InstalledPackages {
  $installed = @{}
  & $bash -lc "pacman -Q" | ForEach-Object {
    $parts = $_.Trim() -split '\s+'
    if ($parts.Count -eq 2) { $installed[$parts[0]] = $parts[1] }
  }
  if ($LASTEXITCODE -ne 0) { throw 'pacman -Q failed.' }
  return $installed
}

New-Item -ItemType Directory -Force -Path $Prefix | Out-Null
New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
if (-not $MsysRoot) {
  $MsysRoot = $Prefix
}
$prefixFull = [System.IO.Path]::GetFullPath($Prefix).TrimEnd('\')
$msysRootFull = [System.IO.Path]::GetFullPath($MsysRoot).TrimEnd('\')
$installingIntoManagedRoot = [string]::Equals($prefixFull, $msysRootFull, [System.StringComparison]::OrdinalIgnoreCase)

$bash = Join-Path $MsysRoot 'usr\bin\bash.exe'
$installer = Join-Path $CacheDir (Split-Path -Leaf $inputs.installer.url)

if (-not (Test-Path $bash)) {
  Get-VerifiedDownload -Url $inputs.installer.url -Sha256 $inputs.installer.sha256 -Destination $installer
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

$hostPackages = @($inputs.host_packages | ForEach-Object { $_.name }) -join ' '
$packages = @($inputs.packages | ForEach-Object { $_.name }) -join ' '
$overwrite = '--overwrite /clang64/include/Block.h'

if ($resolveMode) {
  # The first -Syuu may stop after updating the MSYS2 core; the second finishes.
  & $bash -lc "pacman -Syuu --noconfirm || true"
  & $bash -lc "pacman -Syuu --noconfirm"
  if ($LASTEXITCODE -ne 0) { throw 'MSYS2 package database refresh failed.' }
  & $bash -lc "pacman -S --noconfirm --needed $hostPackages"
  if ($LASTEXITCODE -ne 0) { throw 'MSYS2 host-package installation failed.' }
  & $bash -lc "pacman -S $overwrite --noconfirm --needed $packages"
  if ($LASTEXITCODE -ne 0) { throw 'MSYS2 GNUstep package installation failed.' }

  New-Item -ItemType Directory -Force -Path $ResolveOut | Out-Null
  & $bash -lc "pacman -Q" | Set-Content -Encoding ASCII -Path (Join-Path $ResolveOut 'pacman-Q.txt')
  foreach ($repo in @('msys', 'clang64')) {
    Copy-Item -Force (Join-Path $MsysRoot "var\lib\pacman\sync\$repo.db") (Join-Path $ResolveOut "$repo.db")
  }
  [ordered]@{
    schema_version = 1
    resolved_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    installer = $inputs.installer.url
  } | ConvertTo-Json | Set-Content -Encoding ASCII -Path (Join-Path $ResolveOut 'resolve.json')
}
else {
  # Install exactly the locked package files: download, verify each against
  # the SHA-256 recorded from the signed sync database, then pacman -U. There
  # is no -Sy, so nothing comes from the live repository.
  $installed = Get-InstalledPackages
  $pending = @($lockedPackages | Where-Object { $installed[$_.name] -ne $_.version })
  foreach ($package in $pending) {
    Get-VerifiedDownload -Url $package.url -Sha256 $package.sha256 -Destination (Join-Path $CacheDir $package.filename)
  }
  $coreNames = @('msys2-runtime', 'pacman', 'pacman-mirrors', 'msys2-keyring', 'bash', 'filesystem')
  $stages = @(
    @($pending | Where-Object { $coreNames -contains $_.name }),
    @($pending | Where-Object { $coreNames -notcontains $_.name })
  )
  $cacheUnix = (& $bash -lc "cygpath -u '$CacheDir'").Trim()
  foreach ($stage in $stages) {
    if ($stage.Count -eq 0) { continue }
    $listPath = Join-Path $CacheDir 'locked-install.txt'
    $stage | ForEach-Object { $_.filename } | Set-Content -Encoding ASCII -Path $listPath
    & $bash -lc "cd '$cacheUnix' && pacman -U $overwrite --noconfirm - < locked-install.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Locked MSYS2 package installation failed.' }
  }

  $installed = Get-InstalledPackages
  $lockedNames = @{}
  foreach ($package in $lockedPackages) {
    $lockedNames[$package.name] = $true
    if ($installed[$package.name] -ne $package.version) {
      throw "Locked package $($package.name) is at '$($installed[$package.name])', expected $($package.version)."
    }
  }
  $unlocked = @($installed.Keys | Where-Object { -not $lockedNames.ContainsKey($_) })
  if ($unlocked.Count -gt 0) {
    throw ('Installed packages missing from the lock (installer drift?): ' + ($unlocked -join ', '))
  }
}
& $bash -lc "pacman -Qkk >/tmp/gnustep-cli-pacman-qkk.out 2>&1"
$qkkExit = $LASTEXITCODE
$qkkOutput = & $bash -lc "cat /tmp/gnustep-cli-pacman-qkk.out"
$qkkOutput | ForEach-Object { Write-Host $_ }
if ($qkkExit -ne 0) {
  $unexpectedQkk = @(
    $qkkOutput | Where-Object {
      ($_ -match '^[^:]+: [0-9]+ total files, [1-9][0-9]* altered files$') -and
      ($_ -notmatch '^(ca-certificates|mingw-w64-clang-x86_64-ca-certificates|mingw-w64-clang-x86_64-libobjc2): ')
    }
  )
  if ($unexpectedQkk.Count -gt 0) {
    $unexpectedQkk | ForEach-Object { Write-Error $_ }
    throw 'MSYS2 local package database integrity check failed with unexpected altered package files.'
  }
}

$clangRoot = Join-Path $MsysRoot 'clang64'
if (-not (Test-Path $clangRoot)) {
  throw 'MSYS2 clang64 root not found after package installation.'
}

$toolDirs = @('bin','etc','include','lib','libexec','share')
$clangPrefix = Join-Path $Prefix 'clang64'
New-Item -ItemType Directory -Force -Path $clangPrefix | Out-Null
foreach ($entry in $toolDirs) {
  $source = Join-Path $clangRoot $entry
  if (Test-Path $source) {
    $destination = Join-Path $clangPrefix $entry
    if (-not [string]::Equals([System.IO.Path]::GetFullPath($source).TrimEnd('\'), [System.IO.Path]::GetFullPath($destination).TrimEnd('\'), [System.StringComparison]::OrdinalIgnoreCase)) {
      Copy-Item -Recurse -Force $source $destination
    }
  }
}

$msysRootDirs = @('usr','etc','var')
foreach ($entry in $msysRootDirs) {
  $source = Join-Path $MsysRoot $entry
  if (Test-Path $source) {
    $destination = Join-Path $Prefix $entry
    if (-not [string]::Equals([System.IO.Path]::GetFullPath($source).TrimEnd('\'), [System.IO.Path]::GetFullPath($destination).TrimEnd('\'), [System.StringComparison]::OrdinalIgnoreCase)) {
      Copy-Item -Recurse -Force $source $destination
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

# libdispatch's os/generic_win_base.h typedefs mode_t and pthread_attr_t, which
# MinGW's sys/types.h and winpthreads' pthread.h already define, so Foundation.h
# (which includes dispatch) fails to compile, alone or alongside <pthread.h>.
# Patch every copy, including the root-level compatibility copy made above.
foreach ($genericWinBase in @((Join-Path $Prefix 'clang64\include\os\generic_win_base.h'), (Join-Path $Prefix 'include\os\generic_win_base.h'))) {
  if (Test-Path $genericWinBase) {
    $genericWinBaseText = Get-Content -Path $genericWinBase -Raw
    $patchedText = $genericWinBaseText -replace 'typedef int mode_t;', "/* mode_t is provided by MinGW sys/types.h in this managed toolchain. */"
    $patchedText = $patchedText -replace '(?m)^typedef void pthread_attr_t;\r?$', "#if !defined(__MINGW32__) /* winpthreads defines pthread_attr_t */`ntypedef void pthread_attr_t;`n#endif"
    if ($patchedText -ne $genericWinBaseText) {
      Set-Content -Path $genericWinBase -Value $patchedText -Encoding ASCII -NoNewline
    }
  }
}

# MSYS2's gnustep-base 1.31.1 puts __block (BLOCK_SCOPE) on an instance
# variable, which clang 23 rejects; apply libs-base's fix (gnustep/libs-base#809).
foreach ($scheduler in @((Join-Path $Prefix 'clang64\include\Foundation\NSBackgroundActivityScheduler.h'), (Join-Path $Prefix 'include\Foundation\NSBackgroundActivityScheduler.h'))) {
  if (Test-Path $scheduler) {
    $schedulerText = Get-Content -Path $scheduler -Raw
    $patchedText = $schedulerText -replace 'BLOCK_SCOPE GSScheduledBlock _block;', 'GSScheduledBlock _block;'
    if ($patchedText -ne $schedulerText) {
      Set-Content -Path $scheduler -Value $patchedText -Encoding ASCII -NoNewline
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
