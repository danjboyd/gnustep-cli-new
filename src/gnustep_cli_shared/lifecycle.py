from __future__ import annotations

import json
import shutil
import hashlib
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


def content_store_dir(managed_root: str | Path) -> Path:
    return Path(managed_root).resolve() / "store" / "sha256"


def content_store_path(managed_root: str | Path, sha256: str) -> Path:
    normalized = sha256.lower()
    return content_store_dir(managed_root) / normalized[:2] / normalized[2:]


def store_content(managed_root: str | Path, source_path: str | Path, *, expected_sha256: str | None = None) -> dict[str, Any]:
    source = Path(source_path).resolve()
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if expected_sha256 is not None and actual.lower() != expected_sha256.lower():
        return {
            "schema_version": 1,
            "command": "content-store",
            "ok": False,
            "status": "error",
            "summary": "Content digest did not match the expected artifact digest.",
            "expected_sha256": expected_sha256,
            "actual_sha256": actual,
        }
    destination = content_store_path(managed_root, actual)
    destination.parent.mkdir(parents=True, exist_ok=True)
    reused_existing = destination.exists()
    if not reused_existing:
        shutil.copy2(source, destination)
    return {
        "schema_version": 1,
        "command": "content-store",
        "ok": True,
        "status": "ok",
        "summary": "Content is present in the managed content-addressed store.",
        "sha256": actual,
        "source_path": str(source),
        "store_path": str(destination),
        "reused_existing": reused_existing,
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


def record_active_artifacts(
    managed_root: str | Path,
    *,
    cli_artifact: dict[str, Any] | None = None,
    toolchain_artifact: dict[str, Any] | None = None,
    manifest_digest: str | None = None,
    component_inventory_digest: str | None = None,
) -> dict[str, Any]:
    state = load_cli_state(managed_root)
    if cli_artifact is not None:
        state["cli_artifact_id"] = cli_artifact.get("id")
        state["cli_artifact_sha256"] = cli_artifact.get("sha256")
        state["cli_version"] = cli_artifact.get("version", state.get("cli_version"))
    if toolchain_artifact is not None:
        state["toolchain_artifact_id"] = toolchain_artifact.get("id")
        state["toolchain_artifact_sha256"] = toolchain_artifact.get("sha256")
        state["toolchain_version"] = toolchain_artifact.get("version", state.get("toolchain_version"))
    if manifest_digest is not None:
        state["release_manifest_sha256"] = manifest_digest
    if component_inventory_digest is not None:
        state["component_inventory_sha256"] = component_inventory_digest
    state["last_action"] = "record_active_artifacts"
    state["status"] = state.get("status") if state.get("status") not in {None, "unknown"} else "healthy"
    save_cli_state(managed_root, state)
    return {
        "schema_version": 1,
        "command": "record-active-artifacts",
        "ok": True,
        "status": "ok",
        "summary": "Active artifact identity recorded in managed lifecycle state.",
        "state": state,
    }


def layered_update_plan(
    installed_state: dict[str, Any],
    selected_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    cli_artifact = next((artifact for artifact in selected_artifacts if artifact.get("kind") == "cli"), None)
    toolchain_artifact = next((artifact for artifact in selected_artifacts if artifact.get("kind") == "toolchain"), None)
    cli_change = bool(
        cli_artifact
        and (
            installed_state.get("cli_artifact_sha256") != cli_artifact.get("sha256")
            if installed_state.get("cli_artifact_sha256")
            else installed_state.get("cli_version") != cli_artifact.get("version")
        )
    )
    toolchain_change = bool(
        toolchain_artifact
        and (
            installed_state.get("toolchain_artifact_sha256") != toolchain_artifact.get("sha256")
            if installed_state.get("toolchain_artifact_sha256")
            else installed_state.get("toolchain_version") != toolchain_artifact.get("version")
        )
    )
    if cli_change and not toolchain_change:
        update_kind = "cli_only"
    elif toolchain_change:
        update_kind = "toolchain_required"
    else:
        update_kind = "none"
    layers: list[dict[str, Any]] = []
    if cli_artifact is not None:
        layers.append(
            {
                "name": "cli",
                "artifact_id": cli_artifact.get("id"),
                "sha256": cli_artifact.get("sha256"),
                "current_sha256": installed_state.get("cli_artifact_sha256"),
                "action": "update" if cli_change else "reuse",
                "download_required": cli_change,
                "size": cli_artifact.get("size"),
            }
        )
    if toolchain_artifact is not None:
        layers.append(
            {
                "name": "toolchain",
                "artifact_id": toolchain_artifact.get("id"),
                "sha256": toolchain_artifact.get("sha256"),
                "current_sha256": installed_state.get("toolchain_artifact_sha256"),
                "action": "update" if toolchain_change else "reuse",
                "download_required": toolchain_change and not bool(toolchain_artifact.get("reused")),
                "reused_manifest_reference": bool(toolchain_artifact.get("reused")),
                "size": toolchain_artifact.get("size"),
            }
        )
    planned_download_size = sum(int(layer.get("size") or 0) for layer in layers if layer.get("download_required"))
    return {
        "schema_version": 1,
        "kind": update_kind,
        "update_available": cli_change or toolchain_change,
        "planned_download_size": planned_download_size,
        "layers": layers,
    }


def _matching_delta(
    *,
    installed_sha256: str | None,
    target_artifact: dict[str, Any],
    delta_artifacts: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    failures: list[dict[str, str]] = []
    for delta in delta_artifacts:
        if delta.get("to_artifact") != target_artifact.get("id"):
            continue
        if delta.get("to_sha256") != target_artifact.get("sha256"):
            failures.append({"code": "target_digest_mismatch", "message": f"Delta {delta.get('id')} does not materialize the selected target digest."})
            continue
        if installed_sha256 is None or delta.get("from_sha256") != installed_sha256:
            failures.append({"code": "invalid_base_artifact", "message": f"Delta {delta.get('id')} does not apply to the installed base artifact."})
            continue
        missing = [field for field in ("url", "sha256", "size", "delta_format") if delta.get(field) in (None, "")]
        if missing:
            failures.append({"code": "corrupt_delta", "message": f"Delta {delta.get('id')} is missing required fields: {', '.join(missing)}."})
            continue
        if delta.get("delta_format") != "gnustep-delta-v1":
            failures.append({"code": "unsupported_delta_format", "message": f"Delta {delta.get('id')} uses unsupported format {delta.get('delta_format')}."})
            continue
        return delta, failures
    return None, failures


def layered_update_strategy(
    installed_state: dict[str, Any],
    selected_artifacts: list[dict[str, Any]],
    *,
    delta_artifacts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    base_plan = layered_update_plan(installed_state, selected_artifacts)
    deltas = delta_artifacts or []
    failures: list[dict[str, str]] = []
    strategies: list[dict[str, Any]] = []

    for layer in base_plan["layers"]:
        if layer["action"] != "update":
            strategies.append({**layer, "strategy": "reuse"})
            continue
        target = next((artifact for artifact in selected_artifacts if artifact.get("id") == layer.get("artifact_id")), None)
        if target is None:
            failures.append({"code": "missing_target_artifact", "message": f"Selected artifact {layer.get('artifact_id')} is missing."})
            continue
        delta, delta_failures = _matching_delta(
            installed_sha256=layer.get("current_sha256"),
            target_artifact=target,
            delta_artifacts=deltas,
        )
        failures.extend(delta_failures)
        if delta is not None:
            strategies.append(
                {
                    **layer,
                    "strategy": "delta",
                    "delta_artifact_id": delta.get("id"),
                    "download_required": True,
                    "download_size": delta.get("size"),
                    "fallback": "full_artifact",
                }
            )
            continue
        if target.get("url") and target.get("sha256") and target.get("size") is not None:
            strategies.append(
                {
                    **layer,
                    "strategy": "full_artifact",
                    "download_required": True,
                    "download_size": target.get("size"),
                    "fallback": None,
                }
            )
        else:
            failures.append({"code": "full_artifact_fallback_unavailable", "message": f"No verified full artifact fallback is available for {target.get('id')}."})

    ok = not any(failure["code"] in {"missing_target_artifact", "full_artifact_fallback_unavailable"} for failure in failures)
    return {
        "schema_version": 1,
        "command": "layered-update-strategy",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": "Layered update strategy selected." if ok else "Layered update strategy could not be selected.",
        "kind": base_plan["kind"],
        "update_available": base_plan["update_available"],
        "planned_download_size": sum(int(strategy.get("download_size") or 0) for strategy in strategies if strategy.get("download_required")),
        "strategies": strategies,
        "failures": failures,
    }


def validate_layered_update_preflight(
    *,
    installed_state: dict[str, Any],
    selected_artifacts: list[dict[str, Any]],
    revoked_artifacts: list[str] | None = None,
    delta_artifacts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    revoked = set(revoked_artifacts or [])
    checks: list[dict[str, Any]] = []
    artifact_ids = {artifact.get("id") for artifact in selected_artifacts}
    revoked_selected = sorted(artifact_ids & revoked)
    checks.append(
        {
            "id": "revoked-artifacts-absent",
            "ok": not revoked_selected,
            "failure_reason": "revoked_artifact" if revoked_selected else None,
            "message": "No selected artifacts are revoked." if not revoked_selected else f"Selected artifacts are revoked: {', '.join(revoked_selected)}.",
        }
    )
    strategy = layered_update_strategy(installed_state, selected_artifacts, delta_artifacts=delta_artifacts)
    checks.append(
        {
            "id": "strategy-selectable",
            "ok": strategy["ok"],
            "failure_reason": None if strategy["ok"] else "full_artifact_fallback_failure",
            "message": strategy["summary"],
        }
    )
    ok = all(check["ok"] for check in checks)
    return {
        "schema_version": 1,
        "command": "layered-update-preflight",
        "ok": ok,
        "status": "ok" if ok else "error",
        "summary": "Layered update preflight passed." if ok else "Layered update preflight failed.",
        "checks": checks,
        "strategy": strategy,
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
        issues.append({"code": "stale_staging", "message": f"Stale staging directory found: {staging}"})
        repairs.append({"kind": "clear_staging", "message": f"Removed stale staging directory {staging}"})

    transactions = root / ".transactions"
    if transactions.exists():
        shutil.rmtree(transactions)
        issues.append({"code": "stale_transactions", "message": f"Stale transaction directory found: {transactions}"})
        repairs.append({"kind": "clear_transactions", "message": f"Removed stale transaction directory {transactions}"})

    setup_transaction = _state_dir(root) / "setup-transaction.json"
    if setup_transaction.exists():
        setup_transaction.unlink()
        issues.append({"code": "stale_setup_transaction", "message": f"Stale setup transaction found: {setup_transaction}"})
        repairs.append({"kind": "clear_setup_transaction", "message": f"Removed stale setup transaction {setup_transaction}"})

    state = load_cli_state(root)
    if state["schema_version"] != 1:
        issues.append({"code": "unsupported_state_version", "message": "Unsupported CLI state schema version."})
    else:
        if state.get("status") in {"installing", "upgrading", "repairing"}:
            issues.append({"code": "interrupted_lifecycle_action", "message": f"Lifecycle action was interrupted while status was {state.get('status')}."})
            state["status"] = "needs_repair"
            repairs.append({"kind": "mark_needs_repair", "message": "Marked interrupted managed environment for explicit repair validation."})
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
