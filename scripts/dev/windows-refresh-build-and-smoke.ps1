[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$leaseRoot = 'C:\Users\otvmbootstrap\refresh-run'
$toolchainRoot = 'C:\managed-probe'
$cacheRoot = 'C:\managed-cache'
$srcTar = 'C:\Users\otvmbootstrap\full-cli-src.tar.gz'
$srcRoot = Join-Path $leaseRoot 'src'
$resultsPath = Join-Path $leaseRoot 'results.json'
$indexPath = Join-Path $leaseRoot 'package-index.json'
$payloadDir = Join-Path $leaseRoot 'payload'
$archivePath = Join-Path $leaseRoot 'demo-windows-package.zip'
$managedRoot = Join-Path $leaseRoot 'managed'
$exe = 'C:\Users\otvmbootstrap\refresh-run\src\full-cli\obj\gnustep.exe'
$installTracePath = Join-Path $leaseRoot 'install-trace.txt'

$result = [ordered]@{
  stage = 'starting'
  error = ''
  build_exit = $null
  exe_exists = $false
  version_stdout = ''
  help_stdout = ''
  version_exit = $null
  version_stderr = ''
  help_exit = $null
  help_stderr = ''
  install_exit = $null
  install_stdout = ''
  install_stderr = ''
  install_trace = ''
  remove_exit = $null
  remove_stdout = ''
  remove_stderr = ''
  state_path = Join-Path $managedRoot 'state\installed-packages.json'
  state_text = ''
}

function Invoke-Captured {
  param(
    [scriptblock]$Script
  )

  try {
    $text = (& $Script 2>&1 | Out-String)
    return @{
      output = $text
      exit_code = $LASTEXITCODE
      error = ''
    }
  } catch {
    return @{
      output = ''
      exit_code = -1
      error = ($_ | Out-String)
    }
  }
}

function Save-Results {
  $result | ConvertTo-Json -Depth 8 | Set-Content -Path $resultsPath -Encoding UTF8
}

function Set-Stage {
  param([string]$Name)
  $result.stage = $Name
  Write-Host "[gnustep-cli-smoke] $Name"
  Save-Results
}

function Invoke-ExternalCaptured {
  param(
    [string]$FilePath,
    [string[]]$Arguments,
    [int]$TimeoutSeconds = 120
  )

  $stdoutPath = [System.IO.Path]::GetTempFileName()
  $stderrPath = [System.IO.Path]::GetTempFileName()
  try {
    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -NoNewWindow -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
      Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
      return @{
        output = (Get-Content -Path $stdoutPath -Raw -ErrorAction SilentlyContinue)
        stderr = (Get-Content -Path $stderrPath -Raw -ErrorAction SilentlyContinue)
        exit_code = -999
        error = "process timed out after $TimeoutSeconds seconds"
      }
    }
    return @{
      output = (Get-Content -Path $stdoutPath -Raw -ErrorAction SilentlyContinue)
      stderr = (Get-Content -Path $stderrPath -Raw -ErrorAction SilentlyContinue)
      exit_code = $process.ExitCode
      error = ''
    }
  } catch {
    return @{
      output = (Get-Content -Path $stdoutPath -Raw -ErrorAction SilentlyContinue)
      stderr = (Get-Content -Path $stderrPath -Raw -ErrorAction SilentlyContinue)
      exit_code = -1
      error = ($_ | Out-String)
    }
  } finally {
    Remove-Item -Force $stdoutPath, $stderrPath -ErrorAction SilentlyContinue
  }
}

