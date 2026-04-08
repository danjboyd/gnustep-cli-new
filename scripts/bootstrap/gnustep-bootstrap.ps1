param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$Script:CliVersion = "0.1.0-dev"
$Script:JsonMode = $false
$Script:RootDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
$Script:SetupScope = "user"
$Script:SetupRoot = $null
$Script:SetupManifest = $env:SETUP_MANIFEST

function Get-ManifestObject {
    param([string]$ManifestSource)
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
        Invoke-WebRequest -UseBasicParsing -Uri $ManifestSource -OutFile $manifestPath
    }
    else {
        $manifestPath = (Resolve-Path $ManifestSource).Path
    }
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
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    if ($ArchivePath.ToLowerInvariant().EndsWith(".zip")) {
        Expand-Archive -Path $ArchivePath -DestinationPath $Destination -Force
    }
    else {
        tar -xzf $ArchivePath -C $Destination
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to extract $ArchivePath"
        }
    }
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
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Copy-Item -Recurse -Force (Join-Path $Source '*') $Destination
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
  run        Unavailable in bootstrap. Install the full interface first.
  new        Unavailable in bootstrap. Install the full interface first.
  install    Unavailable in bootstrap. Install the full interface first.
  remove     Unavailable in bootstrap. Install the full interface first.

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
        "--quiet" { }
        "--yes" { }
        "--system" { $Script:SetupScope = "system" }
        "--user" { $Script:SetupScope = "user" }
        "--manifest" { }
        default {
            if ($arg.StartsWith("--")) {
                if ($arg -eq "--root" -or $arg -eq "--manifest") {
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
            $manifest = Get-ManifestObject -ManifestSource $Script:SetupManifest
            $target = Get-HostTarget
            $release = $manifest.json.releases[0]
            $cliArtifact = $release.artifacts | Where-Object { $_.id -eq $target.cliId } | Select-Object -First 1
            $toolchainArtifact = $release.artifacts | Where-Object { $_.id -eq $target.toolchainId } | Select-Object -First 1
            if (-not $cliArtifact -or -not $toolchainArtifact) {
                throw "No matching release artifacts were found for this host."
            }
            $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("gnustep-bootstrap-" + [guid]::NewGuid().ToString())
            New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
            try {
                $cliFile = Join-Path $tempRoot ([System.IO.Path]::GetFileName($cliArtifact.url))
                $toolchainFile = Join-Path $tempRoot ([System.IO.Path]::GetFileName($toolchainArtifact.url))
                $localCli = Join-Path $manifest.dir ([System.IO.Path]::GetFileName($cliArtifact.url))
                $localToolchain = Join-Path $manifest.dir ([System.IO.Path]::GetFileName($toolchainArtifact.url))
                if (Test-Path $localCli) { Copy-Item -Force $localCli $cliFile } else { Invoke-WebRequest -UseBasicParsing -Uri $cliArtifact.url -OutFile $cliFile }
                if (Test-Path $localToolchain) { Copy-Item -Force $localToolchain $toolchainFile } else { Invoke-WebRequest -UseBasicParsing -Uri $toolchainArtifact.url -OutFile $toolchainFile }
                if ((Get-Sha256 $cliFile) -ne $cliArtifact.sha256.ToLowerInvariant()) { throw "CLI checksum verification failed." }
                if ((Get-Sha256 $toolchainFile) -ne $toolchainArtifact.sha256.ToLowerInvariant()) { throw "Toolchain checksum verification failed." }
                $cliExtract = Join-Path $tempRoot "cli"
                $toolchainExtract = Join-Path $tempRoot "toolchain"
                Expand-Artifact -ArchivePath $cliFile -Destination $cliExtract
                Expand-Artifact -ArchivePath $toolchainFile -Destination $toolchainExtract
                $cliRoot = Get-SingleChildDirectory -Path $cliExtract
                $toolchainRoot = Get-SingleChildDirectory -Path $toolchainExtract
                New-Item -ItemType Directory -Force -Path (Join-Path $selectedRoot "bin") | Out-Null
                $cliBinary = Get-ChildItem -Recurse -File $cliRoot | Where-Object { $_.Name -eq "gnustep" -or $_.Name -eq "gnustep.exe" } | Select-Object -First 1
                if (-not $cliBinary) { throw "CLI binary not found in archive." }
                Copy-Item -Force $cliBinary.FullName (Join-Path $selectedRoot "bin" $cliBinary.Name)
                Copy-TreeContents -Source $toolchainRoot -Destination $selectedRoot
                New-Item -ItemType Directory -Force -Path (Join-Path $selectedRoot "state") | Out-Null
                @{
                    schema_version = 1
                    cli_version = $release.version
                    toolchain_version = $release.version
                    packages_version = 1
                    last_action = "setup"
                    status = "healthy"
                } | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 (Join-Path $selectedRoot "state\\cli-state.json")
                $pathHint = '$env:Path = "' + (Join-Path $selectedRoot 'bin') + ';' + (Join-Path $selectedRoot 'System\\Tools') + ';$env:Path"'
                if ($Script:JsonMode) {
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
                            selected_release = $release.version
                            selected_artifacts = @($cliArtifact.id, $toolchainArtifact.id)
                            system_privileges_ok = $true
                        }
                        actions = @(
                            @{ kind = "add_path"; priority = 1; message = "Add $selectedRoot\\bin and $selectedRoot\\System\\Tools to PATH for future shells." },
                            @{ kind = "delete_bootstrap"; priority = 2; message = "The bootstrap script is no longer required and may be deleted." }
                        )
                        install = @{
                            install_root = $selectedRoot
                            path_hint = $pathHint
                        }
                    }
                }
                else {
                    Write-Output "setup: managed installation completed"
                    Write-Output "setup: scope=$($Script:SetupScope) root=$selectedRoot"
                    Write-Output "next: Run this in the current shell:"
                    Write-Output "  $pathHint"
                    Write-Output "next: The bootstrap script is no longer required and may be deleted."
                }
            }
            finally {
                if (Test-Path $tempRoot) {
                    Remove-Item -Recurse -Force $tempRoot
                }
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
                Write-Output "setup: $($_.Exception.Message)"
                Write-Output "next: Check the manifest and artifact availability, then rerun setup."
            }
            exit 1
        }
    }
    "build" { Invoke-UnsupportedCommand "build" }
    "run" { Invoke-UnsupportedCommand "run" }
    "new" { Invoke-UnsupportedCommand "new" }
    "install" { Invoke-UnsupportedCommand "install" }
    "remove" { Invoke-UnsupportedCommand "remove" }
    default {
        Write-Error "Unknown command: $command"
        exit 2
    }
}
