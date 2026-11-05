#!/usr/bin/env bash
# Diagnostic helper (temporary): turn the gnustep-base recipe's TLS patch step into a
# no-op, so the same recipe builds without the seven TLS commits.
# Usage: pkgbuild-without-tls-patches.sh <PKGBUILD>
set -eu
pkgbuild=$1
grep -q '^    patch -p1 -i "${srcdir}/${tls_patch}"$' "$pkgbuild"
sed -i 's|^    patch -p1 -i "${srcdir}/${tls_patch}"$|    echo "skipped ${tls_patch}"|' "$pkgbuild"
grep -n 'skipped' "$pkgbuild"
