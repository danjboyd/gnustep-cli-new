#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
OTVM_DIR=${OTVM_DIR:-"$ROOT_DIR/../OracleTestVMs"}
OTVM_CONFIG=${OTVM_CONFIG:-"$HOME/oracletestvms-libvirt.toml"}
OLD_RELEASE_DIR=${OLD_RELEASE_DIR:-"$ROOT_DIR/dist/stable/previous"}
NEW_RELEASE_DIR=${NEW_RELEASE_DIR:-"$ROOT_DIR/dist/stable/0.1.0-dev"}
SSH_KEY=${SSH_KEY:-"$HOME/.ssh/otvm/id_rsa"}
PROFILE=${PROFILE:-debian-13-gnome-wayland}
TTL_HOURS=${TTL_HOURS:-2}
REMOTE_USER=${REMOTE_USER:-debian}
REMOTE_ROOT=${REMOTE_ROOT:-/tmp/gnustep-debian-upgrade-dogfood}

lease_id=""
guest_ip=""

cleanup() {
  if [[ -n "$lease_id" ]]; then
    (
      cd "$OTVM_DIR"
      PYTHONPATH=src python3 -m oracletestvms --config "$OTVM_CONFIG" destroy "$lease_id" >/dev/null || true
    )
  fi
}
trap cleanup EXIT

require_path() {
  if [[ ! -e "$1" ]]; then
    printf 'missing required path: %s
' "$1" >&2
    exit 2
  fi
}

require_path "$OTVM_DIR/src/oracletestvms"
require_path "$OTVM_CONFIG"
require_path "$OLD_RELEASE_DIR/release-manifest.json"
require_path "$NEW_RELEASE_DIR/release-manifest.json"
require_path "$SSH_KEY"
require_path "$ROOT_DIR/scripts/bootstrap/gnustep-bootstrap.sh"

otvm_json() {
  (
    cd "$OTVM_DIR"
    PYTHONPATH=src python3 -m oracletestvms --config "$OTVM_CONFIG" "$@"
  )
}

ssh_guest() {
  ssh -i "$SSH_KEY"     -o BatchMode=yes     -o ConnectTimeout=15     -o StrictHostKeyChecking=no     -o UserKnownHostsFile=/dev/null     "$REMOTE_USER@$guest_ip" "$@"
}

scp_guest() {
  scp -i "$SSH_KEY"     -o BatchMode=yes     -o ConnectTimeout=15     -o StrictHostKeyChecking=no     -o UserKnownHostsFile=/dev/null     "$@"
}

printf '[debian-upgrade-dogfood] preflight %s
' "$PROFILE" >&2
otvm_json preflight "$PROFILE" >/tmp/gnustep-debian-upgrade-preflight.json
python3 - <<'END_PREFLIGHT_PY'
import json
payload = json.load(open('/tmp/gnustep-debian-upgrade-preflight.json'))
if not payload.get('ready'):
    raise SystemExit(json.dumps(payload, indent=2))
END_PREFLIGHT_PY

printf '[debian-upgrade-dogfood] create %s
' "$PROFILE" >&2
otvm_json create "$PROFILE" --ttl-hours "$TTL_HOURS" >/tmp/gnustep-debian-upgrade-create.json
read -r lease_id guest_ip < <(python3 - <<'END_CREATE_PY'
import json
payload = json.load(open('/tmp/gnustep-debian-upgrade-create.json'))
lease = payload['lease']
remote = lease['remote_access']
print(lease['lease_id'], remote['host'])
END_CREATE_PY
)
printf '[debian-upgrade-dogfood] lease=%s guest=%s
' "$lease_id" "$guest_ip" >&2

printf '[debian-upgrade-dogfood] stage releases
' >&2
ssh_guest "rm -rf '$REMOTE_ROOT' && mkdir -p '$REMOTE_ROOT/old' '$REMOTE_ROOT/new' '$REMOTE_ROOT/bootstrap'"
scp_guest -r "$OLD_RELEASE_DIR/"* "$REMOTE_USER@$guest_ip:$REMOTE_ROOT/old/"
scp_guest -r "$NEW_RELEASE_DIR/"* "$REMOTE_USER@$guest_ip:$REMOTE_ROOT/new/"
scp_guest "$ROOT_DIR/scripts/bootstrap/gnustep-bootstrap.sh" "$REMOTE_USER@$guest_ip:$REMOTE_ROOT/bootstrap/gnustep-bootstrap.sh"

printf '[debian-upgrade-dogfood] run guest upgrade validation
' >&2
ssh_guest "REMOTE_ROOT='$REMOTE_ROOT' sh -s" <<'END_REMOTE_SCRIPT'
set -eu
INSTALL_ROOT="$REMOTE_ROOT/install"
OLD_MANIFEST="$REMOTE_ROOT/old/release-manifest.json"
NEW_MANIFEST="$REMOTE_ROOT/new/release-manifest.json"
BOOTSTRAP="$REMOTE_ROOT/bootstrap/gnustep-bootstrap.sh"
RESULTS="$REMOTE_ROOT/results"
mkdir -p "$RESULTS"
chmod +x "$BOOTSTRAP"
current_step="init"
trap 'status=$?; if [ "$status" -ne 0 ]; then echo "[remote] failed step=$current_step status=$status" >&2; for file in "$RESULTS"/*; do [ -e "$file" ] || continue; echo "[remote] ==== $file ==== " >&2; tail -n 120 "$file" >&2 || true; done; fi; exit "$status"' EXIT

