$ErrorActionPreference = 'Continue'
$env:GNUSTEP_BOOTSTRAP_SKIP_PATH_UPDATE = '1'
$A = 'C:\gnustep-smoke\arlen'
$out = 'C:\gnustep-smoke\arlen-check'; New-Item -ItemType Directory -Force $out | Out-Null
$src = Get-ChildItem C:\gnustep-smoke -Directory -Filter 'install-full-*' | Select-Object -First 1
$root = $src.FullName
Set-Location $out
$log = Join-Path $out 'arlen-check.txt'
# UTF-8 throughout (PS 5.1 Tee-Object -Append writes UTF-16 after a UTF-8 line).
function Say($s) { Add-Content -Path $log -Value $s -Encoding utf8; Write-Output $s }
"elevated: $(([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))" | Out-File $log -Encoding utf8
$gnustep = Join-Path $root 'bin\gnustep.exe'
Say "cli: $(& $gnustep --version) sha256 $((Get-FileHash -Algorithm SHA256 $gnustep).Hash.ToLower())"
Say "arlen zip sha256 $((Get-ChildItem $A\arlen-*.zip | Get-FileHash -Algorithm SHA256).Hash.ToLower())"
$statePath = Join-Path $root 'state\cli-state.json'
$state = Get-Content -Raw $statePath | ConvertFrom-Json
$state | Add-Member -Force -NotePropertyName manifest_path -NotePropertyValue "$A\release-manifest.json"
[IO.File]::WriteAllText($statePath, ($state | ConvertTo-Json -Depth 20))
$env:RELEASE_TRUST_ROOT = "$A\qualification-signing-public.pem"
$index = "$A\package-index.json"
$good = [IO.File]::ReadAllBytes($index)
[IO.File]::WriteAllBytes($index, $good + [byte]10)
$t = & $gnustep --json list --root $root 2>&1 | Out-String; $rc = $LASTEXITCODE
Say "tampered list exit=$rc refused=$($t -match 'does not match the release manifest')"
[IO.File]::WriteAllBytes($index, $good)
$i = & $gnustep --json install --root $root arlen 2>&1 | Out-String; $rc = $LASTEXITCODE
$i | Out-File (Join-Path $out 'install.json') -Encoding utf8
Say "install exit=$rc"
try { $j = $i | ConvertFrom-Json; Say "install ok=$($j.ok) selected=$($j.selected_artifact) version=$($j.version) summary=$($j.summary)" } catch { Say "install json parse failed" }
foreach ($e in 'arlen','boomhauer') {
  $shim = Join-Path $root "bin\$e.cmd"
  Say "$e.cmd exists=$(Test-Path $shim) symlink=$(Test-Path (Join-Path $root "bin\$e.exe"))"
  $global:LASTEXITCODE = 0
  & cmd.exe /c "`"$shim`" --help" *> $null
  Say "$e.cmd --help exit $LASTEXITCODE"
}
$r = & $gnustep --json remove --root $root arlen 2>&1 | Out-String; $rc = $LASTEXITCODE
$r | Out-File (Join-Path $out 'remove.json') -Encoding utf8
Say "remove exit=$rc"
Say "leftovers: pkg=$(Test-Path (Join-Path $root 'packages\io.github.danjboyd.arlen')) arlen.cmd=$(Test-Path (Join-Path $root 'bin\arlen.cmd')) boomhauer.cmd=$(Test-Path (Join-Path $root 'bin\boomhauer.cmd'))"
Say "done"
