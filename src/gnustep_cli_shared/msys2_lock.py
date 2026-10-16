"""Lock the Windows MSYS2 clang64 toolchain inputs to exact package files.

A resolve run of ``assemble-toolchain.ps1 -ResolveOut <dir>`` installs the
current MSYS2 packages and records ``pacman -Q`` plus the sync databases it
resolved against. ``lock_input_manifest`` turns that record into the
``locked_packages`` list of ``input-manifest.json``: every installed package
with its exact version, repository file name, and the SHA-256 that the signed
sync database published for it. Locked builds then install exactly that set
with ``pacman -U`` and never sync against the live repository.
"""

from __future__ import annotations

import json
import tarfile
from pathlib import Path
from typing import Any


REPO_BASE_URLS = {
    "msys": "https://repo.msys2.org/msys/x86_64",
    "clang64": "https://repo.msys2.org/mingw/clang64",
}


def parse_pacman_query(text: str) -> dict[str, str]:
    """Parse ``pacman -Q`` output into a name -> version map."""
    installed: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"unexpected pacman -Q line: {line!r}")
        installed[parts[0]] = parts[1]
    return installed


def _parse_desc(text: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    key = None
    for line in text.splitlines():
        if line.startswith("%") and line.endswith("%"):
            key = line.strip("%")
            fields[key] = []
        elif key and line:
            fields[key].append(line)
    return fields


def read_sync_database(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """Read a pacman sync database into (name, version) -> package entry."""
    entries: dict[tuple[str, str], dict[str, Any]] = {}
    with tarfile.open(path) as archive:
        for member in archive.getmembers():
            if not member.isfile() or not member.name.endswith("/desc"):
                continue
            handle = archive.extractfile(member)
            if handle is None:
                continue
            fields = _parse_desc(handle.read().decode("utf-8"))
            try:
                name = fields["NAME"][0]
                version = fields["VERSION"][0]
                entries[(name, version)] = {
                    "filename": fields["FILENAME"][0],
                    "sha256": fields["SHA256SUM"][0],
                    "size": int(fields["CSIZE"][0]),
                }
            except (KeyError, IndexError, ValueError) as exc:
                raise ValueError(f"incomplete package entry {member.name} in {path}") from exc
    return entries


def locked_packages(installed: dict[str, str], databases: dict[str, dict[tuple[str, str], dict[str, Any]]]) -> list[dict[str, Any]]:
    """Resolve every installed package to the exact repository file it came from."""
    locked = []
    missing = []
    for name in sorted(installed):
        version = installed[name]
        match = None
        for repo in REPO_BASE_URLS:
            entry = databases.get(repo, {}).get((name, version))
            if entry is not None:
                match = (repo, entry)
                break
        if match is None:
            missing.append(f"{name} {version}")
            continue
        repo, entry = match
        locked.append(
            {
                "name": name,
                "version": version,
                "repo": repo,
                "filename": entry["filename"],
                "url": f"{REPO_BASE_URLS[repo]}/{entry['filename']}",
                "sha256": entry["sha256"],
                "size": entry["size"],
            }
        )
    if missing:
        raise ValueError("installed packages not found in the resolved sync databases: " + ", ".join(missing))
    return locked


def lock_input_manifest(manifest: dict[str, Any], resolve_dir: Path) -> dict[str, Any]:
    """Return ``manifest`` with its package pins filled from a resolve run."""
    metadata = json.loads((resolve_dir / "resolve.json").read_text(encoding="utf-8"))
    installed = parse_pacman_query((resolve_dir / "pacman-Q.txt").read_text(encoding="utf-8"))
    databases = {repo: read_sync_database(resolve_dir / f"{repo}.db") for repo in REPO_BASE_URLS}
    locked = locked_packages(installed, databases)
    by_name = {entry["name"]: entry for entry in locked}

    result = json.loads(json.dumps(manifest))
    result["repository_snapshot"] = metadata["resolved_at"]
    for section in ("host_packages", "packages"):
        for package in result.get(section, []):
            entry = by_name.get(package["name"])
            if entry is None:
                raise ValueError(f"requested package {package['name']} was not installed by the resolve run")
            package["version"] = entry["version"]
            package["sha256"] = entry["sha256"]
    result["locked_packages"] = locked
    return result
