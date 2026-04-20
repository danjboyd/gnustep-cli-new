#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
RELEASE_DIR=${RELEASE_DIR:-$ROOT/dist/stable/0.1.0-dev}
TOOLCHAIN_ARCHIVE=${TOOLCHAIN_ARCHIVE:-$RELEASE_DIR/gnustep-toolchain-linux-amd64-clang-0.1.0-dev.tar.gz}
OUTPUT_ARCHIVE=${OUTPUT_ARCHIVE:-$RELEASE_DIR/gnustep-cli-linux-amd64-clang-0.1.0-dev.tar.gz}
VERSION=${VERSION:-0.1.0-dev}
WORK_DIR=${WORK_DIR:-}
PRIVATE_KEY=${PRIVATE_KEY:-}

args=(
  --json build-linux-cli-against-managed-toolchain
  --toolchain-archive "$TOOLCHAIN_ARCHIVE"
  --output-archive "$OUTPUT_ARCHIVE"
  --version "$VERSION"
  --repo-root "$ROOT"
  --release-dir "$RELEASE_DIR"
)
if [[ -n "$WORK_DIR" ]]; then
  args+=(--work-dir "$WORK_DIR")
fi
if [[ -n "$PRIVATE_KEY" ]]; then
  args+=(--private-key "$PRIVATE_KEY")
fi
python3 "$ROOT/scripts/internal/build_infra.py" "${args[@]}"
