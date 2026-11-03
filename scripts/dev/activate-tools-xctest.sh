#!/usr/bin/env sh
set -eu

GNUSTEP_MAKEFILES_DIR=${GNUSTEP_MAKEFILES_DIR:-/usr/share/GNUstep/Makefiles}
USER_GNUSTEP_ROOT=${USER_GNUSTEP_ROOT:-"$HOME/GNUstep"}
# GNUstep packages built with GCC take the Objective-C runtime headers from GCC's
# own include directory, whose version differs by distro release (ubuntu-24.04:
# 13, Debian 13: 14). Use the newest one that has objc/objc.h.
if [ -z "${GCC_OBJC_HEADERS:-}" ]; then
  GCC_OBJC_HEADERS=$(ls -d /usr/lib/gcc/*/*/include/objc 2>/dev/null | sort -V | tail -n 1 | sed 's|/objc$||')
fi
if [ -z "${GCC_OBJC_HEADERS:-}" ] || [ ! -f "$GCC_OBJC_HEADERS/objc/objc.h" ]; then
  printf '%s\n' "No GCC Objective-C runtime headers (objc/objc.h) found; set GCC_OBJC_HEADERS." >&2
  exit 1
fi
export GCC_OBJC_HEADERS
# clang does not search GCC's version directory, where libobjc.so lives.
if [ -z "${GCC_OBJC_LIBDIR:-}" ]; then
  GCC_OBJC_LIBDIR=$(find /usr/lib/gcc -name libobjc.so -print 2>/dev/null | sort -V | tail -n 1 | sed 's,/libobjc\.so$,,')
fi
if [ -z "${GCC_OBJC_LIBDIR:-}" ] || [ ! -f "$GCC_OBJC_LIBDIR/libobjc.so" ]; then
  printf '%s\n' "libobjc.so was not found under /usr/lib/gcc; set GCC_OBJC_LIBDIR." >&2
  exit 1
fi
export GCC_OBJC_LIBDIR

if [ ! -f "$GNUSTEP_MAKEFILES_DIR/GNUstep.sh" ]; then
  printf '%s\n' "GNUstep.sh was not found at $GNUSTEP_MAKEFILES_DIR/GNUstep.sh" >&2
  exit 1
fi

set +u
. "$GNUSTEP_MAKEFILES_DIR/GNUstep.sh"
set -u

export PATH="$USER_GNUSTEP_ROOT/Tools:$PATH"
export LD_LIBRARY_PATH="$USER_GNUSTEP_ROOT/Library/Libraries:${LD_LIBRARY_PATH:-}"
export OBJCFLAGS="-I$GCC_OBJC_HEADERS ${OBJCFLAGS:-}"
export CPPFLAGS="-I$GCC_OBJC_HEADERS ${CPPFLAGS:-}"

printf '%s\n' "Activated GNUstep + tools-xctest development environment."
printf '%s\n' "xctest: $(command -v xctest || printf 'not found')"
printf '%s\n' "GCC Objective-C headers: $GCC_OBJC_HEADERS"
printf '%s\n' "GCC libobjc: $GCC_OBJC_LIBDIR"
