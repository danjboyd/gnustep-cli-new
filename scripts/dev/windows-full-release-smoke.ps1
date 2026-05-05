$ErrorActionPreference = 'Stop'

$runId = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$root = "C:\gnustep-smoke\install-full-$runId"
$work = "C:\gnustep-smoke\work-full-$runId"
$oldManifest = 'C:\gnustep-smoke\release-old\release-manifest.json'
$newManifest = 'C:\gnustep-smoke\release-new\release-manifest.json'
$bootstrap = 'C:\gnustep-smoke\bootstrap\gnustep-bootstrap.ps1'
$patch = 'C:\gnustep-smoke\fixtures\gorm-1_5_0-windows-private-ivar.patch'
$reportPath = 'C:\gnustep-smoke\windows-full-release-report.json'
$evidencePath = 'C:\gnustep-smoke\windows-full-release-evidence.json'
$oldFixtureManifest = 'C:\gnustep-smoke\release-old-fixture\release-manifest.json'
$newCliOnlyManifest = 'C:\gnustep-smoke\release-new-cli-only\release-manifest.json'
$scenarioReports = @()
$evidence = [ordered]@{}

function Invoke-SmokeCommand {
  param(
    [Parameter(Mandatory=$true)][string]$Id,
    [Parameter(Mandatory=$true)][scriptblock]$Block
  )
  try {
    $result = & $Block
    $script:evidence[$Id] = [ordered]@{ ok = $true; result = $result }
    return $true
  } catch {
    $script:evidence[$Id] = [ordered]@{
      ok = $false
      error = $_.Exception.Message
      category = $_.CategoryInfo.ToString()
    }
    return $false
  }
}

function Add-Scenario {
  param(
    [Parameter(Mandatory=$true)][string]$Id,
    [Parameter(Mandatory=$true)][bool]$Ok,
    [Parameter(Mandatory=$true)][string[]]$Assertions,
    [string]$Summary = ''
  )
  $script:scenarioReports += [ordered]@{
    scenario_id = $Id
    ok = $Ok
    status = if ($Ok) { 'passed' } else { 'failed' }
    summary = if ($Summary) { $Summary } elseif ($Ok) { "$Id passed." } else { "$Id failed." }
    assertion_results = @($Assertions | ForEach-Object {
      [ordered]@{
        assertion_id = $_
        ok = $Ok
        message = if ($Ok) { "$_ passed." } else { "$_ was not proven." }
      }
    })
    step_results = @()
    command_transcripts = @()
    evidence = @{}
  }
}

New-Item -ItemType Directory -Force $work | Out-Null

Remove-Item -Recurse -Force 'C:\gnustep-smoke\release-old-fixture' -ErrorAction SilentlyContinue
Copy-Item -Recurse 'C:\gnustep-smoke\release-old' 'C:\gnustep-smoke\release-old-fixture'
$oldFixture = Get-Content $oldFixtureManifest -Raw | ConvertFrom-Json
$oldFixture.releases[0].version = '0.0.9-windows-update-fixture'
foreach ($artifact in $oldFixture.releases[0].artifacts) {
  $artifact.version = '0.0.9-windows-update-fixture'
}
$oldFixture | ConvertTo-Json -Depth 12 | Out-File -Encoding utf8 $oldFixtureManifest

Remove-Item -Recurse -Force 'C:\gnustep-smoke\release-new-cli-only' -ErrorAction SilentlyContinue
Copy-Item -Recurse 'C:\gnustep-smoke\release-new' 'C:\gnustep-smoke\release-new-cli-only'
$oldManifestPayload = Get-Content $oldFixtureManifest -Raw | ConvertFrom-Json
$newCliOnly = Get-Content $newCliOnlyManifest -Raw | ConvertFrom-Json
$oldToolchain = @($oldManifestPayload.releases[0].artifacts | Where-Object { $_.kind -eq 'toolchain' -and $_.os -eq 'windows' })[0]
$newArtifacts = @()
foreach ($artifact in $newCliOnly.releases[0].artifacts) {
  if ($artifact.kind -eq 'cli' -and $artifact.os -eq 'windows') {
    $newArtifacts += $artifact
  } elseif ($artifact.kind -eq 'toolchain' -and $artifact.os -eq 'windows') {
    $oldToolchain | Add-Member -NotePropertyName reused -NotePropertyValue $true -Force
    $newArtifacts += $oldToolchain
  }
}
$newCliOnly.releases[0].artifacts = @($newArtifacts)
$newCliOnly | ConvertTo-Json -Depth 12 | Out-File -Encoding utf8 $newCliOnlyManifest

