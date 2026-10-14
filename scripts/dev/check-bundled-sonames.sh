#!/bin/sh
# Check managed Linux artifacts for bundled host runtime libraries.
#
# Usage: ICU_MAJOR=<n> check-bundled-sonames.sh <archive.tar.gz>...
#
# Fails when an archive bundles glibc, libm, the dynamic loader, libstdc++,
# libgcc_s, or any ICU other than ICU_MAJOR outside System/Sysroot (which is a
# link-time sysroot, not a runtime library directory), or when any ELF in the
# archive needs an ICU SONAME other than ICU_MAJOR. Manifest labels are not
# trusted: this inspects the archive contents directly.
set -eu

ICU_MAJOR=${ICU_MAJOR:?set ICU_MAJOR to the expected ICU major version}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
rc=0

for archive in "$@"; do
  name=$(basename "$archive")
  mkdir -p "$work/$name"
  tar -C "$work/$name" -xzf "$archive"
  echo "== $name"

  bundled=$(find "$work/$name" \( -name 'libc.so.6' -o -name 'libm.so.6' -o -name 'ld-linux*.so*' \
      -o -name 'libpthread.so.0' -o -name 'libdl.so.2' -o -name 'libstdc++.so.6*' -o -name 'libgcc_s.so.1' \
      -o -name 'libicu*.so.[0-9]*' \) -not -path '*/System/Sysroot/*' | sed "s|$work/$name/||" | sort)
  bad=$(printf '%s\n' "$bundled" | grep -vE "libicu[a-z0-9]*\.so\.$ICU_MAJOR(\.|\$)" | sed '/^$/d' || true)
  if [ -n "$bad" ]; then
    echo "FAIL bundled runtime libraries:"
    printf '  %s\n' $bad
    rc=1
  else
    echo "ok: no bundled libc/libm/loader/libstdc++/libgcc_s/non-ICU-$ICU_MAJOR libraries"
  fi

  elves=$(find "$work/$name" -type f -not -path '*/System/Sysroot/*' -exec sh -c 'for f; do if head -c 4 "$f" | grep -q "ELF"; then printf "%s\n" "$f"; fi; done' sh {} +)
  needed=""
  glibc_max=""
  if [ -n "$elves" ]; then
    needed=$(printf '%s\n' "$elves" | while IFS= read -r f; do readelf -d "$f" 2>/dev/null | sed -n 's/.*(NEEDED).*\[\(.*\)\]/\1/p'; done | sort -u)
    glibc_max=$(printf '%s\n' "$elves" | while IFS= read -r f; do objdump -T "$f" 2>/dev/null | grep -o 'GLIBC_2\.[0-9]*'; done | sort -t. -k2 -n -u | tail -n 1)
  fi
  icu_needed=$(printf '%s\n' "$needed" | grep '^libicu' || true)
  echo "icu_needed: $(echo $icu_needed)"
  if [ -n "$icu_needed" ] && printf '%s\n' "$icu_needed" | grep -vqE "\.so\.$ICU_MAJOR\$"; then
    echo "FAIL needs an ICU SONAME other than $ICU_MAJOR"
    rc=1
  fi
  echo "max_glibc_symbol: ${glibc_max:-none}"
done

exit $rc
