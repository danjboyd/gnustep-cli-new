# v0.1.9 Windows update gates, CI form (Dan's ask #7778 answer "fix": GitHub Windows runner, no lease).
# -Gates A runs staged + A0 + A + C2 + C; -Gates BN runs staged + B + N (separate fresh runners, for disk).
# The staged 0.1.9 install is bootstrapped from the staged manifest (throwaway-signed copy).
#  A  THE upgrade for existing users: a v0.1.8 install moved to the staged 0.1.9 by its OWN
#     0.1.8 CLI with an explicit --manifest (the staged copy; RELEASE_TRUST_ROOT for that one
#     command). This exercises v0.1.8's #57/#64 code (30-min extraction, process-tree kill,
#     checked rollback) on a real Windows host.
#  B  a v0.1.5 install updated by the staged 0.1.9 CLI, plain update --yes, no --manifest, no
#     trust override, real production Latest (v0.1.8): expect 0.1.5 -> 0.1.8. On 11-13 this
#     failed with "Failed to copy bin/libclang.dll" on a full disk; now disk is checked first.
#  N  update cli --yes on B's root afterwards (no-op if B upgraded; the upgrade otherwise).
#  C  doctor on the staged 0.1.9 install.
# Not covered: 0.1.8 -> 0.1.9 by default discovery (needs v0.1.9 to be Latest; post-publish).
param(
  [string]$StagedManifest = 'C:\gnustep-smoke\release-new\release-manifest.json',
  [string]$Gates = 'A,BN'
)
$ErrorActionPreference = 'Continue'
$env:GNUSTEP_BOOTSTRAP_SKIP_PATH_UPDATE = '1'
$out = 'C:\gnustep-smoke\update-gates6'
Remove-Item -Recurse -Force $out -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $out | Out-Null
$log = Join-Path $out 'update-gates.txt'
$results = [ordered]@{}
function Say($s) { Add-Content -Path $log -Value $s; Write-Host $s }
function Clear-Trust { Remove-Item Env:\RELEASE_TRUST_ROOT -ErrorAction SilentlyContinue; Remove-Item Env:\GNUSTEP_BOOTSTRAP_ALLOW_UNSIGNED -ErrorAction SilentlyContinue }
function State-Version($root) {
  $p = Join-Path $root 'state\cli-state.json'
  if (-not (Test-Path $p)) { return $null }
  try { return (Get-Content $p -Raw | ConvertFrom-Json).cli_version } catch { return $null }
}
function Bootstrap-Version($ver, $root) {
  Clear-Trust
  $bs = "C:\gnustep-smoke\bs5-$ver.ps1"
  Invoke-WebRequest -UseBasicParsing "https://github.com/danjboyd/gnustep-cli-new/releases/download/v$ver/gnustep-bootstrap.ps1" -OutFile $bs
  & powershell -NoProfile -ExecutionPolicy Bypass -File $bs setup --root $root *> (Join-Path $out ("bootstrap-$ver-" + (Split-Path $root -Leaf) + ".txt"))
  return $LASTEXITCODE
}
# Free space on the gate volume, in GB, logged before each gate (v0.1.8: a full disk looked like a product failure).
function Free-GB { return [math]::Round((Get-PSDrive -Name ($out.Substring(0,1))).Free / 1GB, 1) }
$MinFreeGB = 12
function Check-Disk($gate) {
  $free = Free-GB
  Say "disk before ${gate}: $free GB free"
  if ($free -lt $MinFreeGB) { Say "SKIP ${gate}: only $free GB free (need $MinFreeGB)"; return $false }
  return $true
}
# Remove a gate's install root and its sibling setup backups once its results are recorded.
function Remove-GateRoot($root) {
  $leaf = Split-Path $root -Leaf
  Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue
  Get-ChildItem (Split-Path $root -Parent) -Force -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like ".$leaf.setup-backup*" } | ForEach-Object { Remove-Item -Recurse -Force $_.FullName -ErrorAction SilentlyContinue }
  Say "removed $leaf (and its backups); $(Free-GB) GB free"
}
# Same environment as the tier1-core self-update scenario (and as a user who ran the
# root's GNUstep.ps1): the target root's usr\bin, bin and clang64\bin first on PATH,
# plus the unzip shim the smoke uses.
$shimDir = 'C:\gnustep-smoke\update-gates6-shims'
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
$basePath = $env:PATH
function Run-Cli($exe, $name, [string]$root, [string[]]$cliArgs) {
  $env:PATH = "$shimDir;$root\usr\bin;$root\bin;$root\clang64\bin;" + $basePath
  $env:GNUSTEP_CLI_INSTALL_TRACE = Join-Path $out "$name.trace.log"
  & $exe @cliArgs *> (Join-Path $out "$name.txt")
  Remove-Item Env:GNUSTEP_CLI_INSTALL_TRACE -ErrorAction SilentlyContinue
  $script:lastCode = $LASTEXITCODE
  $env:PATH = $basePath
  Say "$name exit $($script:lastCode) ($exe $($cliArgs -join ' '))"
}


