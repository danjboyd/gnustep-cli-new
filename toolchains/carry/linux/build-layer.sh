#!/usr/bin/env bash
# Build and test the Linux patch layer for one target (docs/specs/patch-layer.md), inside
# that target's build image (toolchains/<target>/Dockerfile), as root.
#
# Usage: build-layer.sh <target> <staging-prefix> <stock-toolchain.tar.gz> <out-dir> <release>
#
# 1. The stock toolchain is unpacked twice: as shipped (the layer's stock reference) and at
#    the staging prefix it was built in, with its prefix placeholders filled in, so the
#    rebuild uses exactly the stock headers, libraries and GNUstep Make.
# 2. Each carried library base for this target (toolchains/carry/carry.json) is rebuilt
#    from its pin with its patches, the same way build-toolchain.sh builds it, and
#    installed into a DESTDIR.
# 3. carry_layer keeps the output files that differ from stock, checks the ABI (no
#    removed dynamic symbol) and writes the layer zip; it is checked against the archive.
# 4. The carried patches' own tests run on Xvfb, first against the stock root and then
#    against the same root with the layer applied. With the layer, every test must pass.
#    On stock, each libs-gui carry's regression test must fail (it shows the bug); the
#    libs-back X11 tests are only recorded there.
set -euo pipefail

target=${1:?usage: build-layer.sh <target> <staging-prefix> <toolchain.tar.gz> <out-dir> <release>}
prefix=${2:?}
tarball=${3:?}
out=${4:?}
release=${5:?}
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../../.." && pwd)
carry_json="$repo/toolchains/carry/carry.json"
work=/work/carry-layer
export PYTHONPATH="$repo/src"

apt-get update -qq
apt-get install -y -qq --no-install-recommends binutils xvfb xauth >/dev/null

rm -rf "$work" "$prefix"
mkdir -p "$work/stock" "$work/pkg" "$work/home" "$prefix" "$out"
tar -C "$work/stock" -xzf "$tarball"
tar -C "$prefix" -xzf "$tarball"
python3 -c 'import sys; from pathlib import Path; from gnustep_cli_shared.build_infra import _replace_managed_prefix_placeholders as r; print(len(r(Path(sys.argv[1]))), "files had the prefix placeholder")' "$prefix"
toolchain_sha256=$(sha256sum "$tarball" | cut -d' ' -f1)
echo "stock toolchain $(basename "$tarball") sha256 $toolchain_sha256"

# The build environment of build-toolchain.sh.
export CC=clang CXX=clang++ OBJC=clang OBJCXX=clang++
export PATH="$prefix/System/Tools:$prefix/bin:$PATH"
export LD_LIBRARY_PATH="$prefix/lib:$prefix/lib64:${LD_LIBRARY_PATH:-}"
export PKG_CONFIG_PATH="$prefix/lib/pkgconfig:$prefix/lib64/pkgconfig:${PKG_CONFIG_PATH:-}"
export CPPFLAGS="-I$prefix/include"
export CFLAGS="-g -O2 -I$prefix/include"
export CXXFLAGS="-I$prefix/include" OBJCFLAGS="-I$prefix/include" OBJCXXFLAGS="-I$prefix/include"
export LDFLAGS="-L$prefix/lib -L$prefix/lib64"
export HOME="$work/home"
set +u
# shellcheck disable=SC1091
. "$prefix/System/Library/Makefiles/GNUstep.sh"
set -u

# Each base for this target: library, pin (from the target's source lock) and patches.
python3 - "$carry_json" "$target" "$repo/toolchains/$target/source-lock.json" > "$work/bases.txt" <<'PY'
import json, sys
from pathlib import Path
from gnustep_cli_shared.carry_layer import bases_for, load_carry, patches_for
carry_json, target, lock = Path(sys.argv[1]), sys.argv[2], json.loads(Path(sys.argv[3]).read_text())
data = load_carry(carry_json)
revisions = {c["name"]: c["revision"] for c in lock["components"]}
for key in sorted(bases_for(data, target)):
    library, base = key.split("/", 1)
    patches = [str(carry_json.parent / p["path"]) for p in patches_for(data, library, base) if target in p["platforms"]]
    if not patches:
        continue
    pin = base.rsplit("-", 1)[-1]
    if not revisions[library].startswith(pin):
        raise SystemExit(f"{key}: the target pins {library} at {revisions[library]}, not {pin}")
    print(library, revisions[library], *patches)
PY
cat "$work/bases.txt"
test -s "$work/bases.txt" || { echo "no carried base for $target" >&2; exit 1; }

