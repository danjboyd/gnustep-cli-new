#!/usr/bin/env sh
set -eu

# Distro packages install GNUstep under /usr/share; a source-built libobjc2 GNUstep
# is usually under /usr/GNUstep.
if [ -z "${GNUSTEP_MAKEFILES_DIR:-}" ]; then
  for candidate in /usr/share/GNUstep/Makefiles /usr/GNUstep/System/Library/Makefiles; do
    if [ -f "$candidate/GNUstep.sh" ]; then
      GNUSTEP_MAKEFILES_DIR=$candidate
      break
    fi
  done
fi
GNUSTEP_MAKEFILES_DIR=${GNUSTEP_MAKEFILES_DIR:-/usr/share/GNUstep/Makefiles}
export GNUSTEP_MAKEFILES_DIR
USER_GNUSTEP_ROOT=${USER_GNUSTEP_ROOT:-"$HOME/GNUstep"}

if [ ! -f "$GNUSTEP_MAKEFILES_DIR/GNUstep.sh" ]; then
  printf '%s\n' "GNUstep.sh was not found at $GNUSTEP_MAKEFILES_DIR/GNUstep.sh" >&2
  exit 1
fi

set +u
. "$GNUSTEP_MAKEFILES_DIR/GNUstep.sh"
set -u

export PATH="$USER_GNUSTEP_ROOT/Tools:$PATH"
export LD_LIBRARY_PATH="$USER_GNUSTEP_ROOT/Library/Libraries:${LD_LIBRARY_PATH:-}"

# A GNUstep built on GCC's runtime takes objc/objc.h and libobjc.so from GCC's own
# version directory, which clang doesn't search (ubuntu-24.04: 13, Debian 13: 14).
# A libobjc2 GNUstep finds its own; adding GCC's there would load two Objective-C
# runtimes into one process and crash. So use GCC's only when clang needs them.
# Setting GCC_OBJC_HEADERS or GCC_OBJC_LIBDIR overrides the probe.
if [ -z "${GCC_OBJC_HEADERS:-}" ] && [ -z "${GCC_OBJC_LIBDIR:-}" ] && \
   ! printf '#include <objc/objc.h>\n' | clang $(gnustep-config --objc-flags 2>/dev/null) -E -x objective-c - >/dev/null 2>&1; then
  GCC_OBJC_HEADERS=$(ls -d /usr/lib/gcc/*/*/include/objc 2>/dev/null | sort -V | tail -n 1 | sed 's|/objc$||')
  GCC_OBJC_LIBDIR=$(find /usr/lib/gcc -name libobjc.so -print 2>/dev/null | sort -V | tail -n 1 | sed 's,/libobjc\.so$,,')
  if [ -z "$GCC_OBJC_HEADERS" ] || [ ! -f "$GCC_OBJC_HEADERS/objc/objc.h" ]; then
    printf '%s\n' "No Objective-C runtime headers (objc/objc.h) found; set GCC_OBJC_HEADERS." >&2
    exit 1
  fi
  if [ -z "$GCC_OBJC_LIBDIR" ] || [ ! -f "$GCC_OBJC_LIBDIR/libobjc.so" ]; then
    printf '%s\n' "libobjc.so was not found under /usr/lib/gcc; set GCC_OBJC_LIBDIR." >&2
    exit 1
  fi
fi
GCC_OBJC_HEADERS=${GCC_OBJC_HEADERS:-}
GCC_OBJC_LIBDIR=${GCC_OBJC_LIBDIR:-}
export GCC_OBJC_HEADERS GCC_OBJC_LIBDIR
if [ -n "$GCC_OBJC_HEADERS" ]; then
  export OBJCFLAGS="-I$GCC_OBJC_HEADERS ${OBJCFLAGS:-}"
  export CPPFLAGS="-I$GCC_OBJC_HEADERS ${CPPFLAGS:-}"
fi

printf '%s\n' "Activated GNUstep + tools-xctest development environment."
printf '%s\n' "xctest: $(command -v xctest || printf 'not found')"
printf '%s\n' "GCC Objective-C headers: ${GCC_OBJC_HEADERS:-none needed}"
printf '%s\n' "GCC libobjc: ${GCC_OBJC_LIBDIR:-none needed}"
