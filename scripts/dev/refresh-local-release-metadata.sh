#!/usr/bin/env sh
set -eu

if [ "$#" -lt 1 ]; then
  echo "usage: $0 <release-dir> [--private-key <path>]" >&2
  exit 2
fi

RELEASE_DIR=$1
shift
PRIVATE_KEY=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --private-key)
      if [ "$#" -lt 2 ]; then
        echo "--private-key requires a value" >&2
        exit 2
      fi
      PRIVATE_KEY=$2
      shift 2
      ;;
    *)
      echo "unknown option: $1" >&2
      exit 2
      ;;
  esac
done

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
if [ -n "$PRIVATE_KEY" ]; then
  python3 "$ROOT/scripts/internal/build_infra.py" --json refresh-local-release-metadata --release-dir "$RELEASE_DIR" --private-key "$PRIVATE_KEY"
else
  python3 "$ROOT/scripts/internal/build_infra.py" --json refresh-local-release-metadata --release-dir "$RELEASE_DIR"
fi
