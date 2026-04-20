#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
TOOLS_XCTEST_DIR=${TOOLS_XCTEST_DIR:-"$REPO_ROOT/.ci/tools-xctest"}
GNUSTEP_MAKEFILES_DIR=${GNUSTEP_MAKEFILES_DIR:-/usr/share/GNUstep/Makefiles}
GCC_OBJC_HEADERS=${GCC_OBJC_HEADERS:-/usr/lib/gcc/x86_64-linux-gnu/14/include}
TOOLS_XCTEST_REPO=${TOOLS_XCTEST_REPO:-https://github.com/gnustep/tools-xctest.git}

if [ ! -f "$GNUSTEP_MAKEFILES_DIR/GNUstep.sh" ]; then
  printf '%s\n' "GNUstep.sh was not found at $GNUSTEP_MAKEFILES_DIR/GNUstep.sh" >&2
  exit 1
fi

mkdir -p "$(dirname "$TOOLS_XCTEST_DIR")"

if [ ! -d "$TOOLS_XCTEST_DIR/.git" ]; then
  git clone --depth 1 "$TOOLS_XCTEST_REPO" "$TOOLS_XCTEST_DIR"
else
  git -C "$TOOLS_XCTEST_DIR" fetch --depth 1 origin HEAD
  git -C "$TOOLS_XCTEST_DIR" reset --hard FETCH_HEAD
fi

set +u
. "$GNUSTEP_MAKEFILES_DIR/GNUstep.sh"
set -u

make -C "$TOOLS_XCTEST_DIR" clean >/dev/null || true
make -C "$TOOLS_XCTEST_DIR" \
  CC=clang \
  OBJC=clang \
  ADDITIONAL_OBJCFLAGS="-I$GCC_OBJC_HEADERS"
make -C "$TOOLS_XCTEST_DIR" \
  CC=clang \
  OBJC=clang \
  ADDITIONAL_OBJCFLAGS="-I$GCC_OBJC_HEADERS" \
  GNUSTEP_INSTALLATION_DOMAIN=USER \
  install

printf '%s\n' "tools-xctest installed to $HOME/GNUstep"
