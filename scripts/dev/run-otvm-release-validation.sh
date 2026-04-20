#!/usr/bin/env sh
set -eu

EXECUTE=0
PROFILES=""
if [ "${1:-}" = "--execute" ]; then
  EXECUTE=1
  shift
fi
if [ "$#" -lt 1 ]; then
  echo "usage: $0 [--execute] <release-dir> [otvm-config] [profiles...]" >&2
  exit 2
fi

RELEASE_DIR=$1
shift
OTVM_CONFIG=${1:-${OTVM_CONFIG:-$HOME/oracletestvms-libvirt.toml}}
if [ "$#" -gt 0 ]; then
  shift
fi
PROFILES="$*"
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
OTVM_ROOT=${OTVM_ROOT:-$ROOT/../OracleTestVMs}
PLAN=${PLAN:-$RELEASE_DIR/otvm-host-validation-plan.json}
SSH_KEY=${SSH_KEY:-$HOME/.ssh/otvm/id_rsa}
SSH_OPTS="-i $SSH_KEY -o BatchMode=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

if [ ! -d "$OTVM_ROOT" ]; then
  echo "OracleTestVMs checkout not found: $OTVM_ROOT" >&2
  exit 3
fi
if [ ! -f "$OTVM_CONFIG" ]; then
  echo "otvm config not found: $OTVM_CONFIG" >&2
  exit 3
fi
if [ ! -f "$SSH_KEY" ]; then
  echo "ssh key not found: $SSH_KEY" >&2
  exit 3
fi

python3 "$ROOT/scripts/internal/build_infra.py" --json otvm-release-host-validation-plan \
  --release-dir "$RELEASE_DIR" \
  --config-path "$OTVM_CONFIG" > "$PLAN"

printf 'wrote validation plan: %s\n' "$PLAN"
python3 - <<'PY2' "$PLAN"
import json, sys
payload = json.load(open(sys.argv[1]))
for target in payload.get("targets", []):
    print(f"{target['id']}: {target.get('profile', 'n/a')} status={target.get('status')}")
PY2

if [ "$EXECUTE" -ne 1 ]; then
  printf '\nRun targeted live validation manually from %s, using short TTLs and explicit destroy cleanup.\n' "$OTVM_ROOT"
  printf 'Example:\n  %s --execute %s %s <profile>\n' "$0" "$RELEASE_DIR" "$OTVM_CONFIG"
  exit 0
fi

LEASES=""
cleanup() {
  for lease in $LEASES; do
    (cd "$OTVM_ROOT" && PYTHONPATH=src python3 -m oracletestvms --config "$OTVM_CONFIG" destroy "$lease") || true
  done
}
trap cleanup EXIT INT TERM

lease_field() {
  file="$1"
  field="$2"
  python3 - <<'PY2' "$file" "$field"
import json, sys
payload = json.load(open(sys.argv[1]))
lease = payload.get("lease", payload)
value = lease
for part in sys.argv[2].split("."):
    value = value.get(part, {}) if isinstance(value, dict) else {}
print(value if isinstance(value, str) else "")
PY2
}

ssh_guest() {
  user="$1"
  host="$2"
  shift 2
  # shellcheck disable=SC2086
  ssh $SSH_OPTS "$user@$host" "$@"
}

scp_to_guest() {
  user="$1"
  host="$2"
  src="$3"
  dest="$4"
  # shellcheck disable=SC2086
  scp $SSH_OPTS -r "$src" "$user@$host:$dest"
}

run_openbsd_probe() {
  host="$1"
  out="$RELEASE_DIR/otvm-openbsd-7.8-fvwm-smoke.json"
  ssh_guest oracleadmin "$host" 'set -eu
    rm -rf /tmp/gnustep-release-smoke && mkdir -p /tmp/gnustep-release-smoke
    doas pkg_add -I gmake gnustep-make gnustep-base gnustep-libobjc2 >/tmp/gnustep-release-smoke/pkg_add.out
    set +u
    . /usr/local/share/GNUstep/Makefiles/GNUstep.sh
    set -u
    cat >/tmp/gnustep-release-smoke/probe.m <<"PROBE"
#import <Foundation/Foundation.h>
int main(void) { @autoreleasepool { NSLog(@"openbsd-release-probe-ok"); } return 0; }
PROBE
    cc $(gnustep-config --objc-flags) /tmp/gnustep-release-smoke/probe.m -o /tmp/gnustep-release-smoke/probe $(gnustep-config --base-libs) >/tmp/gnustep-release-smoke/compile.out 2>/tmp/gnustep-release-smoke/compile.err
    /tmp/gnustep-release-smoke/probe >/tmp/gnustep-release-smoke/probe.out 2>/tmp/gnustep-release-smoke/probe.err
    grep -q openbsd-release-probe-ok /tmp/gnustep-release-smoke/probe.err
  '
  printf '{"ok":true,"profile":"openbsd-7.8-fvwm","summary":"OpenBSD packaged GNUstep compile/run smoke passed."}\n' > "$out"
}

