# Windows gate for the patch layer's CLI side (docs/specs/patch-layer.md).
# Runs under Windows PowerShell 5.1 on a GitHub runner, against a release staged by
# windows-carry-layer.yml: X (0.1.9) and Y (0.1.10, the same artifacts relabelled), each with
# cli, toolchain and carry-layer artifacts, signed with a throwaway key trusted only here.
#   1. bootstrap `setup --variant patched` installs stock, then the CLI applies the layer;
#   2. every layer file is patched, and doctor reports managed.toolchain.variant ok/patched;
#   3. `setup --variant stock`, run by the root's own gnustep.exe (which has the patched
#      gnustep-base DLL loaded), restores stock: the whole clang64 tree is byte-identical
#      to before the layer;
#   4. `setup --variant patched` switches back without reinstalling;
#   5. `update` to Y keeps the variant;
#   6. doctor afterwards reports the patched variant intact.
param([string]$Dir = 'C:\carry-gate\release')
$ErrorActionPreference = 'Continue'
$env:GNUSTEP_BOOTSTRAP_SKIP_PATH_UPDATE = '1'
$out = 'C:\carry-gate\out'
New-Item -ItemType Directory -Force $out | Out-Null
$log = Join-Path $out 'variant-gate.txt'
$results = [ordered]@{}
function Say($s) { Add-Content -Path $log -Value $s; Write-Host $s }
$basePath = $env:PATH

# Throwaway P-256 signing key, as the update gates use.
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
$trust = Join-Path $out 'trust-root.pem'
"-----BEGIN PUBLIC KEY-----`n" + [Convert]::ToBase64String([byte[]]$spki, 'InsertLineBreaks') + "`n-----END PUBLIC KEY-----`n" | Set-Content -Encoding ASCII -NoNewline $trust
function Sign-File($path) {
  $raw = $signer.SignData([System.IO.File]::ReadAllBytes($path), [System.Security.Cryptography.HashAlgorithmName]::SHA256)
  $body = (ConvertTo-DerInteger ([byte[]]$raw[0..31])) + (ConvertTo-DerInteger ([byte[]]$raw[32..63]))
  [System.IO.File]::WriteAllBytes("$path.sig", [byte[]](@([byte]0x30, [byte]$body.Length) + $body))
}
$mx = Join-Path $Dir 'release-manifest.x.json'
$my = Join-Path $Dir 'release-manifest.y.json'
Sign-File $mx; Sign-File $my; $signer.Dispose()