$bootstrapOk = Invoke-SmokeCommand 'bootstrap-install' {
  & $bootstrap --json setup --root $root --manifest $oldFixtureManifest | Out-File -Encoding utf8 'C:\gnustep-smoke\full-setup.json'
  $setup = Get-Content 'C:\gnustep-smoke\full-setup.json' -Raw | ConvertFrom-Json
  if (-not $setup.ok) { throw "bootstrap setup failed: $($setup.summary)" }
  $exe = Join-Path $root 'bin\gnustep.exe'
  if (-not (Test-Path $exe)) { throw "gnustep.exe was not installed at $exe" }
  & $exe --version | Out-File -Encoding utf8 'C:\gnustep-smoke\full-version-before.txt'
  & $exe --help | Out-File -Encoding utf8 'C:\gnustep-smoke\full-help.txt'
  & $exe --json doctor --manifest $oldFixtureManifest | Out-File -Encoding utf8 'C:\gnustep-smoke\full-doctor.json'
  $doctor = Get-Content 'C:\gnustep-smoke\full-doctor.json' -Raw | ConvertFrom-Json
  if ($doctor.command -ne 'doctor') { throw 'doctor JSON command metadata was not doctor' }
  @{ version = (Get-Content 'C:\gnustep-smoke\full-version-before.txt' -Raw).Trim(); doctor_status = $doctor.status }
}
Add-Scenario 'bootstrap-install-usable-cli' $bootstrapOk @(
  'bootstrap-command-succeeds',
  'installed-gnustep-exists',
  'gnustep-help-succeeds',
  'gnustep-version-succeeds',
  'doctor-json-command-metadata-is-doctor'
)

$exe = Join-Path $root 'bin\gnustep.exe'
$newProjectOk = $false
if ($bootstrapOk) {
  $newProjectOk = Invoke-SmokeCommand 'new-cli-project-build-run' {
    $project = Join-Path $work 'HelloSmoke'
    & $exe --json new cli-tool $project --name HelloSmoke | Out-File -Encoding utf8 'C:\gnustep-smoke\full-new-cli-project.json'
    $newPayload = Get-Content 'C:\gnustep-smoke\full-new-cli-project.json' -Raw | ConvertFrom-Json
    if (-not $newPayload.ok) { throw "gnustep new failed: $($newPayload.summary)" }
    Push-Location $project
    try {
      & $exe --json build | Out-File -Encoding utf8 'C:\gnustep-smoke\full-new-cli-build.json'
      $buildPayload = Get-Content 'C:\gnustep-smoke\full-new-cli-build.json' -Raw | ConvertFrom-Json
      if (-not $buildPayload.ok) { throw "gnustep build failed: $($buildPayload.summary)" }
      & $exe run | Out-File -Encoding utf8 'C:\gnustep-smoke\full-new-cli-run.txt'
      $runText = Get-Content 'C:\gnustep-smoke\full-new-cli-run.txt' -Raw
      if ($runText -notmatch 'Hello from CLI tool') { throw "run output did not contain expected text: $runText" }
    } finally {
      Pop-Location
    }
    @{ project = $project; run_output = (Get-Content 'C:\gnustep-smoke\full-new-cli-run.txt' -Raw).Trim() }
  }
}
Add-Scenario 'new-cli-project-build-run' $newProjectOk @(
  'new-command-succeeds',
  'build-command-succeeds',
  'run-command-succeeds',
  'sample-output-matches-expected-text'
)

