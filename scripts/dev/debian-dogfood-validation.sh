#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
OTVM_DIR=${OTVM_DIR:-"$ROOT_DIR/../OracleTestVMs"}
OTVM_CONFIG=${OTVM_CONFIG:-"$HOME/oracletestvms-libvirt.toml"}
RELEASE_DIR=${RELEASE_DIR:-"$ROOT_DIR/dist/stable/0.1.0-dev"}
SSH_KEY=${SSH_KEY:-"$HOME/.ssh/otvm/id_rsa"}
PROFILE=${PROFILE:-debian-13-gnome-wayland}
TTL_HOURS=${TTL_HOURS:-2}
REMOTE_USER=${REMOTE_USER:-debian}
REMOTE_ROOT=${REMOTE_ROOT:-/tmp/gnustep-debian-dogfood}

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
    printf 'missing required path: %s\n' "$1" >&2
    exit 2
  fi
}

require_path "$OTVM_DIR/src/oracletestvms"
require_path "$OTVM_CONFIG"
require_path "$RELEASE_DIR/release-manifest.json"
require_path "$SSH_KEY"

otvm_json() {
  (
    cd "$OTVM_DIR"
    PYTHONPATH=src python3 -m oracletestvms --config "$OTVM_CONFIG" "$@"
  )
}

ssh_guest() {
  ssh -i "$SSH_KEY" \
    -o BatchMode=yes \
    -o ConnectTimeout=15 \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    "$REMOTE_USER@$guest_ip" "$@"
}

scp_guest() {
  scp -i "$SSH_KEY" \
    -o BatchMode=yes \
    -o ConnectTimeout=15 \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    "$@"
}

printf '[debian-dogfood] preflight %s\n' "$PROFILE" >&2
otvm_json preflight "$PROFILE" >/tmp/gnustep-debian-dogfood-preflight.json
python3 - <<'END_PREFLIGHT_PY'
import json
payload = json.load(open("/tmp/gnustep-debian-dogfood-preflight.json"))
if not payload.get("ready"):
    raise SystemExit(json.dumps(payload, indent=2))
END_PREFLIGHT_PY

printf '[debian-dogfood] create %s\n' "$PROFILE" >&2
otvm_json create "$PROFILE" --ttl-hours "$TTL_HOURS" >/tmp/gnustep-debian-dogfood-create.json
read -r lease_id guest_ip < <(python3 - <<'END_CREATE_PY'
import json
payload = json.load(open("/tmp/gnustep-debian-dogfood-create.json"))
lease = payload["lease"]
remote = lease["remote_access"]
print(lease["lease_id"], remote["host"])
END_CREATE_PY
)
printf '[debian-dogfood] lease=%s guest=%s\n' "$lease_id" "$guest_ip" >&2

printf '[debian-dogfood] stage release artifacts\n' >&2
ssh_guest "rm -rf '$REMOTE_ROOT' && mkdir -p '$REMOTE_ROOT/release' '$REMOTE_ROOT/bootstrap'"
scp_guest -r "$RELEASE_DIR/"* "$REMOTE_USER@$guest_ip:$REMOTE_ROOT/release/"
scp_guest "$ROOT_DIR/scripts/bootstrap/gnustep-bootstrap.sh" "$REMOTE_USER@$guest_ip:$REMOTE_ROOT/bootstrap/gnustep-bootstrap.sh"

printf '[debian-dogfood] run guest validation\n' >&2
ssh_guest "REMOTE_ROOT='$REMOTE_ROOT' sh -s" <<'END_REMOTE_SCRIPT'
set -eu
INSTALL_ROOT="$REMOTE_ROOT/install"
MANIFEST="$REMOTE_ROOT/release/release-manifest.json"
BOOTSTRAP="$REMOTE_ROOT/bootstrap/gnustep-bootstrap.sh"
RESULTS="$REMOTE_ROOT/results"
mkdir -p "$RESULTS"
chmod +x "$BOOTSTRAP"
current_step="init"
trap 'status=$?; if [ "$status" -ne 0 ]; then echo "[remote] failed step=$current_step status=$status" >&2; for file in "$RESULTS"/*; do [ -e "$file" ] || continue; echo "[remote] ==== $file ==== " >&2; tail -n 120 "$file" >&2 || true; done; fi; exit "$status"' EXIT

