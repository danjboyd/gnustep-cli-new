#!/usr/bin/env python3
"""Make a throwaway signed release that advertises a package index.

Package install qualification uses this to exercise the same chain a stable
install does -- trust root -> signed manifest -> index digest -> artifact digest --
without production keys: it generates a key pair in the work directory, writes
release-manifest.json with a package-index entry for package-index.json (which must
already be in the work directory), signs it with openssl, and points the managed
root's lifecycle state at it. Run the CLI with RELEASE_TRUST_ROOT set to the printed
public key path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", required=True, help="directory holding package-index.json")
    parser.add_argument("--root", required=True, help="managed root whose state should use this manifest")
    args = parser.parse_args()

    work = Path(args.work).resolve()
    root = Path(args.root).resolve()
    index = work / "package-index.json"
    digest = hashlib.sha256(index.read_bytes()).hexdigest()
    manifest_path = work / "release-manifest.json"
    manifest_path.write_text(json.dumps({
        "schema_version": 1,
        "channel": "stable",
        "generated_at": "2026-01-01T00:00:00Z",
        "releases": [{
            "version": "0.0.0-qualification",
            "status": "active",
            "artifacts": [{
                "id": "package-index-stable",
                "kind": "package-index",
                "format": "json",
                "filename": index.name,
                "sha256": digest,
                "size": index.stat().st_size,
            }],
        }],
    }, indent=2) + "\n")

    private_key = work / "qualification-signing-private.pem"
    public_key = work / "qualification-signing-public.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private_key)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["openssl", "pkey", "-in", str(private_key), "-pubout", "-out", str(public_key)], check=True)
    subprocess.run(["openssl", "dgst", "-sha256", "-sign", str(private_key), "-out", str(manifest_path) + ".sig", str(manifest_path)], check=True)
    private_key.unlink()

    state_path = root / "state" / "cli-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8-sig")) if state_path.exists() else {"schema_version": 1, "status": "healthy"}
    state["manifest_path"] = str(manifest_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    print(public_key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
