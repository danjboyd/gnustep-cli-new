#!/bin/sh
set -eu

WORK_ROOT="${WORK_ROOT:-$HOME/gnustep-openbsd-package-artifacts}"
REPO_ROOT="${REPO_ROOT:-$HOME/gnustep-cli-new}"
TOOLCHAIN_ROOT="${TOOLCHAIN_ROOT:-/opt/gnustep-cli}"
OUTPUT_ROOT="${OUTPUT_ROOT:-$WORK_ROOT/output}"
TARGETS="${TARGETS:-arlen-openbsd-amd64-clang-headless gorm-openbsd-amd64-clang}"
SUMMARY="$OUTPUT_ROOT/openbsd-package-artifacts-summary.json"

rm -rf "$WORK_ROOT"
mkdir -p "$OUTPUT_ROOT"

doas pkg_add -I python%3.12 bash gmake git cmake ninja autoconf%2.72 automake%1.17 \
  gnustep-make gnustep-base gnustep-gui gnustep-back gnustep-libobjc2 >/tmp/gnustep-openbsd-package-pkg-add.log 2>&1 || true
if [ -x /usr/local/bin/bash ] && [ ! -x /bin/bash ]; then
  doas ln -sf /usr/local/bin/bash /bin/bash
fi
doas mkdir -p "$TOOLCHAIN_ROOT"
doas chown "$(id -un)" "$TOOLCHAIN_ROOT"

"$REPO_ROOT/toolchains/openbsd-amd64-clang/build-toolchain.sh" > "$OUTPUT_ROOT/toolchain-build.log" 2>&1

for target in $TARGETS; do
  case "$target" in
    arlen-openbsd-amd64-clang-headless)
      package_id="io.github.danjboyd.arlen"
      ;;
    gorm-openbsd-amd64-clang)
      package_id="org.gnustep.gorm"
      ;;
    *)
      echo "unsupported OpenBSD package target: $target" >&2
      exit 2
      ;;
  esac
  python3 "$REPO_ROOT/scripts/internal/build_infra.py" --json package-managed-source-artifact \
    --packages-dir "$REPO_ROOT/packages" \
    --package-id "$package_id" \
    --target "$target" \
    --output-dir "$OUTPUT_ROOT/$target" \
    --toolchain-root "$TOOLCHAIN_ROOT" > "$OUTPUT_ROOT/$target-report.json"
  python3 -c 'import json,sys; payload=json.load(open(sys.argv[1])); raise SystemExit(0 if payload.get("ok") else 1)' "$OUTPUT_ROOT/$target-report.json"
done

if [ -d "$OUTPUT_ROOT/gorm-openbsd-amd64-clang/work/org.gnustep.gorm-src" ]; then
  set +e
  env DISPLAY="${DISPLAY:-:1}" "$TOOLCHAIN_ROOT/System/Tools/openapp" \
    "$OUTPUT_ROOT/gorm-openbsd-amd64-clang/work/org.gnustep.gorm-src/Applications/Gorm/Gorm.app" \
    > "$OUTPUT_ROOT/gorm-openbsd-launch.log" 2>&1 &
  gorm_pid=$!
  sleep 5
  if kill -0 "$gorm_pid" 2>/dev/null; then
    gorm_launch_ok=true
    kill "$gorm_pid" 2>/dev/null || true
  else
    wait "$gorm_pid"
    status=$?
    if [ "$status" -eq 0 ]; then gorm_launch_ok=true; else gorm_launch_ok=false; fi
  fi
  set -e
else
  gorm_launch_ok=false
fi

python3 - "$SUMMARY" "$OUTPUT_ROOT" "$gorm_launch_ok" <<'PY'
import json, pathlib, sys
summary = {
    "schema_version": 1,
    "command": "openbsd-package-artifacts",
    "ok": sys.argv[3] == "true",
    "status": "ok" if sys.argv[3] == "true" else "error",
    "summary": "OpenBSD package artifacts built and Gorm launch evidence captured." if sys.argv[3] == "true" else "OpenBSD package artifacts built, but Gorm launch evidence failed.",
    "output_root": sys.argv[2],
    "reports": sorted(str(path) for path in pathlib.Path(sys.argv[2]).glob("*-report.json")),
    "gorm_launch_log": str(pathlib.Path(sys.argv[2]) / "gorm-openbsd-launch.log"),
}
pathlib.Path(sys.argv[1]).write_text(json.dumps(summary, indent=2) + "\n")
PY

python3 -c 'import json,sys; payload=json.load(open(sys.argv[1])); raise SystemExit(0 if payload.get("ok") else 1)' "$SUMMARY"
