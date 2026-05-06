[CmdletBinding()]
param(
  [string]$WorkRoot = "C:\gnustep-gorm-validation",
  [string]$ToolchainZip = "C:\gnustep-gorm-validation\gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0.zip",
  [string]$GormPackageZip = "C:\gnustep-gorm-validation\gorm-gorm-windows-amd64-msys2-clang64-1.5.0-snapshot.20260505.zip",
  [string]$ToolchainRoot = "C:\gnustep-gorm-validation\toolchain",
  [string]$OutputDir = "C:\gnustep-gorm-validation\output"
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function New-Directory([string]$Path) {
  New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Capture-Screenshot([string]$Path) {
  Add-Type -AssemblyName System.Windows.Forms
  Add-Type -AssemblyName System.Drawing
  $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
  $bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
  $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
  $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
  $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
  $graphics.Dispose()
  $bitmap.Dispose()
}

function Get-ProcessWindows([string]$ProcessName) {
  return @(Get-Process | Where-Object { $_.ProcessName -eq $ProcessName } | ForEach-Object {
    [pscustomobject]@{
      handle = ('0x{0:X}' -f $_.MainWindowHandle.ToInt64())
      process_id = $_.Id
      visible = ($_.MainWindowHandle -ne [IntPtr]::Zero)
      title = $_.MainWindowTitle
      left = 0
      top = 0
      right = 0
      bottom = 0
      width = if ($_.MainWindowHandle -ne [IntPtr]::Zero) { 1 } else { 0 }
      height = if ($_.MainWindowHandle -ne [IntPtr]::Zero) { 1 } else { 0 }
    }
  })
}

New-Directory $OutputDir
$toolchainRoot = $ToolchainRoot.TrimEnd('\')
$packageRoot = Join-Path $WorkRoot 'package'
$progressLog = Join-Path $OutputDir 'progress.log'
Set-Content -Path $progressLog -Value 'starting validation' -Encoding UTF8
$requiredToolchainPaths = @(
  (Join-Path $toolchainRoot 'clang64\bin'),
  (Join-Path $toolchainRoot 'clang64\share\GNUstep\Makefiles\GNUstep.sh'),
  (Join-Path $toolchainRoot 'usr\bin\bash.exe')
)
if (($requiredToolchainPaths | Where-Object { -not (Test-Path $_) }).Count -gt 0) {
  Remove-Item -Recurse -Force $toolchainRoot -ErrorAction SilentlyContinue
  New-Directory $toolchainRoot
  Add-Content -Path $progressLog -Value 'expanding toolchain'
  Expand-Archive -Force -LiteralPath $ToolchainZip -DestinationPath $toolchainRoot
}
foreach ($link in @('clang64', 'usr', 'bin')) {
  $target = Join-Path $toolchainRoot $link
  $linkPath = "C:\$link"
  if ((Test-Path $target) -and -not (Test-Path $linkPath)) {
    Add-Content -Path $progressLog -Value "creating junction $linkPath -> $target"
    cmd /c "mklink /J `"$linkPath`" `"$target`"" | Out-Null
  }
}
Remove-Item -Recurse -Force $packageRoot -ErrorAction SilentlyContinue
New-Directory $packageRoot
Add-Content -Path $progressLog -Value 'expanding Gorm package'
Expand-Archive -Force -LiteralPath $GormPackageZip -DestinationPath $packageRoot

$env:PATH = "$toolchainRoot\bin;$toolchainRoot\clang64\bin;$toolchainRoot\usr\bin;$packageRoot\Applications\Gorm.app;$packageRoot\Library\Frameworks\GormCore.framework;$packageRoot\Library\Libraries;" + $env:PATH
$env:GNUSTEP_MAKEFILES = Join-Path $toolchainRoot 'clang64\share\GNUstep\Makefiles'
$env:GNUSTEP_CONFIG_FILE = Join-Path $toolchainRoot 'clang64\etc\GNUstep\GNUstep.conf'
$env:GNUSTEP_USER_ROOT = (Join-Path $WorkRoot 'user')
New-Directory $env:GNUSTEP_USER_ROOT

Get-Process | Where-Object { $_.ProcessName -eq 'Gorm' } | Stop-Process -Force -ErrorAction SilentlyContinue
$stdout = Join-Path $OutputDir 'gorm.stdout.log'
$stderr = Join-Path $OutputDir 'gorm.stderr.log'
$exe = Join-Path $packageRoot 'Applications\Gorm.app\Gorm.exe'
$bash = Join-Path $toolchainRoot 'usr\bin\bash.exe'
if (Test-Path $bash) {
  $msysPackage = $packageRoot -replace '\\', '/'
  $msysPackage = $msysPackage -replace '^C:', '/c'
  $launchScript = Join-Path $OutputDir 'launch-gorm.sh'
  @(
    '. /clang64/share/GNUstep/Makefiles/GNUstep.sh',
    "export PATH=/bin:/clang64/bin:/usr/bin:$msysPackage/Applications/Gorm.app:$msysPackage/Library/Frameworks/GormCore.framework:$msysPackage/Library/Libraries:`$PATH",
    "cd $msysPackage/Applications/Gorm.app",
    'exec ./Gorm.exe'
  ) | Set-Content -Path $launchScript -Encoding ASCII
  $process = Start-Process -FilePath $bash -ArgumentList @($launchScript) -WorkingDirectory (Split-Path $exe) -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
} else {
  $process = Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe) -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
}
Add-Content -Path $progressLog -Value "started Gorm pid=$($process.Id)"
Start-Sleep -Seconds 8
Add-Content -Path $progressLog -Value 'collecting window handles'
$windows = @(Get-ProcessWindows -ProcessName 'Gorm')
$visible = @($windows | Where-Object { $_.visible })
$processStillRunning = (-not $process.HasExited) -or (@(Get-Process | Where-Object { $_.ProcessName -eq 'Gorm' }).Count -gt 0)
$screenshot = Join-Path $OutputDir 'gorm-window.png'
Add-Content -Path $progressLog -Value "process_still_running=$processStillRunning visible_windows=$(@($visible).Count)"
try {
  Add-Content -Path $progressLog -Value 'capturing screenshot'
  Capture-Screenshot $screenshot
} catch {
  Set-Content -Path (Join-Path $OutputDir 'screenshot-error.txt') -Value $_.Exception.Message -Encoding UTF8
  $screenshot = $null
}
if ($processStillRunning) {
  Add-Content -Path $progressLog -Value 'stopping Gorm'
  Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
  Get-Process | Where-Object { $_.ProcessName -eq 'Gorm' } | Stop-Process -Force -ErrorAction SilentlyContinue
}
Add-Content -Path $progressLog -Value 'writing summary'

$summary = [pscustomobject]@{
  schema_version = 1
  command = 'windows-gorm-package-gui-validation'
  ok = ($processStillRunning -and @($visible).Count -gt 0)
  status = if ($processStillRunning -and @($visible).Count -gt 0) { 'ok' } else { 'error' }
  summary = if ($processStillRunning -and @($visible).Count -gt 0) { 'Windows Gorm package launched and exposed a visible window.' } else { 'Windows Gorm package launch/window evidence failed.' }
  toolchain_zip = $ToolchainZip
  package_zip = $GormPackageZip
  executable = $exe
  process_still_running_after_wait = $processStillRunning
  visible_windows = $visible
  all_windows = $windows
  screenshot = $screenshot
  stdout = $stdout
  stderr = $stderr
}
$summaryPath = Join-Path $OutputDir 'summary.json'
$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryPath -Encoding UTF8
$summary | ConvertTo-Json -Depth 8
if (-not $summary.ok) { exit 1 }