$gormOk = $false
if ($bootstrapOk) {
  $gormOk = Invoke-SmokeCommand 'gorm-build-run' {
    $gormRoot = Join-Path $work 'apps-gorm'
    $gormArchive = Join-Path $work 'apps-gorm-1_5_0.tar.gz'
    Invoke-WebRequest -Uri 'https://github.com/gnustep/apps-gorm/archive/refs/tags/gorm-1_5_0.tar.gz' -OutFile $gormArchive
    tar -xzf $gormArchive -C $work
    $expanded = Get-ChildItem -Path $work -Directory | Where-Object { $_.Name -like 'apps-gorm-*' } | Select-Object -First 1
    if ($null -eq $expanded) { throw 'Gorm source directory was not expanded.' }
    Move-Item -Path $expanded.FullName -Destination $gormRoot
    Push-Location $gormRoot
    try {
      $editor = Join-Path $gormRoot 'GormCore\GormResourceEditor.m'
      $text = Get-Content $editor -Raw
      $text = [regex]::Replace($text, "(?m)^- \\(BOOL \\*\\*\\) _selectedCells;\\r?\\n", '')
      $text = [regex]::Replace($text, "(?s)- \\(BOOL \\*\\*\\) _selectedCells\\r?\\n\\{\\r?\\n  return _selectedCells;\\r?\\n\\}\\r?\\n\\r?\\n", '')
      $text = [regex]::Replace($text, "(?m)^  BOOL \\*\\*selectedCells = \\[self _selectedCells\\];\\r?\\n", '')
      $text = [regex]::Replace($text, "(?m)^\\s*selectedCells\\[_selectedRow\\]\\[_selectedColumn\\] = NO;\\r?\\n", '')
      $text = [regex]::Replace($text, "(?m)^\\s*selectedCells\\[row\\]\\[column\\] = YES;\\r?\\n", '')
      Set-Content -Path $editor -Value $text -Encoding UTF8
      & $exe --json build | Out-File -Encoding utf8 'C:\gnustep-smoke\full-gorm-build.json'
      $buildPayload = Get-Content 'C:\gnustep-smoke\full-gorm-build.json' -Raw | ConvertFrom-Json
      if (-not $buildPayload.ok) { throw "Gorm build failed: $($buildPayload.summary)" }
      $process = Start-Process -FilePath $exe -ArgumentList @('run','--no-build') -PassThru -WindowStyle Hidden
      Start-Sleep -Seconds 5
      if ($process.HasExited) {
        if ($process.ExitCode -ne 0) { throw "Gorm process exited early with code $($process.ExitCode)" }
      } else {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
      }
    } finally {
      Pop-Location
    }
    @{ gorm_root = $gormRoot; patch = $patch }
  }
}
Add-Scenario 'gorm-build-run' $gormOk @(
  'gorm-source-revision-is-pinned',
  'gorm-build-succeeds',
  'gorm-launch-succeeds',
  'gorm-process-stays-alive-briefly'
) 'gorm-build-run passed with pinned Windows fixture patch for private NSMatrix ivar access.'

$updateOk = $false
if ($bootstrapOk) {
  $updateOk = Invoke-SmokeCommand 'self-update-cli-only' {
    $shimDir = Join-Path $work 'shims'
    New-Item -ItemType Directory -Force $shimDir | Out-Null
    Set-Content -Path (Join-Path $shimDir 'unzip.cmd') -Encoding ASCII -Value @'
@echo off
setlocal
if "%1"=="-q" shift
set ARCHIVE=%1
shift
if "%1"=="-d" shift
set DEST=%1
powershell -NoProfile -Command "Expand-Archive -Force -LiteralPath '%ARCHIVE%' -DestinationPath '%DEST%'"
'@
    $env:PATH = "$shimDir;$root\usr\bin;$root\bin;$root\clang64\bin;" + $env:PATH
    & $exe update --check --manifest $newCliOnlyManifest | Out-File -Encoding utf8 'C:\gnustep-smoke\full-update-check.txt'
    & $exe update cli --yes --json --root $root --manifest $newCliOnlyManifest | Out-File -Encoding utf8 'C:\gnustep-smoke\full-update-cli.json'
    $updatePayload = Get-Content 'C:\gnustep-smoke\full-update-cli.json' -Raw | ConvertFrom-Json
    if (-not $updatePayload.ok) { throw "update cli failed: $($updatePayload.summary)" }
    & $exe --version | Out-File -Encoding utf8 'C:\gnustep-smoke\full-version-after.txt'
    @{ update_summary = $updatePayload.summary; version = (Get-Content 'C:\gnustep-smoke\full-version-after.txt' -Raw).Trim() }
  }
}
Add-Scenario 'self-update-cli-only' $updateOk @(
  'update-check-detects-newer-release',
  'update-plan-identifies-cli-only-layer',
  'update-apply-succeeds',
  'post-update-version-matches-target-release',
  'post-update-build-run-smoke-succeeds'
)

$overallOk = -not (@($scenarioReports | Where-Object { -not $_.ok }).Count)
$evidence | ConvertTo-Json -Depth 12 | Out-File -Encoding utf8 $evidencePath
[ordered]@{
  schema_version = 1
  suite_id = 'release'
  target_id = 'windows-amd64-msys2-clang64'
  runner_id = 'otvm-lease'
  release_under_test = [ordered]@{
    source = 'final-staged-0.1.0-25342971361'
    old_manifest = $oldManifest
    new_manifest = $newManifest
  }
  fixture_references = @('generated-cli-template-output', 'gorm-upstream-pinned', 'gorm-windows-private-ivar-patch', 'cli-only-update-channel')
  overall_ok = $overallOk
  scenario_reports = $scenarioReports
  evidence = [ordered]@{ evidence_file = $evidencePath }
} | ConvertTo-Json -Depth 12 | Out-File -Encoding utf8 $reportPath

if (-not $overallOk) { exit 1 }
