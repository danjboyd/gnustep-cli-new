# Windows counterpart of package-install-qualification.sh: install one package
# artifact into a managed root set up by the PUBLISHED PowerShell bootstrap,
# smoke its declared executables, then remove it and check nothing is left.
#
# Meant for disposable runners. On a real machine, note that the bootstrap's setup
# adds the scratch root's bin to the persistent user PATH and this script does not
# undo that; remove the entry afterwards. It doesn't touch an existing install.
param(
  [Parameter(Mandatory = $true)][string]$PackageId,
  [Parameter(Mandatory = $true)][string]$ArtifactId,
  [Parameter(Mandatory = $true)][string]$ArtifactFile,
  [Parameter(Mandatory = $true)][string]$Bootstrap,
  [Parameter(Mandatory = $true)][string]$OutDir,
  [string]$Repo = (Get-Location).Path,
  # Optional CLI zip (bin/gnustep.exe) to overlay on the bootstrap-installed root,
  # so an unreleased CLI's installer is exercised against the published toolchain.
  [string]$CliZip = ''
)
# Native stderr must not abort the run; each step records its own exit code.
$ErrorActionPreference = 'Continue'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$work = Join-Path $env:RUNNER_TEMP 'pkg-qualify'
Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $work | Out-Null
$root = Join-Path $work 'root'
$steps = [ordered]@{}

function Invoke-Step([string]$Name, [scriptblock]$Body) {
  $global:LASTEXITCODE = 0
  & $Body *> (Join-Path $OutDir "$Name.out")
  $steps[$Name] = $LASTEXITCODE
}

Invoke-Step 'setup' { & powershell -NoProfile -ExecutionPolicy Bypass -File $Bootstrap --json setup --yes --root $root }
$cliUnderTest = 'published'
if ($CliZip) {
  $cliDir = Join-Path $work 'cli-under-test'
  Expand-Archive -Force -Path $CliZip -DestinationPath $cliDir
  Copy-Item -Force (Join-Path $cliDir 'bin\gnustep.exe') (Join-Path $root 'bin\gnustep.exe')
  $cliUnderTest = (Get-FileHash -Algorithm SHA256 -Path $CliZip).Hash.ToLowerInvariant()
}

$index = Join-Path $work 'package-index.json'
$env:PYTHONPATH = Join-Path $Repo 'src'
$indexScript = Join-Path $work 'make-index.py'
@'
import hashlib, json, os, sys
from gnustep_cli_shared.package_repository import generate_package_index
packages_dir, package_id, artifact_id, artifact_path, output = sys.argv[1:]
index = generate_package_index(packages_dir)
index["packages"] = [p for p in index["packages"] if p["id"] == package_id]
matches = [a for a in index["packages"][0]["artifacts"] if a["id"] == artifact_id]
if len(matches) != 1:
    raise SystemExit(f"artifact {artifact_id} not declared by {package_id}")
digest = hashlib.sha256(open(artifact_path, "rb").read()).hexdigest()
matches[0].update({"url": "file:///" + os.path.abspath(artifact_path).replace("\\", "/"), "sha256": digest,
                   "size": os.path.getsize(artifact_path), "filename": os.path.basename(artifact_path), "publish": True})
json.dump(index, open(output, "w"), indent=2)
'@ | Set-Content -Encoding utf8 -Path $indexScript
python $indexScript (Join-Path $Repo 'packages') $PackageId $ArtifactId $ArtifactFile $index *> (Join-Path $OutDir 'index.out')
$steps['index'] = $LASTEXITCODE

$gnustep = Join-Path $root 'bin\gnustep.exe'
# The install goes through a throwaway signed manifest advertising this index, as a
# stable install does, with no --index and no production keys.
$env:RELEASE_TRUST_ROOT = (python (Join-Path $Repo 'scripts\dev\make-qualification-release.py') --work $work --root $root).Trim()

# A changed index must be refused: its digest no longer matches the signed manifest.
$goodIndex = [System.IO.File]::ReadAllBytes($index)
[System.IO.File]::WriteAllBytes($index, $goodIndex + [byte]10)
Invoke-Step 'tampered_list' { & $gnustep --json list --root $root }
$tamperedOut = Get-Content -Raw (Join-Path $OutDir 'tampered_list.out')
$steps['tampered_index'] = $(if ($steps['tampered_list'] -ne 0 -and $tamperedOut -match 'does not match the release manifest') { 0 } else { 1 })
[System.IO.File]::WriteAllBytes($index, $goodIndex)

