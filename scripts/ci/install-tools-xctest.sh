#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
TOOLS_XCTEST_DIR=${TOOLS_XCTEST_DIR:-"$REPO_ROOT/.ci/tools-xctest"}
GNUSTEP_MAKEFILES_DIR=${GNUSTEP_MAKEFILES_DIR:-/usr/share/GNUstep/Makefiles}
TOOLS_XCTEST_REPO=${TOOLS_XCTEST_REPO:-https://github.com/gnustep/tools-xctest.git}
# Pinned to upstream tag v0.1.1 for the CI test runner. This intentionally differs
# from packages/org.gnustep.tools-xctest, which may track a newer upstream commit:
# upstream after v0.1.1 (for example 5c84fc3) requires blocks, which the distro
# GCC-flavored GNUstep on the CI runners does not enable, so tracking it broke CI.
TOOLS_XCTEST_REVISION=${TOOLS_XCTEST_REVISION:-2aac3e5fc65586bda718aaca7d36b5c33b5ec2e3}

if [ ! -f "$GNUSTEP_MAKEFILES_DIR/GNUstep.sh" ]; then
  printf '%s\n' "GNUstep.sh was not found at $GNUSTEP_MAKEFILES_DIR/GNUstep.sh" >&2
  exit 1
fi

mkdir -p "$(dirname "$TOOLS_XCTEST_DIR")"

if [ ! -d "$TOOLS_XCTEST_DIR/.git" ]; then
  git init -q "$TOOLS_XCTEST_DIR"
  git -C "$TOOLS_XCTEST_DIR" remote add origin "$TOOLS_XCTEST_REPO"
fi
git -C "$TOOLS_XCTEST_DIR" fetch --depth 1 origin "$TOOLS_XCTEST_REVISION"
git -C "$TOOLS_XCTEST_DIR" reset --hard FETCH_HEAD

set +u
. "$GNUSTEP_MAKEFILES_DIR/GNUstep.sh"
set -u

if [ -z "${GCC_OBJC_HEADERS:-}" ]; then
  GCC_OBJC_HEADERS=$(find /usr/lib/gcc -path '*/include/objc/objc.h' -print 2>/dev/null | sort -V | tail -n 1 | sed 's,/objc/objc\.h$,,')
fi
if [ -z "${GCC_OBJC_HEADERS:-}" ] || [ ! -f "$GCC_OBJC_HEADERS/objc/objc.h" ]; then
  printf '%s\n' "objc/objc.h was not found under /usr/lib/gcc; install the libobjc development headers." >&2
  exit 1
fi
if [ -z "${GCC_OBJC_LIBDIR:-}" ]; then
  GCC_OBJC_LIBDIR=$(find /usr/lib/gcc -name libobjc.so -print 2>/dev/null | sort -V | tail -n 1 | sed 's,/libobjc\.so$,,')
fi
if [ -z "${GCC_OBJC_LIBDIR:-}" ] || [ ! -f "$GCC_OBJC_LIBDIR/libobjc.so" ]; then
  printf '%s\n' "libobjc.so was not found under /usr/lib/gcc; install the libobjc development library." >&2
  exit 1
fi

make -C "$TOOLS_XCTEST_DIR" clean >/dev/null || true
make -C "$TOOLS_XCTEST_DIR" \
  CC=clang \
  OBJC=clang \
  ADDITIONAL_OBJCFLAGS="-I$GCC_OBJC_HEADERS" \
  ADDITIONAL_LDFLAGS="-L$GCC_OBJC_LIBDIR"
make -C "$TOOLS_XCTEST_DIR" \
  CC=clang \
  OBJC=clang \
  ADDITIONAL_OBJCFLAGS="-I$GCC_OBJC_HEADERS" \
  ADDITIONAL_LDFLAGS="-L$GCC_OBJC_LIBDIR" \
  GNUSTEP_INSTALLATION_DOMAIN=USER \
  install

printf '%s\n' "tools-xctest installed to $HOME/GNUstep"