try {
  Remove-Item -Recurse -Force $leaseRoot, $toolchainRoot, $cacheRoot -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force -Path $leaseRoot, $srcRoot, (Join-Path $payloadDir 'bin') | Out-Null

  Set-Stage 'assemble_toolchain'
  & powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\otvmbootstrap\assemble-toolchain.ps1 -Prefix $toolchainRoot -CacheDir $cacheRoot
  if ($LASTEXITCODE -ne 0) {
    throw "toolchain assembly failed: $LASTEXITCODE"
  }

  Set-Stage 'build_cli'
  & C:\msys64\usr\bin\bash.exe -lc "mkdir -p /c/Users/otvmbootstrap/refresh-run/src && tar -xzf /c/Users/otvmbootstrap/full-cli-src.tar.gz -C /c/Users/otvmbootstrap/refresh-run/src && cd /c/Users/otvmbootstrap/refresh-run/src/full-cli && export PATH=/c/managed-probe/bin:/c/managed-probe/usr/bin:`$PATH && export GNUSTEP_MAKEFILES=/c/managed-probe/share/GNUstep/Makefiles && make"
  $result.build_exit = $LASTEXITCODE
  $result.exe_exists = (Test-Path $exe)

  if (Test-Path $exe) {
    $env:PATH = 'C:\managed-probe\bin;C:\managed-probe\usr\bin;' + $env:PATH
    $env:GNUSTEP_MAKEFILES = '/c/managed-probe/share/GNUstep/Makefiles'

    Set-Stage 'cli_smoke_version'
    $version = Invoke-Captured { & $exe --version }
    $result.version_stdout = $version.output
    $result.version_stderr = $version.error
    $result.version_exit = $version.exit_code
    Save-Results

    Set-Stage 'cli_smoke_help'
    $help = Invoke-Captured { & $exe --help }
    $result.help_stdout = $help.output
    $result.help_stderr = $help.error
    $result.help_exit = $help.exit_code
    Save-Results
  }

  Set-Stage 'prepare_package_fixture'
  Set-Content -Path (Join-Path $payloadDir 'bin\demo-tool.cmd') -Value '@echo off' -Encoding ASCII
  Compress-Archive -Path (Join-Path $payloadDir '*') -DestinationPath $archivePath -Force
  $sha = (Get-FileHash -Algorithm SHA256 -Path $archivePath).Hash.ToLowerInvariant()
  $artifactUrl = 'file:///' + ($archivePath -replace '\\','/')
  $index = @{
    schema_version = 1
    channel = 'stable'
    packages = @(
      @{
        id = 'org.gnustep.demo-windows-smoke'
        name = 'demo-windows-smoke'
        version = '0.1.0'
        kind = 'cli-tool'
        summary = 'Temporary Windows package smoke fixture.'
        requirements = @{
          supported_os = @('windows')
          supported_arch = @('amd64')
          supported_compiler_families = @('clang')
          supported_objc_runtimes = @('libobjc2')
          supported_objc_abi = @('modern')
          required_features = @('blocks')
          forbidden_features = @()
        }
        dependencies = @()
        artifacts = @(
          @{
            id = 'demo-windows-clang'
            os = 'windows'
            arch = 'amd64'
            compiler_family = 'clang'
            toolchain_flavor = 'msys2-clang64'
            objc_runtime = 'libobjc2'
            objc_abi = 'modern'
            required_features = @('blocks')
            url = $artifactUrl
            sha256 = $sha
          }
        )
      }
    )
  }
  $index | ConvertTo-Json -Depth 8 | Set-Content -Path $indexPath -Encoding UTF8

  if (Test-Path $exe) {
    Set-Stage 'install_package'
    $env:GNUSTEP_CLI_INSTALL_TRACE = $installTracePath
    $install = Invoke-Captured { & $exe install --root $managedRoot --index $indexPath org.gnustep.demo-windows-smoke }
    Remove-Item Env:GNUSTEP_CLI_INSTALL_TRACE -ErrorAction SilentlyContinue
    $result.install_stdout = $install.output
    $result.install_stderr = $install.error
    $result.install_exit = $install.exit_code
    if (Test-Path $installTracePath) {
      $result.install_trace = [System.IO.File]::ReadAllText($installTracePath)
    }
    Save-Results

    if ($result.install_exit -eq 0) {
      Set-Stage 'remove_package'
      $env:GNUSTEP_CLI_INSTALL_TRACE = $installTracePath
      $env:GNUSTEP_CLI_INSTALL_TRACE_STDERR = '1'
      & $exe remove --root $managedRoot org.gnustep.demo-windows-smoke
      $result.remove_exit = $LASTEXITCODE
      Remove-Item Env:GNUSTEP_CLI_INSTALL_TRACE -ErrorAction SilentlyContinue
      Remove-Item Env:GNUSTEP_CLI_INSTALL_TRACE_STDERR -ErrorAction SilentlyContinue
      Save-Results
    } else {
      Set-Stage 'skip_remove_after_install_failure'
      $result.remove_exit = $null
      $result.remove_stderr = 'remove skipped because install did not succeed'
      Save-Results
    }
  }
} catch {
  $result.error = ($_ | Out-String)
} finally {
  Write-Host "[gnustep-cli-smoke] finalizing"
  if (Test-Path $result.state_path) {
    $result.state_text = [System.IO.File]::ReadAllText($result.state_path)
  }
  Save-Results
  Write-Host "[gnustep-cli-smoke] complete"
}