# Sign a copy of the staged manifest for gate A and the staged install.
# The staged manifest isn't production-signed before Release, so sign a copy (same
# directory, so relative artifact paths still resolve) with a throwaway P-256 key
# and trust only that key for this one command.
function ConvertTo-DerInteger([byte[]]$Bytes) {
  $index = 0
  while ($index -lt $Bytes.Length - 1 -and $Bytes[$index] -eq 0) { $index++ }
  $value = [byte[]]($Bytes[$index..($Bytes.Length - 1)])
  if ($value[0] -band 0x80) { $value = [byte[]](@([byte]0) + $value) }
  return ,([byte[]](@([byte]0x02, [byte]$value.Length) + $value))
}
$signer = [System.Security.Cryptography.ECDsa]::Create([System.Security.Cryptography.ECCurve+NamedCurves]::nistP256)
$q = $signer.ExportParameters($false).Q
$spki = [byte[]](0x30,0x59,0x30,0x13,0x06,0x07,0x2A,0x86,0x48,0xCE,0x3D,0x02,0x01,0x06,0x08,0x2A,0x86,0x48,0xCE,0x3D,0x03,0x01,0x07,0x03,0x42,0x00,0x04) + $q.X + $q.Y
$FixtureTrustRoot = Join-Path $out 'gate-a-trust-root.pem'
"-----BEGIN PUBLIC KEY-----`n" + [Convert]::ToBase64String([byte[]]$spki, 'InsertLineBreaks') + "`n-----END PUBLIC KEY-----`n" | Set-Content -Encoding ASCII -NoNewline $FixtureTrustRoot
$signedManifest = Join-Path (Split-Path -Parent $StagedManifest) 'release-manifest.gate6-a.json'
Copy-Item -Force $StagedManifest $signedManifest
$raw = $signer.SignData([System.IO.File]::ReadAllBytes($signedManifest), [System.Security.Cryptography.HashAlgorithmName]::SHA256)
$body = (ConvertTo-DerInteger ([byte[]]$raw[0..31])) + (ConvertTo-DerInteger ([byte[]]$raw[32..63]))
[System.IO.File]::WriteAllBytes("$signedManifest.sig", [byte[]](@([byte]0x30, [byte]$body.Length) + $body))
$signer.Dispose()

