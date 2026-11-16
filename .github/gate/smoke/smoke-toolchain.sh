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
# - NSLog, which a clang 23 miscompile of GSPrivateFormat broke in our gnustep-base build
# - strict TLS host verification through NSURLConnection, with gdnc started by the
#   library itself: a trusted site loads, bad certificates are refused, and
#   GS_TLS_VERIFY_S=NO still overrides it
# - trust on a store missing the root, offline: Windows adds many roots to its store
#   only on demand, so gnustep-base also loads its bundled authorities. A local server
#   whose root is only in the bundle must load; with GNUSTEP_SMOKE_STORE_ROOT=1 (CI, as
#   an administrator) one whose root is only in the machine store must load too
# - the bundled authorities' age: refused when more than 365 days old
set -euo pipefail

root=${1:?usage: smoke-toolchain.sh <toolchain-root>}
# Run from the toolchain's own bash, the root is "/"; avoid "//" (a UNC path).
root=${root%/}
export PATH="$root/clang64/bin:$root/usr/bin:$PATH"
export GNUSTEP_MAKEFILES="$root/clang64/share/GNUstep/Makefiles"
work=$(mktemp -d)
# The TLS checks make gnustep-base start gdnc, which keeps the work directory busy on
# Windows; stop it before cleaning up, and don't fail the smoke over the leftover.
cleanup() {
  cd /
  if [ -n "${server_pids:-}" ]; then kill $server_pids 2>/dev/null || true; fi
  if [ -n "${bundle_backup:-}" ] && [ -f "$bundle_backup" ]; then cp "$bundle_backup" "$bundle"; fi
  if [ -n "${store_root_added:-}" ]; then certutil -delstore Root "gnustep-cli smoke store root" >/dev/null 2>&1 || true; fi
  taskkill //F //IM gdnc.exe >/dev/null 2>&1
  rm -rf "$work" 2>/dev/null || true
}
trap cleanup EXIT
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

cat > nslog.m <<'EOF'
#import <Foundation/Foundation.h>
int main(void)
{
  @autoreleasepool {
    NSLog(@"%s %@ %d", "nslog", @"smoke", 42);
  }
  return 0;
}
EOF
# shellcheck disable=SC2086
clang $objc_flags nslog.m -o nslog.exe $base_libs
./nslog.exe 2>&1 | grep -q 'nslog smoke 42'
echo "ok: NSLog formatting"

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
    printf("%s %s\n", argv[1], (d != nil && error == nil) ? "fetched" : "refused");
    return (d != nil && error == nil) ? 0 : 1;
  }
}
EOF
# shellcheck disable=SC2086
clang $objc_flags tls.m -o tls.exe $base_libs
# Nothing starts gdnc here: the library must start it itself.
./tls.exe https://github.com
for host in expired wrong.host self-signed untrusted-root; do
  set +e
  ./tls.exe "https://$host.badssl.com"
  rc=$?
  set -e
  if [ "$rc" -ne 1 ]; then echo "expected a refusal (exit 1) for $host, got $rc" >&2; exit 1; fi
done
GS_TLS_VERIFY_S=NO ./tls.exe https://self-signed.badssl.com
# Address URLs: a certificate naming the address is accepted; one that doesn't is refused.
./tls.exe https://1.1.1.1
gh_addr=$(python -c 'import socket; print(socket.gethostbyname("github.com"))')
set +e
./tls.exe "https://$gh_addr"
rc=$?
set -e
if [ "$rc" -ne 1 ]; then echo "expected a refusal (exit 1) for https://$gh_addr, got $rc" >&2; exit 1; fi
if [ -n "${GNUSTEP_SMOKE_TLS_EXE:-}" ]; then cp tls.exe "$(cygpath -u "$GNUSTEP_SMOKE_TLS_EXE")"; fi
echo "ok: TLS host verification (github.com loads; expired, wrong-host, self-signed, untrusted-root refused; GS_TLS_VERIFY_S=NO overrides; address URLs checked against the certificate)"

