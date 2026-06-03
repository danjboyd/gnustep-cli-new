import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.admin import (
    admin_gap_report,
    admin_build_plan,
    admin_dispatch_builds,
    admin_doctor_parity,
    admin_inventory,
    admin_schedule_template,
    admin_upstream_check,
    admin_upstream_sources,
)
from gnustep_cli_shared.doctor_engine import build_doctor_payload


class AdminCliTests(unittest.TestCase):
    def make_repo(self, tmp: Path) -> tuple[Path, Path]:
        packages = tmp / "packages"
        package_root = packages / "org.example.tool"
        package_root.mkdir(parents=True)
        (tmp / "evidence").mkdir()
        (tmp / "evidence" / "build.json").write_text("{}", encoding="utf-8")
        (tmp / "evidence" / "validation.json").write_text("{}", encoding="utf-8")
        manifest = {
            "id": "org.example.tool",
            "name": "Example Tool",
            "version": "1.0.0",
            "kind": "application",
            "source": {
                "type": "git",
                "url": "https://example.invalid/tool.git",
                "upstream_url": "https://example.invalid/tool.git",
                "revision": "abc123",
                "sha256": "0" * 64,
            },
            "build": {"backend": "gnustep-cli", "build": ["make"]},
            "artifacts": [
                {
                    "id": "example-linux-amd64-clang",
                    "os": "linux",
                    "arch": "amd64",
                    "compiler_family": "clang",
                    "toolchain_flavor": "clang",
                    "version": "1.0.0",
                    "url": "https://example.invalid/example.tar.gz",
                    "sha256": "1" * 64,
                    "build_evidence": "evidence/build.json",
                    "validation_evidence": "evidence/validation.json",
                },
                {
                    "id": "example-openbsd-arm64-clang",
                    "os": "openbsd",
                    "arch": "arm64",
                    "compiler_family": "clang",
                    "toolchain_flavor": "clang",
                    "publish": False,
                },
                {
                    "id": "example-linux-arm64-clang",
                    "os": "linux",
                    "arch": "arm64",
                    "compiler_family": "clang",
                    "toolchain_flavor": "clang",
                    "publish": False,
                },
            ],
        }
        (package_root / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
        package_index = {"schema_version": 1, "packages": [{"id": "org.example.tool"}]}
        (packages / "package-index.json").write_text(json.dumps(package_index), encoding="utf-8")

        toolchain_root = tmp / "toolchains" / "openbsd-amd64-clang"
        toolchain_root.mkdir(parents=True)
        source_lock = {
            "components": [
                {
                    "name": "libs-base",
                    "url": "https://example.invalid/libs-base.git",
                    "revision": "def456",
                }
            ]
        }
        (toolchain_root / "source-lock.json").write_text(json.dumps(source_lock), encoding="utf-8")
        return tmp, packages

    def test_inventory_loads_packages_toolchains_and_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo, packages = self.make_repo(Path(tmpdir))
            payload = admin_inventory(repo, packages_dir=packages)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "inventory")
        self.assertTrue(payload["inputs"]["package_index_present"])
        self.assertEqual(payload["served"]["packages"][0]["id"], "org.example.tool")
        self.assertEqual(payload["served"]["toolchains"][0]["id"], "openbsd-amd64-clang")

    def test_gap_report_reports_missing_proof_as_actionable_blockers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo, packages = self.make_repo(Path(tmpdir))
            payload = admin_gap_report(repo, packages_dir=packages)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["status"], "error")
        codes = {finding["code"] for finding in payload["findings"]}
        self.assertIn("trust_not_production", codes)
        self.assertIn("missing_final_hosted_evidence", codes)
        self.assertIn("admin_automation_not_scheduled", codes)
        self.assertIn("doctor_parity_remaining", codes)

    def test_gap_report_clears_actionable_findings_with_passing_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo, packages = self.make_repo(Path(tmpdir))
            release = repo / "release"
            release.mkdir()
            evidence = repo / "final-evidence"
            evidence.mkdir()
            release_root = repo / "release-root.pem"
            package_root = repo / "package-root.pem"
            scheduler = repo / "scheduler.json"
            doctor = repo / "doctor-parity.json"
            update_all = evidence / "update-all-production-like.json"
            smoke = evidence / "openbsd-full-tier1-core-report.json"
            for path in (release_root, package_root):
                path.write_text("trust-root", encoding="utf-8")
            scheduler.write_text(json.dumps({"ok": True, "command": "admin-curation-scheduled", "summary": "scheduled"}), encoding="utf-8")
            doctor.write_text(json.dumps({"ok": True, "command": "doctor-parity", "summary": "doctor parity passed"}), encoding="utf-8")
            update_all.write_text(json.dumps({"ok": True, "summary": "update all passed"}), encoding="utf-8")
            smoke.write_text(json.dumps({"ok": True, "summary": "smoke passed"}), encoding="utf-8")

            with patch("gnustep_cli_shared.admin.controlled_release_gate", return_value={"ok": True, "summary": "controlled release gate passed"}), patch(
                "gnustep_cli_shared.admin.immediate_rc_blocker_status", return_value={"ok": True, "summary": "Immediate RC blockers are cleared."}
            ), patch("gnustep_cli_shared.admin.validate_update_all_evidence", return_value={"ok": True, "summary": "update all evidence passed"}):
                payload = admin_gap_report(
                    repo,
                    packages_dir=packages,
                    release_dir=release,
                    package_index=packages / "package-index.json",
                    evidence_dir=evidence,
                    release_trust_root=release_root,
                    package_index_trust_root=package_root,
                    smoke_report_paths=[smoke],
                    update_all_evidence=update_all,
                    scheduler_evidence=scheduler,
                    doctor_parity_evidence=doctor,
                )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "ok")
        actionable = [finding for finding in payload["findings"] if finding["severity"] in {"error", "warning"}]
        self.assertEqual(actionable, [])
        codes = {finding["code"] for finding in payload["findings"]}
        self.assertIn("production_trust_verified", codes)
        self.assertIn("final_hosted_evidence_verified", codes)
        self.assertIn("admin_automation_scheduled", codes)
        self.assertIn("doctor_parity_verified", codes)

    def test_upstream_check_reports_current_and_stale_sources(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo, packages = self.make_repo(Path(tmpdir))
            cache = Path(tmpdir) / "upstream.json"
            cache.write_text(
                json.dumps(
                    {
                        "https://example.invalid/tool.git": {"latest_revision": "abc123"},
                        "https://example.invalid/libs-base.git": {"latest_revision": "newer"},
                    }
                ),
                encoding="utf-8",
            )
            payload = admin_upstream_check(repo, packages_dir=packages, upstream_cache=cache)

        codes = {finding["code"] for finding in payload["findings"]}
        self.assertIn("source_current", codes)
        self.assertIn("stale_source", codes)
        self.assertEqual(payload["status"], "warning")

    def test_upstream_check_warns_when_comparison_data_is_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo, packages = self.make_repo(Path(tmpdir))
            payload = admin_upstream_check(repo, packages_dir=packages)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "warning")
        self.assertIn("unknown source comparison", payload["summary"])
        self.assertEqual(payload["actions"][0]["kind"], "provide_upstream_comparison")

    def test_upstream_sources_lists_comparison_inputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo, packages = self.make_repo(Path(tmpdir))
            payload = admin_upstream_sources(repo, packages_dir=packages)

        urls = {source["url"] for source in payload["sources"]}
        self.assertIn("https://example.invalid/tool.git", urls)
        self.assertIn("https://example.invalid/libs-base.git", urls)

    def test_build_plan_uses_valid_dispatch_inputs_and_blocks_packages_without_toolchain(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo, packages = self.make_repo(Path(tmpdir))
            payload = admin_build_plan(repo, packages_dir=packages, targets=["linux-amd64-clang"], version="test-version")

        workflow_action = next(action for action in payload["actions"] if action["kind"] == "github_workflow_dispatch")
        self.assertEqual(workflow_action["workflow"], "linux-managed-artifacts.yml")
        self.assertEqual(workflow_action["inputs"], {"target": "linux-amd64-clang", "version": "test-version"})
        self.assertEqual(payload["otvm_plan"]["targets"], [])
        self.assertEqual(payload["otvm_plan"]["builders"], [])
        package_action = next(action for action in payload["actions"] if action["kind"] == "package_artifact_build")
        self.assertTrue(package_action["blocked"])
        self.assertIn("toolchain_url+toolchain_sha256 or toolchain_artifact_run_id", package_action["missing_inputs"])

    def test_build_plan_unblocks_unix_package_builds_with_toolchain_artifact_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo, packages = self.make_repo(Path(tmpdir))
            payload = admin_build_plan(repo, packages_dir=packages, targets=["linux-amd64-clang"], toolchain_artifact_run_id="12345")

        package_action = next(action for action in payload["actions"] if action["kind"] == "package_artifact_build")
        self.assertFalse(package_action["blocked"])
        self.assertEqual(package_action["inputs"]["toolchain_artifact_run_id"], "12345")

    def test_build_plan_includes_explicit_openbsd_arm64_deferred_target_and_filters_packages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo, packages = self.make_repo(Path(tmpdir))
            payload = admin_build_plan(
                repo,
                packages_dir=packages,
                targets=["openbsd-arm64-clang"],
                version="arm64-version",
                toolchain_artifact_run_id="67890",
            )

        otvm_actions = [action for action in payload["actions"] if action["kind"] == "otvm_build_required"]
        self.assertEqual(len(otvm_actions), 1)
        self.assertEqual(otvm_actions[0]["target"], "openbsd-arm64-clang")
        self.assertTrue(otvm_actions[0]["deferred"])

        package_actions = [action for action in payload["actions"] if action["kind"] == "package_artifact_build"]
        self.assertEqual([action["artifact"] for action in package_actions], ["example-openbsd-arm64-clang"])
        self.assertTrue(package_actions[0]["deferred"])
        self.assertFalse(package_actions[0]["blocked"])
        self.assertEqual(package_actions[0]["matched_targets"], ["openbsd-arm64-clang"])
        self.assertEqual(package_actions[0]["inputs"]["toolchain_artifact_run_id"], "67890")
        self.assertNotIn("toolchain_artifact_name", package_actions[0]["inputs"])

    def test_dispatch_builds_is_dry_run_and_skips_blocked_package_actions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo, packages = self.make_repo(Path(tmpdir))
            payload = admin_dispatch_builds(repo, packages_dir=packages, targets=["linux-amd64-clang"], version="test-version")

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "warning")
        self.assertEqual(len(payload["dispatches"]), 1)
        self.assertFalse(payload["dispatches"][0]["applied"])
        self.assertEqual(payload["blocked"][0]["kind"], "package_artifact_build")

    def test_schedule_template_contains_systemd_and_cron(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = admin_schedule_template("gap-report", repo_root=tmpdir)

        self.assertIn("systemd_service", payload["templates"])
        self.assertIn("mkdir -p .artifacts", payload["templates"]["cron"])

    def test_doctor_parity_accepts_matching_doctor_payloads(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            native = Path(tmpdir) / "native-doctor.json"
            shared = Path(tmpdir) / "shared-doctor.json"
            payload = build_doctor_payload(interface="full")
            native.write_text(json.dumps(payload), encoding="utf-8")
            shared.write_text(json.dumps(payload), encoding="utf-8")
            result = admin_doctor_parity(native_doctor=native, shared_doctor=shared)

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "ok")

    def test_doctor_parity_rejects_missing_core_check(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            native = Path(tmpdir) / "native-doctor.json"
            shared = Path(tmpdir) / "shared-doctor.json"
            native_payload = build_doctor_payload(interface="full")
            shared_payload = build_doctor_payload(interface="full")
            native_payload["checks"] = [check for check in native_payload["checks"] if check["id"] != "toolchain.features"]
            native.write_text(json.dumps(native_payload), encoding="utf-8")
            shared.write_text(json.dumps(shared_payload), encoding="utf-8")
            result = admin_doctor_parity(native_doctor=native, shared_doctor=shared)

        self.assertFalse(result["ok"])
        failed = {check["id"] for check in result["checks"] if not check["ok"]}
        self.assertIn("required-checks-present", failed)

    def test_admin_script_emits_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo, packages = self.make_repo(Path(tmpdir))
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "internal" / "admin.py"),
                    "--json",
                    "inventory",
                    "--repo-root",
                    str(repo),
                    "--packages-dir",
                    str(packages),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["command"], "inventory")
        self.assertEqual(payload["served"]["packages"][0]["id"], "org.example.tool")


if __name__ == "__main__":
    unittest.main()
