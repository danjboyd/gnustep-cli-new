from __future__ import annotations

import json
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .build_infra import (
    build_matrix,
    controlled_release_gate,
    immediate_rc_blocker_status,
    package_artifact_build_plan,
    session_build_box_plan,
    validate_update_all_evidence,
)


SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_root(repo_root: str | Path | None = None) -> Path:
    return Path(repo_root).resolve() if repo_root else Path.cwd().resolve()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _maybe_read_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return _read_json(path)


def _evidence_json(path: str | Path | None) -> tuple[bool, str, dict[str, Any] | None]:
    if path is None:
        return False, "Evidence path was not supplied.", None
    evidence_path = Path(path).resolve()
    if not evidence_path.exists():
        return False, f"Evidence file is missing: {evidence_path}", None
    try:
        payload = _read_json(evidence_path)
    except Exception as exc:
        return False, f"Evidence file is invalid JSON: {exc}", None
    ok = bool(payload.get("ok", payload.get("overall_ok", False)))
    summary = payload.get("summary") or ("Evidence reports ok." if ok else "Evidence does not report ok.")
    return ok, summary, payload


def _status_from_findings(findings: list[dict[str, Any]]) -> tuple[bool, str]:
    severities = {finding.get("severity") for finding in findings}
    if "error" in severities:
        return False, "error"
    if "warning" in severities:
        return True, "warning"
    return True, "ok"


def _payload(command: str, ok: bool, status: str, summary: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "ok": ok,
        "status": status,
        "summary": summary,
    }
    payload.update(extra)
    return payload


def _package_manifests(packages_dir: Path) -> list[dict[str, Any]]:
    manifests = []
    for manifest_path in sorted(packages_dir.glob("*/package.json")):
        payload = _read_json(manifest_path)
        payload["_manifest_path"] = str(manifest_path)
        manifests.append(payload)
    return manifests


def _toolchain_records(root: Path) -> list[dict[str, Any]]:
    records = []
    for target_dir in sorted((root / "toolchains").glob("*")):
        if not target_dir.is_dir():
            continue
        manifest = _maybe_read_json(target_dir / "toolchain-manifest.json")
        inventory = _maybe_read_json(target_dir / "component-inventory.json")
        source_lock = _maybe_read_json(target_dir / "source-lock.json")
        input_manifest = _maybe_read_json(target_dir / "input-manifest.json")
        if manifest is None and inventory is None and source_lock is None and input_manifest is None:
            continue
        records.append(
            {
                "id": target_dir.name,
                "toolchain_manifest": manifest,
                "component_inventory": inventory,
                "source_lock": source_lock,
                "input_manifest": input_manifest,
            }
        )
    return records


def _release_records(release_dir: Path | None) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    if release_dir is None:
        return [], None
    manifest = _maybe_read_json(release_dir / "release-manifest.json")
    if manifest is None:
        return [], None
    records = []
    for release in manifest.get("releases", []):
        for artifact in release.get("artifacts", []):
            record = dict(artifact)
            record["release_version"] = release.get("version")
            record["release_status"] = release.get("status")
            records.append(record)
    return records, manifest


