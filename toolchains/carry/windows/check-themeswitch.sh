#!/usr/bin/env bash
# WinUITheme's ThemeSwitch harness (themeswitch/main.m, from the winuitheme agent): live
# theme switches with a window of controls open, against real theme bundles, on one
# toolchain root. It complements check-theme-live-switch.sh (libs-gui's own unit test)
# with the themes users run.
#
# Usage (from an MSYS2 bash):
#   check-themeswitch.sh <root-in-unix-form> <pass|fail|record> <out-dir> <theme-src-dir>
# <theme-src-dir> holds checkouts named winuitheme, adwaita and, if available, funthemes
# (Gumdrop lives in its Themes/Gumdrop).
#
# Each case runs as its own process with a fresh private home (GNUSTEP_HOME plus
# HOMEDRIVE/HOMEPATH and HOME) and a 120 s timeout. A case passes on exit 0 with "OK" as the
# last line of its output.
#   pass:   every case must pass (the patched root).
#   fail:   W-G must fail with a crash, not a load failure or a timeout (the stock root,
#           which overflows the stack on the first WinUITheme<->Gumdrop switch). Needs Gumdrop.
#   record: report only.
# Writes <out-dir>/summary.txt and one <case>.txt per case.
set -uo pipefail

root=${1:?usage: check-themeswitch.sh <root> <pass|fail|record> <out-dir> <theme-src-dir>}
expect=${2:?}
out=${3:?}
src=${4:?}
root=${root%/}
here=$(cd "$(dirname "$0")" && pwd)
export PATH="$root/clang64/bin:$root/usr/bin:$PATH"
export GNUSTEP_MAKEFILES="$root/clang64/share/GNUstep/Makefiles"
mkdir -p "$out"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
summary="$out/summary.txt"
: > "$summary"
log() { echo "$*" | tee -a "$summary"; }

log "root: $root ($expect expected)"
for f in clang64/bin/gnustep-gui-0.dll clang64/bin/gnustep-base-1_31.dll; do
  log "  $f sha256 $(sha256sum "$root/$f" | cut -c1-16)"
done

build() { # name dir
  local name=$1 dir=$2
  ( cd "$dir" && make -j"$(nproc)" messages=yes ) > "$out/build-$name.txt" 2>&1
  local code=$?
  if [ $code -ne 0 ]; then
    tail -n 40 "$out/build-$name.txt"
    log "build $name: FAILED ($code)"
    exit 1
  fi
  log "build $name: ok"
}

# Build every theme and the harness against this root, in a scratch copy of the sources.
cp -r "$here/themeswitch" "$work/harness"
build ThemeSwitch "$work/harness"
exe="$work/harness/obj/ThemeSwitch.exe"
test -f "$exe" || { log "no ThemeSwitch.exe"; exit 1; }

cp -r "$src/winuitheme" "$work/winuitheme"
build WinUITheme "$work/winuitheme"
W="$work/winuitheme/WinUITheme.theme"
cp -r "$src/adwaita" "$work/adwaita"
build Adwaita "$work/adwaita"
A="$work/adwaita/Adwaita.theme"
G=""
if [ -d "$src/funthemes/Themes/Gumdrop" ]; then
  cp -r "$src/funthemes" "$work/funthemes"
  build Gumdrop "$work/funthemes/Themes/Gumdrop"
  G="$work/funthemes/Themes/Gumdrop/Gumdrop.theme"
fi
for t in "$W" "$A" ${G:+"$G"}; do
  test -d "$t" || { log "missing theme bundle $t"; exit 1; }
done
# Pass Windows paths: NSBundle on Windows resolves those, not MSYS ones.
W=$(cygpath -m "$W"); A=$(cygpath -m "$A")
[ -n "$G" ] && G=$(cygpath -m "$G")

declare -a names args
add() { names+=("$1"); args+=("$2"); }
if [ -n "$G" ]; then
  add W-G "-cycles 10 $W $G"
  add G-W "-cycles 10 $G $W"
  add W-default "-cycles 10 $W GNUstep"
  add pre-G "-preload -cycles 10 $G"
  add all4 "-cycles 20 $W $G $A GNUstep"
else
  log "Gumdrop not available: running the WinUITheme/Adwaita substitutes instead"
  add W-default "-cycles 10 $W GNUstep"
  add W-A "-cycles 10 $W $A"
  add A-W "-cycles 10 $A $W"
  add pre-A "-preload -cycles 10 $A"
  add all3 "-cycles 20 $W $A GNUstep"
  if [ "$expect" = fail ]; then
    log "the stock expectation needs Gumdrop; recording only"
    expect=record
  fi
fi

failures=0
wg_result=""
for i in "${!names[@]}"; do
  name=${names[$i]}
  home="$work/home-$name"
  mkdir -p "$home"
  winhome=$(cygpath -w "$home")
  # shellcheck disable=SC2086
  (
    export HOME="$home" GNUSTEP_HOME="$winhome" HOMEDRIVE="${winhome:0:2}" HOMEPATH="${winhome:2}"
    if command -v gspath > /dev/null 2>&1; then
      echo "gspath defaults: $(gspath defaults 2>&1)"
    fi
    timeout 120 "$exe" ${args[$i]}
  ) > "$out/$name.txt" 2>&1
  code=$?
  last=$(tr -d '\r' < "$out/$name.txt" | grep -v '^\s*$' | tail -n 1)
  if [ $code -eq 0 ] && [ "$last" = OK ]; then
    result=pass
  elif [ $code -eq 124 ]; then
    result=timeout
  elif [ $code -eq 2 ]; then
    result=load-failure
  else
    result=crash
  fi
  growth=$(grep -o 'growth after warm-up.*' "$out/$name.txt" | tr -d '\r' || true)
  slow=$(grep -o 'slowest switch [0-9]* ms' "$out/$name.txt" | tr -d '\r' || true)
  log "case $name: $result (exit $code) ${growth:+; $growth}${slow:+; $slow}"
  [ "$name" = W-G ] && wg_result=$result
  [ "$result" = pass ] || failures=$((failures + 1))
done

case "$expect" in
  pass)
    if [ $failures -ne 0 ]; then log "themeswitch: expected every case to pass, $failures did not"; exit 1; fi ;;
  fail)
    if [ "$wg_result" != crash ]; then log "themeswitch: expected W-G to crash on this root, got $wg_result"; exit 1; fi ;;
esac
log "themeswitch ($expect expected): ok, $failures of ${#names[@]} cases did not pass"
