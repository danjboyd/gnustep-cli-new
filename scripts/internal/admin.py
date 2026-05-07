#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.admin import (
    admin_build_plan,
    admin_dispatch_builds,
    admin_doctor_parity,
    admin_gap_report,
    admin_inventory,
    admin_schedule_template,
    admin_upstream_check,
    admin_upstream_sources,
)


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root", default=str(ROOT))


def _add_package_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--packages-dir")


def _add_build_common(parser: argparse.ArgumentParser) -> None:
    _add_common(parser)
    _add_package_common(parser)
    parser.add_argument("--target", action="append", dest="targets")
    parser.add_argument("--channel", default="dogfood")
    parser.add_argument("--version", default="0.1.0-dev-current")
    parser.add_argument("--runner-label")
    parser.add_argument("--toolchain-url")
    parser.add_argument("--toolchain-sha256")
    parser.add_argument("--toolchain-artifact-run-id")
    parser.add_argument("--toolchain-artifact-name")
    parser.add_argument("--windows-toolchain-source", default="assemble-msys2")
    parser.add_argument("--windows-toolchain-zip-url")
    parser.add_argument("--windows-toolchain-zip-sha256")


def _emit(payload: dict[str, Any], json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, separators=(",", ":")))
        return
    print(f"{payload.get('command')}: {payload.get('status')}: {payload.get('summary')}")
    for finding in payload.get("findings", []):
        print(f"{payload.get('command')}: finding={finding.get('code')} severity={finding.get('severity')} {finding.get('message', '')}")
    for action in payload.get("actions", []):
        kind = action.get("kind")
        target = action.get("target") or action.get("artifact") or action.get("package") or ""
        blocked = " blocked=true" if action.get("blocked") else ""
        print(f"{payload.get('command')}: action={kind} {target}{blocked}".rstrip())
    for dispatch in payload.get("dispatches", []):
        print(f"{payload.get('command')}: dispatch={' '.join(dispatch.get('command', []))}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    inventory = subparsers.add_parser("inventory")
    _add_common(inventory)
    _add_package_common(inventory)
    inventory.add_argument("--release-dir")
    inventory.add_argument("--package-index")

    upstream = subparsers.add_parser("upstream-check")
    _add_common(upstream)
    _add_package_common(upstream)
    upstream.add_argument("--upstream-cache")
    upstream.add_argument("--fetch", action="store_true")

    upstream_sources = subparsers.add_parser("upstream-sources")
    _add_common(upstream_sources)
    _add_package_common(upstream_sources)

    gap = subparsers.add_parser("gap-report")
    _add_common(gap)
    _add_package_common(gap)
    gap.add_argument("--release-dir")
    gap.add_argument("--package-index")
    gap.add_argument("--evidence-dir")
    gap.add_argument("--release-trust-root")
    gap.add_argument("--package-index-trust-root")
    gap.add_argument("--smoke-report", action="append", default=[])
    gap.add_argument("--update-all-evidence")
    gap.add_argument("--scheduler-evidence")
    gap.add_argument("--doctor-parity-evidence")

    build_plan = subparsers.add_parser("build-plan")
    _add_build_common(build_plan)
    build_plan.add_argument("--otvm-config", default="~/oracletestvms-libvirt.toml")

    dispatch = subparsers.add_parser("dispatch-builds")
    _add_build_common(dispatch)
    dispatch.add_argument("--repo", default="danjboyd/gnustep-cli-new")
    dispatch.add_argument("--apply", action="store_true")

    schedule = subparsers.add_parser("schedule-template")
    _add_common(schedule)
    schedule.add_argument("--command", default="gap-report")

    doctor_parity = subparsers.add_parser("doctor-parity")
    doctor_parity.add_argument("--native-doctor", required=True)
    doctor_parity.add_argument("--shared-doctor", required=True)

    args = parser.parse_args()
    if args.subcommand == "inventory":
        payload = admin_inventory(args.repo_root, release_dir=args.release_dir, package_index=args.package_index, packages_dir=args.packages_dir)
    elif args.subcommand == "upstream-check":
        payload = admin_upstream_check(args.repo_root, packages_dir=args.packages_dir, upstream_cache=args.upstream_cache, fetch=args.fetch)
    elif args.subcommand == "upstream-sources":
        payload = admin_upstream_sources(args.repo_root, packages_dir=args.packages_dir)
    elif args.subcommand == "gap-report":
        payload = admin_gap_report(
            args.repo_root,
            release_dir=args.release_dir,
            package_index=args.package_index,
            packages_dir=args.packages_dir,
            evidence_dir=args.evidence_dir,
            release_trust_root=args.release_trust_root,
            package_index_trust_root=args.package_index_trust_root,
            smoke_report_paths=args.smoke_report,
            update_all_evidence=args.update_all_evidence,
            scheduler_evidence=args.scheduler_evidence,
            doctor_parity_evidence=args.doctor_parity_evidence,
        )
    elif args.subcommand == "build-plan":
        payload = admin_build_plan(
            args.repo_root,
            packages_dir=args.packages_dir,
            targets=args.targets,
            channel=args.channel,
            version=args.version,
            otvm_config=args.otvm_config,
            runner_label=args.runner_label,
            toolchain_url=args.toolchain_url,
            toolchain_sha256=args.toolchain_sha256,
            toolchain_artifact_run_id=args.toolchain_artifact_run_id,
            toolchain_artifact_name=args.toolchain_artifact_name,
            windows_toolchain_source=args.windows_toolchain_source,
            windows_toolchain_zip_url=args.windows_toolchain_zip_url,
            windows_toolchain_zip_sha256=args.windows_toolchain_zip_sha256,
        )
    elif args.subcommand == "dispatch-builds":
        payload = admin_dispatch_builds(
            args.repo_root,
            packages_dir=args.packages_dir,
            targets=args.targets,
            channel=args.channel,
            version=args.version,
            repo=args.repo,
            apply=args.apply,
            runner_label=args.runner_label,
            toolchain_url=args.toolchain_url,
            toolchain_sha256=args.toolchain_sha256,
            toolchain_artifact_run_id=args.toolchain_artifact_run_id,
            toolchain_artifact_name=args.toolchain_artifact_name,
            windows_toolchain_source=args.windows_toolchain_source,
            windows_toolchain_zip_url=args.windows_toolchain_zip_url,
            windows_toolchain_zip_sha256=args.windows_toolchain_zip_sha256,
        )
    elif args.subcommand == "doctor-parity":
        payload = admin_doctor_parity(native_doctor=args.native_doctor, shared_doctor=args.shared_doctor)
    else:
        payload = admin_schedule_template(args.command, repo_root=args.repo_root)

    _emit(payload, args.json)
    return 0 if payload.get("ok", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