current_step="host prerequisites"
sudo apt-get update >"$RESULTS/apt-update.stdout" 2>"$RESULTS/apt-update.stderr"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y clang make >"$RESULTS/apt-install.stdout" 2>"$RESULTS/apt-install.stderr"

current_step="bootstrap setup"
"$BOOTSTRAP" --json setup --root "$INSTALL_ROOT" --manifest "$MANIFEST" >"$RESULTS/setup.json"
python3 - "$RESULTS/setup.json" <<'END_SETUP_PY'
import json, sys
payload = json.load(open(sys.argv[1]))
if not payload.get("ok"):
    raise SystemExit(json.dumps(payload, indent=2))
END_SETUP_PY

current_step="installed version"
"$INSTALL_ROOT/bin/gnustep" --version >"$RESULTS/version.txt" 2>"$RESULTS/version.stderr"
current_step="installed help"
"$INSTALL_ROOT/bin/gnustep" --help >"$RESULTS/help.txt" 2>"$RESULTS/help.stderr"
current_step="installed doctor"
"$INSTALL_ROOT/bin/gnustep" doctor --json --manifest "$MANIFEST" >"$RESULTS/doctor.json" 2>"$RESULTS/doctor.stderr"
python3 - "$RESULTS/doctor.json" <<'END_DOCTOR_PY'
import json, sys
payload = json.load(open(sys.argv[1]))
env = payload.get("environment", {})
toolchain = env.get("toolchain", {})
assessment = env.get("native_toolchain", {})
if payload.get("command") != "doctor":
    raise SystemExit("doctor command metadata missing")
if env.get("os") != "linux" or env.get("arch") != "amd64":
    raise SystemExit(f"unexpected host: {env.get('os')}/{env.get('arch')}")
if toolchain.get("compiler_family") != "clang":
    raise SystemExit(f"expected managed clang toolchain, got {toolchain.get('compiler_family')}")
if toolchain.get("objc_runtime") != "libobjc2":
    raise SystemExit(f"expected libobjc2, got {toolchain.get('objc_runtime')}")
if assessment.get("preference") not in ("native", "managed"):
    raise SystemExit("native toolchain assessment missing preference")
END_DOCTOR_PY

cat >"$REMOTE_ROOT/probe.m" <<'END_PROBE'
#import <Foundation/Foundation.h>
int main(void) {
  @autoreleasepool {
    NSLog(@"debian-managed-probe-ok");
  }
  return 0;
}
END_PROBE
current_step="managed environment activation"
export PATH="$INSTALL_ROOT/bin:$INSTALL_ROOT/Tools:$INSTALL_ROOT/System/Tools:$INSTALL_ROOT/Local/Tools:$PATH"
export LD_LIBRARY_PATH="$INSTALL_ROOT/Library/Libraries:$INSTALL_ROOT/Local/Library/Libraries:$INSTALL_ROOT/System/Library/Libraries:$INSTALL_ROOT/lib:$INSTALL_ROOT/lib64:${LD_LIBRARY_PATH:-}"
current_step="managed clang probe compile"
objc_flags=$($INSTALL_ROOT/System/Tools/gnustep-config --objc-flags)
base_libs=$($INSTALL_ROOT/System/Tools/gnustep-config --base-libs)
# shellcheck disable=SC2086
clang $objc_flags "$REMOTE_ROOT/probe.m" -o "$REMOTE_ROOT/probe" $base_libs >"$RESULTS/probe-compile.stdout" 2>"$RESULTS/probe-compile.stderr"
current_step="managed clang probe run"
"$REMOTE_ROOT/probe" >"$RESULTS/probe.stdout" 2>"$RESULTS/probe.stderr"
grep -q "debian-managed-probe-ok" "$RESULTS/probe.stderr"

