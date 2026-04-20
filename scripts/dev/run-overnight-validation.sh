#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
OTVM_ROOT=${OTVM_ROOT:-"$ROOT/../OracleTestVMs"}
OTVM_CONFIG=${OTVM_CONFIG:-"$HOME/oracletestvms-libvirt.toml"}
RELEASE_URL=${RELEASE_URL:-"https://example.invalid/releases/nightly"}
STAMP=${STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}
EVIDENCE_DIR=${EVIDENCE_DIR:-"$ROOT/docs/validation/overnight-$STAMP"}
PROFILES=${PROFILES:-"debian-13-gnome-wayland openbsd-7.8-fvwm fedora-gnome-wayland arch-gnome-wayland windows-2022"}

mkdir -p "$EVIDENCE_DIR"

log() {
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$EVIDENCE_DIR/run.log"
}

run_capture() {
  name=$1
  shift
  log "START $name"
  set +e
  "$@" > "$EVIDENCE_DIR/$name.out" 2> "$EVIDENCE_DIR/$name.err"
  rc=$?
  set -e
  printf '%s\n' "$rc" > "$EVIDENCE_DIR/$name.rc"
  if [ "$rc" -eq 0 ]; then
    log "PASS $name"
  else
    log "FAIL $name rc=$rc"
  fi
  return "$rc"
}

run_shell_capture() {
  name=$1
  shift
  log "START $name"
  set +e
  eval "$*" > "$EVIDENCE_DIR/$name.out" 2> "$EVIDENCE_DIR/$name.err"
  rc=$?
  set -e
  printf '%s\n' "$rc" > "$EVIDENCE_DIR/$name.rc"
  if [ "$rc" -eq 0 ]; then
    log "PASS $name"
  else
    log "FAIL $name rc=$rc"
  fi
  return "$rc"
}

cleanup_pycache() {
  find "$ROOT" "$OTVM_ROOT" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
}

otvm_cmd() {
  printf "PYTHONPATH='%s/src' python3 -m oracletestvms --config '%s'" "$OTVM_ROOT" "$OTVM_CONFIG"
}

lease_summary() {
  input=$1
  output=$2
  python3 - "$input" "$output" <<'PY'
import json
import sys
source, dest = sys.argv[1], sys.argv[2]
try:
    data = json.load(open(source, encoding="utf-8"))
except Exception as exc:
    json.dump({"ok": False, "error": str(exc)}, open(dest, "w", encoding="utf-8"), indent=2)
    raise SystemExit(0)
leases = []
for entry in data.get("leases", []):
    lease = entry.get("lease", {})
    if lease.get("status") != "destroyed":
        leases.append({
            "lease_id": lease.get("lease_id"),
            "profile": lease.get("profile_slug"),
            "status": lease.get("status"),
            "public_ip": lease.get("public_ip"),
            "ttl_expires_at": lease.get("ttl_expires_at"),
        })
json.dump({"ok": True, "active_or_incomplete_count": len(leases), "leases": leases}, open(dest, "w", encoding="utf-8"), indent=2)
PY
}

missing_fedora_arch_pins() {
  python3 - "$OTVM_CONFIG" <<'PY'
import sys
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib
config = tomllib.load(open(sys.argv[1], "rb"))
infra = config.get("infra", {})
for key in ("fedora_gnome_wayland_image_ocid", "arch_gnome_wayland_image_ocid"):
    if not str(infra.get(key, "")).strip():
        print(key)
PY
}

OTVM=$(otvm_cmd)

log "overnight validation evidence: $EVIDENCE_DIR"
log "repo: $ROOT"
log "otvm root: $OTVM_ROOT"
log "otvm config: $OTVM_CONFIG"
log "profiles: $PROFILES"

run_capture git-status-before git -C "$ROOT" status --short || true
run_capture otvm-head git -C "$OTVM_ROOT" rev-parse HEAD || true
run_shell_capture otvm-config-show "$OTVM config-show" || true
run_shell_capture otvm-catalog-list "$OTVM catalog-list" || true
run_shell_capture otvm-list-before "$OTVM list" || true
lease_summary "$EVIDENCE_DIR/otvm-list-before.out" "$EVIDENCE_DIR/otvm-active-before.json" || true

