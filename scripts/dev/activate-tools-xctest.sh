#!/usr/bin/env sh
set -eu

GNUSTEP_MAKEFILES_DIR=${GNUSTEP_MAKEFILES_DIR:-/usr/share/GNUstep/Makefiles}
USER_GNUSTEP_ROOT=${USER_GNUSTEP_ROOT:-"$HOME/GNUstep"}
GCC_OBJC_HEADERS=${GCC_OBJC_HEADERS:-/usr/lib/gcc/x86_64-linux-gnu/14/include}

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
