from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .doctor_engine import CLI_VERSION, DEFAULT_MANIFEST, build_doctor_payload


def _default_user_root(os_name: str) -> str:
    if os_name == "windows":
        return r"%LOCALAPPDATA%\gnustep-cli"
    return "~/.local/share/gnustep-cli"


def _default_system_root(os_name: str) -> str:
    if os_name == "windows":
        return r"%ProgramFiles%\gnustep-cli"
    return "/opt/gnustep-cli"


def _has_system_privileges(os_name: str) -> bool:
    if os_name == "windows":
        return False
    geteuid = getattr(os, "geteuid", None)
    return bool(geteuid and geteuid() == 0)


def build_setup_payload(
    *,
    scope: str = "user",
    manifest_path: str | None = None,
    install_root: str | None = None,
) -> tuple[dict[str, Any], int]:
    doctor = build_doctor_payload(Path(manifest_path) if manifest_path else None)
    os_name = doctor["environment"]["os"]
    selected_scope = scope
    selected_root = install_root or (_default_system_root(os_name) if selected_scope == "system" else _default_user_root(os_name))
    active_release = json.loads((Path(manifest_path) if manifest_path else DEFAULT_MANIFEST).read_text())["releases"][0]
    selected_artifacts = active_release.get("artifacts", [])
    system_priv_ok = selected_scope != "system" or _has_system_privileges(os_name)

    status = "ok"
    ok = True
    summary = "Managed installation plan created."
    actions: list[dict[str, Any]] = []
    exit_code = 0

    if not system_priv_ok:
        status = "error"
        ok = False
        summary = "System-wide installation requires elevated privileges."
        actions.append(
            {
                "kind": "rerun_with_elevated_privileges",
                "priority": 1,
                "message": (
                    "Re-run this command with sudo."
                    if os_name != "windows"
                    else "Re-run PowerShell as Administrator and try again."
                ),
            }
        )
        exit_code = 3
    elif not doctor["environment"]["bootstrap_prerequisites"]["curl"] and not doctor["environment"]["bootstrap_prerequisites"]["wget"]:
        status = "error"
        ok = False
        summary = "Bootstrap prerequisites are incomplete."
        actions.append(
            {
                "kind": "install_downloader",
                "priority": 1,
                "message": "Install curl or wget, then rerun setup.",
            }
        )
        exit_code = 3
    else:
        actions.append(
            {
                "kind": "apply_install_plan",
                "priority": 1,
                "message": "Proceed with artifact download and managed installation once implementation is complete.",
            }
        )

    payload = {
        "schema_version": 1,
        "command": "setup",
        "cli_version": CLI_VERSION,
        "ok": ok,
        "status": status,
        "summary": summary,
        "doctor": {
            "status": doctor["status"],
            "environment_classification": doctor["environment_classification"],
            "summary": doctor["summary"],
        },
        "plan": {
            "scope": selected_scope,
            "install_root": selected_root,
            "channel": "stable",
            "manifest_path": str(Path(manifest_path) if manifest_path else DEFAULT_MANIFEST),
            "selected_release": active_release["version"],
            "selected_artifacts": [artifact["id"] for artifact in selected_artifacts],
            "system_privileges_ok": system_priv_ok,
        },
        "actions": actions,
    }
    return payload, exit_code


def render_setup_human(payload: dict[str, Any]) -> str:
    plan = payload["plan"]
    lines = [
        f"setup: {payload['summary']}",
        f"setup: scope={plan['scope']} root={plan['install_root']}",
        f"setup: selected release={plan['selected_release']}",
    ]
    for action in payload["actions"]:
        lines.append(f"next: {action['message']}")
    return "\n".join(lines)

