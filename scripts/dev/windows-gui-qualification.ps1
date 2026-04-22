[CmdletBinding()]
param(
  [string]$ManagedRoot = "$env:LOCALAPPDATA\gnustep-cli",
  [string]$ReferenceMsysRoot = "C:\msys64",
  [string]$GormRoot = "C:\Users\Administrator\git\apps-gorm",
  [string]$OutputDir = "C:\gnustep-gui-qualification",
  [switch]$SkipGorm
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function New-Directory([string]$Path) {
  New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Get-TreeCount([string]$Path) {
  if (-not (Test-Path $Path)) { return 0 }
  $item = Get-Item $Path
  if (-not $item.PSIsContainer) { return 1 }
  return (Get-ChildItem $Path -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object).Count
}

function Write-RuntimeDiff {
  param([string]$ManagedRoot, [string]$ReferenceMsysRoot, [string]$OutputPath)
  $paths = @(
    'clang64\bin',
    'clang64\etc',
    'clang64\lib\GNUstep',
    'clang64\share\GNUstep',
    'usr\bin',
    'etc\pacman.conf',
    'etc\profile',
    'etc\fstab',
    'var\lib\pacman\local'
  )
  $rows = foreach ($relative in $paths) {
    $managedPath = Join-Path $ManagedRoot $relative
    $referencePath = Join-Path $ReferenceMsysRoot $relative
    [pscustomobject]@{
      relative_path = $relative
      managed_exists = Test-Path $managedPath
      managed_count = Get-TreeCount $managedPath
      reference_exists = Test-Path $referencePath
      reference_count = Get-TreeCount $referencePath
    }
  }
  $rows | ConvertTo-Json -Depth 4 | Set-Content -Path $OutputPath -Encoding UTF8
  return $rows
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
  Add-Type @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public class GNUstepQualificationWindows {
  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
}
'@ -ErrorAction SilentlyContinue
  $process = Get-Process | Where-Object { $_.ProcessName -eq $ProcessName } | Select-Object -First 1
  if (-not $process) { return @() }
  $target = [uint32]$process.Id
  $rows = New-Object System.Collections.Generic.List[object]
  [GNUstepQualificationWindows]::EnumWindows({
    param($handle, $lparam)
    $windowPid = [uint32]0
    [void][GNUstepQualificationWindows]::GetWindowThreadProcessId($handle, [ref]$windowPid)
    if ($windowPid -eq $target) {
      $titleBuilder = New-Object System.Text.StringBuilder 512
      $rect = New-Object GNUstepQualificationWindows+RECT
      [void][GNUstepQualificationWindows]::GetWindowText($handle, $titleBuilder, $titleBuilder.Capacity)
      [void][GNUstepQualificationWindows]::GetWindowRect($handle, [ref]$rect)
      $rows.Add([pscustomobject]@{
        handle = ('0x{0:X}' -f $handle.ToInt64())
        visible = [GNUstepQualificationWindows]::IsWindowVisible($handle)
        title = $titleBuilder.ToString()
        left = $rect.Left
        top = $rect.Top
        right = $rect.Right
        bottom = $rect.Bottom
        width = $rect.Right - $rect.Left
        height = $rect.Bottom - $rect.Top
      })
    }
    return $true
  }, [IntPtr]::Zero) | Out-Null
  return @($rows)
}

function New-AppKitSmokeProject([string]$ProjectRoot) {
  New-Directory $ProjectRoot
  @'
include $(GNUSTEP_MAKEFILES)/common.make

APP_NAME = SmokeWindow
SmokeWindow_OBJC_FILES = main.m

include $(GNUSTEP_MAKEFILES)/application.make
'@ | Set-Content -Path (Join-Path $ProjectRoot 'GNUmakefile') -Encoding ASCII
  @'
#import <AppKit/AppKit.h>

@interface AppDelegate : NSObject
{
  NSWindow *_window;
}
@end

@implementation AppDelegate
- (void)applicationDidFinishLaunching:(NSNotification *)notification
{
  NSRect frame = NSMakeRect(180, 180, 420, 180);
  _window = [[NSWindow alloc] initWithContentRect:frame
                                        styleMask:(NSTitledWindowMask | NSClosableWindowMask | NSMiniaturizableWindowMask)
                                          backing:NSBackingStoreBuffered
                                            defer:NO];
  [_window setTitle:@"GNUstep Managed GUI Smoke"];
  NSTextField *label = [[NSTextField alloc] initWithFrame:NSMakeRect(24, 72, 360, 32)];
  [label setStringValue:@"GNUstep managed AppKit window"];
  [label setBezeled:NO];
  [label setDrawsBackground:NO];
  [label setEditable:NO];
  [label setSelectable:NO];
  [[_window contentView] addSubview:label];
  [_window makeKeyAndOrderFront:nil];
}
@end

int main(int argc, const char **argv)
{
  NSAutoreleasePool *pool = [NSAutoreleasePool new];
  NSApplication *app = [NSApplication sharedApplication];
  AppDelegate *delegate = [AppDelegate new];
  [app setDelegate:delegate];
  [pool release];
  return NSApplicationMain(argc, argv);
}
'@ | Set-Content -Path (Join-Path $ProjectRoot 'main.m') -Encoding ASCII
}

function Invoke-QualificationCommand([string]$Command, [string]$WorkingDirectory, [string]$LogPath) {
  Push-Location $WorkingDirectory
  try {
    Invoke-Expression $Command *>&1 | Tee-Object -FilePath $LogPath
    if ($LASTEXITCODE -ne 0) {
      throw "Command failed with exit code ${LASTEXITCODE}: $Command"
    }
  } finally {
    Pop-Location
  }
}

New-Directory $OutputDir
$runtimeDiffPath = Join-Path $OutputDir 'runtime-diff.json'
$runtimeDiff = Write-RuntimeDiff -ManagedRoot $ManagedRoot -ReferenceMsysRoot $ReferenceMsysRoot -OutputPath $runtimeDiffPath

$smokeRoot = Join-Path $OutputDir 'SmokeWindow'
New-AppKitSmokeProject $smokeRoot
Invoke-QualificationCommand -Command 'gnustep clean' -WorkingDirectory $smokeRoot -LogPath (Join-Path $OutputDir 'smoke-clean.log')
Invoke-QualificationCommand -Command 'gnustep build' -WorkingDirectory $smokeRoot -LogPath (Join-Path $OutputDir 'smoke-build.log')
Get-Process | Where-Object { $_.ProcessName -eq 'SmokeWindow' } | Stop-Process -Force -ErrorAction SilentlyContinue
Invoke-QualificationCommand -Command 'gnustep run' -WorkingDirectory $smokeRoot -LogPath (Join-Path $OutputDir 'smoke-run.log')
Start-Sleep -Seconds 4
$smokeWindows = Get-ProcessWindows -ProcessName 'SmokeWindow'
Capture-Screenshot (Join-Path $OutputDir 'smoke-window.png')

$gormWindows = @()
if (-not $SkipGorm) {
  if (-not (Test-Path $GormRoot)) {
    throw "Gorm root does not exist: $GormRoot"
  }
  Invoke-QualificationCommand -Command 'gnustep clean' -WorkingDirectory $GormRoot -LogPath (Join-Path $OutputDir 'gorm-clean.log')
  Invoke-QualificationCommand -Command 'gnustep build' -WorkingDirectory $GormRoot -LogPath (Join-Path $OutputDir 'gorm-build.log')
  Get-Process | Where-Object { $_.ProcessName -eq 'Gorm' } | Stop-Process -Force -ErrorAction SilentlyContinue
  Invoke-QualificationCommand -Command 'gnustep run' -WorkingDirectory $GormRoot -LogPath (Join-Path $OutputDir 'gorm-run.log')
  Start-Sleep -Seconds 8
  $gormWindows = Get-ProcessWindows -ProcessName 'Gorm'
  Capture-Screenshot (Join-Path $OutputDir 'gorm-window.png')
}

$summary = [pscustomobject]@{
  schema_version = 1
  command = 'windows-gui-qualification'
  managed_root = $ManagedRoot
  reference_msys_root = $ReferenceMsysRoot
  output_dir = $OutputDir
  runtime_diff = $runtimeDiff
  smoke = [pscustomobject]@{
    visible_windows = @($smokeWindows | Where-Object { $_.visible -and $_.width -gt 40 -and $_.height -gt 40 })
    screenshot = Join-Path $OutputDir 'smoke-window.png'
  }
  gorm = [pscustomobject]@{
    skipped = [bool]$SkipGorm
    visible_windows = @($gormWindows | Where-Object { $_.visible -and $_.width -gt 40 -and $_.height -gt 40 })
    screenshot = if ($SkipGorm) { $null } else { Join-Path $OutputDir 'gorm-window.png' }
  }
}

$summaryPath = Join-Path $OutputDir 'summary.json'
$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryPath -Encoding UTF8
$summary | ConvertTo-Json -Depth 8
