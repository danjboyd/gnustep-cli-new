$ErrorActionPreference = 'Continue'
$out = 'C:\gnustep-smoke\post'; Remove-Item -Recurse -Force $out -ErrorAction SilentlyContinue; New-Item -ItemType Directory -Force $out | Out-Null
$log = Join-Path $out 'post-checks.txt'
# UTF-8 throughout (PS 5.1 Tee-Object -Append writes UTF-16 after a UTF-8 line).
function Say($s) { Add-Content -Path $log -Value $s -Encoding utf8; Write-Output $s }
"elevated: $(([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))" | Out-File $log -Encoding utf8
Get-Process gdnc -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 2
Say "gdnc before (should be 0): $(@(Get-Process gdnc -ErrorAction SilentlyContinue).Count)"
$root = (Get-ChildItem C:\gnustep-smoke -Directory -Filter 'install-full-*' | Select-Object -First 1).FullName
Say "root: $root"
$bash = Join-Path $root 'usr\bin\bash.exe'
$env:CHERE_INVOKING = '1'
$cygpath = Join-Path $root 'usr\bin\cygpath.exe'
$script = (& $cygpath -u 'C:\gnustep-smoke\smoke-toolchain.sh' | Out-String).Trim()
$rootu = (& $cygpath -u $root | Out-String).Trim()
Say "script: $script root: $rootu"
$env:GNUSTEP_SMOKE_TLS_EXE = Join-Path $out 'tls.exe'
& $bash -lc "bash '$script' '$rootu'" *> (Join-Path $out 'smoke-toolchain.txt')
Say "smoke-toolchain exit $LASTEXITCODE"
Get-Content (Join-Path $out 'smoke-toolchain.txt') | Where-Object { $_ -match '^ok: |fetched$|refused$|expected' } | ForEach-Object { Say $_ }
Say "gdnc after (started by the library): $(@(Get-Process gdnc -ErrorAction SilentlyContinue).Count)"
$env:PATH = (Join-Path $root 'clang64\bin') + ';' + $env:PATH
if (-not (Test-Path (Join-Path $out 'tls.exe'))) { Say "tls.exe missing: outside-bash checks not run"; Say "done"; exit 1 }
foreach ($u in @('https://github.com', 'https://expired.badssl.com', 'https://1.1.1.1')) {
  $global:LASTEXITCODE = 0
  & (Join-Path $out 'tls.exe') $u *> $null
  Say "outside bash: $u exit $LASTEXITCODE"
}
Say "done"