def admin_inventory(
    repo_root: str | Path | None = None,
    *,
    release_dir: str | Path | None = None,
    package_index: str | Path | None = None,
    packages_dir: str | Path | None = None,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    packages_root = Path(packages_dir).resolve() if packages_dir else root / "packages"
    package_index_path = Path(package_index).resolve() if package_index else packages_root / "package-index.json"
    release_path = Path(release_dir).resolve() if release_dir else None
    package_index_payload = _maybe_read_json(package_index_path)
    release_artifacts, release_manifest = _release_records(release_path)
    package_manifests = _package_manifests(packages_root)
    matrix = build_matrix()

    packages = []
    for manifest in package_manifests:
        package_entry = {
            "id": manifest.get("id"),
            "name": manifest.get("name"),
            "version": manifest.get("version"),
            "source": manifest.get("source", {}),
            "manifest_path": manifest.get("_manifest_path"),
            "artifacts": [],
        }
        for artifact in manifest.get("artifacts", []):
            package_entry["artifacts"].append(
                {
                    "id": artifact.get("id"),
                    "version": artifact.get("version", manifest.get("version")),
                    "os": artifact.get("os"),
                    "arch": artifact.get("arch"),
                    "publish": artifact.get("publish", True),
                    "status": artifact.get("status"),
                    "url": artifact.get("url"),
                    "sha256": artifact.get("sha256"),
                    "size": artifact.get("size"),
                    "build_evidence": artifact.get("build_evidence"),
                    "validation_evidence": artifact.get("validation_evidence"),
                }
            )
        packages.append(package_entry)

    served = {
        "release_artifacts": release_artifacts,
        "package_index": package_index_payload,
        "packages": packages,
        "toolchains": _toolchain_records(root),
        "matrix": matrix.get("targets", []),
    }
    inputs = {
        "repo_root": str(root),
        "packages_dir": str(packages_root),
        "package_index": str(package_index_path),
        "release_dir": str(release_path) if release_path else None,
        "release_manifest_present": release_manifest is not None,
        "package_index_present": package_index_payload is not None,
    }
    summary = f"Inventory loaded for {len(packages)} packages and {len(served['toolchains'])} toolchain targets."
    return _payload("inventory", True, "ok", summary, inputs=inputs, served=served, findings=[], actions=[])


def _latest_for_source(source: dict[str, Any], cache: dict[str, Any]) -> dict[str, Any] | None:
    candidates = [source.get("upstream"), source.get("upstream_url"), source.get("url")]
    for candidate in candidates:
        if candidate and candidate in cache:
            value = cache[candidate]
            return value if isinstance(value, dict) else {"latest_revision": value}
    return None


def _git_latest_revision(url: str) -> dict[str, Any] | None:
    proc = subprocess.run(
        ["git", "ls-remote", url, "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return {"error": proc.stderr.strip() or "git ls-remote failed"}
    revision = proc.stdout.split()[0] if proc.stdout.split() else None
    return {"latest_revision": revision} if revision else None


def _source_url(source: dict[str, Any]) -> str | None:
    for key in ("upstream_url", "upstream", "url"):
        if source.get(key):
            return str(source[key])
    return None


def admin_upstream_check(
    repo_root: str | Path | None = None,
    *,
    packages_dir: str | Path | None = None,
    upstream_cache: str | Path | None = None,
    fetch: bool = False,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    packages_root = Path(packages_dir).resolve() if packages_dir else root / "packages"
    cache = _read_json(Path(upstream_cache).resolve()) if upstream_cache else {}
    findings = []

    def check_source(kind: str, owner: str, source: dict[str, Any]) -> None:
        current = source.get("revision")
        latest = _latest_for_source(source, cache)
        if latest is None and fetch and _source_url(source):
            latest = _git_latest_revision(str(_source_url(source)))
        if latest is None:
            findings.append(
                {
                    "code": "upstream_unknown",
                    "severity": "warning",
                    "kind": kind,
                    "id": owner,
                    "current_revision": current,
                    "source_url": _source_url(source),
                    "message": "No upstream comparison data was available.",
                }
            )
            return
        if latest.get("error"):
            findings.append(
                {
                    "code": "upstream_check_failed",
                    "severity": "warning",
                    "kind": kind,
                    "id": owner,
                    "current_revision": current,
                    "message": latest["error"],
                }
            )
            return
        latest_revision = latest.get("latest_revision") or latest.get("revision")
        latest_tag = latest.get("latest_tag")
        stale = bool(latest_revision and current and latest_revision != current)
        findings.append(
            {
                "code": "stale_source" if stale else "source_current",
                "severity": "warning" if stale else "info",
                "kind": kind,
                "id": owner,
                "current_revision": current,
                "latest_revision": latest_revision,
                "latest_tag": latest_tag,
                "message": "Pinned source differs from upstream." if stale else "Pinned source matches upstream comparison data.",
            }
        )

    for manifest in _package_manifests(packages_root):
        check_source("package", manifest.get("id", ""), manifest.get("source", {}))
    for toolchain in _toolchain_records(root):
        source_lock = toolchain.get("source_lock") or {}
        for component in source_lock.get("components", []):
            check_source("toolchain-component", f"{toolchain['id']}:{component.get('name')}", component)

    stale_count = len([f for f in findings if f["code"] == "stale_source"])
    unknown_count = len([f for f in findings if f["code"] == "upstream_unknown"])
    failed_count = len([f for f in findings if f["code"] == "upstream_check_failed"])
    status = "warning" if stale_count or unknown_count or failed_count else "ok"
    summary_parts = [f"{stale_count} stale source pin(s)"]
    if unknown_count:
        summary_parts.append(f"{unknown_count} unknown source comparison(s)")
    if failed_count:
        summary_parts.append(f"{failed_count} failed upstream check(s)")
    return _payload(
        "upstream-check",
        True,
        status,
        "Upstream check completed with " + ", ".join(summary_parts) + ".",
        inputs={"repo_root": str(root), "packages_dir": str(packages_root), "upstream_cache": str(upstream_cache) if upstream_cache else None, "fetch": fetch},
        findings=findings,
        actions=[] if not (unknown_count or failed_count) else [{"kind": "provide_upstream_comparison", "priority": 1, "message": "Supply an upstream comparison cache or rerun with --fetch so pinned source freshness can be evaluated."}],
    )


def admin_upstream_sources(
    repo_root: str | Path | None = None,
    *,
    packages_dir: str | Path | None = None,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    packages_root = Path(packages_dir).resolve() if packages_dir else root / "packages"
    sources: list[dict[str, Any]] = []

    def add(kind: str, owner: str, source: dict[str, Any]) -> None:
        url = _source_url(source)
        if url:
            sources.append({"kind": kind, "id": owner, "url": url, "current_revision": source.get("revision")})

    for manifest in _package_manifests(packages_root):
        add("package", manifest.get("id", ""), manifest.get("source", {}))
    for toolchain in _toolchain_records(root):
        source_lock = toolchain.get("source_lock") or {}
        for component in source_lock.get("components", []):
            add("toolchain-component", f"{toolchain['id']}:{component.get('name')}", component)

    return _payload(
        "upstream-sources",
        True,
        "ok",
        f"Listed {len(sources)} upstream source pin(s).",
        inputs={"repo_root": str(root), "packages_dir": str(packages_root)},
        sources=sources,
    )


def admin_gap_report(
    repo_root: str | Path | None = None,
    *,
    release_dir: str | Path | None = None,
    package_index: str | Path | None = None,
    packages_dir: str | Path | None = None,
    evidence_dir: str | Path | None = None,
    release_trust_root: str | Path | None = None,
    package_index_trust_root: str | Path | None = None,
    smoke_report_paths: list[str | Path] | None = None,
    update_all_evidence: str | Path | None = None,
    scheduler_evidence: str | Path | None = None,
    doctor_parity_evidence: str | Path | None = None,
) -> dict[str, Any]:
    inventory = admin_inventory(repo_root, release_dir=release_dir, package_index=package_index, packages_dir=packages_dir)
    publication = package_artifact_build_plan(str(Path(packages_dir).resolve() if packages_dir else _repo_root(repo_root) / "packages"))
    root = _repo_root(repo_root)
    packages_root = Path(packages_dir).resolve() if packages_dir else root / "packages"
    package_index_path = Path(package_index).resolve() if package_index else packages_root / "package-index.json"
    release_path = Path(release_dir).resolve() if release_dir else None
    evidence_path = Path(evidence_dir).resolve() if evidence_dir else release_path
    findings: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []

    trust_missing = [name for name, value in {
        "release_dir": release_path,
        "package_index": package_index_path if package_index_path.exists() else None,
        "release_trust_root": release_trust_root,
        "package_index_trust_root": package_index_trust_root,
    }.items() if not value]
    if trust_missing:
        findings.append(
            {
                "code": "trust_not_production",
                "severity": "error",
                "missing": trust_missing,
                "message": "Production release and package-index trust cannot be proven until release artifacts, package index, and external trust roots are supplied.",
            }
        )
        actions.append({"kind": "provision_production_trust", "priority": 1, "message": "Provide CI-held release and package-index trust roots and run the controlled release gate."})
    else:
        trust_gate = controlled_release_gate(
            release_path,
            package_index_path=package_index_path,
            release_trust_root=release_trust_root,
            package_index_trust_root=package_index_trust_root,
        )
        findings.append(
            {
                "code": "production_trust_verified" if trust_gate.get("ok") else "trust_not_production",
                "severity": "info" if trust_gate.get("ok") else "error",
                "message": trust_gate.get("summary", "Controlled release gate evaluated."),
                "gate": trust_gate,
            }
        )
        if not trust_gate.get("ok"):
            actions.append({"kind": "provision_production_trust", "priority": 1, "message": "Fix release/package-index signing or trust-root verification failures."})

    smoke_paths = list(smoke_report_paths or [])
    if not smoke_paths and evidence_path is not None:
        for name in ("openbsd-full-tier1-core-report.json", "openbsd-full-release-report.json", "windows-full-tier1-core-report.json", "windows-full-release-report.json"):
            candidate = evidence_path / name
            if candidate.exists():
                smoke_paths.append(candidate)
    update_path = Path(update_all_evidence).resolve() if update_all_evidence else (evidence_path / "update-all-production-like.json" if evidence_path else None)
    if release_path is None or evidence_path is None:
        findings.append(
            {
                "code": "missing_final_hosted_evidence",
                "severity": "error",
                "message": "Final hosted evidence cannot be proven until release and evidence directories are supplied.",
            }
        )
        actions.append({"kind": "refresh_candidate_evidence", "priority": 2, "message": "Collect fresh hosted Linux, OpenBSD, Windows, and update-all evidence for the exact candidate."})
    else:
        rc_gate = immediate_rc_blocker_status(
            release_dir=release_path,
            evidence_dir=evidence_path,
            package_index_path=package_index_path,
            release_trust_root=release_trust_root,
            package_index_trust_root=package_index_trust_root,
            smoke_report_paths=smoke_paths,
            update_all_evidence_path=update_path,
            packages_dir=packages_root,
        )
        findings.append(
            {
                "code": "final_hosted_evidence_verified" if rc_gate.get("ok") else "missing_final_hosted_evidence",
                "severity": "info" if rc_gate.get("ok") else "error",
                "message": rc_gate.get("summary", "Immediate RC blocker gate evaluated."),
                "gate": rc_gate,
            }
        )
        if not rc_gate.get("ok"):
            actions.append({"kind": "refresh_candidate_evidence", "priority": 2, "message": "Refresh the failing final candidate evidence and rerun immediate RC blocker status."})
        if update_path is not None:
            update_gate = validate_update_all_evidence(update_path)
            findings.append(
                {
                    "code": "update_all_evidence_verified" if update_gate.get("ok") else "missing_update_all_evidence",
                    "severity": "info" if update_gate.get("ok") else "error",
                    "message": update_gate.get("summary", "Update-all evidence evaluated."),
                    "gate": update_gate,
                }
            )

    scheduler_ok, scheduler_summary, scheduler_payload = _evidence_json(scheduler_evidence)
    if scheduler_ok:
        findings.append({"code": "admin_automation_scheduled", "severity": "info", "message": scheduler_summary, "evidence": scheduler_payload})
    else:
        findings.append(
            {
                "code": "admin_automation_not_scheduled",
                "severity": "warning",
                "message": "Recurring admin inventory, freshness, and gap-report runs still need production scheduler evidence.",
                "details": scheduler_summary,
            }
        )
        actions.append({"kind": "schedule_admin_curation", "priority": 3, "message": "Install the scheduled GitHub Actions admin curation workflow and provide its evidence JSON."})

    doctor_ok, doctor_summary, doctor_payload = _evidence_json(doctor_parity_evidence)
    if doctor_ok:
        findings.append({"code": "doctor_parity_verified", "severity": "info", "message": doctor_summary, "evidence": doctor_payload})
    else:
        findings.append(
            {
                "code": "doctor_parity_remaining",
                "severity": "warning",
                "message": "Native Objective-C doctor deep-detection parity needs final built-CLI evidence.",
                "details": doctor_summary,
            }
        )
        actions.append({"kind": "prove_doctor_parity", "priority": 4, "message": "Run final built-native-CLI doctor parity evidence on the release-supported platforms."})

    for target in inventory["served"]["matrix"]:
        if not target.get("publish", True):
            findings.append(
                {
                    "code": "deferred_target",
                    "severity": "info",
                    "target": target.get("id"),
                    "message": "Target is modeled but not published for the current support claim.",
                }
            )
    for package in publication.get("packages", []):
        for artifact in package.get("artifacts", []):
            if artifact.get("publish") is False:
                findings.append(
                    {
                        "code": "unpublished_artifact",
                        "severity": "info",
                        "package": package.get("id"),
                        "artifact": artifact.get("id"),
                        "message": "Package artifact is planned but not publishable for the current channel.",
                    }
                )
    ok, status = _status_from_findings(findings)
    if ok and status == "ok":
        summary = "All actionable admin gap findings are closed for the supplied evidence."
    elif status == "warning":
        summary = "Admin gap report has remaining warnings."
    else:
        summary = "Admin gap report has remaining blockers."
    inputs = dict(inventory["inputs"])
    inputs.update(
        {
            "evidence_dir": str(evidence_path) if evidence_path else None,
            "release_trust_root": str(release_trust_root) if release_trust_root else None,
            "package_index_trust_root": str(package_index_trust_root) if package_index_trust_root else None,
            "smoke_reports": [str(path) for path in smoke_paths],
            "update_all_evidence": str(update_path) if update_path else None,
            "scheduler_evidence": str(scheduler_evidence) if scheduler_evidence else None,
            "doctor_parity_evidence": str(doctor_parity_evidence) if doctor_parity_evidence else None,
        }
    )
    return _payload("gap-report", ok, status, summary, inputs=inputs, findings=findings, actions=actions)


def admin_build_plan(
    repo_root: str | Path | None = None,
    *,
    packages_dir: str | Path | None = None,
    targets: list[str] | None = None,
    channel: str = "dogfood",
    version: str = "0.1.0-dev-current",
    otvm_config: str = "~/oracletestvms-libvirt.toml",
    runner_label: str | None = None,
    toolchain_url: str | None = None,
    toolchain_sha256: str | None = None,
    toolchain_artifact_run_id: str | None = None,
    toolchain_artifact_name: str | None = None,
    windows_toolchain_source: str = "assemble-msys2",
    windows_toolchain_zip_url: str | None = None,
    windows_toolchain_zip_sha256: str | None = None,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    packages_root = Path(packages_dir).resolve() if packages_dir else root / "packages"
    package_plan = package_artifact_build_plan(str(packages_root))
    matrix_targets = build_matrix().get("targets", [])
    selected = set(targets or [])
    actions = []

    for target in matrix_targets:
        if selected and target.get("id") not in selected:
            continue
        if not target.get("publish", True):
            actions.append({"kind": "skip_deferred_target", "target": target.get("id"), "reason": "Target publish=false."})
            continue
        workflow = "linux-managed-artifacts.yml" if target.get("os") == "linux" else "windows-current-source-artifacts.yml" if target.get("os") == "windows" else None
        if workflow:
            if target.get("os") == "linux":
                inputs = {"target": target.get("id"), "version": version}
                if runner_label:
                    inputs["runner_label"] = runner_label
            else:
                inputs = {"version": version, "toolchain_source": windows_toolchain_source}
                if windows_toolchain_zip_url:
                    inputs["toolchain_zip_url"] = windows_toolchain_zip_url
                if windows_toolchain_zip_sha256:
                    inputs["toolchain_zip_sha256"] = windows_toolchain_zip_sha256
            actions.append({"kind": "github_workflow_dispatch", "target": target.get("id"), "workflow": workflow, "inputs": inputs})
        else:
            actions.append({"kind": "otvm_build_required", "target": target.get("id"), "message": "Use OTVM-backed build/validation for this target."})

    for package in package_plan.get("packages", []):
        for artifact in package.get("artifacts", []):
            if artifact.get("publish") is False:
                continue
            package_version = artifact.get("version") or package.get("version") or version
            if artifact.get("os") == "windows":
                inputs = {"package_id": package.get("id"), "target": artifact.get("id"), "version": package_version, "toolchain_source": windows_toolchain_source}
                if windows_toolchain_zip_url:
                    inputs["toolchain_zip_url"] = windows_toolchain_zip_url
                if windows_toolchain_zip_sha256:
                    inputs["toolchain_zip_sha256"] = windows_toolchain_zip_sha256
                missing_inputs = []
                if windows_toolchain_source == "existing-zip":
                    missing_inputs = [name for name, value in {"toolchain_zip_url": windows_toolchain_zip_url, "toolchain_zip_sha256": windows_toolchain_zip_sha256}.items() if not value]
                workflow = "windows-package-app-artifact.yml"
            else:
                inputs = {"package_id": package.get("id"), "target": artifact.get("id"), "version": package_version}
                if toolchain_artifact_run_id:
                    inputs["toolchain_artifact_run_id"] = toolchain_artifact_run_id
                    if toolchain_artifact_name:
                        inputs["toolchain_artifact_name"] = toolchain_artifact_name
                elif toolchain_url or toolchain_sha256:
                    if toolchain_url:
                        inputs["toolchain_url"] = toolchain_url
                    if toolchain_sha256:
                        inputs["toolchain_sha256"] = toolchain_sha256
                if runner_label:
                    inputs["runner_label"] = runner_label
                has_artifact_ref = bool(toolchain_artifact_run_id)
                has_url_ref = bool(toolchain_url and toolchain_sha256)
                missing_inputs = [] if has_artifact_ref or has_url_ref else ["toolchain_url+toolchain_sha256 or toolchain_artifact_run_id"]
                workflow = "package-app-artifact.yml"
            actions.append(
                {
                    "kind": "package_artifact_build",
                    "package": package.get("id"),
                    "artifact": artifact.get("id"),
                    "workflow": workflow,
                    "inputs": inputs,
                    "blocked": bool(missing_inputs),
                    "missing_inputs": missing_inputs,
                }
            )

    otvm_targets = [a["target"] for a in actions if a["kind"] == "otvm_build_required"]
    if otvm_targets:
        otvm_plan = session_build_box_plan(targets=otvm_targets, ttl_hours=8, channel=channel, repo_root=str(root), otvm_config=otvm_config)
    else:
        otvm_plan = {
            "schema_version": 1,
            "command": "session-build-box-plan",
            "ok": True,
            "status": "ok",
            "summary": "No OTVM-backed build targets are required for this plan.",
            "channel": channel,
            "ttl_hours": 8,
            "otvm_config": otvm_config,
            "targets": [],
            "builders": [],
            "steps": [],
            "cost_controls": {"default_ttl_hours": 8, "requires_explicit_cleanup": True, "list_active_leases_before_provisioning": True},
        }
    return _payload(
        "build-plan",
        True,
        "ok",
        f"Build plan generated with {len(actions)} action(s).",
        inputs={"repo_root": str(root), "packages_dir": str(packages_root), "targets": targets or [], "channel": channel, "version": version},
        findings=[],
        actions=actions,
        otvm_plan=otvm_plan,
    )


def admin_dispatch_builds(
    repo_root: str | Path | None = None,
    *,
    packages_dir: str | Path | None = None,
    targets: list[str] | None = None,
    channel: str = "dogfood",
    version: str = "0.1.0-dev-current",
    repo: str = "danjboyd/gnustep-cli-new",
    apply: bool = False,
    runner_label: str | None = None,
    toolchain_url: str | None = None,
    toolchain_sha256: str | None = None,
    toolchain_artifact_run_id: str | None = None,
    toolchain_artifact_name: str | None = None,
    windows_toolchain_source: str = "assemble-msys2",
    windows_toolchain_zip_url: str | None = None,
    windows_toolchain_zip_sha256: str | None = None,
) -> dict[str, Any]:
    plan = admin_build_plan(
        repo_root,
        packages_dir=packages_dir,
        targets=targets,
        channel=channel,
        version=version,
        runner_label=runner_label,
        toolchain_url=toolchain_url,
        toolchain_sha256=toolchain_sha256,
        toolchain_artifact_run_id=toolchain_artifact_run_id,
        toolchain_artifact_name=toolchain_artifact_name,
        windows_toolchain_source=windows_toolchain_source,
        windows_toolchain_zip_url=windows_toolchain_zip_url,
        windows_toolchain_zip_sha256=windows_toolchain_zip_sha256,
    )
    dispatches = []
    failures = []
    blocked = []
    for action in plan["actions"]:
        if action.get("kind") not in {"github_workflow_dispatch", "package_artifact_build"}:
            continue
        if action.get("blocked"):
            blocked.append(action)
            continue
        workflow = action["workflow"]
        inputs = action.get("inputs", {})
        command = ["gh", "workflow", "run", workflow, "--repo", repo]
        for key, value in inputs.items():
            command.extend(["-f", f"{key}={value}"])
        dispatch = {"action": action, "command": command, "applied": False}
        if apply:
            proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            dispatch["applied"] = proc.returncode == 0
            dispatch["returncode"] = proc.returncode
            if proc.returncode != 0:
                dispatch["stderr"] = proc.stderr
                failures.append(dispatch)
        dispatches.append(dispatch)
    ok = not failures
    findings = []
    if failures:
        findings.append({"code": "dispatch_failed", "severity": "error", "message": "One or more workflow dispatches failed."})
    if blocked:
        findings.append({"code": "dispatch_blocked", "severity": "warning", "message": "One or more planned dispatches need additional toolchain inputs before they can be run.", "count": len(blocked)})
    return _payload(
        "dispatch-builds",
        ok,
        "warning" if blocked and ok else "ok" if ok else "error",
        "Build dispatch plan generated." if not apply else ("Build dispatches completed." if ok else "Some build dispatches failed."),
        inputs={"repo": repo, "apply": apply, "channel": channel, "version": version},
        findings=findings,
        actions=plan["actions"],
        dispatches=dispatches,
        blocked=blocked,
    )


def admin_doctor_parity(
    *,
    native_doctor: str | Path,
    shared_doctor: str | Path,
) -> dict[str, Any]:
    native_path = Path(native_doctor).resolve()
    shared_path = Path(shared_doctor).resolve()
    native = _read_json(native_path)
    shared = _read_json(shared_path)
    checks: list[dict[str, Any]] = []

    def add(check_id: str, ok: bool, message: str, **extra: Any) -> None:
        item = {"id": check_id, "ok": ok, "message": message}
        item.update(extra)
        checks.append(item)

    required_top = {
        "schema_version",
        "command",
        "ok",
        "status",
        "environment_classification",
        "environment",
        "compatibility",
        "checks",
        "actions",
    }
    required_check_ids = {
        "host.identity",
        "bootstrap.downloader",
        "toolchain.detect",
        "native-toolchain.assess",
        "toolchain.features",
        "toolchain.probe",
        "managed.install.integrity",
        "toolchain.compatibility",
    }
    native_top_missing = sorted(required_top - set(native))
    shared_top_missing = sorted(required_top - set(shared))
    add("top-level-shape", not native_top_missing and not shared_top_missing, "Native and shared doctor payloads expose the required top-level JSON shape.", native_missing=native_top_missing, shared_missing=shared_top_missing)
    add("command", native.get("command") == "doctor" and shared.get("command") == "doctor", "Both payloads are doctor payloads.")
    add(
        "classification-match",
        native.get("environment_classification") == shared.get("environment_classification"),
        "Native and shared doctor classifications match.",
        native_classification=native.get("environment_classification"),
        shared_classification=shared.get("environment_classification"),
    )
    add(
        "assessment-match",
        native.get("native_toolchain_assessment") == shared.get("native_toolchain_assessment"),
        "Native and shared native-toolchain assessments match.",
        native_assessment=native.get("native_toolchain_assessment"),
        shared_assessment=shared.get("native_toolchain_assessment"),
    )
    native_check_ids = {check.get("id") for check in native.get("checks", []) if isinstance(check, dict)}
    shared_check_ids = {check.get("id") for check in shared.get("checks", []) if isinstance(check, dict)}
    add(
        "required-checks-present",
        required_check_ids.issubset(native_check_ids) and required_check_ids.issubset(shared_check_ids),
        "Native and shared doctor payloads include the required core check ids.",
        native_missing=sorted(required_check_ids - native_check_ids),
        shared_missing=sorted(required_check_ids - shared_check_ids),
    )
    native_features = next((check for check in native.get("checks", []) if isinstance(check, dict) and check.get("id") == "toolchain.features"), {})
    shared_features = next((check for check in shared.get("checks", []) if isinstance(check, dict) and check.get("id") == "toolchain.features"), {})
    feature_keys = {"blocks", "objc2_syntax", "nonfragile_abi"}
    native_feature_details = native_features.get("details", {}) if isinstance(native_features, dict) else {}
    shared_feature_details = shared_features.get("details", {}) if isinstance(shared_features, dict) else {}
    add(
        "toolchain-features-shape",
        feature_keys.issubset(set(native_feature_details)) and feature_keys.issubset(set(shared_feature_details)),
        "Native and shared toolchain.features checks expose required feature details.",
        native_missing=sorted(feature_keys - set(native_feature_details)),
        shared_missing=sorted(feature_keys - set(shared_feature_details)),
    )
    add(
        "compatibility-shape",
        isinstance(native.get("compatibility"), dict) and isinstance(shared.get("compatibility"), dict),
        "Native and shared doctor payloads expose structured compatibility objects.",
    )
    native_actions_ok = isinstance(native.get("actions"), list) and all(isinstance(action, dict) and {"kind", "priority", "message"}.issubset(action) for action in native.get("actions", []))
    shared_actions_ok = isinstance(shared.get("actions"), list) and all(isinstance(action, dict) and {"kind", "priority", "message"}.issubset(action) for action in shared.get("actions", []))
    add("actions-shape", native_actions_ok and shared_actions_ok, "Native and shared doctor payloads expose structured action entries.")
    ok = all(check["ok"] for check in checks)
    return _payload(
        "doctor-parity",
        ok,
        "ok" if ok else "error",
        "Native doctor parity evidence passed." if ok else "Native doctor parity evidence failed.",
        inputs={"native_doctor": str(native_path), "shared_doctor": str(shared_path)},
        checks=checks,
    )


def admin_schedule_template(command: str = "gap-report", *, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repo_root)
    executable = str(root / "scripts" / "internal" / "admin.py")
    shell_command = f"cd {shlex.quote(str(root))} && mkdir -p .artifacts && {shlex.quote(executable)} --json {shlex.quote(command)}"
    systemd_service = (
        "[Unit]\n"
        "Description=GNUstep CLI admin curation check\n\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"WorkingDirectory={root}\n"
        f"ExecStart={executable} --json {command}\n"
    )
    systemd_timer = (
        "[Unit]\n"
        "Description=Run GNUstep CLI admin curation check daily\n\n"
        "[Timer]\n"
        "OnCalendar=daily\n"
        "Persistent=true\n\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    )
    cron = f"17 3 * * * {shell_command} >> {root}/.artifacts/gnustep-admin-{command}.jsonl 2>&1"
    return _payload(
        "schedule-template",
        True,
        "ok",
        "Scheduler templates generated.",
        inputs={"repo_root": str(root), "admin_command": command},
        findings=[],
        actions=[],
        templates={"systemd_service": systemd_service, "systemd_timer": systemd_timer, "cron": cron},
    )
