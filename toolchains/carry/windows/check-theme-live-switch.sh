#!/usr/bin/env bash
# Run libs-gui's GSTheme live-switch regression test (Tests/gui/GSTheme/liveSwitch.m, added
# by the carried patch libs-gui/msys2-0.32.0/0004) against a toolchain root.
# Usage (from an MSYS2 bash): check-theme-live-switch.sh <root-in-unix-form> <pass|fail>
# The test switches between two themes overriding the same method, in both directions,
# and between a theme overriding an inherited method and back; a chaining loop is caught
# by a depth guard and reported as a failed test instead of a stack overflow.
# "pass": every test passes (the patched root). "fail": at least one fails (the stock
# root, which has the bug); this only shows the test detects it.
set -euo pipefail

root=${1:?usage: check-theme-live-switch.sh <root> <pass|fail>}
expect=${2:?usage: check-theme-live-switch.sh <root> <pass|fail>}
root=${root%/}
here=$(cd "$(dirname "$0")" && pwd)
patch_file="$here/../libs-gui/msys2-0.32.0/0004-GSTheme-capture-override-originals-at-activation.patch"
export PATH="$root/clang64/bin:$root/usr/bin:$PATH"
export GNUSTEP_MAKEFILES="$root/clang64/share/GNUstep/Makefiles"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# The new file's lines, from its "+++ b/" header to the end of its hunk.
awk '
  /^\+\+\+ b\/Tests\/gui\/GSTheme\/liveSwitch\.m/ { f = 1; next }
  f && /^@@/ { next }
  f && /^(diff --git|-- $)/ { exit }
  f { sub(/^\+/, ""); print }
' "$patch_file" | tr -d '\r' > "$work/liveSwitch.m"
test -s "$work/liveSwitch.m"

testing_h=$(find "$GNUSTEP_MAKEFILES" -name Testing.h -path '*TestFramework*' | head -n 1)
test -n "$testing_h" || { echo "no TestFramework/Testing.h under $GNUSTEP_MAKEFILES" >&2; exit 1; }

cd "$work"
objc_flags=$(gnustep-config --objc-flags)
gui_libs=$(gnustep-config --gui-libs)
# shellcheck disable=SC2086
clang $objc_flags -DHAVE_MODE_T=1 -I"$(dirname "$testing_h")" -o liveSwitch.exe liveSwitch.m $gui_libs
set +e
./liveSwitch.exe > out.txt 2>&1
code=$?
set -e
cat out.txt
passed=$(grep -c '^Passed test' out.txt || true)
failed=$(grep -c -E '^(Failed test|Dashed hope)' out.txt || true)
skipped=$(grep -c -E '^(Skipped set|Failed set)|Uncaught' out.txt || true)
echo "theme live switch: exit $code, passed $passed, failed $failed, other $skipped"
if [ "$expect" = pass ]; then
  if [ "$code" -ne 0 ] || [ "$passed" -eq 0 ] || [ "$failed" -ne 0 ] || [ "$skipped" -ne 0 ]; then
    echo "theme live switch: expected every test to pass" >&2; exit 1
  fi
else
  if [ "$failed" -eq 0 ] && [ "$code" -eq 0 ]; then
    echo "theme live switch: expected the stock root to fail the test" >&2; exit 1
  fi
fi
echo "theme live switch ($expect expected): ok"
