#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
LOCK_DIR=${TMPDIR:-/tmp}/gnustep-cli-native-tests.lock

. "$SCRIPT_DIR/activate-tools-xctest.sh"

# Legacy workflow tests use unsigned fixture manifests; opt them out of release
# signature verification. The dedicated signature tests unset this per-test.
export GNUSTEP_BOOTSTRAP_ALLOW_UNSIGNED=1

cd "$REPO_ROOT"

while ! mkdir "$LOCK_DIR" 2>/dev/null; do
  sleep 1
done
trap 'rm -rf "$LOCK_DIR" "$BUILD_LOG"' EXIT INT TERM

rm -rf src/full-cli/Tests/obj src/full-cli/Tests/FullCLITests.bundle
make -C src/full-cli/Tests clean >/dev/null || true
BUILD_LOG=$(mktemp)

# Capture make's own status: `make | tee` in POSIX sh reports tee's, which hid a
# failing test build and let CI pass with no tests run.
set +e
make -C src/full-cli/Tests \
  CC=clang \
  OBJC=clang \
  ADDITIONAL_OBJCFLAGS="-I$GCC_OBJC_HEADERS" \
  ADDITIONAL_LDFLAGS="-L$GCC_OBJC_LIBDIR" \
  > "$BUILD_LOG" 2>&1
build_status=$?
set -e
cat "$BUILD_LOG"
if [ "$build_status" -ne 0 ]; then
  printf '%s\n' "Native Objective-C test build failed (make exit $build_status)." >&2
  exit 1
fi

if grep -q "warning:" "$BUILD_LOG"; then
  printf '%s\n' "Native Objective-C test build emitted compiler warnings." >&2
  exit 1
fi

BUNDLE_PATH=$(find src/full-cli/Tests -name 'FullCLITests.bundle' -print | head -n 1)

if [ -z "$BUNDLE_PATH" ]; then
  printf '%s\n' "FullCLITests.bundle was not produced by the native test build." >&2
  exit 1
fi

TEST_LOG=$(mktemp)
trap 'rm -rf "$LOCK_DIR" "$BUILD_LOG" "$TEST_LOG"' EXIT INT TERM
set +e
xctest "$BUNDLE_PATH" > "$TEST_LOG" 2>&1
test_status=$?
set -e
cat "$TEST_LOG"
if [ "$test_status" -ne 0 ]; then
  exit "$test_status"
fi
# xctest exits 0 when it loads nothing; an empty run is a failure, not a pass.
if grep -q "No tests found" "$TEST_LOG" || ! grep -Eq "[1-9][0-9]* tests? executed" "$TEST_LOG"; then
  printf '%s\n' "xctest ran no tests from $BUNDLE_PATH." >&2
  exit 1
fi