current_step="host prerequisites"
sudo apt-get update >"$RESULTS/apt-update.stdout" 2>"$RESULTS/apt-update.stderr"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y clang make >"$RESULTS/apt-install.stdout" 2>"$RESULTS/apt-install.stderr"

current_step="bootstrap old release"
"$BOOTSTRAP" --json setup --root "$INSTALL_ROOT" --manifest "$OLD_MANIFEST" >"$RESULTS/setup-old.json" 2>"$RESULTS/setup-old.stderr"
python3 - "$RESULTS/setup-old.json" <<'END_SETUP_OLD_PY'
import json, sys
payload = json.load(open(sys.argv[1]))
if not payload.get('ok'):
    raise SystemExit(json.dumps(payload, indent=2))
END_SETUP_OLD_PY

current_step="check updates"
"$INSTALL_ROOT/bin/gnustep" update --check --json --root "$INSTALL_ROOT" --manifest "$NEW_MANIFEST" >"$RESULTS/check-updates.json" 2>"$RESULTS/check-updates.stderr"
python3 - "$RESULTS/check-updates.json" <<'END_CHECK_PY'
import json, sys
payload = json.load(open(sys.argv[1]))
if not payload.get('ok'):
    raise SystemExit(json.dumps(payload, indent=2))
plan = payload.get('plan', {}).get('cli', payload.get('update_plan', {}))
if not plan.get('update_available'):
    raise SystemExit(json.dumps(payload, indent=2))
END_CHECK_PY

current_step="upgrade"
"$INSTALL_ROOT/bin/gnustep" update cli --yes --json --root "$INSTALL_ROOT" --manifest "$NEW_MANIFEST" >"$RESULTS/upgrade.json" 2>"$RESULTS/upgrade.stderr"
python3 - "$RESULTS/upgrade.json" <<'END_UPGRADE_PY'
import json, sys
payload = json.load(open(sys.argv[1]))
if not payload.get('ok') or payload.get('operation') not in {'update_cli', 'upgrade'}:
    raise SystemExit(json.dumps(payload, indent=2))
END_UPGRADE_PY

current_step="post-upgrade state"
python3 - "$INSTALL_ROOT/state/cli-state.json" <<'END_STATE_PY'
import json, os, sys
state = json.load(open(sys.argv[1]))
if state.get('last_action') != 'upgrade':
    raise SystemExit(json.dumps(state, indent=2))
previous = state.get('previous_release_path')
if not previous or not os.path.exists(previous):
    raise SystemExit(json.dumps(state, indent=2))
END_STATE_PY

current_step="post-upgrade smoke"
"$INSTALL_ROOT/bin/gnustep" --version >"$RESULTS/version.txt" 2>"$RESULTS/version.stderr"
"$INSTALL_ROOT/bin/gnustep" doctor --json --manifest "$NEW_MANIFEST" >"$RESULTS/doctor.json" 2>"$RESULTS/doctor.stderr"
python3 - "$RESULTS/doctor.json" <<'END_DOCTOR_PY'
import json, sys
payload = json.load(open(sys.argv[1]))
if payload.get('command') != 'doctor':
    raise SystemExit(json.dumps(payload, indent=2))
END_DOCTOR_PY

current_step="rollback"
"$INSTALL_ROOT/bin/gnustep" setup --rollback --json --root "$INSTALL_ROOT" >"$RESULTS/rollback.json" 2>"$RESULTS/rollback.stderr"
python3 - "$RESULTS/rollback.json" "$INSTALL_ROOT/state/cli-state.json" <<'END_ROLLBACK_PY'
import json, os, sys
payload = json.load(open(sys.argv[1]))
if not payload.get('ok') or payload.get('operation') != 'rollback':
    raise SystemExit(json.dumps(payload, indent=2))
state = json.load(open(sys.argv[2]))
if state.get('last_action') != 'rollback' or state.get('status') != 'healthy':
    raise SystemExit(json.dumps(state, indent=2))
END_ROLLBACK_PY
"$INSTALL_ROOT/bin/gnustep" --version >"$RESULTS/rollback-version.txt" 2>"$RESULTS/rollback-version.stderr"
"$INSTALL_ROOT/bin/gnustep" doctor --json --manifest "$OLD_MANIFEST" >"$RESULTS/rollback-doctor.json" 2>"$RESULTS/rollback-doctor.stderr"
python3 - "$RESULTS/rollback-doctor.json" <<'END_ROLLBACK_DOCTOR_PY'
import json, sys
payload = json.load(open(sys.argv[1]))
if payload.get('command') != 'doctor':
    raise SystemExit(json.dumps(payload, indent=2))
END_ROLLBACK_DOCTOR_PY

trap - EXIT
printf '{"ok":true,"summary":"Debian upgrade and rollback dogfood validation passed."}
' >"$RESULTS/summary.json"
END_REMOTE_SCRIPT

printf '[debian-upgrade-dogfood] fetch summary
' >&2
scp_guest "$REMOTE_USER@$guest_ip:$REMOTE_ROOT/results/summary.json" /tmp/gnustep-debian-upgrade-summary.json
cat /tmp/gnustep-debian-upgrade-summary.json