# The staged 0.1.9 install that supplies the new CLI: the stamped 0.1.9 bootstrap with the
# same throwaway-signed staged manifest, as the release smoke does.
$staged = 'C:\gnustep-smoke\gate6-staged-018'
$env:RELEASE_TRUST_ROOT = $FixtureTrustRoot
& powershell -NoProfile -ExecutionPolicy Bypass -File 'C:\gnustep-smoke\bootstrap\gnustep-bootstrap.ps1' setup --root $staged --manifest $signedManifest *> (Join-Path $out 'bootstrap-staged-0.1.9.txt')
$bsS = $LASTEXITCODE
Clear-Trust
$newCli = Join-Path $staged 'bin\gnustep.exe'
Say "staged 0.1.9 bootstrap exit $bsS; root $staged; version $(State-Version $staged)"
if ((State-Version $staged) -ne '0.1.9') { Say 'FAIL: staged install is not 0.1.9; stop'; $results | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $out 'update-gates.json') -Encoding utf8; Say 'done'; exit 1 }
if ($Gates -match 'A') {
# A0: the candidate smoke exactly as the CLI runs it (powershell, managed-root env, PATH), on the
# staged install's 0.1.9 release, with its output kept (v0.1.9 lease: A's smoke exited 1 with no output).
$stagedLauncher = Join-Path $staged 'current\bin\gnustep.exe'
if (-not (Test-Path $stagedLauncher)) { $stagedLauncher = Join-Path $staged 'bin\gnustep.exe' }
$smoke = "`$env:GNUSTEP_CLI_MANAGED_ROOT='$staged'; `$env:GNUSTEP_CLI_NO_DELEGATE='1'; `$env:PATH='$staged\clang64\bin;$staged\bin;$staged\usr\bin;' + `$env:PATH; & '$stagedLauncher' --version"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -Command $smoke *> (Join-Path $out 'A0-candidate-smoke.txt'); $codeA0 = $LASTEXITCODE
$a0Text = (Get-Content (Join-Path $out 'A0-candidate-smoke.txt') -Raw -ErrorAction SilentlyContinue)
$results.A0 = [ordered]@{ launcher = $stagedLauncher; exit = $codeA0; output = "$a0Text".Trim(); ok = ($codeA0 -eq 0 -and "$a0Text" -match '0\.1\.9') }
Say "A0: exit $codeA0 output=$("$a0Text".Trim()) ok=$($results.A0.ok)"
$rootA = 'C:\gnustep-smoke\gate6-a-017'
if (-not (Check-Disk 'A')) { $results.A = [ordered]@{ ok = $false; not_run = 'low disk' }; $results | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $out 'update-gates.json') -Encoding utf8; Say 'STOP: low disk before A'; exit 1 }
$bsA = Bootstrap-Version '0.1.8' $rootA
Say "A bootstrap 0.1.8 exit $bsA; version $(State-Version $rootA)"
$env:RELEASE_TRUST_ROOT = $FixtureTrustRoot
Run-Cli (Join-Path $rootA 'bin\gnustep.exe') 'A-update-explicit-manifest' $rootA @('update', '--yes', '--root', $rootA, '--manifest', $signedManifest); $codeA = $script:lastCode
Clear-Trust
$verA = State-Version $rootA
$results.A = [ordered]@{ route = 'explicit --manifest (staged copy signed with a throwaway key; RELEASE_TRUST_ROOT for this command only)'; cli = '0.1.8 (#57, #64)'; exit = $codeA; before = '0.1.8'; after = $verA; ok = ($codeA -eq 0 -and $verA -eq '0.1.9') }
Say "A: 0.1.8 -> $verA ok=$($results.A.ok)"
$results.A.disk_free_gb_after = Free-GB
# C2: doctor on A's UPGRADED install, with its own (now 0.1.9) CLI: must recognise the managed
# root (the empty .staging every upgrade leaves made the 0.1.9 doctor say "repair", PR #76).
if ($results.A.ok) {
  $env:PATH = (Join-Path $rootA 'clang64\bin') + ';' + (Join-Path $rootA 'usr\bin') + ';' + (Join-Path $rootA 'bin') + ';' + $basePath
  Run-Cli (Join-Path $rootA 'bin\gnustep.exe') 'C2-doctor-upgraded' $rootA @('doctor', '--json'); $codeC2 = $script:lastCode
  $env:PATH = $basePath
  $c2Ok = $false; $c2Root = $null; $c2Integrity = $null
  try {
    $doc2 = Get-Content (Join-Path $out 'C2-doctor-upgraded.txt') -Raw | ConvertFrom-Json
    $c2Root = (@($doc2.checks) | Where-Object { $_.id -eq 'native-toolchain.assess' } | Select-Object -First 1).details.managed_root
    $c2Integrity = (@($doc2.checks) | Where-Object { $_.id -eq 'managed.install.integrity' } | Select-Object -First 1).status
    $c2Action = (@($doc2.actions) | Where-Object { $_.kind -match 'toolchain' } | Select-Object -First 1).kind
    $c2Ok = ($c2Integrity -eq 'ok' -and $c2Root -and (($c2Root -replace '/', '\').TrimEnd('\') -ieq $rootA.TrimEnd('\')) -and $c2Action -eq 'use_managed_toolchain')
  } catch { Say "C2 parse error: $($_.Exception.Message)" }
  $results.C2 = [ordered]@{ exit = $codeC2; integrity = $c2Integrity; managed_root = $c2Root; action = $c2Action; ok = $c2Ok }
} else {
  $results.C2 = [ordered]@{ ok = $false; not_run = 'A did not upgrade' }
}
Say "C2: integrity=$($results.C2.integrity) managed_root=$($results.C2.managed_root) ok=$($results.C2.ok)"
Remove-GateRoot $rootA
# C: doctor on the staged 0.1.9 managed install.
$env:PATH = (Join-Path $staged 'clang64\bin') + ';' + (Join-Path $staged 'usr\bin') + ';' + (Join-Path $staged 'bin') + ';' + $basePath
Run-Cli $newCli 'C-doctor' $staged @('doctor', '--json'); $codeC = $script:lastCode
$env:PATH = $basePath
$cOk = $false; $cRoot = $null; $cAction = $null
try {
  $doc = Get-Content (Join-Path $out 'C-doctor.txt') -Raw | ConvertFrom-Json
  $chk = @($doc.checks) | Where-Object { $_.id -eq 'native-toolchain.assess' } | Select-Object -First 1
  $cRoot = $chk.details.managed_root
  $cAction = (@($doc.actions) | Where-Object { $_.kind -match 'toolchain' } | Select-Object -First 1).kind
  $choose = (Get-Content (Join-Path $out 'C-doctor.txt') -Raw) -match 'choose a managed install'
  $cOk = ($cRoot -and (($cRoot -replace '/', '\').TrimEnd('\') -ieq $staged.TrimEnd('\')) -and $cAction -eq 'use_managed_toolchain' -and -not $choose)
} catch { Say "C parse error: $($_.Exception.Message)" }
$results.C = [ordered]@{ exit = $codeC; managed_root = $cRoot; action = $cAction; ok = $cOk }
Say "C: managed_root=$cRoot action=$cAction ok=$cOk"
}


if ($Gates -match 'BN') {
# B: v0.1.5 install, staged 0.1.9 CLI, real production Latest (v0.1.8), no --manifest
$rootB = 'C:\gnustep-smoke\gate6-b-015'
if (-not (Check-Disk 'B')) { $results.B = [ordered]@{ ok = $false; not_run = 'low disk' }; $results | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $out 'update-gates.json') -Encoding utf8; Say 'STOP: low disk before B'; exit 1 }
$bsB = Bootstrap-Version '0.1.5' $rootB
Say "B bootstrap 0.1.5 exit $bsB; version $(State-Version $rootB)"
Clear-Trust
$results.B_disk_free_gb_before = Free-GB
Run-Cli $newCli 'B-new-cli-update-check' $rootB @('update', '--check', '--root', $rootB); $codeBc = $script:lastCode
Run-Cli $newCli 'B-new-cli-update-yes' $rootB @('update', '--yes', '--root', $rootB); $codeB = $script:lastCode
$verB = State-Version $rootB
$results.B = [ordered]@{ route = 'default discovery (production Latest v0.1.8, no --manifest, no trust override)'; cli = 'staged 0.1.9'; check_exit = $codeBc; exit = $codeB; before = '0.1.5'; after = $verB; ok = ($codeB -eq 0 -and $verB -eq '0.1.8') }
Say "B: 0.1.5 -> $verB exit $codeB ok=$($results.B.ok)"
Get-ChildItem $rootB -Force -ErrorAction SilentlyContinue | ForEach-Object { Say ('B root: ' + $_.Name) }

# N: B's install now records the production 0.1.8 manifest and Latest is 0.1.8, so
# the staged 0.1.9 CLI's `update cli --yes` must find nothing newer and change nothing (#64).
$curBefore = (Get-Item "$rootB\current" -ErrorAction SilentlyContinue).Target
$snapBefore = @(Get-ChildItem C:\gnustep-smoke -Force -Directory | Where-Object { $_.Name -like '.gate6-b-015.setup-backup*' }).Count
Run-Cli $newCli 'N-update-cli-noop' $rootB @('update', 'cli', '--yes', '--root', $rootB); $codeN = $script:lastCode
$curAfter = (Get-Item "$rootB\current" -ErrorAction SilentlyContinue).Target
$snapAfter = @(Get-ChildItem C:\gnustep-smoke -Force -Directory | Where-Object { $_.Name -like '.gate6-b-015.setup-backup*' }).Count
$noopText = Get-Content (Join-Path $out 'N-update-cli-noop.txt') -Raw -ErrorAction SilentlyContinue
$verN = State-Version $rootB
if ($verB -eq '0.1.8') {
  $results.N = [ordered]@{ route = 'update cli --yes, nothing newer (B already at production Latest 0.1.8)'; kind = 'noop'; cli = 'staged 0.1.9'; exit = $codeN; version = $verN; current_before = "$curBefore"; current_after = "$curAfter"; snapshots_before = $snapBefore; snapshots_after = $snapAfter; ok = ($codeN -eq 0 -and $noopText -match 'No updates were found' -and "$curBefore" -eq "$curAfter" -and $snapBefore -eq $snapAfter) }
} else {
  # B didn't upgrade, so N is itself the 0.1.5 -> Latest upgrade through `update cli --yes`.
  $results.N = [ordered]@{ route = 'update cli --yes from 0.1.5 (B did not upgrade first)'; kind = 'upgrade'; cli = 'staged 0.1.9'; exit = $codeN; before = $verB; version = $verN; ok = ($codeN -eq 0 -and $verN -eq '0.1.8') }
}
Say "N: exit $codeN version $(State-Version $rootB) current unchanged=$("$curBefore" -eq "$curAfter") snapshots $snapBefore->$snapAfter ok=$($results.N.ok)"



Remove-GateRoot $rootB
}


$results.not_covered = @('0.1.8 -> 0.1.9 by default discovery (needs v0.1.9 as Latest; post-publish check)', 'OpenBSD', 'Windows native unit tests')
$results.disk_free_gb_end = Free-GB
$results | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $out 'update-gates.json') -Encoding utf8
$failed = @($results.Keys | Where-Object { $results[$_] -is [System.Collections.IDictionary] -and $results[$_].Contains('ok') -and -not $results[$_].ok })
Set-Content -Path (Join-Path $out 'exit.txt') -Value ($(if ($failed.Count) { 'failed ' + ($failed -join ',') } else { 'passed' })) -Encoding ascii
Say "done; failed: $($failed -join ',')"
if ($failed.Count) { exit 1 }
