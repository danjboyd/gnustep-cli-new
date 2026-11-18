#!/usr/bin/env bash
# Smoke-test a Windows toolchain root with the patch layer applied.
# Usage (from an MSYS2 bash): smoke-layer.sh <patched-root-in-unix-form>
# - an AppKit program builds against the patched root and starts the GUI: the patched
#   gnustep-gui and gnustep-back load, and the display server is the win32 backend's;
# - the backend's carried defaults are read without changing a stock app: with none of
#   them set, the program behaves as with stock (it just starts and exits).
# The full toolchain smoke (smoke-toolchain.sh) runs on the same root first.
set -euo pipefail

root=${1:?usage: smoke-layer.sh <patched-root>}
root=${root%/}
export PATH="$root/clang64/bin:$root/usr/bin:$PATH"
export GNUSTEP_MAKEFILES="$root/clang64/share/GNUstep/Makefiles"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"

cat > layer-smoke.m <<'EOF'
#import <AppKit/AppKit.h>
#import <GNUstepGUI/GSDisplayServer.h>
#include <stdio.h>

int main(int argc, char **argv)
{
  @autoreleasepool
    {
      [NSApplication sharedApplication];
      GSDisplayServer *server = GSCurrentServer();
      printf("display server: %s\n", server ? [NSStringFromClass([server class]) UTF8String] : "(none)");
      return (server != nil && [NSStringFromClass([server class]) isEqualToString: @"WIN32Server"]) ? 0 : 1;
    }
}
EOF

objc_flags=$(gnustep-config --objc-flags)
gui_libs=$(gnustep-config --gui-libs)
# shellcheck disable=SC2086
clang $objc_flags -DHAVE_MODE_T=1 -o layer-smoke.exe layer-smoke.m $gui_libs
./layer-smoke.exe
echo "layer smoke: ok"
