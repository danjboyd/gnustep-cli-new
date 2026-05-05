set -eu

SMOKE="$HOME/gnustep-openbsd-release-smoke"
SRC="$HOME/gnustep-cli-new"
INSTALL_ROOT="$HOME/.local/share/gnustep-cli-openbsd-release"
BOOTSTRAP="$SMOKE/gnustep-bootstrap.sh"
SUMMARY="$SMOKE/openbsd-full-release-evidence.json"

rm -rf "$SMOKE" "$SRC" "$INSTALL_ROOT" "$HOME/SmokeToolOpenBSD" "$HOME/apps-gorm-1_5_0" "$HOME/apps-gorm-gorm-1_5_0" "$HOME/apps-gorm-1.5.0.tar.gz"
mkdir -p "$SMOKE"
cp "$HOME/full-cli-src-only.tar.gz" "$SMOKE/full-cli-src-only.tar.gz"
cp "$HOME/gnustep-bootstrap.sh" "$BOOTSTRAP"
cp "$HOME/openbsd_bootstrap_smoke.py" "$SMOKE/openbsd_bootstrap_smoke.py"
cp "$HOME/openbsd_self_update_smoke.py" "$SMOKE/openbsd_self_update_smoke.py"
chmod +x "$BOOTSTRAP"

doas pkg_add -I python gmake gnustep-make gnustep-base gnustep-gui gnustep-back gnustep-libobjc2 >/tmp/gnustep-openbsd-pkg-add.log 2>&1 || true

mkdir -p "$SRC"
tar -xzf "$SMOKE/full-cli-src-only.tar.gz" -C "$SRC"
set +u
. /usr/local/share/GNUstep/Makefiles/GNUstep.sh
set -u
export GNUSTEP_MAKEFILES=/usr/local/share/GNUstep/Makefiles
cd "$SRC/src/full-cli"
gmake clean >/dev/null 2>&1 || true
gmake > "$SMOKE/full-cli-build.log" 2>&1

python3 "$SMOKE/openbsd_bootstrap_smoke.py" > "$SMOKE/bootstrap-fixture.json"
BOOTSTRAP_MANIFEST=$(python3 -c 'import json; print(json.load(open("'"$SMOKE"'/bootstrap-fixture.json"))["manifest"])')
"$BOOTSTRAP" --json setup --root "$INSTALL_ROOT" --manifest "$BOOTSTRAP_MANIFEST" > "$SMOKE/bootstrap-setup.json"
python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); raise SystemExit(0 if p.get("ok") else 1)' "$SMOKE/bootstrap-setup.json"

export PATH="$INSTALL_ROOT/bin:$INSTALL_ROOT/Tools:$INSTALL_ROOT/System/Tools:$PATH"
gnustep --version > "$SMOKE/version.txt" 2>&1
gnustep --json doctor --manifest "$BOOTSTRAP_MANIFEST" > "$SMOKE/doctor.json" 2>&1
python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); raise SystemExit(0 if p.get("command") == "doctor" else 1)' "$SMOKE/doctor.json"

cd "$HOME"
gnustep --json new cli-tool "$HOME/SmokeToolOpenBSD" --name SmokeToolOpenBSD > "$SMOKE/new-project.json"
cd "$HOME/SmokeToolOpenBSD"
gnustep --json build > "$SMOKE/new-project-build.json"
gnustep run > "$SMOKE/new-project-run.txt" 2>&1
grep -q "Hello from CLI tool" "$SMOKE/new-project-run.txt"

cd "$HOME"
ftp -Vo "$HOME/apps-gorm-1.5.0.tar.gz" https://github.com/gnustep/apps-gorm/archive/refs/tags/gorm-1_5_0.tar.gz > "$SMOKE/gorm-download.log" 2>&1
tar -xzf "$HOME/apps-gorm-1.5.0.tar.gz"
if [ -d "$HOME/apps-gorm-gorm-1_5_0" ]; then
  GORM="$HOME/apps-gorm-gorm-1_5_0"
else
  GORM="$HOME/apps-gorm-1_5_0"
fi
cd "$GORM"
gnustep --json build > "$SMOKE/gorm-build.json" 2>"$SMOKE/gorm-build.stderr"
set +e
env DISPLAY=:1 gnustep run --no-build > "$SMOKE/gorm-run.txt" 2>&1 &
GORM_PID=$!
sleep 5
if kill -0 "$GORM_PID" 2>/dev/null; then
  GORM_ALIVE=true
  kill "$GORM_PID" 2>/dev/null || true
else
  wait "$GORM_PID"
  GORM_STATUS=$?
  if [ "$GORM_STATUS" -eq 0 ]; then GORM_ALIVE=true; else GORM_ALIVE=false; fi
fi
set -e
if [ "$GORM_ALIVE" != true ]; then
  echo "Gorm did not stay alive or exit cleanly" >&2
  exit 1
fi

python3 "$SMOKE/openbsd_self_update_smoke.py" > "$SMOKE/self-update-fixture.json"
UPDATE_ROOT=$(python3 -c 'import json; print(json.load(open("'"$SMOKE"'/self-update-fixture.json"))["install_root"])')
UPDATE_MANIFEST=$(python3 -c 'import json; print(json.load(open("'"$SMOKE"'/self-update-fixture.json"))["manifest"])')
"$UPDATE_ROOT/bin/gnustep" update --check --manifest "$UPDATE_MANIFEST" > "$SMOKE/self-update-check.txt" 2>&1
"$UPDATE_ROOT/bin/gnustep" --json update cli --yes --root "$UPDATE_ROOT" --manifest "$UPDATE_MANIFEST" > "$SMOKE/self-update.json" 2>&1
python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); raise SystemExit(0 if p.get("ok") else 1)' "$SMOKE/self-update.json"

python3 - <<'PY' "$SUMMARY"
import json, sys
summary = {
  "schema_version": 1,
  "command": "openbsd-full-release-evidence",
  "ok": True,
  "status": "ok",
  "summary": "OpenBSD native-packaged full release smoke passed on OTVM.",
  "target_id": "openbsd-amd64-clang",
  "scenarios": {
    "bootstrap-install-usable-cli": ["bootstrap-setup.json", "doctor.json", "version.txt"],
    "new-cli-project-build-run": ["new-project.json", "new-project-build.json", "new-project-run.txt"],
    "gorm-build-run": ["gorm-build.json", "gorm-run.txt"],
    "self-update-cli-only": ["self-update.json", "self-update-check.txt"],
  },
}
open(sys.argv[1], "w").write(json.dumps(summary, indent=2) + "\n")
PY