# Trust on a store missing the root, offline. Each server's root is made here, so it is
# in no Windows store unless this test adds it.
bundle=$(find "$root/clang64/lib/GNUstep/Libraries/gnustep-base" -path '*/GSTLS/ca-certificates.crt' | head -n 1)
if [ -z "$bundle" ]; then echo "gnustep-base has no GSTLS/ca-certificates.crt" >&2; exit 1; fi
make_server_cert() { # name, root common name
  MSYS2_ARG_CONV_EXCL='*' openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes \
    -keyout "$1-root.key" -out "$1-root.crt" -days 2 -subj "/CN=$2" \
    -addext basicConstraints=critical,CA:TRUE -addext keyUsage=critical,keyCertSign,cRLSign 2>/dev/null
  MSYS2_ARG_CONV_EXCL='*' openssl req -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes \
    -keyout "$1.key" -out "$1.csr" -subj "/CN=127.0.0.1" 2>/dev/null
  printf 'subjectAltName=IP:127.0.0.1\nbasicConstraints=CA:FALSE\nextendedKeyUsage=serverAuth\n' > "$1.ext"
  openssl x509 -req -in "$1.csr" -CA "$1-root.crt" -CAkey "$1-root.key" -CAcreateserial \
    -out "$1.crt" -days 2 -extfile "$1.ext" 2>/dev/null
}
cat > serve.py <<'PY'
import http.server, ssl, sys
httpd = http.server.HTTPServer(("127.0.0.1", int(sys.argv[1])), http.server.SimpleHTTPRequestHandler)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(sys.argv[2], sys.argv[3])
httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
httpd.serve_forever()
PY
start_server() { # port, name
  python serve.py "$1" "$2.crt" "$2.key" >/dev/null 2>&1 &
  server_pids="${server_pids:-} $!"
  python -c 'import socket, sys, time
for _ in range(100):
    try:
        socket.create_connection(("127.0.0.1", int(sys.argv[1])), 1).close(); sys.exit(0)
    except OSError:
        time.sleep(0.1)
sys.exit("server on port %s did not start" % sys.argv[1])' "$1"
}
expect_tls() { # expected exit, url
  set +e
  ./tls.exe "$2"
  rc=$?
  set -e
  if [ "$rc" -ne "$1" ]; then echo "expected exit $1 for $2, got $rc" >&2; exit 1; fi
}
make_server_cert bundled "gnustep-cli smoke bundle root"
start_server 18443 bundled
expect_tls 1 https://127.0.0.1:18443/
# Add the root to the bundled authorities for one request, then restore them exactly:
# this toolchain is packaged after the smoke.
bundle_sha=$(sha256sum "$bundle" | cut -d' ' -f1)
bundle_backup="$work/ca-certificates.crt.orig"
cp "$bundle" "$bundle_backup"
cat bundled-root.crt >> "$bundle"
expect_tls 0 https://127.0.0.1:18443/
cp "$bundle_backup" "$bundle"
bundle_backup=
if [ "$(sha256sum "$bundle" | cut -d' ' -f1)" != "$bundle_sha" ]; then
  echo "could not restore $bundle" >&2; exit 1
fi
if [ "${GNUSTEP_SMOKE_STORE_ROOT:-}" = 1 ]; then
  # A root only in the machine store, as an enterprise root would be, must still load.
  make_server_cert store "gnustep-cli smoke store root"
  start_server 18444 store
  expect_tls 1 https://127.0.0.1:18444/
  certutil -addstore Root "$(cygpath -w "$work/store-root.crt")" >/dev/null
  store_root_added=1
  expect_tls 0 https://127.0.0.1:18444/
  certutil -delstore Root "gnustep-cli smoke store root" >/dev/null
  store_root_added=
  store_note="; a root only in the machine store loads"
fi
echo "ok: trust on a store missing the root (a root only in the bundled authorities loads${store_note:-})"

# The bundled authorities' age, from the ca-certificates package they were taken from.
source_file="$(dirname "$bundle")/ca-certificates.source"
if [ ! -f "$source_file" ]; then echo "no $source_file: the bundled authorities' origin is unknown" >&2; exit 1; fi
python - "$source_file" <<'PY'
import datetime, re, sys
text = open(sys.argv[1]).read().strip()
m = re.search(r"ca-certificates (\d{8})", text)
if not m:
    sys.exit(f"cannot read a date from {text!r}")
age = (datetime.date.today() - datetime.datetime.strptime(m.group(1), "%Y%m%d").date()).days
if age > 365:
    sys.exit(f"the bundled authorities are {age} days old ({text}); re-lock ca-certificates and rebuild gnustep-base")
print(f"ok: bundled authorities from {text}, {age} days old")
PY
