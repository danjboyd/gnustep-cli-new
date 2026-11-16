# Gate S: a managed Windows root updates ITSELF (`gnustep update` from its own bin), through the
# root-moving (non-pointer-only) upgrade path. Manifest X (0.1.8) installs; manifest Y is the same
# artifacts relabelled 0.1.9. Both are signed with a throwaway P-256 key trusted only for these
# commands. -Expect pass for the PR #77 CLI; -Expect fail for the unfixed control CLI.
param(
  [string]$Dir = 'C:\gnustep-smoke\release-new',
  [ValidateSet('pass', 'fail')][string]$Expect = 'pass'
)
$ErrorActionPreference = 'Continue'
$env:GNUSTEP_BOOTSTRAP_SKIP_PATH_UPDATE = '1'
$out = 'C:\gnustep-smoke\gate-s'
Remove-Item -Recurse -Force $out -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $out | Out-Null
$log = Join-Path $out 'gate-s.txt'
$results = [ordered]@{ expect = $Expect }
function Say($s) { Add-Content -Path $log -Value $s; Write-Host $s }
function Clear-Trust { Remove-Item Env:\RELEASE_TRUST_ROOT -ErrorAction SilentlyContinue }
function State-Version($root) {
  $p = Join-Path $root 'state\cli-state.json'
  if (-not (Test-Path $p)) { return $null }
  try { return (Get-Content $p -Raw | ConvertFrom-Json).cli_version } catch { return $null }
}
function Free-GB { return [math]::Round((Get-PSDrive -Name 'C').Free / 1GB, 1) }
$basePath = $env:PATH

# Throwaway signing key, as update-gates8.ps1 does.
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
$trust = Join-Path $out 'gate-s-trust-root.pem'
"-----BEGIN PUBLIC KEY-----`n" + [Convert]::ToBase64String([byte[]]$spki, 'InsertLineBreaks') + "`n-----END PUBLIC KEY-----`n" | Set-Content -Encoding ASCII -NoNewline $trust
function Sign-File($path) {
  $raw = $signer.SignData([System.IO.File]::ReadAllBytes($path), [System.Security.Cryptography.HashAlgorithmName]::SHA256)
  $body = (ConvertTo-DerInteger ([byte[]]$raw[0..31])) + (ConvertTo-DerInteger ([byte[]]$raw[32..63]))
  [System.IO.File]::WriteAllBytes("$path.sig", [byte[]](@([byte]0x30, [byte]$body.Length) + $body))
}
$mx = Join-Path $Dir 'release-manifest.s-x.json'
$my = Join-Path $Dir 'release-manifest.s-y.json'
Sign-File $mx; Sign-File $my; $signer.Dispose()

$root = 'C:\gnustep-smoke\gate-s-root'
$env:RELEASE_TRUST_ROOT = $trust
& powershell -NoProfile -ExecutionPolicy Bypass -File 'C:\gnustep-smoke\bootstrap\gnustep-bootstrap.ps1' setup --root $root --manifest $mx *> (Join-Path $out 'bootstrap-x.txt')
$bsCode = $LASTEXITCODE
Clear-Trust
$results.install = [ordered]@{ exit = $bsCode; version = (State-Version $root) }
Say "install X: exit $bsCode version $(State-Version $root); $(Free-GB) GB free"
if ((State-Version $root) -ne '0.1.8') { Say 'STOP: install X did not produce 0.1.8'; $results.S = [ordered]@{ ok = $false; not_run = 'install failed' } }
else {
  # The root's own CLI updates the root, with the root on PATH as after `. GNUstep.ps1`.
  $env:PATH = "$root\usr\bin;$root\bin;$root\clang64\bin;" + $basePath
  $env:GNUSTEP_CLI_INSTALL_TRACE = Join-Path $out 'S-self-update.trace.log'
  $env:RELEASE_TRUST_ROOT = $trust
  & "$root\bin\gnustep.exe" update --yes --root $root --manifest $my *> (Join-Path $out 'S-self-update.txt')
  $sCode = $LASTEXITCODE
  Clear-Trust
  Remove-Item Env:GNUSTEP_CLI_INSTALL_TRACE -ErrorAction SilentlyContinue
  $env:PATH = $basePath
  $verAfter = State-Version $root
  # On Windows the active release is named in current\release.txt (a folder, not a symlink).
  $current = "$((Get-Content "$root\current\release.txt" -ErrorAction SilentlyContinue | Select-Object -First 1))".Trim()
  $trace = Get-Content (Join-Path $out 'S-self-update.trace.log') -ErrorAction SilentlyContinue
  $smokeOk = [bool]($trace | Select-String -SimpleMatch 'windows.upgrade.cli.stage.smoke.ok')
  $smokeFailed = [bool]($trace | Select-String -SimpleMatch 'windows.upgrade.cli.stage.smoke.failed')
  # After the update the root's launcher must run, and doctor must recognise the managed root.
  $env:PATH = "$root\usr\bin;$root\bin;$root\clang64\bin;" + $basePath
  $verOut = (& "$root\bin\gnustep.exe" --version 2>&1 | Out-String).Trim(); $verCode = $LASTEXITCODE
  & "$root\bin\gnustep.exe" doctor --json *> (Join-Path $out 'S-doctor.txt'); $docCode = $LASTEXITCODE
  $env:PATH = $basePath
  $integrity = $null; $mroot = $null
  try {
    $doc = Get-Content (Join-Path $out 'S-doctor.txt') -Raw | ConvertFrom-Json
    $integrity = (@($doc.checks) | Where-Object { $_.id -eq 'managed.install.integrity' } | Select-Object -First 1).status
    $mroot = (@($doc.checks) | Where-Object { $_.id -eq 'native-toolchain.assess' } | Select-Object -First 1).details.managed_root
  } catch { Say "doctor parse error: $($_.Exception.Message)" }
  $passed = ($sCode -eq 0 -and $verAfter -eq '0.1.9' -and $current -eq '0.1.9' -and (Test-Path "$root\releases\0.1.9\bin\gnustep.exe") -and $smokeOk -and $verCode -eq 0 -and $integrity -eq 'ok' -and $mroot -and (($mroot -replace '/', '\').TrimEnd('\') -ieq $root))
  $results.S = [ordered]@{ exit = $sCode; version_after = $verAfter; current = $current; smoke_ok = $smokeOk; smoke_failed = $smokeFailed; launcher_version_exit = $verCode; launcher_version = $verOut; doctor_exit = $docCode; integrity = $integrity; managed_root = $mroot; passed = $passed }
  Say "S: exit $sCode 0.1.8 -> $verAfter current=$current smoke_ok=$smokeOk smoke_failed=$smokeFailed launcher=$verCode/$verOut integrity=$integrity managed_root=$mroot passed=$passed"
  $results.S.ok = $(if ($Expect -eq 'pass') { $passed } else { (-not $passed) -and $smokeFailed -and $verAfter -eq '0.1.8' })
}
$results | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $out 'gate-s.json') -Encoding utf8
Say "expect=$Expect ok=$($results.S.ok)"
if (-not $results.S.ok) { exit 1 }
