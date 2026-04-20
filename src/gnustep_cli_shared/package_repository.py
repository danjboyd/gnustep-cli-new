from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def discover_package_manifests(packages_root: str | Path) -> list[Path]:
    root = Path(packages_root).resolve()
    if not root.exists():
        return []
    return sorted(path for path in root.glob("*/package.json") if path.is_file())



def _patches_for_artifact(package_patches: list[dict[str, Any]], artifact_id: str) -> list[dict[str, Any]]:
    selected = []
    for patch in package_patches:
        applies_to = patch.get("applies_to")
        if applies_to is None or artifact_id in applies_to:
            selected.append(patch)
    return selected


def generate_package_index(packages_root: str | Path, channel: str = "stable") -> dict[str, Any]:
    manifests = discover_package_manifests(packages_root)
    packages: list[dict[str, Any]] = []
    for manifest_path in manifests:
        payload = json.loads(manifest_path.read_text())
        package_source = payload.get("source", {})
        package_patches = payload.get("patches", [])
        artifacts = []
        for artifact in payload["artifacts"]:
            enriched = dict(artifact)
            enriched["source"] = package_source
            enriched["patches"] = _patches_for_artifact(package_patches, str(artifact.get("id", "")))
            artifacts.append(enriched)
        packages.append(
            {
                "id": payload["id"],
                "name": payload["name"],
                "version": payload["version"],
                "kind": payload["kind"],
                "summary": payload.get("summary", ""),
                "source": package_source,
                "patches": package_patches,
                "build": payload.get("build", {}),
                "requirements": payload["requirements"],
                "dependencies": payload.get("dependencies", []),
                "artifacts": artifacts,
            }
        )
    return {
        "schema_version": 1,
        "channel": channel,
        "generated_at": "TBD",
        "metadata_version": 1,
        "expires_at": "TBD",
        "trust": {
            "root_version": 1,
            "signature_policy": "single-role-v1",
            "signatures": [],
        },
        "packages": packages,
    }


def write_package_index(packages_root: str | Path, output_path: str | Path, channel: str = "stable") -> Path:
    payload = generate_package_index(packages_root, channel=channel)
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n")
    return output




