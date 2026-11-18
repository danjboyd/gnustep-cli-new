#!/usr/bin/env python3
"""Write the dogfood package-index.json: the committed tools-xctest entry, with one
artifact pointing at the freshly built package (url and sha256 filled in).
Usage: make-index.py <repo> <artifact-id> <artifact-file> <artifact-url> <out-dir>"""
import hashlib, json, sys
from pathlib import Path

repo, artifact_id, artifact_file, url, out = sys.argv[1:]
index = json.loads((Path(repo) / "packages" / "package-index.json").read_text())
entry = next(p for p in index["packages"] if p["id"] == "org.gnustep.tools-xctest")
artifact = next(a for a in entry["artifacts"] if a["id"] == artifact_id)
data = Path(artifact_file).read_bytes()
artifact.update({"url": url, "sha256": hashlib.sha256(data).hexdigest(), "publish": True, "status": "dogfood"})
entry["artifacts"] = [artifact]
index["packages"] = [entry]
index["channel"] = "dogfood"
Path(out).mkdir(parents=True, exist_ok=True)
(Path(out) / "package-index.json").write_text(json.dumps(index, indent=2) + "\n")
print(f"index: {artifact_id} {artifact['sha256']} {url}")
