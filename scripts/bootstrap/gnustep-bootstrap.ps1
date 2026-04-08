param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$Script:CliVersion = "0.1.0-dev"
$Script:JsonMode = $false
$Script:RootDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
$Script:SetupScope = "user"
$Script:SetupRoot = $null

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
        default {
            if ($arg.StartsWith("--")) {
                if ($arg -eq "--root") {
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
}

if ($remaining.Count -eq 0) {
    Show-Help
    exit 2
}

$command = $remaining[0]
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
        if ($Script:JsonMode) {
            Write-JsonObject @{
                schema_version = 1
                command = "setup"
                cli_version = $Script:CliVersion
                ok = $true
                status = "ok"
                summary = "Managed installation plan created."
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
                    system_privileges_ok = $true
                }
                actions = @(
                    @{
                        kind = "apply_install_plan"
                        priority = 1
                        message = "Proceed with artifact download and managed installation once implementation is complete."
                    }
                )
            }
        }
        else {
            Write-Output "setup: managed installation plan created"
            Write-Output "setup: scope=$($Script:SetupScope) root=$selectedRoot"
            Write-Output "next: Artifact download and managed installation are not implemented yet."
        }
        exit 0
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
