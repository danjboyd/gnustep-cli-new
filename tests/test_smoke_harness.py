import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.smoke_harness import (
    empty_smoke_report,
    evidence_smoke_report,
    evaluate_release_gate,
    fixture_record,
    phase26_exit_status,
    runner_execution_plan,
    smoke_plan,
    smoke_scenario,
    suite_catalog,
    suite_definition,
    target_profile,
    validate_smoke_catalog,
    workflow_plan,
)


class SmokeHarnessTests(unittest.TestCase):
    def test_catalog_validation_passes(self):
        payload = validate_smoke_catalog()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["targets"], 2)
        self.assertEqual(payload["scenarios"], 5)
        self.assertEqual(payload["fixtures"], 4)

    def test_windows_target_profile_is_tier1_otvm_managed(self):
        payload = target_profile("windows-amd64-msys2-clang64")
        self.assertEqual(payload["runner_profile"], "otvm-lease")
        self.assertEqual(payload["bootstrap_kind"], "powershell")
        self.assertTrue(payload["gui_available"])
        self.assertIn("tier1", payload["tags"])

    def test_openbsd_target_profile_uses_posix_bootstrap(self):
        payload = target_profile("openbsd-amd64-clang")
        self.assertEqual(payload["bootstrap_kind"], "posix-sh")
        self.assertEqual(payload["path_style"], "posix")
        self.assertEqual(payload["metadata"]["expected_objc_runtime"], "libobjc2")
        self.assertIn("native-packaged", payload["tags"])
        self.assertNotIn("managed", payload["tags"])
        self.assertEqual(payload["metadata"]["toolchain_source_policy"], "native-packaged-preferred")
        self.assertFalse(payload["metadata"]["managed_artifacts_required"])
        self.assertIn("gnustep-make", payload["metadata"]["native_package_prerequisites"])

    def test_core_scenarios_are_registered(self):
        scenario_ids = [
            "bootstrap-install-usable-cli",
            "new-cli-project-build-run",
            "gorm-build-run",
            "self-update-cli-only",
        ]
        for scenario_id in scenario_ids:
            with self.subTest(scenario_id=scenario_id):
                payload = smoke_scenario(scenario_id)
                self.assertEqual(payload["id"], scenario_id)
                self.assertEqual(
                    payload["supported_targets"],
                    ["windows-amd64-msys2-clang64", "openbsd-amd64-clang"],
                )

    def test_gorm_scenario_requires_gui_and_pinned_fixture(self):
        payload = smoke_scenario("gorm-build-run")
        self.assertTrue(payload["gui_required"])
        self.assertEqual(payload["fixture_policy"], "pinned-upstream-revision")
        self.assertIn("gorm-build-succeeds", payload["assertions"])

    def test_windows_shell_pacman_scenario_is_windows_only(self):
        payload = smoke_scenario("windows-shell-pacman")
        self.assertEqual(payload["supported_targets"], ["windows-amd64-msys2-clang64"])
        self.assertFalse(payload["gui_required"])
        self.assertIn("managed-msys2-toolchain", payload["artifact_prerequisites"])
        self.assertIn("pacman-query-succeeds-inside-shell", payload["assertions"])

    def test_windows_managed_shell_suite_contains_pacman_scenario(self):
        payload = suite_definition("windows-managed-shell")
        self.assertEqual(payload["scenario_ids"], ["windows-shell-pacman"])

    def test_gorm_fixture_is_pinned_to_immutable_reference(self):
        payload = fixture_record("gorm-upstream-pinned")
        self.assertEqual(payload["provenance"]["reference"], "gorm-1_5_0")
        self.assertEqual(payload["provenance"]["commit"], "a8cd1792e08a50dd9900474373e6ca8daad4a4a9")
        self.assertFalse(payload["provenance"]["mutable"])

    def test_windows_gorm_template_includes_private_ivar_patch_fixture(self):
        payload = empty_smoke_report(
            suite_id="tier1-core",
            target_id="windows-amd64-msys2-clang64",
            release_source="/tmp/staged-release",
            scenario_ids=["gorm-build-run"],
        )
        self.assertEqual(
            payload["fixture_references"],
            ["gorm-upstream-pinned", "gorm-windows-private-ivar-patch"],
        )
        fixture = fixture_record("gorm-windows-private-ivar-patch")
        self.assertEqual(fixture["provenance"]["target_id"], "windows-amd64-msys2-clang64")
        self.assertEqual(
            fixture["expected_observations"]["removes_symbol_reference"],
            "__objc_ivar_offset_NSMatrix._selectedCells",
        )

    def test_otvm_runner_plan_for_windows_includes_lease_lifecycle(self):
        payload = runner_execution_plan(
            target_id="windows-amd64-msys2-clang64",
            release_source="https://example.invalid/dogfood/release-manifest.json",
            scenario_ids=["bootstrap-install-usable-cli", "self-update-cli-only"],
            reuse_existing=True,
            ttl_hours=4,
        )
        self.assertEqual(payload["kind"], "otvm")
        self.assertTrue(payload["reuse_existing"])
        self.assertEqual(payload["ttl_hours"], 4)
        self.assertEqual(payload["transport"]["lease_profile"], "windows-2022")
        self.assertIn("collect-report-json-and-failure-artifacts", payload["stage_actions"])

    def test_empty_report_template_contains_fixture_references_and_runner_plan(self):
        payload = empty_smoke_report(
            suite_id="tier1-core",
            target_id="openbsd-amd64-clang",
            release_source="/tmp/staged-release",
            scenario_ids=["gorm-build-run"],
        )
        self.assertEqual(payload["runner_id"], "otvm-lease")
        self.assertEqual(payload["fixture_references"], ["gorm-upstream-pinned"])
        self.assertEqual(payload["scenario_reports"][0]["scenario_id"], "gorm-build-run")
        self.assertIn("runner_execution_plan", payload["evidence"])
        self.assertEqual(
            payload["evidence"]["runner_execution_plan"]["transport"]["lease_profile"],
            "openbsd-7.8-fvwm",
        )

    def test_smoke_plan_defaults_to_tier1_core_suite(self):
        payload = smoke_plan()
        self.assertEqual(payload["suite"]["id"], "tier1-core")
        self.assertEqual(len(payload["targets"]), 2)
        self.assertEqual(
            [scenario["id"] for scenario in payload["targets"][0]["scenarios"]],
            list(suite_definition("tier1-core")["scenario_ids"]),
        )

    def test_quick_suite_plan_can_be_scoped_to_single_target(self):
        payload = smoke_plan(suite_id="quick", target_ids=["openbsd-amd64-clang"])
        self.assertEqual(len(payload["targets"]), 1)
        self.assertEqual(payload["targets"][0]["target"]["id"], "openbsd-amd64-clang")
        self.assertEqual(
            [scenario["id"] for scenario in payload["targets"][0]["scenarios"]],
            ["bootstrap-install-usable-cli", "new-cli-project-build-run"],
        )

    def test_planner_rejects_unknown_target(self):
        with self.assertRaises(ValueError):
            smoke_plan(target_ids=["plan9-amd64"])

    def test_suite_catalog_includes_release_mode(self):
        payload = suite_catalog()
        release_suite = next(item for item in payload if item["id"] == "release")
        self.assertEqual(release_suite["mode"], "release")
        self.assertEqual(release_suite["release_gate_usage"], "stable-publication")

    def test_workflow_plan_emits_runner_and_report_commands(self):
        payload = workflow_plan(
            suite_id="quick",
            target_ids=["windows-amd64-msys2-clang64"],
            release_source="dogfood",
            reuse_existing_runner=True,
            ttl_hours=2,
        )
        command_ids = [command["id"] for command in payload["commands"]]
        self.assertIn("validate-catalog", command_ids)
        self.assertIn("runner-plan-windows-amd64-msys2-clang64", command_ids)
        self.assertIn("report-template-windows-amd64-msys2-clang64", command_ids)

    def test_release_gate_passes_for_matching_report(self):
        with tempfile.TemporaryDirectory() as tempdir:
            report_path = Path(tempdir) / "windows.json"
            report_path.write_text(
                json.dumps(
                    evidence_smoke_report(
                        suite_id="tier1-core",
                        target_id="windows-amd64-msys2-clang64",
                        release_source="dogfood",
                        passed_scenario_ids=[
                            "bootstrap-install-usable-cli",
                            "new-cli-project-build-run",
                            "gorm-build-run",
                            "self-update-cli-only",
                        ],
                    )
                )
            )
            payload = evaluate_release_gate(
                gate_id="dogfood",
                report_paths=[report_path],
                expected_targets=["windows-amd64-msys2-clang64"],
            )
            self.assertTrue(payload["ok"])

    def test_release_gate_rejects_wrong_suite_or_missing_target(self):
        with tempfile.TemporaryDirectory() as tempdir:
            report_path = Path(tempdir) / "windows.json"
            report_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "suite_id": "quick",
                        "target_id": "windows-amd64-msys2-clang64",
                        "runner_id": "otvm-lease",
                        "release_under_test": {"source": "dogfood"},
                        "fixture_references": [],
                        "overall_ok": True,
                        "scenario_reports": [],
                        "evidence": {},
                    }
                )
            )
            payload = evaluate_release_gate(
                gate_id="release-candidate",
                report_paths=[report_path],
                expected_targets=["windows-amd64-msys2-clang64", "openbsd-amd64-clang"],
            )
            self.assertFalse(payload["ok"])
            finding_kinds = [finding["kind"] for finding in payload["findings"]]
            self.assertIn("wrong_suite", finding_kinds)
            self.assertIn("missing_targets", finding_kinds)

    def test_phase26_exit_status_requires_live_reports_for_full_pass(self):
        payload = phase26_exit_status()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["status"], "warning")
        check_ids = [check["id"] for check in payload["checks"]]
        self.assertIn("tier1-reports-pass", check_ids)

    def test_evidence_smoke_report_requires_every_suite_scenario_for_gate(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            evidence = temp / "windows-evidence.json"
            evidence.write_text(json.dumps({"ok": True, "summary": "Windows update passed."}))
            report = evidence_smoke_report(
                suite_id="tier1-core",
                target_id="windows-amd64-msys2-clang64",
                release_source="local-dogfood",
                passed_scenario_ids=["bootstrap-install-usable-cli", "self-update-cli-only"],
                evidence_paths=[evidence],
            )
            report_path = temp / "windows-report.json"
            report_path.write_text(json.dumps(report))
            gate = evaluate_release_gate(
                gate_id="dogfood",
                report_paths=[report_path],
                expected_targets=["windows-amd64-msys2-clang64"],
            )
            self.assertFalse(gate["ok"])
            self.assertFalse(report["overall_ok"])
            self.assertIn("report_failed", [finding["kind"] for finding in gate["findings"]])

    def test_smoke_report_loader_accepts_powershell_utf8_bom(self):
        with tempfile.TemporaryDirectory() as tempdir:
            report_path = Path(tempdir) / "windows-report.json"
            report_path.write_text(
                "\ufeff" + json.dumps(
                    evidence_smoke_report(
                        suite_id="tier1-core",
                        target_id="windows-amd64-msys2-clang64",
                        release_source="local-dogfood",
                        passed_scenario_ids=[
                            "bootstrap-install-usable-cli",
                            "new-cli-project-build-run",
                            "gorm-build-run",
                            "self-update-cli-only",
                        ],
                    )
                ),
                encoding="utf-8",
            )
            gate = evaluate_release_gate(
                gate_id="dogfood",
                report_paths=[report_path],
                expected_targets=["windows-amd64-msys2-clang64"],
            )
            self.assertTrue(gate["ok"])


class SmokeHarnessScriptTests(unittest.TestCase):
    def test_run_smoke_tests_script_lists_scenarios(self):
        proc = subprocess.run(
            [sys.executable, "scripts/dev/run-smoke-tests.py", "--list-scenarios"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(len(payload["scenarios"]), 5)

    def test_run_smoke_tests_script_lists_fixtures(self):
        proc = subprocess.run(
            [sys.executable, "scripts/dev/run-smoke-tests.py", "--list-fixtures"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(len(payload["fixtures"]), 4)

    def test_run_smoke_tests_script_lists_suites(self):
        proc = subprocess.run(
            [sys.executable, "scripts/dev/run-smoke-tests.py", "--list-suites"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertGreaterEqual(len(payload["suites"]), 3)

    def test_run_smoke_tests_script_emits_plan(self):
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/dev/run-smoke-tests.py",
                "--suite",
                "quick",
                "--target",
                "windows-amd64-msys2-clang64",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["suite"]["id"], "quick")
        self.assertEqual(len(payload["targets"]), 1)
        self.assertEqual(payload["targets"][0]["target"]["id"], "windows-amd64-msys2-clang64")

    def test_run_smoke_tests_script_emits_workflow_plan(self):
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/dev/run-smoke-tests.py",
                "--workflow-plan",
                "--suite",
                "quick",
                "--target",
                "openbsd-amd64-clang",
                "--release-source",
                "dogfood",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["suite"]["id"], "quick")
        self.assertEqual(payload["targets"], ["openbsd-amd64-clang"])

    def test_run_smoke_tests_script_emits_runner_plan(self):
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/dev/run-smoke-tests.py",
                "--runner-plan",
                "--target",
                "openbsd-amd64-clang",
                "--release-source",
                "dogfood",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["plan"]["transport"]["lease_profile"], "openbsd-7.8-fvwm")

    def test_run_smoke_tests_script_emits_report_template(self):
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/dev/run-smoke-tests.py",
                "--report-template",
                "--target",
                "windows-amd64-msys2-clang64",
                "--scenario",
                "self-update-cli-only",
                "--release-source",
                "https://example.invalid/dogfood/release-manifest.json",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["target_id"], "windows-amd64-msys2-clang64")
        self.assertEqual(payload["fixture_references"], ["cli-only-update-channel"])
        self.assertEqual(payload["scenario_reports"][0]["scenario_id"], "self-update-cli-only")

    def test_run_smoke_tests_script_evaluates_release_gate(self):
        with tempfile.TemporaryDirectory() as tempdir:
            report_path = Path(tempdir) / "windows.json"
            report_path.write_text(
                json.dumps(
                    evidence_smoke_report(
                        suite_id="tier1-core",
                        target_id="windows-amd64-msys2-clang64",
                        release_source="dogfood",
                        passed_scenario_ids=[
                            "bootstrap-install-usable-cli",
                            "new-cli-project-build-run",
                            "gorm-build-run",
                            "self-update-cli-only",
                        ],
                    )
                )
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    "scripts/dev/run-smoke-tests.py",
                    "--release-gate",
                    "dogfood",
                    "--target",
                    "windows-amd64-msys2-clang64",
                    "--report",
                    str(report_path),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["ok"])

    def test_run_smoke_tests_script_reports_phase26_status(self):
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/dev/run-smoke-tests.py",
                "--phase26-exit-status",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["command"], "phase26-exit-status")
        self.assertFalse(payload["ok"])

    def test_run_smoke_tests_script_imports_evidence_report(self):
        with tempfile.TemporaryDirectory() as tempdir:
            evidence = Path(tempdir) / "evidence.json"
            evidence.write_text(json.dumps({"ok": True, "summary": "Imported evidence passed."}))
            proc = subprocess.run(
                [
                    sys.executable,
                    "scripts/dev/run-smoke-tests.py",
                    "--evidence-report",
                    "--suite",
                    "tier1-core",
                    "--target",
                    "windows-amd64-msys2-clang64",
                    "--release-source",
                    "local-dogfood",
                    "--passed-scenario",
                    "self-update-cli-only",
                    "--evidence-file",
                    str(evidence),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["target_id"], "windows-amd64-msys2-clang64")
            self.assertFalse(payload["overall_ok"])
            self.assertEqual(payload["scenario_reports"][3]["scenario_id"], "self-update-cli-only")
            self.assertTrue(payload["scenario_reports"][3]["ok"])


if __name__ == "__main__":
    unittest.main()