run_debian_probe() {
  host="$1"
  out="$RELEASE_DIR/otvm-debian-13-gnome-wayland-smoke.json"
  ssh_guest debian "$host" 'set -eu; rm -rf /tmp/gnustep-release-smoke; mkdir -p /tmp/gnustep-release-smoke/release /tmp/gnustep-release-smoke/bootstrap'
  scp_to_guest debian "$host" "$RELEASE_DIR/." /tmp/gnustep-release-smoke/release/
  scp_to_guest debian "$host" "$ROOT/scripts/bootstrap/gnustep-bootstrap.sh" /tmp/gnustep-release-smoke/bootstrap/gnustep-bootstrap.sh
  ssh_guest debian "$host" 'set -eu
    sudo apt-get update >/tmp/gnustep-release-smoke/apt-update.out
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y clang make >/tmp/gnustep-release-smoke/apt-install.out
    INSTALL_ROOT=/tmp/gnustep-release-smoke/install
    MANIFEST=/tmp/gnustep-release-smoke/release/release-manifest.json
    BOOTSTRAP=/tmp/gnustep-release-smoke/bootstrap/gnustep-bootstrap.sh
    RESULTS=/tmp/gnustep-release-smoke/results
    mkdir -p "$RESULTS"
    chmod +x "$BOOTSTRAP"
    "$BOOTSTRAP" --json setup --root "$INSTALL_ROOT" --manifest "$MANIFEST" >"$RESULTS/setup.json"
    python3 - "$RESULTS/setup.json" <<"END_SETUP_PY"
import json, sys
payload=json.load(open(sys.argv[1]))
if not payload.get("ok"):
    raise SystemExit(json.dumps(payload, indent=2))
END_SETUP_PY
    "$INSTALL_ROOT/bin/gnustep" --version >"$RESULTS/version.txt" 2>"$RESULTS/version.stderr"
    "$INSTALL_ROOT/bin/gnustep" --help >"$RESULTS/help.txt" 2>"$RESULTS/help.stderr"
    "$INSTALL_ROOT/bin/gnustep" doctor --json --manifest "$MANIFEST" >"$RESULTS/doctor.json" 2>"$RESULTS/doctor.stderr"
    python3 - "$RESULTS/doctor.json" <<"END_DOCTOR_PY"
import json, sys
payload=json.load(open(sys.argv[1]))
if payload.get("command") != "doctor":
    raise SystemExit(json.dumps(payload, indent=2))
END_DOCTOR_PY
    printf "{\"ok\":true,\"profile\":\"debian-13-gnome-wayland\",\"summary\":\"Debian staged release smoke passed.\"}\n" >"$RESULTS/summary.json"
  '
  # shellcheck disable=SC2086
  scp $SSH_OPTS "debian@$host:/tmp/gnustep-release-smoke/results/summary.json" "$out"
  python3 - <<'PY2' "$out"
import json, sys
payload=json.load(open(sys.argv[1], encoding='utf-8-sig'))
print(json.dumps(payload, indent=2))
if not payload.get('ok'):
    raise SystemExit(1)
PY2
}

