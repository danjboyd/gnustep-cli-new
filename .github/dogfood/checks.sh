#!/usr/bin/env bash
# tools-xctest dogfood checks, run in the managed toolchain's shell after
# `gnustep install org.gnustep.tools-xctest` (Linux, and MSYS2 bash on Windows).
# Usage: checks.sh <managed-root> <makefiles-dir> <sample-dir> <out-dir> <xctest-for-explicit-run>
set -u
root=${1%/}; makefiles=$2; sample=$3; out=$4; xctest_explicit=$5
log=$out/checks.txt
say() { printf '%s\n' "$*" | tee -a "$log"; }
run() { name=$1; shift; "$@" > "$out/$name.txt" 2>&1; rc=$?; say "$name exit $rc"; return $rc; }
# GNUstep.sh reads variables that may be unset (ZSH_VERSION, ...).
set +u
. "$makefiles/GNUstep.sh"
set -u
say "GNUSTEP_MAKEFILES=$GNUSTEP_MAKEFILES"
pkg=$root/packages/org.gnustep.tools-xctest
inc=$GNUSTEP_MAKEFILES/Auxiliary/xctest.make
if [ -f "$inc" ]; then say "include present: $(tail -n 1 "$inc")"; else say "include missing: $inc"; fi
cd "$sample"
run make-check make check
grep -E "tests? (PASSED|FAILED)|Executed" "$out/make-check.txt" | tee -a "$log"
make clean > /dev/null 2>&1
run make-check-explicit make check XCTEST="$xctest_explicit"
grep -E "tests? (PASSED|FAILED)|Executed" "$out/make-check-explicit.txt" | tee -a "$log"
make clean > /dev/null 2>&1
run make-check-failing make check ADDITIONAL_OBJCFLAGS=-DSAMPLE_FAIL
grep -E "tests? (PASSED|FAILED)|testDeliberateFailure" "$out/make-check-failing.txt" | head -n 5 | tee -a "$log"
make clean > /dev/null 2>&1
# xctest-bundle: wrap a plain shared library of tests (what Meson users do).
case "$(uname -s)" in
  MINGW*|MSYS*) lib=SampleTests.dll ;;
  *) lib=libSampleTests.so ;;
esac
run shared-library sh -c "clang -shared -fPIC \$(gnustep-config --objc-flags) -I'$pkg/Library/Headers' SampleTests.m -o $lib -L'$pkg/Library/Libraries' -lXCTest \$(gnustep-config --base-libs)"
run xctest-bundle "$pkg/bin/xctest-bundle" Wrapped.xctest "$lib" && run xctest-bundle-run "$xctest_explicit" Wrapped.xctest
grep -E "tests? (PASSED|FAILED)" "$out/xctest-bundle-run.txt" 2>/dev/null | tee -a "$log"
say "checks done"
