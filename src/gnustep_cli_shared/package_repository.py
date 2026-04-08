from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def discover_package_manifests(packages_root: str | Path) -> list[Path]:
    root = Path(packages_root).resolve()
    if not root.exists():
        return []
    return sorted(path for path in root.glob("*/package.json") if path.is_file())


def generate_package_index(packages_root: str | Path, channel: str = "stable") -> dict[str, Any]:
    manifests = discover_package_manifests(packages_root)
    packages: list[dict[str, Any]] = []
    for manifest_path in manifests:
        payload = json.loads(manifest_path.read_text())
        packages.append(
            {
                "id": payload["id"],
                "name": payload["name"],
                "version": payload["version"],
                "kind": payload["kind"],
                "summary": payload.get("summary", ""),
                "requirements": payload["requirements"],
                "dependencies": payload.get("dependencies", []),
                "artifacts": payload["artifacts"],
            }
        )
    return {
        "schema_version": 1,
        "channel": channel,
        "generated_at": "TBD",
        "packages": packages,
    }


def write_package_index(packages_root: str | Path, output_path: str | Path, channel: str = "stable") -> Path:
    payload = generate_package_index(packages_root, channel=channel)
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n")
    return output