run_windows_probe() {
  host="$1"
  out="$RELEASE_DIR/otvm-windows-2022-smoke.json"
  diagnostics="$RELEASE_DIR/otvm-windows-2022-diagnostics"
  smoke_script="$RELEASE_DIR/otvm-windows-2022-smoke.ps1"
  mkdir -p "$diagnostics"
  cat > "$smoke_script" <<'PS1'
$ErrorActionPreference = 'Stop'
$root = 'C:\gnustep-smoke\install'
$manifest = 'C:\gnustep-smoke\release\release-manifest.json'
$bootstrap = 'C:\gnustep-smoke\bootstrap\gnustep-bootstrap.ps1'
$setupOut = 'C:\gnustep-smoke\setup.json'
function Write-SmokeSummary($payload) {
  $payload | ConvertTo-Json -Depth 8 -Compress | Out-File -Encoding utf8 'C:\gnustep-smoke\summary.json'
}

try {
  & $bootstrap --json setup --root $root --manifest $manifest | Out-File -Encoding utf8 $setupOut
} catch {
  Write-SmokeSummary @{
    ok = $false
    profile = 'windows-2022'
    stage = 'bootstrap-setup'
    summary = 'Windows bootstrap setup command failed.'
    error = $_.Exception.Message
  }
  exit 1
}

$setupRaw = ''
if (Test-Path $setupOut) { $setupRaw = Get-Content $setupOut -Raw }
try {
  $setup = $setupRaw | ConvertFrom-Json
} catch {
  Write-SmokeSummary @{
    ok = $false
    profile = 'windows-2022'
    stage = 'bootstrap-setup-json'
    summary = 'Windows bootstrap setup did not emit parseable JSON.'
    error = $_.Exception.Message
    setup_raw = $setupRaw
  }
  exit 1
}
if (-not $setup.ok) {
  Write-SmokeSummary @{
    ok = $false
    profile = 'windows-2022'
    stage = 'bootstrap-setup'
    summary = 'Windows bootstrap setup failed.'
    setup = $setup
  }
  exit 1
}
$exe = Join-Path $root 'bin\gnustep.exe'
& $exe --version | Out-File -Encoding utf8 'C:\gnustep-smoke\version.txt'
cmd.exe /c "`"$exe`" --help > C:\gnustep-smoke\cmd-help.txt"
& $exe --json doctor --manifest $manifest | Out-File -Encoding utf8 'C:\gnustep-smoke\doctor.json'
$doctorRaw = Get-Content 'C:\gnustep-smoke\doctor.json' -Raw
$doctorOk = $false
$doctorCommand = $null
try {
  $doctor = $doctorRaw | ConvertFrom-Json
  $doctorCommand = $doctor.command
  if ($doctor.command -eq 'doctor') { $doctorOk = $true }
} catch {
  $doctorCommand = 'parse-error'
}
if ($doctorOk) {
  Write-SmokeSummary @{ ok = $true; profile = 'windows-2022'; summary = 'Windows bootstrap/full CLI smoke passed.' }
} else {
  Write-SmokeSummary @{ ok = $false; profile = 'windows-2022'; stage = 'doctor-json'; summary = 'Windows doctor JSON smoke failed.'; doctor_command = $doctorCommand; doctor_raw = $doctorRaw }
  exit 1
}
PS1
  ssh_guest otvmbootstrap "$host" 'powershell -NoProfile -Command "Remove-Item -Recurse -Force C:\\gnustep-smoke -ErrorAction SilentlyContinue; New-Item -ItemType Directory -Force C:\\gnustep-smoke\\release,C:\\gnustep-smoke\\bootstrap | Out-Null"'
  scp_to_guest otvmbootstrap "$host" "$RELEASE_DIR/." '/C:/gnustep-smoke/release/'
  scp_to_guest otvmbootstrap "$host" "$ROOT/scripts/bootstrap/gnustep-bootstrap.ps1" '/C:/gnustep-smoke/bootstrap/gnustep-bootstrap.ps1'
  scp_to_guest otvmbootstrap "$host" "$smoke_script" '/C:/gnustep-smoke/bootstrap/otvm-windows-2022-smoke.ps1'
  set +e
  ssh_guest otvmbootstrap "$host" 'powershell -NoProfile -ExecutionPolicy Bypass -File C:\gnustep-smoke\bootstrap\otvm-windows-2022-smoke.ps1'
  remote_status=$?
  # shellcheck disable=SC2086
  scp $SSH_OPTS "otvmbootstrap@$host:/C:/gnustep-smoke/summary.json" "$out"
  summary_status=$?
  for name in setup.json doctor.json version.txt cmd-help.txt; do
    # shellcheck disable=SC2086
    scp $SSH_OPTS "otvmbootstrap@$host:/C:/gnustep-smoke/$name" "$diagnostics/$name" >/dev/null 2>&1 || true
  done
  set -e
  if [ "$summary_status" -ne 0 ]; then
    printf '{"ok":false,"profile":"windows-2022","stage":"diagnostics","summary":"Windows smoke failed before summary.json could be retrieved.","remote_status":%s}\n' "$remote_status" > "$out"
  fi
  python3 - <<'PY2' "$out"
import json, sys
payload=json.load(open(sys.argv[1], encoding='utf-8-sig'))
print(json.dumps(payload, indent=2))
if not payload.get('ok'):
    raise SystemExit(1)
PY2
}
run_profile_probe() {
  profile="$1"
  status_file="$2"
  host=$(lease_field "$status_file" remote_access.host)
  case "$profile" in
    openbsd-7.8-fvwm) run_openbsd_probe "$host" ;;
    windows-2022) run_windows_probe "$host" ;;
    debian-13-gnome-wayland) run_debian_probe "$host" ;;
    *) printf '{"ok":true,"profile":"%s","summary":"No profile-specific smoke probe is defined."}\n' "$profile" > "$RELEASE_DIR/otvm-$profile-smoke.json" ;;
  esac
}

if [ -z "$PROFILES" ]; then
  PROFILES=$(python3 - <<'PY2' "$PLAN"
import json, sys
payload=json.load(open(sys.argv[1], encoding='utf-8-sig'))
for target in payload.get('targets', []):
    profile=target.get('profile')
    if profile and target.get('status') == 'ready':
        print(profile)
PY2
)
fi

for profile in $PROFILES; do
  printf 'creating %s\n' "$profile"
  result=$(cd "$OTVM_ROOT" && PYTHONPATH=src python3 -m oracletestvms --config "$OTVM_CONFIG" create "$profile" --ttl-hours 2 --request-key-file ~/.ssh/otvm/id_rsa.pub --progress off)
  lease=$(printf '%s\n' "$result" | python3 -c 'import json,sys; print(json.load(sys.stdin)["lease"]["lease_id"])')
  LEASES="$LEASES $lease"
  printf '%s\n' "$result" > "$RELEASE_DIR/otvm-$profile-create.json"
  status_file="$RELEASE_DIR/otvm-$profile-status.json"
  (cd "$OTVM_ROOT" && PYTHONPATH=src python3 -m oracletestvms --config "$OTVM_CONFIG" status "$lease") > "$status_file"
  run_profile_probe "$profile" "$status_file"
done
