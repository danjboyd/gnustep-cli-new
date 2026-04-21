param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$Script:CliVersion = "0.1.0-dev"
$Script:JsonMode = $false
$Script:QuietMode = $false
$Script:RootDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
$Script:SetupScope = "user"
$Script:SetupRoot = $null
$Script:SetupManifest = $env:SETUP_MANIFEST
$Script:TracePath = $env:GNUSTEP_BOOTSTRAP_TRACE
$Script:IsWindowsHost = $env:OS -eq "Windows_NT"


function Write-SetupProgress {
    param([string]$Message)
    if (-not $Script:JsonMode -and -not $Script:QuietMode) {
        Write-Output "setup: $Message"
    }
}

function Format-ByteCount {
    param([long]$Bytes)
    if ($Bytes -ge 1073741824) {
        return ("{0:N1} GB" -f ($Bytes / 1073741824.0))
    }
    if ($Bytes -ge 1048576) {
        return ("{0:N1} MB" -f ($Bytes / 1048576.0))
    }
    if ($Bytes -ge 1024) {
        return ("{0:N1} KB" -f ($Bytes / 1024.0))
    }
    return ("{0} bytes" -f $Bytes)
}

function Save-UrlToFile {
    param(
        [string]$Url,
        [string]$OutFile,
        [string]$Label
    )
    $request = [System.Net.HttpWebRequest]::Create($Url)
    $response = $null
    $inputStream = $null
    $outputStream = $null
    $downloaded = [int64]0
    $lastProgress = [DateTime]::MinValue
    $showProgress = -not $Script:JsonMode -and -not $Script:QuietMode

    try {
        $response = $request.GetResponse()
        $total = [int64]$response.ContentLength
        $inputStream = $response.GetResponseStream()
        $outputStream = [System.IO.File]::Open($OutFile, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        $buffer = New-Object byte[] 1048576

        while (($read = $inputStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
            $outputStream.Write($buffer, 0, $read)
            $downloaded += $read
            if ($showProgress) {
                $now = [DateTime]::UtcNow
                if (($now - $lastProgress).TotalMilliseconds -ge 500) {
                    if ($total -gt 0) {
                        $percent = [Math]::Min(100, [Math]::Floor(($downloaded * 100.0) / $total))
                        Write-Progress -Activity "Downloading $Label" -Status "$(Format-ByteCount $downloaded) of $(Format-ByteCount $total)" -PercentComplete $percent
                    }
                    else {
                        Write-Progress -Activity "Downloading $Label" -Status "$(Format-ByteCount $downloaded) downloaded"
                    }
                    $lastProgress = $now
                }
            }
        }
    }
    finally {
        if ($outputStream) { $outputStream.Dispose() }
        if ($inputStream) { $inputStream.Dispose() }
        if ($response) { $response.Dispose() }
        if ($showProgress) {
            Write-Progress -Activity "Downloading $Label" -Completed
        }
    }
    Write-SetupProgress "downloaded $Label ($(Format-ByteCount $downloaded))"
}

function Write-TraceEvent {
    param([string]$Step, [string]$Message = "")
    if (-not $Script:TracePath) {
        return
    }
    try {
        $traceDir = Split-Path -Parent $Script:TracePath
        if ($traceDir) {
            New-Item -ItemType Directory -Force -Path $traceDir | Out-Null
        }
        $record = @{
            timestamp = [DateTimeOffset]::UtcNow.ToString("o")
            step = $Step
            message = $Message
            pid = $PID
        } | ConvertTo-Json -Compress
        Add-Content -Encoding UTF8 -Path $Script:TracePath -Value $record
    }
    catch {
    }
}

function Get-ManifestObject {
    param([string]$ManifestSource)
    Write-TraceEvent "manifest.start" $ManifestSource
    if (-not $ManifestSource) {
        $localManifest = Join-Path $Script:RootDir "dist\stable\$($Script:CliVersion)\release-manifest.json"
        if (Test-Path $localManifest) {
            $ManifestSource = $localManifest
        }
        else {
            $ManifestSource = "https://github.com/danjboyd/gnustep-cli-new/releases/download/v$($Script:CliVersion)/release-manifest.json"
        }
    }
    if ($ManifestSource -match '^https?://') {
        $manifestPath = Join-Path ([System.IO.Path]::GetTempPath()) ("gnustep-manifest-" + [guid]::NewGuid().ToString() + ".json")
        Write-TraceEvent "manifest.download" $ManifestSource
        Save-UrlToFile -Url $ManifestSource -OutFile $manifestPath -Label "release manifest"
        Write-TraceEvent "manifest.downloaded" $manifestPath
    }
    else {
        $manifestPath = (Resolve-Path $ManifestSource).Path
        Write-TraceEvent "manifest.local" $manifestPath
    }
    Write-TraceEvent "manifest.loaded" $manifestPath
    return @{
        path = $manifestPath
        dir = Split-Path -Parent $manifestPath
        json = Get-Content -Raw $manifestPath | ConvertFrom-Json
    }
}

function Get-HostTarget {
    $arch = if ([Environment]::Is64BitOperatingSystem) { "amd64" } else { "unknown" }
    return @{
        os = "windows"
        arch = $arch
        cliId = "cli-windows-$arch-msys2-clang64"
        toolchainId = "toolchain-windows-$arch-msys2-clang64"
    }
}

function Get-Sha256 {
    param([string]$Path)
    return (Get-FileHash -Algorithm SHA256 -Path $Path).Hash.ToLowerInvariant()
}

function Expand-Artifact {
    param([string]$ArchivePath, [string]$Destination)
    Write-TraceEvent "extract.start" "$ArchivePath -> $Destination"
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    if ($ArchivePath.ToLowerInvariant().EndsWith(".zip")) {
        if ($Script:IsWindowsHost) {
            tar -xf $ArchivePath -C $Destination
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to extract $ArchivePath"
            }
        }
        else {
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            $archive = [System.IO.Compression.ZipFile]::OpenRead($ArchivePath)
            $destinationFull = [System.IO.Path]::GetFullPath($Destination)
            try {
                foreach ($entry in $archive.Entries) {
                    if ([string]::IsNullOrEmpty($entry.FullName)) {
                        continue
                    }
                    $relativePath = $entry.FullName.Replace("/", [System.IO.Path]::DirectorySeparatorChar).Replace("\", [System.IO.Path]::DirectorySeparatorChar)
                    $targetPath = [System.IO.Path]::GetFullPath((Join-Path $Destination $relativePath))
                    if (-not $targetPath.StartsWith($destinationFull, [System.StringComparison]::OrdinalIgnoreCase)) {
                        throw "Archive entry escapes destination root: $($entry.FullName)"
                    }
                    if ($relativePath.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
                        New-Item -ItemType Directory -Force -Path $targetPath | Out-Null
                        continue
                    }
                    $targetDir = Split-Path -Parent $targetPath
                    if ($targetDir) {
                        New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
                    }
                    [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $targetPath, $true)
                }
            }
            finally {
                $archive.Dispose()
            }
        }
    }
    else {
        tar -xzf $ArchivePath -C $Destination
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to extract $ArchivePath"
        }
    }
    Write-TraceEvent "extract.complete" "$ArchivePath -> $Destination"
}

function Get-SingleChildDirectory {
    param([string]$Path)
    $children = Get-ChildItem -Force $Path
    if ($children.Count -eq 1 -and $children[0].PSIsContainer) {
        return $children[0].FullName
    }
    return $Path
}

function Copy-TreeContents {
    param([string]$Source, [string]$Destination)
    Write-TraceEvent "copy.start" "$Source -> $Destination"
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    if ($Script:IsWindowsHost) {
        robocopy $Source $Destination /E /COPY:DAT /DCOPY:DAT /R:2 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
        if ($LASTEXITCODE -gt 7) {
            throw "Failed to copy $Source to $Destination with robocopy exit code $LASTEXITCODE."
        }
    }
    else {
        Copy-Item -Recurse -Force -ErrorAction Stop (Join-Path $Source '*') $Destination
    }
    Write-TraceEvent "copy.complete" "$Source -> $Destination"
}

function Remove-TempTree {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return
    }
    if ($env:GNUSTEP_BOOTSTRAP_KEEP_TEMP -eq "1") {
        Write-TraceEvent "cleanup.skipped" $Path
        return
    }
    Write-TraceEvent "cleanup.start" $Path
    if ($Script:IsWindowsHost) {
        $quoted = '"' + $Path.Replace('"', '""') + '"'
        Start-Process -FilePath "cmd.exe" -ArgumentList "/d", "/c", "rmdir /s /q $quoted" -WindowStyle Hidden | Out-Null
        Write-TraceEvent "cleanup.deferred" $Path
        return
    }
    Remove-Item -Recurse -Force $Path
    Write-TraceEvent "cleanup.complete" $Path
}

