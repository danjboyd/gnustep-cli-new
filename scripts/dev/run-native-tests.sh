#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
LOCK_DIR=${TMPDIR:-/tmp}/gnustep-cli-native-tests.lock

. "$SCRIPT_DIR/activate-tools-xctest.sh"

cd "$REPO_ROOT"

while ! mkdir "$LOCK_DIR" 2>/dev/null; do
  sleep 1
done
trap 'rm -rf "$LOCK_DIR" "$BUILD_LOG"' EXIT INT TERM

rm -rf src/full-cli/Tests/obj src/full-cli/Tests/FullCLITests.bundle
make -C src/full-cli/Tests clean >/dev/null || true
BUILD_LOG=$(mktemp)

make -C src/full-cli/Tests \
  CC=clang \
  OBJC=clang \
  ADDITIONAL_OBJCFLAGS="-I/usr/lib/gcc/x86_64-linux-gnu/14/include" \
  2>&1 | tee "$BUILD_LOG"

if grep -q "warning:" "$BUILD_LOG"; then
  printf '%s\n' "Native Objective-C test build emitted compiler warnings." >&2
  exit 1
fi

BUNDLE_PATH=$(find src/full-cli/Tests -name 'FullCLITests.bundle' -print | head -n 1)

if [ -z "$BUNDLE_PATH" ]; then
  printf '%s\n' "FullCLITests.bundle was not produced by the native test build." >&2
  exit 1
fi

xctest "$BUNDLE_PATH"
