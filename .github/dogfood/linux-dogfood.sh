#!/bin/sh
# tools-xctest qualification on the staged v0.1.9 CLI and toolchain, as an unprivileged user
# in the target's distro container. Usage: linux-dogfood.sh <repo> <cli-artifacts-dir> <xctest-package> <out> <target>
set -u
REPO=$1; ARTIFACTS=$2; PKG=$3; OUT=$4; T=$5
export HOME=${HOME:?}
R=$HOME/.local/share/gnustep-cli
W=$HOME/dogfood; mkdir -p "$W" "$OUT"
log=$OUT/dogfood.txt
say() { printf '%s\n' "$*" | tee -a "$log"; }
step() { name=$1; shift; "$@" > "$OUT/$name.txt" 2>&1; rc=$?; say "$name exit $rc"; return $rc; }
cli=$(ls "$ARTIFACTS"/gnustep-cli-$T-*.tar.gz); toolchain=$(ls "$ARTIFACTS"/gnustep-toolchain-$T-*.tar.gz)
version=${cli##*/gnustep-cli-$T-}; version=${version%.tar.gz}
say "cli $(sha256sum "$cli" | cut -c1-12) toolchain $(sha256sum "$toolchain" | cut -c1-12) package $(sha256sum "$PKG" | cut -c1-12) version $version"
PYTHONPATH="$REPO/src" python3 - "$T" "$version" "$toolchain" "$cli" "$W/release-manifest.json" <<'PY'
import hashlib, json, sys
from gnustep_cli_shared.build_infra import release_manifest_from_matrix
target, version, toolchain, cli, output = sys.argv[1:]
manifest = release_manifest_from_matrix(version, "file:///unused")
paths = {f"cli-{target}": cli, f"toolchain-{target}": toolchain}
release = manifest["releases"][0]
release["artifacts"] = [a for a in release["artifacts"] if a["id"] in paths]
for artifact in release["artifacts"]:
    digest = hashlib.sha256(open(paths[artifact["id"]], "rb").read()).hexdigest()
    artifact.update({"url": "file://" + paths[artifact["id"]], "sha256": digest, "integrity": {"sha256": digest}, "published": True})
json.dump(manifest, open(output, "w"), indent=2)
PY
step setup env GNUSTEP_BOOTSTRAP_ALLOW_UNSIGNED=1 sh "$REPO/scripts/bootstrap/gnustep-bootstrap.sh" --yes --json setup --user --manifest "$W/release-manifest.json" || exit 1
export PATH="$R/bin:$PATH"
step version gnustep --version
python3 "$REPO/.github/dogfood/make-index.py" "$REPO" "tools-xctest-$T" "$PKG" "file://$PKG" "$W/index" | tee -a "$log"
python3 "$REPO/scripts/dev/make-qualification-release.py" --work "$W/index" --root "$R" | tee -a "$log"
export RELEASE_TRUST_ROOT="$W/index/qualification-signing-public.pem"
step install gnustep install --json --root "$R" org.gnustep.tools-xctest
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print('install ok', d.get('ok'), 'links', [(l['kind'], l['path']) for l in d.get('executable_links', [])])" "$OUT/install.txt" | tee -a "$log"
step xctest-help "$R/bin/xctest" --help
cp -R "$REPO/.github/dogfood/sample" "$W/sample"
bash "$REPO/.github/dogfood/checks.sh" "$R" "$R/System/Library/Makefiles" "$W/sample" "$OUT" "$R/packages/org.gnustep.tools-xctest/bin/xctest"
step remove gnustep remove --json --root "$R" org.gnustep.tools-xctest
left=$(ls -d "$R/packages/org.gnustep.tools-xctest" "$R/System/Library/Makefiles/Auxiliary/xctest.make" "$R/bin/xctest" "$R/bin/xctest-bundle" 2>/dev/null)
say "left after remove: ${left:-none}"
say "done"