package_args=()
while read -r library revision patches; do
  echo "== $library at $revision"
  git clone -q "https://github.com/gnustep/$library.git" "$work/src/$library"
  git -C "$work/src/$library" checkout -q --detach "$revision"
  for patch in $patches; do
    echo "   apply $(basename "$patch")"
    git -C "$work/src/$library" apply -p1 "$patch"
  done
  (
    cd "$work/src/$library"
    ./configure --prefix="$prefix" > "$out/configure-$library.log" 2>&1
    make -j"$(nproc)" > "$out/make-$library.log" 2>&1
    make install DESTDIR="$work/pkg/$library" > "$out/install-$library.log" 2>&1
  ) || { tail -n 60 "$out"/*-"$library".log; exit 1; }
  # The packaged toolchain holds each library's .so, .so.<soname> and .so.<version> as
  # three copies, not symlinks (its packaging dereferences them), and programs load the
  # soname file. Turn the install's symlinks into copies too, so the layer replaces every
  # one of them.
  find "$work/pkg/$library" -type l | while read -r link; do
    if [ -f "$link" ]; then cp --remove-destination "$(readlink -f "$link")" "$link"; fi
  done
  package_args+=(--package-root "$work/pkg/$library$prefix")
done < "$work/bases.txt"

layer="$out/gnustep-carry-$target-$release.zip"
python3 -m gnustep_cli_shared.carry_layer build --carry-json "$carry_json" --stock-root "$work/stock" \
  "${package_args[@]}" --target "$target" --release "$release" --toolchain-sha256 "$toolchain_sha256" \
  --nm nm --out "$layer" | tee "$out/layer-build.txt"
python3 - "$layer" "$tarball" "$toolchain_sha256" <<'PY'
import sys
from pathlib import Path
from gnustep_cli_shared.carry_layer import verify_against_toolchain
errors = verify_against_toolchain(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3])
print("\n".join(errors) or "layer matches the stock toolchain archive")
raise SystemExit(1 if errors else 0)
PY

# The carried patches' tests, compiled once against the stock headers.
testing_h=$(find "$GNUSTEP_MAKEFILES" -name Testing.h -path '*TestFramework*' | head -n 1)
test -n "$testing_h" || { echo "no TestFramework/Testing.h under $GNUSTEP_MAKEFILES" >&2; exit 1; }
# Each entry: <source path>|<stock expectation>. "fail": the test shows the bug on the
# stock root (a libs-gui carry's own regression test). "record": the stock result is only
# reported (the libs-back X11 tests cover new behaviour; some parts may pass on stock).
# Every test must pass with the layer applied.
tests=()
if [ -d "$work/src/libs-gui" ]; then
  tests+=("libs-gui/Tests/gui/GSTheme/liveSwitch.m|fail" "libs-gui/Tests/gui/NSInputManager/commandBindings.m|fail")
fi
if [ -d "$work/src/libs-back" ]; then
  for t in "$work"/src/libs-back/Tests/x11/*.m; do
    tests+=("libs-back/Tests/x11/$(basename "$t")|record")
  done
fi
mkdir -p "$work/tests"
for entry in "${tests[@]}"; do
  t=${entry%%|*}
  name=$(basename "$t" .m)
  extra=()
  case "$t" in
    libs-back/*) extra=(-I"$work/src/libs-back" -I"$work/src/libs-back/Tests/x11" -lX11 -lXrender -lXext) ;;
  esac
  # shellcheck disable=SC2046
  clang $(gnustep-config --objc-flags) -I"$(dirname "$testing_h")" -o "$work/tests/$name" "$work/src/$t" \
    $(gnustep-config --gui-libs) "${extra[@]}"
done

run_tests() { # <stock|layer>
  local phase=$1 status=0
  for entry in "${tests[@]}"; do
    local t=${entry%%|*} stock_expect=${entry##*|} name log code passed failed skipped other
    name=$(basename "$t" .m)
    log="$out/test-$name-$phase.txt"
    set +e
    (cd "$work/tests" && timeout 180 xvfb-run -a -s "-screen 0 1280x1024x24" "./$name") > "$log" 2>&1
    code=$?
    set -e
    passed=$(grep -c '^Passed test' "$log" || true)
    failed=$(grep -c -E '^(Failed test|Dashed hope)' "$log" || true)
    skipped=$(grep -c '^Skipped set' "$log" || true)
    other=$(grep -c -E '^Failed set|Uncaught' "$log" || true)
    echo "$name ($phase): exit $code, passed $passed, failed $failed, skipped sets $skipped, other $other"
    if [ "$phase" = layer ]; then
      # A libs-back set that needs a real desktop (GNOME Shell) may skip on Xvfb; a
      # libs-gui carry's test must run in full.
      if [ "$code" -ne 0 ] || [ "$passed" -eq 0 ] || [ "$failed" -ne 0 ] || [ "$other" -ne 0 ] \
         || { [ "$stock_expect" = fail ] && [ "$skipped" -ne 0 ]; }; then
        cat "$log"; status=1
      fi
    elif [ "$stock_expect" = fail ] && [ "$failed" -eq 0 ] && [ "$code" -eq 0 ]; then
      echo "$name: expected the stock root to fail (the bug the patch fixes)"; cat "$log"; status=1
    fi
  done
  return $status
}

echo "== stock root: each libs-gui carry's test must show its bug; the libs-back tests are recorded"
run_tests stock
echo "== stock root with the layer applied: every test must pass"
(cd "$prefix" && python3 -c 'import sys, zipfile; z = zipfile.ZipFile(sys.argv[1]); [z.extract(n) for n in z.namelist() if n != "carry-layer.json"]' "$layer")
run_tests layer
sha256sum "$layer" | tee "$out/SHA256SUMS"
echo "linux patch layer for $target: ok"