Invoke-Step 'install' { & $gnustep --json install --root $root $PackageId }

$manifest = Get-Content -Raw (Join-Path $Repo "packages\$PackageId\package.json") | ConvertFrom-Json
$executables = @($manifest.install.executables)
$env:PATH = "$root\clang64\bin;$root\bin;$root\usr\bin;$env:PATH"
foreach ($conf in @("$root\clang64\etc\GNUstep\GNUstep.conf", "$root\etc\GNUstep\GNUstep.conf")) {
  if (Test-Path $conf) { $env:GNUSTEP_CONFIG_FILE = $conf; break }
}
$smoke = @()
$smokeOk = $true
foreach ($exe in $executables) {
  $path = Join-Path $root "packages\$PackageId\bin\$exe.exe"
  if (-not (Test-Path $path)) { $smoke += "$exe missing"; $smokeOk = $false; continue }
  $global:LASTEXITCODE = 0
  & $path --help *> $null
  $rc = $LASTEXITCODE
  $smoke += "$exe --help exit $rc"
  # Negative codes are NTSTATUS loader/crash failures (0xC0000135 = DLL not found).
  if ($rc -lt 0 -or $rc -ge 126) { $smokeOk = $false }
  # The exposed command in <root>\bin must run the same program with the same result.
  $shim = Join-Path $root "bin\$exe.cmd"
  if (Test-Path $shim) {
    $global:LASTEXITCODE = 0
    & cmd.exe /c "`"$shim`" --help" *> $null
    $shimRc = $LASTEXITCODE
    $smoke += "$exe.cmd --help exit $shimRc"
    if ($shimRc -ne $rc) { $smokeOk = $false }
  } else {
    $smoke += "$exe.cmd not exposed"
    $smokeOk = $false
  }
}
$smoke | Out-File -Encoding utf8 (Join-Path $OutDir 'smoke.out')
$steps['smoke'] = $(if ($smokeOk) { 0 } else { 1 })

Invoke-Step 'remove' { & $gnustep --json remove --root $root $PackageId }

$leftover = @()
if (Test-Path (Join-Path $root "packages\$PackageId")) { $leftover += "packages\$PackageId" }
foreach ($exe in $executables) {
  foreach ($name in @($exe, "$exe.exe", "$exe.cmd")) {
    if (Test-Path (Join-Path $root "bin\$name")) { $leftover += "bin\$name" }
  }
}
$state = Join-Path $root 'state\installed-packages.json'
if ((Test-Path $state) -and ((Get-Content -Raw $state) -match [regex]::Escape("`"$PackageId`""))) { $leftover += 'state entry' }
$leftover | Out-File -Encoding utf8 (Join-Path $OutDir 'leftovers.out')
$steps['leftovers'] = $(if ($leftover.Count -eq 0) { 0 } else { 1 })

$installJson = $null
try { $installJson = Get-Content -Raw (Join-Path $OutDir 'install.out') | ConvertFrom-Json } catch { }
$selected = $(if ($installJson) { $installJson.selected_artifact } else { $null })
$ok = ($selected -eq $ArtifactId)
foreach ($name in @('setup', 'index', 'tampered_index', 'install', 'smoke', 'remove', 'leftovers')) { if ($steps[$name] -ne 0) { $ok = $false } }
$summary = [ordered]@{
  schema_version = 1
  kind = 'package-install-qualification'
  package_id = $PackageId
  artifact_id = $ArtifactId
  artifact_sha256 = (Get-FileHash -Algorithm SHA256 -Path $ArtifactFile).Hash.ToLowerInvariant()
  cli_under_test = $cliUnderTest
  os = (Get-CimInstance Win32_OperatingSystem).Caption
  steps = $steps
  selected_artifact = $selected
  installed_version = $(if ($installJson) { $installJson.version } else { $null })
  smoke = $smoke
  leftovers = $leftover
  ok = $ok
}
$summary | ConvertTo-Json -Depth 5 | Out-File -Encoding utf8 (Join-Path $OutDir 'package-install-qualification.json')
$summary | ConvertTo-Json -Depth 5
if (-not $ok) { exit 1 }
exit 0