function Install-CliBundle {
    param([string]$Source, [string]$Destination)
    Copy-TreeContents -Source $Source -Destination $Destination
    $cli = Join-Path $Destination "bin\gnustep.exe"
    if (-not (Test-Path $cli)) {
        $cli = Join-Path $Destination "bin\gnustep"
    }
    if (-not (Test-Path $cli)) {
        throw "CLI bundle did not install a runnable gnustep binary."
    }
}

function Get-PathSetupCommand {
    param([string]$InstallRoot)
    return '. "' + (Join-Path $InstallRoot 'GNUstep.ps1') + '"'
}

function Ensure-GNUstepActivationScripts {
    param([string]$InstallRoot)

    $ps1Path = Join-Path $InstallRoot "GNUstep.ps1"
    $batPath = Join-Path $InstallRoot "GNUstep.bat"
    $tmpPath = Join-Path $InstallRoot "tmp"
    $etcPath = Join-Path $InstallRoot "etc"
    $fstabPath = Join-Path $etcPath "fstab"
    New-Item -ItemType Directory -Force -Path $tmpPath, $etcPath | Out-Null
    Set-Content -Encoding ASCII -Path $fstabPath -Value (($tmpPath.Replace('\', '/')) + " /tmp ntfs binary,noacl,posix=0,user 0 0")
    $ps1Content = @"
`$prefix = Split-Path -Parent `$MyInvocation.MyCommand.Path
`$env:GNUSTEP_MAKEFILES = Join-Path `$prefix 'clang64\share\GNUstep\Makefiles'
`$env:GNUSTEP_CONFIG_FILE = Join-Path `$prefix 'clang64\etc\GNUstep\GNUstep.conf'
`$env:TMPDIR = Join-Path `$prefix 'tmp'
`$env:TEMP = `$env:TMPDIR
`$env:TMP = `$env:TMPDIR
`$env:PATH = (Join-Path `$prefix 'clang64\bin') + ';' + (Join-Path `$prefix 'bin') + ';' + (Join-Path `$prefix 'usr\bin') + ';' + `$env:PATH
"@
    $batContent = @"
@echo off
set "GNUSTEP_MAKEFILES=%~dp0clang64\share\GNUstep\Makefiles"
set "GNUSTEP_CONFIG_FILE=%~dp0clang64\etc\GNUstep\GNUstep.conf"
set "TMPDIR=%~dp0tmp"
set "TEMP=%~dp0tmp"
set "TMP=%~dp0tmp"
set "PATH=%~dp0clang64\bin;%~dp0bin;%~dp0usr\bin;%PATH%"
"@

    Set-Content -Encoding UTF8 -Path $ps1Path -Value $ps1Content
    Set-Content -Encoding ASCII -Path $batPath -Value $batContent
    Write-TraceEvent "activation.write.complete" $InstallRoot
}

function Add-PathEntry {
    param(
        [string[]]$Entries,
        [string]$Target
    )

    $existing = [Environment]::GetEnvironmentVariable("Path", $Target)
    $parts = @()
    if ($existing) {
        $parts = @($existing -split ';' | Where-Object { $_ -and $_.Trim() })
    }
    for ($i = $Entries.Count - 1; $i -ge 0; $i--) {
        $entry = $Entries[$i]
        $alreadyPresent = $false
        foreach ($part in $parts) {
            if ([string]::Equals($part.TrimEnd('\'), $entry.TrimEnd('\'), [System.StringComparison]::OrdinalIgnoreCase)) {
                $alreadyPresent = $true
                break
            }
        }
        if (-not $alreadyPresent) {
            $parts = @($entry) + $parts
        }
    }
    [Environment]::SetEnvironmentVariable("Path", ($parts -join ';'), $Target)
}

function Set-GNUstepUserEnvironment {
    param(
        [string]$InstallRoot,
        [string]$Scope
    )

    if ($env:GNUSTEP_BOOTSTRAP_SKIP_PATH_UPDATE -eq "1") {
        Write-TraceEvent "path.update.skipped" "GNUSTEP_BOOTSTRAP_SKIP_PATH_UPDATE=1"
        return $false
    }

    $target = if ($Scope -eq "system") { "Machine" } else { "User" }
    $binPath = Join-Path $InstallRoot "bin"
    Add-PathEntry -Entries @($binPath) -Target $target
    [Environment]::SetEnvironmentVariable("GNUSTEP_MAKEFILES", (Join-Path $InstallRoot "clang64\share\GNUstep\Makefiles"), $target)
    [Environment]::SetEnvironmentVariable("GNUSTEP_CONFIG_FILE", (Join-Path $InstallRoot "clang64\etc\GNUstep\GNUstep.conf"), $target)
    Write-TraceEvent "path.update.complete" "$target $InstallRoot"
    return $true
}

function Show-Help {
    @"
GNUstep CLI bootstrap interface

Usage:
  gnustep-bootstrap.ps1 [global-options] <command> [command-options]

Commands:
  setup      Install the full GNUstep CLI and its dependencies.
  doctor     Inspect this machine and report GNUstep/toolchain readiness.
  build      Unavailable in bootstrap. Install the full interface first.
  clean      Unavailable in bootstrap. Install the full interface first.
  run        Unavailable in bootstrap. Install the full interface first.
  shell      Unavailable in bootstrap. Install the full interface first.
  new        Unavailable in bootstrap. Install the full interface first.
  install    Unavailable in bootstrap. Install the full interface first.
  remove     Unavailable in bootstrap. Install the full interface first.
  update     Unavailable in bootstrap. Install the full interface first.

Global options:
  --help
  --version
  --json
  --verbose
  --quiet
  --yes
"@
}

function Write-JsonObject {
    param([hashtable]$Object)
    $Object | ConvertTo-Json -Depth 8 -Compress
}

function Invoke-UnsupportedCommand {
    param([string]$CommandName)
    if ($Script:JsonMode) {
        Write-JsonObject @{
            schema_version = 1
            command = $CommandName
            ok = $false
            status = "error"
            summary = "This command is unavailable in bootstrap."
            actions = @(
                @{
                    kind = "install_full_cli"
                    priority = 1
                    message = "Install the full GNUstep CLI to use '$CommandName'."
                }
            )
        }
    }
    else {
        Write-Output "$CommandName`: unavailable in bootstrap"
        Write-Output "Install the full GNUstep CLI to use '$CommandName'."
    }
    exit 3
}

if (-not $ArgsList) {
    Show-Help
    exit 2
}

$remaining = New-Object System.Collections.Generic.List[string]
foreach ($arg in $ArgsList) {
    switch ($arg) {
        "--help" {
            Show-Help
            exit 0
        }
        "--version" {
            Write-Output $Script:CliVersion
            exit 0
        }
        "--json" {
            $Script:JsonMode = $true
        }
        "--verbose" { }
        "--quiet" { $Script:QuietMode = $true }
        "--yes" { }
        "--trace" { }
        "--system" { $Script:SetupScope = "system" }
        "--user" { $Script:SetupScope = "user" }
        "--manifest" { }
        default {
            if ($arg.StartsWith("--")) {
                if ($arg -eq "--root" -or $arg -eq "--manifest" -or $arg -eq "--trace") {
                    continue
                }
                Write-Error "Unknown option: $arg"
                exit 2
            }
            $remaining.Add($arg)
        }
    }
}

for ($i = 0; $i -lt $ArgsList.Count; $i++) {
    if ($ArgsList[$i] -eq "--root") {
        if ($i + 1 -ge $ArgsList.Count) {
            Write-Error "--root requires a value"
            exit 2
        }
        $Script:SetupRoot = $ArgsList[$i + 1]
    }
    if ($ArgsList[$i] -eq "--trace") {
        if ($i + 1 -ge $ArgsList.Count) {
            Write-Error "--trace requires a value"
            exit 2
        }
        $Script:TracePath = $ArgsList[$i + 1]
    }
    if ($ArgsList[$i] -eq "--manifest") {
        if ($i + 1 -ge $ArgsList.Count) {
            Write-Error "--manifest requires a value"
            exit 2
        }
        $Script:SetupManifest = $ArgsList[$i + 1]
    }
}

if ($remaining.Count -eq 0) {
    Show-Help
    exit 2
}

$command = $remaining[0]
$commandArgs = @()
if ($remaining.Count -gt 1) {
    $commandArgs = $remaining.GetRange(1, $remaining.Count - 1)
}

foreach ($arg in $commandArgs) {
    switch ($arg) {
        "--system" { $Script:SetupScope = "system" }
        "--user" { $Script:SetupScope = "user" }
        default { }
    }
}

for ($i = 0; $i -lt $commandArgs.Count; $i++) {
    if ($commandArgs[$i] -eq "--root") {
        if ($i + 1 -ge $commandArgs.Count) {
            Write-Error "--root requires a value"
            exit 2
        }
        $Script:SetupRoot = $commandArgs[$i + 1]
    }
    if ($commandArgs[$i] -eq "--trace") {
        if ($i + 1 -ge $commandArgs.Count) {
            Write-Error "--trace requires a value"
            exit 2
        }
        $Script:TracePath = $commandArgs[$i + 1]
    }
    if ($commandArgs[$i] -eq "--manifest") {
        if ($i + 1 -ge $commandArgs.Count) {
            Write-Error "--manifest requires a value"
            exit 2
        }
        $Script:SetupManifest = $commandArgs[$i + 1]
    }
}

switch ($command) {
    "doctor" {
        if ($Script:JsonMode) {
            Write-JsonObject @{
                schema_version = 1
                command = "doctor"
                cli_version = $Script:CliVersion
                ok = $true
                status = "warning"
                environment_classification = "no_toolchain"
                summary = "No preexisting GNUstep toolchain was detected."
                environment = @{
                    os = "windows"
                    arch = "unknown"
                    bootstrap_prerequisites = @{
                        powershell = $true
                    }
                }
                compatibility = @{
                    compatible = $true
                    target_kind = $null
                    target_id = $null
                    reasons = @()
                    warnings = @(
                        @{
                            code = "toolchain_not_present"
                            message = "No preexisting GNUstep toolchain was detected; a managed install will be required."
                        }
                    )
                }
                checks = @(
                    @{
                        id = "bootstrap.powershell"
                        title = "Check for PowerShell bootstrap runtime"
                        status = "ok"
                        severity = "error"
                        message = "PowerShell bootstrap runtime is available."
                    }
                )
                actions = @(@{ kind = "install_managed_toolchain"; priority = 1; message = "Install the supported managed GNUstep toolchain." })
            }
        }
        else {
            Write-Output "doctor: PowerShell bootstrap runtime is available"
            Write-Output "doctor: no preexisting GNUstep toolchain was detected"
            Write-Output "next: Install the supported managed GNUstep toolchain."
        }
        exit 0
    }
    "setup" {
        $selectedRoot = $Script:SetupRoot
        if (-not $selectedRoot) {
            if ($Script:SetupScope -eq "system") {
                $selectedRoot = "%ProgramFiles%\gnustep-cli"
            }
            else {
                $selectedRoot = "%LOCALAPPDATA%\gnustep-cli"
            }
        }
        if ($selectedRoot -like "%LOCALAPPDATA%*") {
            $selectedRoot = $selectedRoot -replace "%LOCALAPPDATA%", $env:LOCALAPPDATA
        }
        if ($selectedRoot -like "%ProgramFiles%*") {
            $selectedRoot = $selectedRoot -replace "%ProgramFiles%", $env:ProgramFiles
        }
        $isAdmin = $false
        try {
            $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
            $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
            $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
        } catch {
            $isAdmin = $false
        }
        if ($Script:SetupScope -eq "system" -and -not $isAdmin) {
            if ($Script:JsonMode) {
                Write-JsonObject @{
                    schema_version = 1
                    command = "setup"
                    cli_version = $Script:CliVersion
                    ok = $false
                    status = "error"
                    summary = "System-wide installation requires elevated privileges."
                    doctor = @{
                        status = "warning"
                        environment_classification = "no_toolchain"
                        summary = "No preexisting GNUstep toolchain was detected."
                    }
                    plan = @{
                        scope = $Script:SetupScope
                        install_root = $selectedRoot
                        channel = "stable"
                        selected_release = $null
                        selected_artifacts = @()
                        system_privileges_ok = $false
                    }
                    actions = @(
                        @{
                            kind = "rerun_with_elevated_privileges"
                            priority = 1
                            message = "Re-run PowerShell as Administrator and try again."
                        }
                    )
                }
            }
            else {
                Write-Output "setup: system-wide installation requires elevated privileges"
                Write-Output "next: Re-run PowerShell as Administrator and try again."
            }
            exit 3
        }
        try {
            Write-SetupProgress "starting managed installation into $selectedRoot"
            Write-TraceEvent "setup.start" $selectedRoot
            if (-not $Script:SetupManifest) {
                $Script:SetupManifest = "https://github.com/danjboyd/gnustep-cli-new/releases/download/v$($Script:CliVersion)/release-manifest.json"
            }
            Write-SetupProgress "loading release manifest from $Script:SetupManifest"
            Write-TraceEvent "setup.manifest.resolve" $Script:SetupManifest
            $manifest = Get-ManifestObject -ManifestSource $Script:SetupManifest
            Write-TraceEvent "setup.target" "windows"
            $target = Get-HostTarget
            $release = $manifest.json.releases[0]
            $cliArtifact = $release.artifacts | Where-Object { $_.id -eq $target.cliId } | Select-Object -First 1
            $toolchainArtifact = $release.artifacts | Where-Object { $_.id -eq $target.toolchainId } | Select-Object -First 1
            if (-not $cliArtifact -or -not $toolchainArtifact) {
                throw "No matching release artifacts were found for this host."
            }
            Write-SetupProgress "selected release $($release.version) artifacts: $($cliArtifact.id), $($toolchainArtifact.id)"
            $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("gsb-" + [guid]::NewGuid().ToString("N"))
            New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
            try {
                $cliFile = Join-Path $tempRoot ([System.IO.Path]::GetFileName($cliArtifact.url))
                $toolchainFile = Join-Path $tempRoot ([System.IO.Path]::GetFileName($toolchainArtifact.url))
                $localCli = Join-Path $manifest.dir ([System.IO.Path]::GetFileName($cliArtifact.url))
                $localToolchain = Join-Path $manifest.dir ([System.IO.Path]::GetFileName($toolchainArtifact.url))
                Write-SetupProgress "fetching CLI artifact $([System.IO.Path]::GetFileName($cliArtifact.url))"
                Write-TraceEvent "artifact.cli.fetch.start" $cliArtifact.url
                if (Test-Path $localCli) { Copy-Item -Force $localCli $cliFile } else { Save-UrlToFile -Url $cliArtifact.url -OutFile $cliFile -Label $([System.IO.Path]::GetFileName($cliArtifact.url)) }
                Write-TraceEvent "artifact.cli.fetch.complete" $cliFile
                Write-SetupProgress "fetching toolchain artifact $([System.IO.Path]::GetFileName($toolchainArtifact.url))"
                Write-TraceEvent "artifact.toolchain.fetch.start" $toolchainArtifact.url
                if (Test-Path $localToolchain) { Copy-Item -Force $localToolchain $toolchainFile } else { Save-UrlToFile -Url $toolchainArtifact.url -OutFile $toolchainFile -Label $([System.IO.Path]::GetFileName($toolchainArtifact.url)) }
                Write-TraceEvent "artifact.toolchain.fetch.complete" $toolchainFile
                Write-SetupProgress "verifying artifact checksums"
                Write-TraceEvent "artifact.checksum.start" $cliFile
                $expectedCliSha = ([string]$cliArtifact.sha256).ToLowerInvariant()
                if ((Get-Sha256 $cliFile) -ne $expectedCliSha) { throw "CLI checksum verification failed." }
                Write-TraceEvent "artifact.checksum.cli.complete" $cliFile
                $expectedToolchainSha = ([string]$toolchainArtifact.sha256).ToLowerInvariant()
                if ((Get-Sha256 $toolchainFile) -ne $expectedToolchainSha) { throw "Toolchain checksum verification failed." }
                Write-TraceEvent "artifact.checksum.complete" $toolchainFile
                $cliExtract = Join-Path $tempRoot "c"
                $toolchainExtract = Join-Path $tempRoot "t"
                Write-SetupProgress "extracting CLI artifact"
                Expand-Artifact -ArchivePath $cliFile -Destination $cliExtract
                Write-SetupProgress "extracting toolchain artifact; this can take several minutes"
                Expand-Artifact -ArchivePath $toolchainFile -Destination $toolchainExtract
                $cliRoot = Get-SingleChildDirectory -Path $cliExtract
                $toolchainRoot = Get-SingleChildDirectory -Path $toolchainExtract
                New-Item -ItemType Directory -Force -Path (Join-Path $selectedRoot "bin") | Out-Null
                Write-SetupProgress "installing CLI files"
                Write-TraceEvent "install.cli.start" $cliRoot
                Install-CliBundle -Source $cliRoot -Destination $selectedRoot
                Write-TraceEvent "install.cli.complete" $selectedRoot
                Write-SetupProgress "installing GNUstep toolchain files"
                Write-TraceEvent "install.toolchain.start" $toolchainRoot
                Copy-TreeContents -Source $toolchainRoot -Destination $selectedRoot
                Write-TraceEvent "install.toolchain.complete" $selectedRoot
                New-Item -ItemType Directory -Force -Path (Join-Path $selectedRoot "state") | Out-Null
                Write-SetupProgress "recording managed install state"
                @{
                    schema_version = 1
                    cli_version = $release.version
                    toolchain_version = $release.version
                    packages_version = 1
                    last_action = "setup"
                    status = "healthy"
                } | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 (Join-Path $selectedRoot "state\\cli-state.json")
                Write-TraceEvent "install.state.complete" (Join-Path $selectedRoot "state\\cli-state.json")
                Ensure-GNUstepActivationScripts -InstallRoot $selectedRoot
                $pathPersisted = Set-GNUstepUserEnvironment -InstallRoot $selectedRoot -Scope $Script:SetupScope
                $pathHint = Get-PathSetupCommand -InstallRoot $selectedRoot
                if ($Script:JsonMode) {
                    Write-TraceEvent "setup.success" $selectedRoot
                    Write-JsonObject @{
                        schema_version = 1
                        command = "setup"
                        cli_version = $Script:CliVersion
                        ok = $true
                        status = "ok"
                        summary = "Managed installation completed."
                        doctor = @{
                            status = "warning"
                            environment_classification = "no_toolchain"
                            summary = "No preexisting GNUstep toolchain was detected."
                            os = "windows"
                        }
                        plan = @{
                            scope = $Script:SetupScope
                            install_root = $selectedRoot
                            channel = "stable"
                            manifest_path = $Script:SetupManifest
                            selected_release = $release.version
                            selected_artifacts = @($cliArtifact.id, $toolchainArtifact.id)
                            system_privileges_ok = $true
                        }
                        actions = @(
                            @{ kind = "add_path"; priority = 1; message = "Add $selectedRoot\bin to PATH for future shells. The CLI uses its private MSYS2 runtime internally." },
                            @{ kind = "delete_bootstrap"; priority = 2; message = "The bootstrap script is no longer required and may be deleted." }
                        )
                        install = @{
                            install_root = $selectedRoot
                            path_hint = $pathHint
                            path_persisted = $pathPersisted
                        }
                    }
                }
                else {
                    Write-Output "setup: managed installation completed"
                    Write-Output "setup: scope=$($Script:SetupScope) root=$selectedRoot"
                    if ($pathPersisted) {
                        Write-Output "setup: updated $($Script:SetupScope) PATH for future PowerShell sessions"
                    }
                    else {
                        Write-Output "setup: PATH update skipped for future PowerShell sessions"
                    }
                    Write-Output "next: Run this in the current shell:"
                    Write-Output "  $pathHint"
                    Write-Output "next: The bootstrap script is no longer required and may be deleted."
                }
            }
            finally {
                Remove-TempTree -Path $tempRoot
            }
            exit 0
        }
        catch {
            if ($Script:JsonMode) {
                Write-JsonObject @{
                    schema_version = 1
                    command = "setup"
                    cli_version = $Script:CliVersion
                    ok = $false
                    status = "error"
                    summary = $_.Exception.Message
                    doctor = @{
                        status = "warning"
                        environment_classification = "no_toolchain"
                        summary = "No preexisting GNUstep toolchain was detected."
                        os = "windows"
                    }
                    plan = @{
                        scope = $Script:SetupScope
                        install_root = $selectedRoot
                        channel = "stable"
                        selected_release = $null
                        selected_artifacts = @()
                        system_privileges_ok = $true
                    }
                    trace_path = $Script:TracePath
                    actions = @(
                        @{
                            kind = "report_bug"
                            priority = 1
                            message = "Check the manifest and artifact availability, then rerun setup."
                        }
                    )
                }
            }
            else {
                Write-TraceEvent "setup.error" $_.Exception.Message
                Write-Output "setup: $($_.Exception.Message)"
                Write-Output "next: Check the manifest and artifact availability, then rerun setup."
            }
            exit 1
        }
    }
    "build" { Invoke-UnsupportedCommand "build" }
    "clean" { Invoke-UnsupportedCommand "clean" }
    "run" { Invoke-UnsupportedCommand "run" }
    "shell" { Invoke-UnsupportedCommand "shell" }
    "new" { Invoke-UnsupportedCommand "new" }
    "install" { Invoke-UnsupportedCommand "install" }
    "remove" { Invoke-UnsupportedCommand "remove" }
    "update" { Invoke-UnsupportedCommand "update" }
    default {
        Write-Error "Unknown command: $command"
        exit 2
    }
}
