from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def _state_dir(managed_root: Path) -> Path:
    return managed_root / "state"


def _cli_state_path(managed_root: Path) -> Path:
    return _state_dir(managed_root) / "cli-state.json"


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "cli_version": None,
        "toolchain_version": None,
        "packages_version": 1,
        "last_action": None,
        "status": "unknown",
    }


def load_cli_state(managed_root: str | Path) -> dict[str, Any]:
    root = Path(managed_root).resolve()
    path = _cli_state_path(root)
    if not path.exists():
        return _default_state()
    return json.loads(path.read_text())


def save_cli_state(managed_root: str | Path, state: dict[str, Any]) -> Path:
    root = Path(managed_root).resolve()
    path = _cli_state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n")
    return path


def plan_upgrade(
    managed_root: str | Path,
    *,
    current_cli_version: str | None,
    target_cli_version: str,
    current_toolchain_version: str | None = None,
    target_toolchain_version: str | None = None,
) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    if current_cli_version != target_cli_version:
        actions.append(
            {
                "kind": "upgrade_cli",
                "priority": 1,
                "message": f"Upgrade CLI from {current_cli_version or 'not-installed'} to {target_cli_version}.",
            }
        )
    if target_toolchain_version and current_toolchain_version != target_toolchain_version:
        actions.append(
            {
                "kind": "upgrade_toolchain",
                "priority": 2,
                "message": (
                    f"Upgrade managed toolchain from {current_toolchain_version or 'not-installed'} "
                    f"to {target_toolchain_version}."
                ),
            }
        )
    return {
        "schema_version": 1,
        "command": "upgrade-plan",
        "ok": True,
        "status": "ok",
        "summary": "Upgrade plan created." if actions else "Managed environment is already at the requested versions.",
        "managed_root": str(Path(managed_root).resolve()),
        "current_cli_version": current_cli_version,
        "target_cli_version": target_cli_version,
        "current_toolchain_version": current_toolchain_version,
        "target_toolchain_version": target_toolchain_version,
        "actions": actions,
    }


def apply_upgrade_state(
    managed_root: str | Path,
    *,
    cli_version: str,
    toolchain_version: str | None = None,
) -> dict[str, Any]:
    state = load_cli_state(managed_root)
    state["cli_version"] = cli_version
    state["toolchain_version"] = toolchain_version
    state["last_action"] = "upgrade"
    state["status"] = "healthy"
    save_cli_state(managed_root, state)
    return {
        "schema_version": 1,
        "command": "upgrade-apply",
        "ok": True,
        "status": "ok",
        "summary": "Managed environment state updated for the requested versions.",
        "state": state,
    }


def repair_managed_root(managed_root: str | Path) -> dict[str, Any]:
    root = Path(managed_root).resolve()
    issues: list[dict[str, str]] = []
    repairs: list[dict[str, str]] = []

    required_dirs = [
        root / "state",
        root / "packages",
    ]
    for directory in required_dirs:
        if not directory.exists():
            issues.append({"code": "missing_directory", "message": f"Missing required directory: {directory}"})
            directory.mkdir(parents=True, exist_ok=True)
            repairs.append({"kind": "create_directory", "message": f"Created {directory}"})

    staging = root / ".staging"
    if staging.exists():
        shutil.rmtree(staging)
        repairs.append({"kind": "clear_staging", "message": f"Removed stale staging directory {staging}"})

    state = load_cli_state(root)
    if state["schema_version"] != 1:
        issues.append({"code": "unsupported_state_version", "message": "Unsupported CLI state schema version."})
    else:
        save_cli_state(root, state)
        repairs.append({"kind": "normalize_state", "message": "Ensured CLI state file exists."})

    return {
        "schema_version": 1,
        "command": "repair",
        "ok": True,
        "status": "ok",
        "summary": "Managed environment repair scan completed.",
        "issues": issues,
        "repairs": repairs,
    }

