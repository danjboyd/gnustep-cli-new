#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
INSTALL_ROOT=${INSTALL_ROOT:-"$ROOT_DIR/.artifacts/update-all-production-like/install"}
OLD_MANIFEST=${OLD_MANIFEST:?set OLD_MANIFEST to the starting release manifest}
NEW_MANIFEST=${NEW_MANIFEST:?set NEW_MANIFEST to the target release manifest}
PACKAGE_ID=${PACKAGE_ID:-org.gnustep.tools-xctest}
TARGET_ID=${TARGET_ID:-local-managed}
EVIDENCE_DIR=${EVIDENCE_DIR:-"$ROOT_DIR/.artifacts/update-all-production-like/evidence"}
BOOTSTRAP=${BOOTSTRAP:-"$ROOT_DIR/scripts/bootstrap/gnustep-bootstrap.sh"}

mkdir -p "$EVIDENCE_DIR"

run_json() {
  local name=$1
  shift
  "$@" >"$EVIDENCE_DIR/$name.json" 2>"$EVIDENCE_DIR/$name.stderr"
}

require_ok_json() {
  python3 - "$1" <<'PY'
import json
import sys
payload = json.load(open(sys.argv[1], encoding="utf-8-sig"))
if not payload.get("ok"):
    raise SystemExit(json.dumps(payload, indent=2))
PY
}

copy_state() {
  local name=$1
  if [[ -f "$INSTALL_ROOT/state/cli-state.json" ]]; then
    cp "$INSTALL_ROOT/state/cli-state.json" "$EVIDENCE_DIR/$name"
  fi
}

rm -rf "$INSTALL_ROOT"
chmod +x "$BOOTSTRAP"

started_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

run_json setup-old "$BOOTSTRAP" --json setup --root "$INSTALL_ROOT" --manifest "$OLD_MANIFEST" --yes
require_ok_json "$EVIDENCE_DIR/setup-old.json"
copy_state cli-state-before.json

run_json update-check "$INSTALL_ROOT/bin/gnustep" update all --check --json --root "$INSTALL_ROOT" --manifest "$NEW_MANIFEST"
require_ok_json "$EVIDENCE_DIR/update-check.json"

run_json update-all "$INSTALL_ROOT/bin/gnustep" update all --yes --json --root "$INSTALL_ROOT" --manifest "$NEW_MANIFEST"
require_ok_json "$EVIDENCE_DIR/update-all.json"
copy_state cli-state-after.json

"$INSTALL_ROOT/bin/gnustep" --version >"$EVIDENCE_DIR/version.txt" 2>"$EVIDENCE_DIR/version.stderr"
run_json doctor "$INSTALL_ROOT/bin/gnustep" doctor --json --manifest "$NEW_MANIFEST"

completed_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

python3 - "$EVIDENCE_DIR" "$TARGET_ID" "$PACKAGE_ID" "$started_at" "$completed_at" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
target_id = sys.argv[2]
package_id = sys.argv[3]
started_at = sys.argv[4]
completed_at = sys.argv[5]

update = json.loads((root / "update-all.json").read_text(encoding="utf-8-sig"))
check = json.loads((root / "update-check.json").read_text(encoding="utf-8-sig"))
before_path = root / "cli-state-before.json"
after_path = root / "cli-state-after.json"
before = json.loads(before_path.read_text(encoding="utf-8-sig")) if before_path.exists() else {}
after = json.loads(after_path.read_text(encoding="utf-8-sig")) if after_path.exists() else {}

package_updates = []
for candidate in update.get("package_updates", []) or update.get("packages", []) or []:
    if isinstance(candidate, dict):
        package_updates.append({
            "id": candidate.get("id") or candidate.get("package_id") or package_id,
            "from_version": candidate.get("from_version"),
            "to_version": candidate.get("to_version"),
            "ok": bool(candidate.get("ok", update.get("ok"))),
        })
if not package_updates:
    package_updates.append({"id": package_id, "from_version": None, "to_version": None, "ok": bool(update.get("ok"))})

payload = {
    "schema_version": 1,
    "ok": bool(update.get("ok")),
    "summary": "gnustep update all --yes passed on a production-like managed install.",
    "production_like": True,
    "command": "gnustep update all --yes",
    "target": target_id,
    "started_at": started_at,
    "completed_at": completed_at,
    "scopes": {"cli": True, "toolchain": True, "packages": True},
    "release_transition": {
        "from_version": before.get("cli_version") or before.get("version") or before.get("active_release_version"),
        "to_version": after.get("cli_version") or after.get("version") or after.get("active_release_version"),
    },
    "package_updates": package_updates,
    "result": {"ok": bool(update.get("ok")), "exit_code": 0},
    "artifacts": {
        "setup": "setup-old.json",
        "check": "update-check.json",
        "stdout": "update-all.json",
        "stderr": "update-all.stderr",
        "doctor": "doctor.json",
        "state_before": "cli-state-before.json",
        "state_after": "cli-state-after.json",
        "version": "version.txt",
    },
    "raw_update_check": check,
    "raw_update_result": update,
}
(root / "update-all-production-like.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

python3 "$ROOT_DIR/scripts/internal/build_infra.py" --json validate-update-all-evidence \
  --evidence "$EVIDENCE_DIR/update-all-production-like.json" >/dev/null

printf '%s\n' "$EVIDENCE_DIR/update-all-production-like.json"
