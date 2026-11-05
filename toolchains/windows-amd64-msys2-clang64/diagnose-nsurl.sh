#!/usr/bin/env bash
# Diagnose NSURLConnection on an assembled Windows toolchain: gdnc auto-start, plain
# HTTP and HTTPS, with and without a gdnc started by hand. Prints results; it does not
# judge them, so the same script can run against old and new toolchains.
# Usage (from the toolchain's own bash): diagnose-nsurl.sh <toolchain-root-in-unix-form>
set -u
root=${1:?usage: diagnose-nsurl.sh <toolchain-root>}
root=${root%/}
export PATH="$root/clang64/bin:$root/usr/bin:$PATH"
export GNUSTEP_MAKEFILES="$root/clang64/share/GNUstep/Makefiles"
work=$(mktemp -d)
cd "$work"
cat > fetch.m <<'EOF'
#import <Foundation/Foundation.h>
int main(int argc, char **argv)
{
  @autoreleasepool {
    NSURLRequest *r = [NSURLRequest requestWithURL: [NSURL URLWithString: [NSString stringWithUTF8String: argv[1]]]
                                       cachePolicy: NSURLRequestReloadIgnoringCacheData
                                   timeoutInterval: 30];
    NSURLResponse *response = nil;
    NSError *error = nil;
    NSData *d = nil;
    @try {
      d = [NSURLConnection sendSynchronousRequest: r returningResponse: &response error: &error];
    }
    @catch (NSException *e) {
      printf("%s exception %s: %s\n", argv[1], [[e name] UTF8String], [[e reason] UTF8String]);
      return 3;
    }
    printf("%s %s%s%s\n", argv[1], (d != nil && error == nil) ? "fetched" : "refused",
           error ? " - " : "", error ? [[error localizedDescription] UTF8String] : "");
    return (d != nil && error == nil) ? 0 : 1;
  }
}
EOF
cat > defaults.m <<'EOF'
#import <Foundation/Foundation.h>
int main(void)
{
  @autoreleasepool {
    @try {
      NSString *v = [[NSUserDefaults standardUserDefaults] stringForKey: @"GSTLSVerifyServer"];
      printf("defaults ok (%s)\n", v ? [v UTF8String] : "unset");
      [NSHTTPCookieStorage sharedHTTPCookieStorage];
      printf("cookie storage ok\n");
    }
    @catch (NSException *e) {
      printf("exception %s: %s\n", [[e name] UTF8String], [[e reason] UTF8String]);
      return 3;
    }
  }
  return 0;
}
EOF
flags=$(gnustep-config --objc-flags); libs=$(gnustep-config --base-libs)
# shellcheck disable=SC2086
clang $flags fetch.m -o fetch.exe $libs || { echo "compile failed"; exit 0; }
# shellcheck disable=SC2086
clang $flags defaults.m -o defaults.exe $libs || { echo "compile failed"; exit 0; }
echo "== gnustep-base: $(ls "$root"/clang64/bin/gnustep-base*.dll 2>/dev/null | xargs -n1 basename | tr '\n' ' ')"
echo "== pacman: $(pacman -Q mingw-w64-clang-x86_64-gnustep-base 2>/dev/null)"
run() { echo "-- $*"; timeout 60 "$@"; echo "   exit $?"; }
echo "== A. no gdnc running (library auto-starts it)"
run ./defaults.exe
run ./fetch.exe http://example.com
run ./fetch.exe https://github.com
echo "   gdnc processes after A: $(ps -W 2>/dev/null | grep -ci gdnc)"
echo "== B. gdnc --auto started by hand, as the library does"
gdnc --auto > gdnc-auto.log 2>&1 &
sleep 5
echo "   gdnc --auto still running: $(ps -W 2>/dev/null | grep -ci gdnc)"; head -5 gdnc-auto.log
echo "== C. gdnc --no-fork started by hand"
gdnc --no-fork > gdnc-nofork.log 2>&1 &
pid=$!
sleep 5
run ./defaults.exe
run ./fetch.exe http://example.com
run ./fetch.exe https://github.com
run ./fetch.exe https://expired.badssl.com
run env GS_TLS_VERIFY_S=NO ./fetch.exe https://self-signed.badssl.com
kill "$pid" 2>/dev/null
head -10 gdnc-nofork.log
if [ -n "${DIAG_GDB:-}" ] && command -v gdb >/dev/null; then
  echo "== D. backtraces under gdb"
  cat > gdb.cmds <<'GDB'
set pagination off
set confirm off
handle SIGSEGV stop print
run
bt 30
info sharedlibrary gnustep
quit
GDB
  timeout 120 gdb -q -batch -x gdb.cmds --args gdnc --auto 2>&1 | tail -45
  gdnc --no-fork > /dev/null 2>&1 &
  pid=$!
  sleep 5
  timeout 120 gdb -q -batch -x gdb.cmds --args ./fetch.exe https://github.com 2>&1 | tail -45
  timeout 60 ./fetch.exe https://expired.badssl.com; echo "   expired exit $?"
  kill "$pid" 2>/dev/null
  echo "-- gdnc --no-fork under gdb, then a client request"
  (sleep 8; timeout 60 ./fetch.exe http://example.com; timeout 60 ./fetch.exe https://github.com) &
  timeout 120 gdb -q -batch -x gdb.cmds --args gdnc --no-fork 2>&1 | tail -45
fi
exit 0
