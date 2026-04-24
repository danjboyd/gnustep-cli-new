#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.smoke_harness import (
    empty_smoke_report,
    evidence_smoke_report,
    evaluate_release_gate,
    fixture_catalog,
    phase26_exit_status,
    release_gate_catalog,
    runner_execution_plan,
    runner_profiles,
    smoke_plan,
    smoke_scenarios,
    suite_catalog,
    suite_definition,
    target_profiles,
    validate_smoke_catalog,
    workflow_plan,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List and plan GNUstep CLI cross-platform smoke scenarios."
    )
    parser.add_argument(
        "--suite",
        default="tier1-core",
        help="Smoke suite to plan. Default: tier1-core",
    )
    parser.add_argument(
        "--target",
        action="append",
        dest="targets",
        default=[],
        help="Target ID to include. May be passed more than once.",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        dest="scenarios",
        default=[],
        help="Scenario ID to include. May be passed more than once.",
    )
    parser.add_argument(
        "--list-suites",
        action="store_true",
        help="Print known smoke suite definitions.",
    )
    parser.add_argument(
        "--list-targets",
        action="store_true",
        help="Print known smoke target profiles.",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="Print known smoke scenario definitions.",
    )
    parser.add_argument(
        "--list-runners",
        action="store_true",
        help="Print known smoke runner profiles.",
    )
    parser.add_argument(
        "--list-fixtures",
        action="store_true",
        help="Print pinned smoke fixture records.",
    )
    parser.add_argument(
        "--release-source",
        default="dist-or-manifest-unspecified",
        help="Release directory, manifest URL, or channel identifier used for planning/report templates.",
    )
    parser.add_argument(
        "--reuse-existing-runner",
        action="store_true",
        help="Ask the runner planner to prefer reusing an existing host or lease.",
    )
    parser.add_argument(
        "--ttl-hours",
        type=int,
        help="Requested TTL for lease-backed execution planning.",
    )
    parser.add_argument(
        "--runner-plan",
        action="store_true",
        help="Print the runner execution plan for exactly one selected target.",
    )
    parser.add_argument(
        "--report-template",
        action="store_true",
        help="Print an empty structured smoke report template for exactly one selected target.",
    )
    parser.add_argument(
        "--list-release-gates",
        action="store_true",
        help="Print known smoke release-gate policies.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the smoke catalog and exit.",
    )
    parser.add_argument(
        "--workflow-plan",
        action="store_true",
        help="Print a developer workflow plan for the selected suite and targets.",
    )
    parser.add_argument(
        "--release-gate",
        choices=["dogfood", "release-candidate", "stable"],
        help="Evaluate a smoke release gate against one or more report JSON files.",
    )
    parser.add_argument(
        "--report",
        action="append",
        dest="reports",
        default=[],
        help="Smoke report JSON path. May be passed more than once.",
    )
    parser.add_argument(
        "--phase26-exit-status",
        action="store_true",
        help="Evaluate Phase 26 exit criteria against optional smoke reports.",
    )
    parser.add_argument(
        "--evidence-report",
        action="store_true",
        help="Import externally collected live evidence as a structured smoke report.",
    )
    parser.add_argument(
        "--passed-scenario",
        action="append",
        dest="passed_scenarios",
        default=[],
        help="Scenario ID that passed in the imported live evidence. May be passed more than once.",
    )
    parser.add_argument(
        "--evidence-file",
        action="append",
        dest="evidence_files",
        default=[],
        help="JSON evidence file to reference from an imported smoke report. May be passed more than once.",
    )
    return parser.parse_args()


def emit(payload: object) -> int:
    print(json.dumps(payload, indent=2))
    return 0


def main() -> int:
    args = parse_args()

    if args.list_targets:
        return emit({"schema_version": 1, "targets": target_profiles()})
    if args.list_suites:
        return emit({"schema_version": 1, "suites": suite_catalog()})
    if args.list_scenarios:
        return emit({"schema_version": 1, "scenarios": smoke_scenarios()})
    if args.list_runners:
        return emit({"schema_version": 1, "runners": runner_profiles()})
    if args.list_fixtures:
        return emit({"schema_version": 1, "fixtures": fixture_catalog()})
    if args.list_release_gates:
        return emit({"schema_version": 1, "release_gates": release_gate_catalog()})
    if args.validate_only:
        payload = validate_smoke_catalog()
        print(json.dumps(payload, indent=2))
        return 0 if payload["ok"] else 1
    if args.workflow_plan:
        return emit(
            workflow_plan(
                suite_id=args.suite,
                target_ids=args.targets or None,
                release_source=args.release_source,
                reuse_existing_runner=args.reuse_existing_runner,
                ttl_hours=args.ttl_hours,
            )
        )
    if args.runner_plan:
        if len(args.targets) != 1:
            raise SystemExit("--runner-plan requires exactly one --target")
        return emit(
            {
                "schema_version": 1,
                "plan": runner_execution_plan(
                    target_id=args.targets[0],
                    release_source=args.release_source,
                    scenario_ids=args.scenarios or None,
                    reuse_existing=args.reuse_existing_runner,
                    ttl_hours=args.ttl_hours,
                ),
            }
        )
    if args.report_template:
        if len(args.targets) != 1:
            raise SystemExit("--report-template requires exactly one --target")
        return emit(
            empty_smoke_report(
                suite_id=args.suite,
                target_id=args.targets[0],
                release_source=args.release_source,
                scenario_ids=args.scenarios or None,
            )
        )
    if args.evidence_report:
        if len(args.targets) != 1:
            raise SystemExit("--evidence-report requires exactly one --target")
        return emit(
            evidence_smoke_report(
                suite_id=args.suite,
                target_id=args.targets[0],
                release_source=args.release_source,
                passed_scenario_ids=args.passed_scenarios,
                evidence_paths=args.evidence_files,
            )
        )
    if args.release_gate:
        if not args.reports:
            raise SystemExit("--release-gate requires at least one --report")
        payload = evaluate_release_gate(
            gate_id=args.release_gate,
            report_paths=args.reports,
            expected_targets=args.targets or None,
        )
        print(json.dumps(payload, indent=2))
        return 0 if payload["ok"] else 1
    if args.phase26_exit_status:
        payload = phase26_exit_status(args.reports or None)
        print(json.dumps(payload, indent=2))
        return 0 if payload["ok"] else 1

    payload = smoke_plan(
        suite_id=args.suite,
        target_ids=args.targets or None,
        scenario_ids=args.scenarios or None,
    )
    payload["suite_definition"] = suite_definition(args.suite)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
