#!/usr/bin/env bash
# Smoke-test an assembled Windows MSYS2 clang64 toolchain.
# Usage (from the toolchain's own bash): smoke-toolchain.sh <toolchain-root-in-unix-form>
# Each check guards a defect that shipped or nearly shipped:
# - Foundation.h with the toolchain's own flags (libdispatch mode_t clash)
# - <pthread.h> with Foundation in one translation unit (pthread_attr_t clash)
# - clang 23 compiling gnustep-base headers (gnustep/libs-base#807)
# - python's pyexpat loading its libexpat (xml.etree)
# - curl with TLS and asynchronous DNS
# - MSYS perl, which v0.1.1 dropped (Arlen's test helpers use it)
# - strict TLS host verification in gnustep-base (good site loads, bad ones refused);
#   set GNUSTEP_SMOKE_TLS_EXE to keep the test program for a run outside this bash
set -euo pipefail

root=${1:?usage: smoke-toolchain.sh <toolchain-root>}
# Run from the toolchain's own bash, the root is "/"; avoid "//" (a UNC path).
root=${root%/}
export PATH="$root/clang64/bin:$root/usr/bin:$PATH"
export GNUSTEP_MAKEFILES="$root/clang64/share/GNUstep/Makefiles"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"

objc_flags=$(gnustep-config --objc-flags)
base_libs=$(gnustep-config --base-libs)

cat > hello.m <<'EOF'
#import <Foundation/Foundation.h>

int main(void)
{
  @autoreleasepool {
    int (^twice)(int) = ^(int value) { return value * 2; };
    NSString *message = [NSString stringWithFormat: @"foundation-ok %d", twice(21)];
    printf("%s\n", [message UTF8String]);
  }
  return 0;
}
EOF
# shellcheck disable=SC2086
clang $objc_flags hello.m -o hello.exe $base_libs
./hello.exe | grep -qx 'foundation-ok 42'
echo "ok: Foundation hello-world (blocks) with gnustep-config flags"

cat > pthread_foundation.m <<'EOF'
#include <pthread.h>
#import <Foundation/Foundation.h>

int main(void)
{
  pthread_attr_t attr;
  pthread_attr_init(&attr);
  pthread_attr_destroy(&attr);
  return [NSString class] == Nil;
}
EOF
# shellcheck disable=SC2086
clang $objc_flags pthread_foundation.m -o pthread_foundation.exe $base_libs -lpthread
./pthread_foundation.exe
echo "ok: <pthread.h> together with Foundation"

python -c "import pyexpat, xml.etree.ElementTree as ET; assert ET.fromstring('<a><b/></a>')[0].tag == 'b'"
echo "ok: python pyexpat / xml.etree"

curl_features=$(curl -V | sed -n 's/^Features: //p')
for feature in SSL AsynchDNS; do
  case " $curl_features " in
    *" $feature "*) ;;
    *) echo "curl lacks $feature: $curl_features" >&2; exit 1 ;;
  esac
done
echo "ok: curl with SSL and AsynchDNS ($(curl -V | head -n 1))"

perl -e 'use strict; use warnings; alarm 5; print "ok: perl $^V\n"'

cat > tls.m <<'EOF'
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
# shellcheck disable=SC2086
clang $objc_flags tls.m -o tls.exe $base_libs
if ! ./tls.exe https://github.com; then
  echo "TLS failed for https://github.com; rerunning with GS_TLS_DEBUG=1" >&2
  GS_TLS_DEBUG=1 ./tls.exe https://github.com 2>&1 | tail -40 >&2 || true
  exit 1
fi
for host in expired wrong.host self-signed untrusted-root; do
  if ./tls.exe "https://$host.badssl.com" 2>/dev/null; then echo "TLS accepted a bad certificate: $host" >&2; exit 1; fi
done
GS_TLS_VERIFY_S=NO ./tls.exe https://self-signed.badssl.com 2>/dev/null
echo "ok: TLS host verification (github.com loads; expired, wrong-host, self-signed, untrusted-root refused; GS_TLS_VERIFY_S=NO overrides)"
if [ -n "${GNUSTEP_SMOKE_TLS_EXE:-}" ]; then cp tls.exe "$(cygpath -u "$GNUSTEP_SMOKE_TLS_EXE")"; fi
