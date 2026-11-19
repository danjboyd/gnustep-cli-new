#!/usr/bin/env bash
# Linux gate for the patch layer's CLI side (docs/specs/patch-layer.md), the counterpart of
# variant-gate.ps1. Runs as root in a clean debian:13 container (linux-carry-layer.yml).
#
# Usage: linux-variant-gate.sh <target> <cli.tar.gz> <toolchain.tar.gz> <layer.zip> <out-dir>
#
# It stages two releases from the given archives, X (0.1.9) and Y (0.1.10, the same
# artifacts relabelled), each with cli, toolchain and carry-layer artifacts, signed with a
# throwaway key trusted only here. Then:
#   1. bootstrap `setup --variant patched` installs stock, then the CLI applies the layer;
#   2. every layer file is patched, and doctor reports managed.toolchain.variant ok/patched;
#   3. `setup --variant stock` restores stock: the toolchain tree is byte-identical to before;
#   4. `setup --variant patched` switches back without reinstalling;
#   5. `update` to Y keeps the variant;
#   6. doctor afterwards reports the patched variant intact.
set -uo pipefail

target=${1:?usage: linux-variant-gate.sh <target> <cli.tar.gz> <toolchain.tar.gz> <layer.zip> <out-dir>}
cli=${2:?}
toolchain=${3:?}
layer=${4:?}
out=${5:?}
repo=$(cd "$(dirname "$0")/../.." && pwd)
export PYTHONPATH="$repo/src"
mkdir -p "$out"
log="$out/variant-gate.txt"
: > "$log"
say() { echo "$*" | tee -a "$log"; }

# Host prerequisites, from the bootstrap's own list, plus what the gate itself uses.
packages=$(sh -c ". /dev/stdin; host_prerequisite_packages debian" <<EOF
$(sed -n '/^host_prerequisite_packages()/,/^}/p' "$repo/scripts/bootstrap/gnustep-bootstrap.sh")
EOF
)
apt-get update -qq
# shellcheck disable=SC2086
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends $packages openssl python3 >/dev/null
say "host prerequisites: $packages"

gate=/work/variant-gate
release="$gate/release"
root="$gate/root"
mkdir -p "$release"
python3 - "$target" "$cli" "$toolchain" "$layer" "$gate/staged" "$release" <<'PY'
import json, pathlib, sys
from gnustep_cli_shared.build_infra import stage_release_assets
target, cli, toolchain, layer, staged, dest = sys.argv[1:7]
stage_release_assets("0.1.9", staged, "https://gate.invalid/releases",
                     cli_inputs={target: cli}, toolchain_inputs={target: toolchain}, carry_inputs={target: layer})
src = pathlib.Path(staged) / "stable" / "0.1.9"
dest = pathlib.Path(dest)
manifest = json.loads((src / "release-manifest.json").read_text())
for f in src.iterdir():
    if f.suffix in (".zip", ".gz"):
        (dest / f.name).write_bytes(f.read_bytes())
print([(a["id"], a["sha256"][:12]) for a in manifest["releases"][0]["artifacts"]])
for name, version, meta in (("x", "0.1.9", 1), ("y", "0.1.10", 2)):
    m = json.loads(json.dumps(manifest))
    m["metadata_version"] = meta
    m["releases"][0]["version"] = version
    for a in m["releases"][0]["artifacts"]:
        a["version"] = version
        if isinstance(a.get("requires_toolchain"), dict):
            a["requires_toolchain"]["version"] = version
    (dest / f"release-manifest.{name}.json").write_text(json.dumps(m, indent=2))
import zipfile
(dest / "carry-layer.json").write_bytes(zipfile.ZipFile(layer).read("carry-layer.json"))
PY
[ -f "$release/release-manifest.x.json" ] || { say "STOP: staging failed"; exit 1; }

# Throwaway P-256 key; the bootstrap and the CLI verify DER ECDSA signatures with it.
openssl ecparam -name prime256v1 -genkey -noout -out "$gate/key.pem" 2>/dev/null
openssl ec -in "$gate/key.pem" -pubout -out "$out/trust-root.pem" 2>/dev/null
for m in x y; do
  openssl dgst -sha256 -sign "$gate/key.pem" -out "$release/release-manifest.$m.json.sig" "$release/release-manifest.$m.json"
done
export RELEASE_TRUST_ROOT="$out/trust-root.pem"
export GNUSTEP_BOOTSTRAP_SKIP_PATH_UPDATE=1
sed 's/^CLI_VERSION=.*/CLI_VERSION="0.1.9"/' "$repo/scripts/bootstrap/gnustep-bootstrap.sh" > "$gate/gnustep-bootstrap.sh"