run_capture python-unit-tests python3 -m unittest discover -s "$ROOT/tests" || true
run_capture native-unit-tests "$ROOT/scripts/dev/run-native-tests.sh" || true
run_shell_capture release-plan "python3 '$ROOT/scripts/internal/build_infra.py' --json published-url-qualification-plan --release-url '$RELEASE_URL' --config-path '$OTVM_CONFIG'" || true
if [ -f "$ROOT/dist/stable/0.1.0-dev/release-manifest.json" ]; then
  run_shell_capture local-release-host-validation-plan "python3 '$ROOT/scripts/internal/build_infra.py' --json otvm-release-host-validation-plan --release-dir '$ROOT/dist/stable/0.1.0-dev' --config-path '$OTVM_CONFIG'" || true
  run_shell_capture local-release-qualification-bundle "python3 '$ROOT/scripts/internal/build_infra.py' --json qualify-release --release-dir '$ROOT/dist/stable/0.1.0-dev' --install-root '$EVIDENCE_DIR/local-release-install-root'" || true
fi

missing=$(missing_fedora_arch_pins || true)
if printf '%s\n' "$missing" | grep -q fedora_gnome_wayland_image_ocid; then
  log "fedora image pin missing; building Fedora libvirt image"
  run_shell_capture otvm-build-fedora "$OTVM fedora-build-libvirt-image --write-config '$OTVM_CONFIG'" || true
fi
if printf '%s\n' "$missing" | grep -q arch_gnome_wayland_image_ocid; then
  log "arch image pin missing; building Arch libvirt image"
  run_shell_capture otvm-build-arch "$OTVM arch-build-libvirt-image --write-config '$OTVM_CONFIG'" || true
fi

run_shell_capture otvm-config-show-after-image-build "$OTVM config-show" || true

for profile in $PROFILES; do
  safe=$(printf '%s' "$profile" | tr -c 'A-Za-z0-9_' '-')
  run_shell_capture "preflight-$safe" "$OTVM preflight '$profile'" || true
done

for profile in $PROFILES; do
  safe=$(printf '%s' "$profile" | tr -c 'A-Za-z0-9_' '-')
  run_shell_capture "acceptance-$safe" "$OTVM acceptance-run '$profile' --ttl-hours 2" || true
  run_shell_capture "otvm-list-after-$safe" "$OTVM list" || true
  lease_summary "$EVIDENCE_DIR/otvm-list-after-$safe.out" "$EVIDENCE_DIR/otvm-active-after-$safe.json" || true
  run_shell_capture "otvm-reap-after-$safe" "$OTVM reap" || true
done

run_shell_capture otvm-list-final "$OTVM list" || true
lease_summary "$EVIDENCE_DIR/otvm-list-final.out" "$EVIDENCE_DIR/otvm-active-final.json" || true
run_capture git-status-after git -C "$ROOT" status --short || true
cleanup_pycache

python3 - "$EVIDENCE_DIR" <<'PY'
from pathlib import Path
import json
import sys

root = Path(sys.argv[1])
summary = {
    "evidence_dir": str(root),
    "passed": [],
    "failed": [],
    "active_or_incomplete_leases": None,
}
for rc_file in sorted(root.glob("*.rc")):
    rc = rc_file.read_text(encoding="utf-8").strip()
    name = rc_file.stem
    if rc == "0":
        summary["passed"].append(name)
    else:
        summary["failed"].append({"name": name, "rc": rc})
active = root / "otvm-active-final.json"
if active.exists():
    try:
        summary["active_or_incomplete_leases"] = json.loads(active.read_text(encoding="utf-8"))
    except Exception as exc:
        summary["active_or_incomplete_leases"] = {"ok": False, "error": str(exc)}
(root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
PY

log "overnight validation complete"
