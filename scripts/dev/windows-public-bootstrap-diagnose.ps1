param(
  [string]$BootstrapPath = "C:\Windows\Temp\gnustep-bootstrap.ps1",
  [string]$InstallRoot = "C:\gnustep-public-diagnose\install",
  [string]$WorkRoot = "C:\gnustep-public-diagnose",
  [string]$TaskName = "GNUstepPublicBootstrapDiagnose",
  [int]$TimeoutSeconds = 900,
  [switch]$DirectProcess
)

$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $WorkRoot | Out-Null
$trace = Join-Path $WorkRoot 'setup-trace.jsonl'
$stdout = Join-Path $WorkRoot 'setup.stdout.log'
$stderr = Join-Path $WorkRoot 'setup.stderr.log'
$runner = Join-Path $WorkRoot 'run-bootstrap-diagnose.ps1'
$status = Join-Path $WorkRoot 'status.json'

@"
`$ErrorActionPreference = 'Continue'
`$env:GNUSTEP_BOOTSTRAP_TRACE = '$trace'
`$env:GNUSTEP_BOOTSTRAP_KEEP_TEMP = '1'
`$started = [DateTimeOffset]::UtcNow.ToString('o')
try {
  & '$BootstrapPath' setup --json --yes --root '$InstallRoot' --trace '$trace' > '$stdout' 2> '$stderr'
  `$exitCode = `$LASTEXITCODE
  `$ok = (`$exitCode -eq 0)
} catch {
  `$exitCode = 250
  `$ok = `$false
  `$_.Exception.Message | Out-File -Encoding UTF8 -Append '$stderr'
}
@{
  schema_version = 1
  command = 'windows-public-bootstrap-diagnose'
  ok = `$ok
  exit_code = `$exitCode
  started_at = `$started
  finished_at = [DateTimeOffset]::UtcNow.ToString('o')
  trace_path = '$trace'
  stdout_path = '$stdout'
  stderr_path = '$stderr'
  install_root = '$InstallRoot'
} | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 '$status'
exit `$exitCode
"@ | Set-Content -Encoding UTF8 $runner

if ($DirectProcess) {
  $process = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $runner) -PassThru -WindowStyle Hidden
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline -and -not (Test-Path $status) -and -not $process.HasExited) {
    Start-Sleep -Seconds 5
  }
  if (Test-Path $status) {
    Get-Content -Raw $status
  } else {
    if (-not $process.HasExited) {
      Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
    @{
      schema_version = 1
      command = 'windows-public-bootstrap-diagnose'
      ok = $false
      status = 'timeout_or_hung'
      execution_mode = 'direct-process'
      process_id = $process.Id
      process_exit_code = if ($process.HasExited) { $process.ExitCode } else { $null }
      trace_path = $trace
      stdout_path = $stdout
      stderr_path = $stderr
      install_root = $InstallRoot
    } | ConvertTo-Json -Depth 5
  }
  exit 0
}

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`""
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Seconds $TimeoutSeconds)
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
Register-ScheduledTask -TaskName $TaskName -Action $action -Principal $principal -Settings $settings | Out-Null
Start-ScheduledTask -TaskName $TaskName

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
  Start-Sleep -Seconds 5
  $task = Get-ScheduledTask -TaskName $TaskName
  $info = Get-ScheduledTaskInfo -TaskName $TaskName
  if (Test-Path $status) { break }
} while ((Get-Date) -lt $deadline -and $task.State -ne 'Ready')

if (Test-Path $status) {
  Get-Content -Raw $status
} else {
  @{
    schema_version = 1
    command = 'windows-public-bootstrap-diagnose'
    ok = $false
    status = 'timeout_or_hung'
    task_state = (Get-ScheduledTask -TaskName $TaskName).State.ToString()
    last_task_result = (Get-ScheduledTaskInfo -TaskName $TaskName).LastTaskResult
    trace_path = $trace
    stdout_path = $stdout
    stderr_path = $stderr
    install_root = $InstallRoot
  } | ConvertTo-Json -Depth 5
}