exe="$root/bin/gnustep"
with_root() { PATH="$root/bin:$root/Tools:$root/System/Tools:$PATH" "$@"; }
json_field() { # <file> <python expression on d>
  python3 - "$1" "$2" <<'PY'
import json, sys
text = open(sys.argv[1], errors="replace").read()
start = text.find("{")
try:
    d = json.loads(text[start:]) if start >= 0 else {}
except ValueError:
    d = {}
try:
    print(eval(sys.argv[2], {"d": d}))
except Exception:
    print("")
PY
}
layer_state() {
  python3 - "$release/carry-layer.json" "$root" <<'PY'
import hashlib, json, sys
from pathlib import Path
files = json.load(open(sys.argv[1]))["files"]
root = Path(sys.argv[2])
p = s = 0
for f in files:
    path = root / f["path"]
    h = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
    p += h == f["sha256"]
    s += h == f["stock_sha256"]
print("patched" if p == len(files) else "stock" if s == len(files) else f"mixed (patched {p}, stock {s} of {len(files)})")
PY
}
tree_digest() { # every toolchain file outside state/, by path and content
  (cd "$root" && find . -path ./state -prune -o -type f -print | LC_ALL=C sort | xargs -d '\n' sha256sum | sha256sum | cut -c1-64)
}
doctor_variant() { # <name>
  with_root "$exe" doctor --json > "$out/$1-doctor.txt" 2>&1
  json_field "$out/$1-doctor.txt" "next((c['status'] + '/' + str(c['details'].get('toolchain_variant')) for c in d.get('checks', []) if c.get('id') == 'managed.toolchain.variant'), 'missing')"
}
step() { # <name> <command...>
  local name=$1; shift
  with_root "$@" > "$out/$name.txt" 2>&1
  local code=$?
  local files doctor variant
  files=$(layer_state)
  doctor=$(doctor_variant "$name")
  variant=$(json_field "$root/state/cli-state.json" "d.get('toolchain_variant')")
  say "$name: exit $code; files $files; state toolchain_variant=$variant; doctor $doctor"
  printf '%s|%s|%s\n' "$code" "$files" "$doctor" > "$out/$name.result"
}
result() { cut -d'|' -f"$2" "$out/$1.result"; }

# 1. Bootstrap with --variant patched.
sh "$gate/gnustep-bootstrap.sh" --json setup --user --variant patched --root "$root" --manifest "$release/release-manifest.x.json" > "$out/bootstrap.txt" 2> "$out/bootstrap-stderr.txt"
bs_code=$?
bs_variant=$(json_field "$out/bootstrap.txt" "d.get('toolchain_variant')")
bs_files=$(layer_state)
bs_doctor=$(doctor_variant bootstrap)
say "bootstrap --variant patched: exit $bs_code; json toolchain_variant=$bs_variant; files $bs_files; doctor $bs_doctor"
ok=no
if [ "$bs_code" -ne 0 ]; then
  say "STOP: the bootstrap failed"; tail -n 20 "$out/bootstrap.txt" "$out/bootstrap-stderr.txt" | tee -a "$log"
else
  # 3. Back to stock.
  step to-stock "$exe" setup --variant stock --root "$root" --json
  stock_tree=$(tree_digest)
  record_removed=$([ -e "$root/carry-layer.json" ] && echo no || echo yes)
  # 4. Patched again without reinstalling; then stock again: the tree must match.
  step to-patched "$exe" setup --variant patched --root "$root" --manifest "$release/release-manifest.x.json" --json
  patched_tree=$(tree_digest)
  step to-stock-again "$exe" setup --variant stock --root "$root" --json
  identical=$([ "$(tree_digest)" = "$stock_tree" ] && echo yes || echo no)
  differs=$([ "$patched_tree" != "$stock_tree" ] && echo yes || echo no)
  say "stock tree identical after a round trip=$identical; patched tree differs=$differs; carry-layer.json removed on stock=$record_removed"
  # 5. Patched, then update to Y: the variant must survive.
  step before-update "$exe" setup --variant patched --root "$root" --manifest "$release/release-manifest.x.json" --json
  step update "$exe" update --yes --json --root "$root" --manifest "$release/release-manifest.y.json"
  version=$(json_field "$root/state/cli-state.json" "d.get('cli_version')")
  say "after update: cli_version=$version"
  if [ "$bs_variant" = patched ] && [ "$bs_files" = patched ] && [ "$bs_doctor" = ok/patched ] \
     && [ "$(result to-stock 1)" = 0 ] && [ "$(result to-stock 2)" = stock ] && [ "$(result to-stock 3)" = ok/stock ] && [ "$record_removed" = yes ] \
     && [ "$(result to-patched 1)" = 0 ] && [ "$(result to-patched 2)" = patched ] && [ "$(result to-patched 3)" = ok/patched ] \
     && [ "$(result to-stock-again 1)" = 0 ] && [ "$identical" = yes ] && [ "$differs" = yes ] \
     && [ "$(result update 1)" = 0 ] && [ "$(result update 2)" = patched ] && [ "$(result update 3)" = ok/patched ] && [ "$version" = 0.1.10 ]; then
    ok=yes
  fi
fi
say "ok=$ok"
[ "$ok" = yes ]
