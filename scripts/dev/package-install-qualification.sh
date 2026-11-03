#!/bin/sh
# Install one package artifact into a managed root set up by the PUBLISHED
# bootstrap, inside a clean container of the target distro release, then smoke
# its declared executables and remove it again.
#
# usage: package-install-qualification.sh <package-id> <artifact-id> <artifact-file> <bootstrap.sh> <out-dir> [cli-tarball]
# cli-tarball overlays an unreleased CLI on the bootstrap-installed root. The install
# goes through a throwaway signed manifest that advertises the one-package index
# (scripts/dev/make-qualification-release.py), with no --index, and a tampered index
# must be refused first.
# The repository is expected at $REPO (default /src); it supplies the package
# manifest the one-package index is generated from.
set -eu
PKG_ID=$1
ARTIFACT_ID=$2
ARTIFACT_FILE=$3
BOOTSTRAP=$4
OUT=$5
CLI_TARBALL=${6:-}
REPO=${REPO:-/src}
USER_NAME=gsqualify
mkdir -p "$OUT"

export DEBIAN_FRONTEND=noninteractive
apt-get update >/dev/null
apt-get install -y --no-install-recommends sudo ca-certificates curl python3 binutils openssl >/dev/null

id "$USER_NAME" >/dev/null 2>&1 || useradd -m -s /bin/sh "$USER_NAME"
printf '%s ALL=(ALL) NOPASSWD:ALL\n' "$USER_NAME" > /etc/sudoers.d/gsqualify
chmod 0440 /etc/sudoers.d/gsqualify
work=$(su - "$USER_NAME" -c 'mktemp -d')
R="$work/root"
cp "$BOOTSTRAP" "$work/gnustep-bootstrap.sh"
cp "$ARTIFACT_FILE" "$work/"
artifact="$work/$(basename "$ARTIFACT_FILE")"
chown -R "$USER_NAME" "$work"

steps="$OUT/steps.txt"
: > "$steps"
step() {
  name=$1; shift
  set +e
  su - "$USER_NAME" -c "cd '$work' && R='$R' $*" > "$OUT/$name.out" 2> "$OUT/$name.err"
  rc=$?
  set -e
  printf '%s %s\n' "$name" "$rc" >> "$steps"
  return 0
}

step setup "sh ./gnustep-bootstrap.sh --json setup --yes --root '$R'"
if [ -n "$CLI_TARBALL" ]; then
  tar -xzf "$CLI_TARBALL" --strip-components=1 -C "$R"
  chown -R "$USER_NAME" "$R"
fi

# One-package index from the checkout's manifests; the artifact points at the
# file under test so its bytes, not a published URL, are what gets installed.
PYTHONPATH="$REPO/src" python3 - "$REPO/packages" "$PKG_ID" "$ARTIFACT_ID" "$artifact" "$work/package-index.json" <<'PY'
import hashlib, json, os, sys
from gnustep_cli_shared.package_repository import generate_package_index
packages_dir, package_id, artifact_id, artifact_path, output = sys.argv[1:]
index = generate_package_index(packages_dir)
index["packages"] = [p for p in index["packages"] if p["id"] == package_id]
if len(index["packages"]) != 1:
    raise SystemExit(f"package {package_id} not found")
matches = [a for a in index["packages"][0]["artifacts"] if a["id"] == artifact_id]
if len(matches) != 1:
    raise SystemExit(f"artifact {artifact_id} not declared by {package_id}")
artifact = matches[0]
digest = hashlib.sha256(open(artifact_path, "rb").read()).hexdigest()
artifact.update({"url": "file://" + artifact_path, "sha256": digest, "size": os.path.getsize(artifact_path),
                 "filename": os.path.basename(artifact_path), "publish": True})
json.dump(index, open(output, "w"), indent=2)
PY
chown "$USER_NAME" "$work/package-index.json"

trust_root=$(python3 "$REPO/scripts/dev/make-qualification-release.py" --work "$work" --root "$R")
chown -R "$USER_NAME" "$work"
gnustep="RELEASE_TRUST_ROOT='$trust_root' '$R/bin/gnustep'"

# A changed index must be refused: its digest no longer matches the signed manifest.
cp "$work/package-index.json" "$work/package-index.good"
printf '\n' >> "$work/package-index.json"
step tampered_index "! $gnustep --json list --root '$R' > tampered.json; grep -q 'does not match the release manifest' tampered.json"
cp "$work/package-index.good" "$work/package-index.json"
chown "$USER_NAME" "$work/package-index.json"

step install "$gnustep --json install --root '$R' '$PKG_ID'"

# Smoke every declared executable through the managed environment.
executables=$(python3 -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1]))["install"].get("executables", [])))' "$REPO/packages/$PKG_ID/package.json")
cat > "$work/smoke.sh" <<SMOKE
set -u
set +u
. "\$R/System/Library/Makefiles/GNUstep.sh" >/dev/null 2>&1
set -u
pkg="\$R/packages/$PKG_ID"
status=0
for exe in $executables; do
  path="\$pkg/bin/\$exe"
  if [ ! -x "\$path" ]; then echo "\$exe missing"; status=1; continue; fi
  if ldd "\$path" | grep -q "not found"; then echo "\$exe has unresolved libraries:"; ldd "\$path" | grep "not found"; status=1; fi
  "\$path" --help >/dev/null 2>&1 < /dev/null
  rc=\$?
  echo "\$exe --help exit \$rc"
  # 126+ means it could not execute or died on a signal (loader failure, crash).
  if [ "\$rc" -ge 126 ]; then status=1; fi
done
exit \$status
SMOKE
chown "$USER_NAME" "$work/smoke.sh"
step smoke "sh ./smoke.sh"

step remove "$gnustep --json remove --root '$R' '$PKG_ID'"
step leftovers "test ! -e '$R/packages/$PKG_ID' && for exe in $executables; do test ! -e '$R/bin/'\$exe || exit 1; done && ! grep -q '\"$PKG_ID\"' '$R/state/installed-packages.json'"

python3 - "$OUT" "$PKG_ID" "$ARTIFACT_ID" "$artifact" <<'PY'
import hashlib, json, os, sys
out, package_id, artifact_id, artifact = sys.argv[1:]
steps = dict(line.split() for line in open(os.path.join(out, "steps.txt")) if line.strip())
def last_json(name):
    text = open(os.path.join(out, name + ".out")).read().strip()
    for line in reversed(text.splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            pass
    try:
        return json.loads(text)
    except ValueError:
        return {}
install = last_json("install")
summary = {
    "schema_version": 1,
    "kind": "package-install-qualification",
    "package_id": package_id,
    "artifact_id": artifact_id,
    "artifact_sha256": hashlib.sha256(open(artifact, "rb").read()).hexdigest(),
    "os_release": dict(line.rstrip("\n").split("=", 1) for line in open("/etc/os-release") if "=" in line),
    "steps": steps,
    "selected_artifact": install.get("selected_artifact"),
    "installed_version": install.get("version"),
    "smoke": open(os.path.join(out, "smoke.out")).read().strip().splitlines(),
    "ok": all(steps.get(name) == "0" for name in ("setup", "tampered_index", "install", "smoke", "remove", "leftovers"))
          and install.get("selected_artifact") == artifact_id,
}
json.dump(summary, open(os.path.join(out, "package-install-qualification.json"), "w"), indent=2)
print(json.dumps(summary, indent=2))
raise SystemExit(0 if summary["ok"] else 1)
PY
