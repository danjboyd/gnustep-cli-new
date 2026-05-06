#!/bin/sh
set -eu

PACKAGE_INDEX="${1:-packages/package-index.json}"
RELEASE_TAG="${2:-v0.1.0}"
DOWNLOAD_ROOT="${DOWNLOAD_ROOT:-.artifacts/package-release-asset-verification}"

rm -rf "$DOWNLOAD_ROOT"
mkdir -p "$DOWNLOAD_ROOT"

python3 - "$PACKAGE_INDEX" "$DOWNLOAD_ROOT/expected.json" <<'PY'
import json, pathlib, sys
index = json.load(open(sys.argv[1], encoding="utf-8"))
expected = []
for package in index.get("packages", []):
    for artifact in package.get("artifacts", []):
        url = artifact.get("url") or ""
        filename = artifact.get("filename")
        if artifact.get("publish") is True and filename and "/releases/download/" in url:
            expected.append({
                "package_id": package.get("id"),
                "artifact_id": artifact.get("id"),
                "filename": filename,
                "sha256": artifact.get("sha256"),
                "url": url,
            })
pathlib.Path(sys.argv[2]).write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
PY

gh release view "$RELEASE_TAG" --json assets > "$DOWNLOAD_ROOT/release-assets.json"

python3 - "$DOWNLOAD_ROOT/expected.json" "$DOWNLOAD_ROOT/release-assets.json" "$DOWNLOAD_ROOT/plan.json" <<'PY'
import json, pathlib, sys
expected = json.load(open(sys.argv[1], encoding="utf-8"))
assets = {asset.get("name"): asset for asset in json.load(open(sys.argv[2], encoding="utf-8")).get("assets", [])}
plan = []
ok = True
for item in expected:
    asset = assets.get(item.get("filename"))
    present = asset is not None
    digest = asset.get("digest", "") if asset else ""
    digest_ok = digest == f"sha256:{item.get('sha256')}"
    ok = ok and present and digest_ok
    plan.append({**item, "release_asset_present": present, "release_asset_digest": digest, "release_asset_digest_ok": digest_ok})
pathlib.Path(sys.argv[3]).write_text(json.dumps({"ok": ok, "artifacts": plan}, indent=2) + "\n", encoding="utf-8")
raise SystemExit(0 if ok else 1)
PY

python3 - "$DOWNLOAD_ROOT/expected.json" <<'PY' > "$DOWNLOAD_ROOT/download-list.txt"
import json, sys
for item in json.load(open(sys.argv[1], encoding="utf-8")):
    print(item["filename"])
PY

while IFS= read -r filename; do
  gh release download "$RELEASE_TAG" --pattern "$filename" --dir "$DOWNLOAD_ROOT/downloads" --clobber
done < "$DOWNLOAD_ROOT/download-list.txt"

python3 - "$DOWNLOAD_ROOT/expected.json" "$DOWNLOAD_ROOT/downloads" "$RELEASE_TAG" "$DOWNLOAD_ROOT/summary.json" <<'PY'
import hashlib, json, pathlib, sys
expected = json.load(open(sys.argv[1], encoding="utf-8"))
downloads = pathlib.Path(sys.argv[2])
release_tag = sys.argv[3]
results = []
ok = True
for item in expected:
    path = downloads / item["filename"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    digest_ok = digest == item.get("sha256")
    ok = ok and digest_ok
    results.append({**item, "downloaded": path.exists(), "download_sha256": digest, "download_sha256_ok": digest_ok})
summary = {"schema_version": 1, "command": "verify-package-release-assets", "ok": ok, "status": "ok" if ok else "error", "release_tag": release_tag, "artifacts": results}
pathlib.Path(sys.argv[4]).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
raise SystemExit(0 if ok else 1)
PY
