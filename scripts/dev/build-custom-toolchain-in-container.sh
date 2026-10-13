#!/bin/sh
# Build a custom GNUstep toolchain from a lock inside the pinned build image.
#
# Usage: build-custom-toolchain-in-container.sh <lock.json> <prefix> [jobs]
#
# The image comes from toolchains/<recipe>/Dockerfile, where <recipe> is the
# lock's container.recipe (default linux-amd64-clang, a debian:13 base). Any
# container.apt_packages are installed first, so optional libraries that
# libs-gui/libs-back detect at configure time are explicit lock inputs rather
# than whatever the developer's machine has installed. The lock directory is
# mounted read-only and the prefix's parent read-write at the same absolute
# paths, so the built toolchain works at <prefix> on the host. Files are handed
# back to the invoking user afterwards.
set -eu

if [ "$#" -lt 2 ]; then
  printf '%s\n' "usage: $0 <lock.json> <prefix> [jobs]" >&2
  exit 2
fi

REPO=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
LOCK=$(CDPATH= cd -- "$(dirname "$1")" && pwd)/$(basename "$1")
PREFIX=$2
JOBS=${3:-}
case "$PREFIX" in
  /*) ;;
  *) printf '%s\n' "prefix must be an absolute path" >&2; exit 2 ;;
esac
PREFIX_PARENT=$(dirname "$PREFIX")
mkdir -p "$PREFIX_PARENT"
LOCK_DIR=$(dirname "$LOCK")

# Validate on the host first so obvious lock or prefix problems fail fast.
python3 "$REPO/scripts/internal/build_infra.py" --json validate-custom-toolchain-lock --lock "$LOCK"
echo
# The managed-root guard must run with the host HOME: inside the container HOME
# is different, so the host's ~/.local/share/gnustep-cli would not be protected.
PYTHONPATH="$REPO/src" python3 - "$PREFIX" <<'PY'
import json, sys
from gnustep_cli_shared.custom_toolchain import check_custom_prefix
result = check_custom_prefix(sys.argv[1])
if not result["ok"]:
    print(json.dumps(result))
    raise SystemExit(1)
PY

read_lock() {
  python3 - "$LOCK" "$1" <<'PY'
import json, sys
lock = json.load(open(sys.argv[1]))
container = lock.get("container") or {}
if sys.argv[2] == "recipe":
    print(container.get("recipe", "linux-amd64-clang"))
else:
    print(" ".join(container.get("apt_packages", [])))
PY
}
RECIPE=$(read_lock recipe)
APT_PACKAGES=$(read_lock apt_packages)
test -f "$REPO/toolchains/$RECIPE/Dockerfile"

IMAGE="gnustep-custom-toolchain-$RECIPE"
docker build -t "$IMAGE" "$REPO/toolchains/$RECIPE"

jobs_arg=""
[ -n "$JOBS" ] && jobs_arg="--jobs $JOBS"
docker run --rm \
  -v "$REPO:/src:ro" \
  -v "$LOCK_DIR:$LOCK_DIR:ro" \
  -v "$PREFIX_PARENT:$PREFIX_PARENT" \
  -e HOME=/tmp/custom-toolchain-home \
  -e APT_PACKAGES="$APT_PACKAGES" \
  -e HOST_UID="$(id -u)" \
  -e HOST_GID="$(id -g)" \
  "$IMAGE" \
  sh -c '
    set -eu
    if [ -n "$APT_PACKAGES" ]; then
      apt-get update >/dev/null
      DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends $APT_PACKAGES >/dev/null
    fi
    mkdir -p "$HOME"
    status=0
    python3 /src/scripts/internal/build_infra.py --json build-custom-toolchain \
      --lock "$1" --prefix "$2" $3 || status=$?
    chown -R "$HOST_UID:$HOST_GID" "$2" "$(dirname "$2")/.$(basename "$2")-build" 2>/dev/null || true
    exit $status
  ' sh "$LOCK" "$PREFIX" "$jobs_arg"
