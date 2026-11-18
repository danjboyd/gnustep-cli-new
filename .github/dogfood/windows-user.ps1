# Runs as the standard user: install tools-xctest from the signed dogfood index,
# run checks.sh in the toolchain's own bash, then remove it.
$ErrorActionPreference = 'Continue'
$g = 'C:\dogfood'; $out = "$g\out"; $root = "$g\root"
function Say($s) { Add-Content -Path "$out\dogfood.txt" -Value $s -Encoding utf8; Write-Output $s }
Say "elevated: $(([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))"
$env:RELEASE_TRUST_ROOT = "$g\index\qualification-signing-public.pem"
$gnustep = Join-Path $root 'bin\gnustep.exe'
& $gnustep install --json --root $root org.gnustep.tools-xctest *> "$out\install.txt"
Say "install exit $LASTEXITCODE"
Say "include file: $(Test-Path "$root\clang64\share\GNUstep\Makefiles\Auxiliary\xctest.make")"
& "$root\bin\xctest.cmd" --help *> "$out\xctest-help.txt"
Say "xctest.cmd --help exit $LASTEXITCODE"
$env:CHERE_INVOKING = '1'
$cygpath = Join-Path $root 'usr\bin\cygpath.exe'
$u = { param($p) (& $cygpath -u $p | Out-String).Trim() }
# In the toolchain's own bash the root is "/"; drop it so paths aren't "//..." (a UNC path).
$rootu = (& $u $root).TrimEnd('/')
$env:PATH = "$root\clang64\bin;$root\usr\bin;$env:PATH"
& (Join-Path $root 'usr\bin\bash.exe') -lc "bash '$(& $u "$g\checks.sh")' '$rootu' '$rootu/clang64/share/GNUstep/Makefiles' '$(& $u "$g\sample")' '$(& $u $out)' '$rootu/packages/org.gnustep.tools-xctest/libexec/xctest.exe'" *> "$out\checks-console.txt"
Say "checks.sh exit $LASTEXITCODE"
& $gnustep remove --json --root $root org.gnustep.tools-xctest *> "$out\remove.txt"
Say "remove exit $LASTEXITCODE"
$left = @("$root\packages\org.gnustep.tools-xctest", "$root\clang64\share\GNUstep\Makefiles\Auxiliary\xctest.make", "$root\bin\xctest.cmd", "$root\bin\xctest-bundle.cmd") | Where-Object { Test-Path $_ }
Say "left after remove: $(if ($left) { $left -join ' ' } else { 'none' })"
Say "done"
exit 0