$root = 'C:\carry-gate\root'
$exe = Join-Path $root 'bin\gnustep.exe'
function With-Root([scriptblock]$block) {
  $env:PATH = "$root\usr\bin;$root\bin;$root\clang64\bin;" + $basePath
  $env:RELEASE_TRUST_ROOT = $trust
  try { & $block } finally { Remove-Item Env:\RELEASE_TRUST_ROOT -ErrorAction SilentlyContinue; $env:PATH = $basePath }
}
function Read-Json($path) {
  # The JSON document is the output from its first line starting with "{" (a command may
  # print warnings to stderr first, which *> merges in).
  try {
    $lines = @(Get-Content $path)
    $start = 0
    while ($start -lt $lines.Count -and -not $lines[$start].TrimStart().StartsWith('{')) { $start++ }
    if ($start -ge $lines.Count) { return $null }
    return ([string]::Join("`n", $lines[$start..($lines.Count - 1)]) | ConvertFrom-Json)
  } catch { return $null }
}
function Tree-Digest {
  # sha256 of every file under clang64, sorted by path: equal digests mean an identical tree.
  $base = Join-Path $root 'clang64'
  $lines = Get-ChildItem -Recurse -File $base | Sort-Object FullName | ForEach-Object {
    $_.FullName.Substring($base.Length) + ' ' + (Get-FileHash -Algorithm SHA256 $_.FullName).Hash
  }
  $joined = [string]::Join("`n", $lines)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  return ([System.BitConverter]::ToString($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($joined))) -replace '-', '').ToLower()
}
$layerFiles = @((Read-Json (Join-Path $Dir 'carry-layer.json')).files)
function Layer-State {
  # "patched" if every layer file is the patched one, "stock" if every one is stock, else "mixed".
  $p = 0; $s = 0
  foreach ($f in $layerFiles) {
    $path = Join-Path $root ($f.path -replace '/', '\')
    $h = if (Test-Path $path) { (Get-FileHash -Algorithm SHA256 $path).Hash.ToLower() } else { '' }
    if ($h -eq $f.sha256) { $p++ } elseif ($h -eq $f.stock_sha256) { $s++ }
  }
  if ($p -eq $layerFiles.Count) { return 'patched' }
  if ($s -eq $layerFiles.Count) { return 'stock' }
  return "mixed (patched $p, stock $s of $($layerFiles.Count))"
}
function Doctor-Variant($name) {
  With-Root { & $exe doctor --json *> (Join-Path $out "$name-doctor.txt") }
  $doc = Read-Json (Join-Path $out "$name-doctor.txt")
  $check = @($doc.checks) | Where-Object { $_.id -eq 'managed.toolchain.variant' } | Select-Object -First 1
  if (-not $check) { return 'missing' }
  return "$($check.status)/$($check.details.toolchain_variant)"
}
function Step($name, [scriptblock]$cli) {
  With-Root { & $cli *> (Join-Path $out "$name.txt") }
  $code = $LASTEXITCODE
  $state = Layer-State
  $doctor = Doctor-Variant $name
  $variant = (Read-Json (Join-Path $root 'state\cli-state.json')).toolchain_variant
  Say "${name}: exit $code; files $state; state toolchain_variant=$variant; doctor $doctor"
  return [ordered]@{ exit = $code; files = $state; state_variant = $variant; doctor = $doctor }
}

# 1. Bootstrap install with --variant patched (stock first, so record stock's tree too).
$env:RELEASE_TRUST_ROOT = $trust
$env:GNUSTEP_BOOTSTRAP_ALLOW_UNSIGNED = '1'
& powershell -NoProfile -ExecutionPolicy Bypass -File 'C:\carry-gate\bootstrap\gnustep-bootstrap.ps1' --json setup --variant patched --root $root --manifest $mx > (Join-Path $out 'bootstrap.txt') 2> (Join-Path $out 'bootstrap-stderr.txt')
$bsCode = $LASTEXITCODE
Remove-Item Env:\GNUSTEP_BOOTSTRAP_ALLOW_UNSIGNED -ErrorAction SilentlyContinue
Remove-Item Env:\RELEASE_TRUST_ROOT -ErrorAction SilentlyContinue
$bs = Read-Json (Join-Path $out 'bootstrap.txt')
$results.bootstrap = [ordered]@{ exit = $bsCode; toolchain_variant = $bs.toolchain_variant; carry_ok = $bs.carry_layer.ok; files = (Layer-State); doctor = (Doctor-Variant 'bootstrap') }
Say "bootstrap --variant patched: exit $bsCode; json toolchain_variant=$($bs.toolchain_variant) carry_layer.ok=$($bs.carry_layer.ok); files $($results.bootstrap.files); doctor $($results.bootstrap.doctor)"
$ok = $false
if ($bsCode -ne 0) { Say 'STOP: the bootstrap failed'; Get-Content (Join-Path $out 'bootstrap.txt') | Select-Object -Last 20 | ForEach-Object { Say "  $_" } }
else {
  # 3. Back to stock, by the root's own exe (its gnustep-base DLL is the patched one).
  $results.to_stock = Step 'to-stock' { & $exe setup --variant stock --root $root --json }
  $stockTree = Tree-Digest
  $results.record_removed = -not (Test-Path (Join-Path $root 'carry-layer.json'))
  # 4. Patched again, without reinstalling; then stock again: the tree must match.
  $results.to_patched = Step 'to-patched' { & $exe setup --variant patched --root $root --manifest $mx --json }
  $patchedTree = Tree-Digest
  $results.to_stock_again = Step 'to-stock-again' { & $exe setup --variant stock --root $root --json }
  $results.stock_tree_identical = ((Tree-Digest) -eq $stockTree)
  $results.patched_tree_differs = ($patchedTree -ne $stockTree)
  Say "stock tree identical after a round trip=$($results.stock_tree_identical); patched tree differs=$($results.patched_tree_differs)"
  # 5. Patched, then update to Y: the variant must survive.
  $results.before_update = Step 'before-update' { & $exe setup --variant patched --root $root --manifest $mx --json }
  $results.update = Step 'update' { & $exe update --yes --json --root $root --manifest $my }
  $results.update_version = (Read-Json (Join-Path $root 'state\cli-state.json')).cli_version
  Say "after update: cli_version=$($results.update_version)"
  $ok = ($results.bootstrap.toolchain_variant -eq 'patched' -and $results.bootstrap.files -eq 'patched' -and $results.bootstrap.doctor -eq 'ok/patched' `
    -and $results.to_stock.exit -eq 0 -and $results.to_stock.files -eq 'stock' -and $results.to_stock.doctor -eq 'ok/stock' -and $results.record_removed `
    -and $results.to_patched.exit -eq 0 -and $results.to_patched.files -eq 'patched' -and $results.to_patched.doctor -eq 'ok/patched' `
    -and $results.to_stock_again.exit -eq 0 -and $results.stock_tree_identical -and $results.patched_tree_differs `
    -and $results.update.exit -eq 0 -and $results.update.files -eq 'patched' -and $results.update.doctor -eq 'ok/patched' -and $results.update_version -eq '0.1.10')
}
$results.ok = $ok
$results | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $out 'variant-gate.json') -Encoding ASCII
Say "ok=$ok"
if (-not $ok) { exit 1 }