def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _openssl_sign_file(input_path: Path, signature_path: Path, private_key_path: Path) -> bool:
    proc = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", str(private_key_path), "-out", str(signature_path), str(input_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def _openssl_verify_file(input_path: Path, signature_path: Path, public_key_path: Path) -> bool:
    proc = subprocess.run(
        ["openssl", "dgst", "-sha256", "-verify", str(public_key_path), "-signature", str(signature_path), str(input_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return proc.returncode == 0



def _parse_metadata_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or value in {"", "TBD"}:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _package_metadata_policy_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    now = datetime.now(UTC)

    def add(check_id: str, ok: bool, message: str) -> None:
        checks.append({"id": check_id, "ok": ok, "message": message})

    metadata_version = payload.get("metadata_version")
    add("metadata-version-supported", isinstance(metadata_version, int) and metadata_version >= 1, "metadata_version is supported")
    generated_at = _parse_metadata_time(payload.get("generated_at"))
    if generated_at is not None:
        add("metadata-generated-not-in-future", generated_at <= now, "metadata generated_at is not in the future")
    expires_at = _parse_metadata_time(payload.get("expires_at"))
    if expires_at is not None:
        add("metadata-not-expired", expires_at > now, "metadata expires_at is still valid")
    package_ids = {package.get("id") for package in payload.get("packages", []) if package.get("id")}
    trust = payload.get("trust") if isinstance(payload.get("trust"), dict) else {}
    revoked = sorted(set(trust.get("revoked_packages", []) or []) & package_ids)
    add("revoked-packages-absent", not revoked, "package index does not reference revoked packages" if not revoked else f"revoked packages present: {', '.join(revoked)}")
    return checks


def package_index_provenance_document(index_path: str | Path, *, builder_identity: str = "local") -> dict[str, Any]:
    path = Path(index_path).resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    packages = []
    for package in payload.get("packages", []):
        packages.append(
            {
                "id": package.get("id"),
                "version": package.get("version"),
                "kind": package.get("kind"),
                "source": package.get("source", {}),
                "patches": [
                    {
                        "id": patch.get("id"),
                        "path": patch.get("path"),
                        "sha256": patch.get("sha256"),
                    }
                    for patch in package.get("patches", [])
                ],
                "artifact_count": len(package.get("artifacts", [])),
                "build": package.get("build", {}),
                "artifact_digests": [
                    {
                        "id": artifact.get("id"),
                        "sha256": artifact.get("sha256"),
                        "source_sha256": artifact.get("source", {}).get("sha256"),
                        "patches": [
                            {
                                "id": patch.get("id"),
                                "sha256": patch.get("sha256"),
                            }
                            for patch in artifact.get("patches", [])
                        ],
                    }
                    for artifact in package.get("artifacts", [])
                ],
            }
        )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "builder_identity": builder_identity,
        "package_index": {
            "filename": path.name,
            "sha256": _sha256(path),
            "channel": payload.get("channel"),
            "metadata_version": payload.get("metadata_version"),
            "expires_at": payload.get("expires_at"),
        },
        "packages": packages,
        "qualification": {
            "index_generation": "required",
            "signature_verification": "required_for_release",
            "artifact_digest_verification": "required_before_install",
        },
    }


def write_package_index_provenance(index_path: str | Path, *, builder_identity: str = "local") -> Path:
    path = Path(index_path).resolve()
    provenance_path = path.with_name("package-index-provenance.json")
    provenance = package_index_provenance_document(path, builder_identity=builder_identity)
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return provenance_path


def sign_package_index_metadata(index_path: str | Path, private_key_path: str | Path, public_key_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(index_path).resolve()
    private_key = Path(private_key_path).resolve()
    if not path.exists():
        return {"schema_version": 1, "command": "sign-package-index", "ok": False, "status": "error", "summary": "Package index is missing.", "index_path": str(path)}
    if not private_key.exists():
        return {"schema_version": 1, "command": "sign-package-index", "ok": False, "status": "error", "summary": "Signing private key is missing.", "index_path": str(path)}
    provenance_path = write_package_index_provenance(path)
    public_key = Path(public_key_path).resolve() if public_key_path else path.with_name("package-index-signing-public.pem")
    if public_key_path is None:
        proc = subprocess.run(["openssl", "pkey", "-in", str(private_key), "-pubout", "-out", str(public_key)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if proc.returncode != 0:
            return {"schema_version": 1, "command": "sign-package-index", "ok": False, "status": "error", "summary": "Failed to derive package index signing public key.", "index_path": str(path), "stderr": proc.stderr}
    signatures = []
    ok = True
    for input_path in (path, provenance_path):
        signature_path = input_path.with_name(f"{input_path.name}.sig")
        signed = _openssl_sign_file(input_path, signature_path, private_key)
        signatures.append({"filename": input_path.name, "signature": signature_path.name, "ok": signed})
        ok = ok and signed
    return {"schema_version": 1, "command": "sign-package-index", "ok": ok, "status": "ok" if ok else "error", "summary": "Package index metadata signed." if ok else "Package index metadata signing failed.", "index_path": str(path), "public_key": str(public_key), "signatures": signatures}


def package_index_trust_gate(index_path: str | Path, *, require_signatures: bool = True, trusted_public_key_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(index_path).resolve()
    provenance_path = path.with_name("package-index-provenance.json")
    bundled_public_key_path = path.with_name("package-index-signing-public.pem")
    public_key_path = Path(trusted_public_key_path).resolve() if trusted_public_key_path else bundled_public_key_path
    checks: list[dict[str, Any]] = []

    def add(check_id: str, ok: bool, message: str) -> None:
        checks.append({"id": check_id, "ok": ok, "message": message})

    add("package-index-present", path.exists(), "package-index.json is present")
    add("provenance-present", provenance_path.exists(), "package-index-provenance.json is present")
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            checks.extend(_package_metadata_policy_checks(payload))
        except Exception as exc:
            add("package-index-json", False, f"package-index.json is invalid: {exc}")
    if path.exists() and provenance_path.exists():
        try:
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            recorded_digest = provenance.get("package_index", {}).get("sha256")
            add("provenance-index-digest", recorded_digest == _sha256(path), "provenance records the package index digest")
        except Exception as exc:
            add("provenance-json", False, f"package-index-provenance.json is invalid: {exc}")
    if require_signatures:
        if trusted_public_key_path:
            add("trusted-public-key-present", public_key_path.exists(), "trusted package index signing public key is present")
            if public_key_path.exists() and bundled_public_key_path.exists():
                add("bundled-public-key-matches-trust-root", _sha256(public_key_path) == _sha256(bundled_public_key_path), "bundled package index public key matches the trusted root")
        else:
            add("public-key-present", public_key_path.exists(), "package index signing public key is present")
        for input_path in (path, provenance_path):
            signature_path = input_path.with_name(f"{input_path.name}.sig")
            add(f"signature-present:{input_path.name}", signature_path.exists(), f"signature exists for {input_path.name}")
            if input_path.exists() and signature_path.exists() and public_key_path.exists():
                add(f"signature-valid:{input_path.name}", _openssl_verify_file(input_path, signature_path, public_key_path), f"signature verifies for {input_path.name}")
    ok = all(check["ok"] for check in checks)
    return {
        "schema_version": 1,
        "command": "package-index-trust-gate",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": "Package index trust gate passed." if ok else "Package index trust gate failed.",
        "index_path": str(path),
        "require_signatures": require_signatures,
        "trusted_public_key": str(public_key_path) if trusted_public_key_path else None,
        "checks": checks,
    }