current_step="native cli new/build/run"
WORKFLOW_ROOT="$REMOTE_ROOT/workflow"
mkdir -p "$WORKFLOW_ROOT"
cd "$WORKFLOW_ROOT"
"$INSTALL_ROOT/bin/gnustep" new cli-tool DogfoodTool --json >"$RESULTS/new.json" 2>"$RESULTS/new.stderr"
cd "$WORKFLOW_ROOT/DogfoodTool"
"$INSTALL_ROOT/bin/gnustep" build --json >"$RESULTS/build.json" 2>"$RESULTS/build.stderr"
"$INSTALL_ROOT/bin/gnustep" run --json >"$RESULTS/run.json" 2>"$RESULTS/run.stderr"
python3 - "$RESULTS/new.json" "$RESULTS/build.json" "$RESULTS/run.json" <<'END_WORKFLOW_PY'
import json, sys
for path in sys.argv[1:]:
    payload = json.load(open(path))
    if not payload.get("ok"):
        raise SystemExit(json.dumps(payload, indent=2))
END_WORKFLOW_PY
cd "$REMOTE_ROOT"

mkdir -p "$REMOTE_ROOT/package-payload/bin"
printf '#!/bin/sh\nprintf demo-package-ok\\n\n' >"$REMOTE_ROOT/package-payload/bin/demo-package-tool"
chmod +x "$REMOTE_ROOT/package-payload/bin/demo-package-tool"
tar -czf "$REMOTE_ROOT/demo-package.tar.gz" -C "$REMOTE_ROOT/package-payload" .
sha=$(sha256sum "$REMOTE_ROOT/demo-package.tar.gz" | awk '{print $1}')
cat >"$REMOTE_ROOT/package-index.json" <<END_INDEX
{
  "schema_version": 1,
  "channel": "dogfood",
  "packages": [
    {
      "id": "org.gnustep.demo-debian-dogfood",
      "name": "demo-debian-dogfood",
      "version": "0.1.0",
      "kind": "cli-tool",
      "summary": "Temporary Debian dogfood package fixture.",
      "requirements": {
        "supported_os": ["linux"],
        "supported_arch": ["amd64"],
        "supported_compiler_families": ["clang"],
        "supported_objc_runtimes": ["libobjc2"],
        "supported_objc_abi": ["modern"],
        "required_features": ["blocks"],
        "forbidden_features": []
      },
      "dependencies": [],
      "artifacts": [
        {
          "id": "demo-linux-clang",
          "os": "linux",
          "arch": "amd64",
          "compiler_family": "clang",
          "toolchain_flavor": "clang",
          "objc_runtime": "libobjc2",
          "objc_abi": "modern",
          "required_features": ["blocks"],
          "url": "file://$REMOTE_ROOT/demo-package.tar.gz",
          "sha256": "$sha"
        }
      ]
    }
  ]
}
END_INDEX
current_step="package install"
"$INSTALL_ROOT/bin/gnustep" install --json --root "$INSTALL_ROOT" --index "$REMOTE_ROOT/package-index.json" org.gnustep.demo-debian-dogfood >"$RESULTS/package-install.json" 2>"$RESULTS/package-install.stderr"
current_step="package remove"
"$INSTALL_ROOT/bin/gnustep" remove --json --root "$INSTALL_ROOT" org.gnustep.demo-debian-dogfood >"$RESULTS/package-remove.json" 2>"$RESULTS/package-remove.stderr"
python3 - "$RESULTS/package-install.json" "$RESULTS/package-remove.json" <<'END_PACKAGE_PY'
import json, sys
for path in sys.argv[1:]:
    payload = json.load(open(path))
    if not payload.get("ok"):
        raise SystemExit(json.dumps(payload, indent=2))
END_PACKAGE_PY

trap - EXIT
printf '{"ok":true,"summary":"Debian dogfood validation passed."}\n' >"$RESULTS/summary.json"
END_REMOTE_SCRIPT

printf '[debian-dogfood] fetch summary\n' >&2
scp_guest "$REMOTE_USER@$guest_ip:$REMOTE_ROOT/results/summary.json" /tmp/gnustep-debian-dogfood-summary.json
cat /tmp/gnustep-debian-dogfood-summary.json
