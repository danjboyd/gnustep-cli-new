import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.lifecycle import (
    apply_upgrade_state,
    content_store_path,
    layered_update_plan,
    layered_update_strategy,
    load_cli_state,
    plan_upgrade,
    record_active_artifacts,
    repair_managed_root,
    store_content,
    validate_layered_update_preflight,
)


class LifecycleTests(unittest.TestCase):
    def test_upgrade_plan_detects_cli_change(self):
        payload = plan_upgrade("/tmp/example", current_cli_version="0.1.0", target_cli_version="0.2.0")
        self.assertTrue(payload["actions"])
        self.assertEqual(payload["actions"][0]["kind"], "upgrade_cli")

    def test_apply_upgrade_state_persists(self):
        with tempfile.TemporaryDirectory() as tempdir:
            payload = apply_upgrade_state(tempdir, cli_version="0.2.0", toolchain_version="1.0.0")
            self.assertTrue(payload["ok"])
            state = load_cli_state(tempdir)
            self.assertEqual(state["cli_version"], "0.2.0")

    def test_repair_creates_state_and_packages_dirs(self):
        with tempfile.TemporaryDirectory() as tempdir:
            payload = repair_managed_root(tempdir)
            self.assertTrue(payload["ok"])
            self.assertTrue((Path(tempdir) / "state").exists())
            self.assertTrue((Path(tempdir) / "packages").exists())

    def test_content_store_records_payload_by_digest(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            payload = root / "artifact.bin"
            payload.write_text("artifact")
            stored = store_content(root, payload)
            self.assertTrue(stored["ok"])
            self.assertTrue(Path(stored["store_path"]).exists())
            self.assertEqual(Path(stored["store_path"]), content_store_path(root, stored["sha256"]))
            stored_again = store_content(root, payload, expected_sha256=stored["sha256"])
            self.assertTrue(stored_again["reused_existing"])

    def test_record_active_artifacts_and_layered_update_plan(self):
        with tempfile.TemporaryDirectory() as tempdir:
            cli = {"id": "cli-linux-amd64-clang", "kind": "cli", "version": "0.1.0", "sha256": "a" * 64, "size": 10}
            toolchain = {"id": "toolchain-linux-amd64-clang", "kind": "toolchain", "version": "2026.04.0", "sha256": "b" * 64, "size": 100}
            record_active_artifacts(tempdir, cli_artifact=cli, toolchain_artifact=toolchain, manifest_digest="c" * 64)
            state = load_cli_state(tempdir)
            self.assertEqual(state["cli_artifact_sha256"], "a" * 64)
            newer_cli = dict(cli)
            newer_cli["version"] = "0.1.1"
            newer_cli["sha256"] = "d" * 64
            plan = layered_update_plan(state, [newer_cli, toolchain])
            self.assertEqual(plan["kind"], "cli_only")
            self.assertEqual(plan["planned_download_size"], 10)
            layers = {layer["name"]: layer for layer in plan["layers"]}
            self.assertEqual(layers["cli"]["action"], "update")
            self.assertEqual(layers["toolchain"]["action"], "reuse")

    def test_layered_update_strategy_prefers_matching_delta(self):
        installed = {"toolchain_artifact_sha256": "a" * 64, "toolchain_version": "2026.04.0"}
        target = {
            "id": "toolchain-linux-amd64-clang",
            "kind": "toolchain",
            "version": "2026.04.1",
            "sha256": "b" * 64,
            "url": "https://example.invalid/full.tar.gz",
            "size": 1000,
        }
        delta = {
            "id": "delta-toolchain-linux-amd64-clang",
            "kind": "toolchain-delta",
            "from_artifact": "toolchain-linux-amd64-clang",
            "to_artifact": "toolchain-linux-amd64-clang",
            "from_sha256": "a" * 64,
            "to_sha256": "b" * 64,
            "url": "https://example.invalid/delta.bin",
            "sha256": "c" * 64,
            "size": 12,
            "delta_format": "gnustep-delta-v1",
        }
        strategy = layered_update_strategy(installed, [target], delta_artifacts=[delta])
        self.assertTrue(strategy["ok"])
        self.assertEqual(strategy["strategies"][0]["strategy"], "delta")
        self.assertEqual(strategy["planned_download_size"], 12)

    def test_layered_update_strategy_falls_back_to_full_artifact_for_wrong_base_delta(self):
        installed = {"toolchain_artifact_sha256": "x" * 64, "toolchain_version": "2026.04.0"}
        target = {
            "id": "toolchain-linux-amd64-clang",
            "kind": "toolchain",
            "version": "2026.04.1",
            "sha256": "b" * 64,
            "url": "https://example.invalid/full.tar.gz",
            "size": 1000,
        }
        delta = {
            "id": "delta-toolchain-linux-amd64-clang",
            "kind": "toolchain-delta",
            "from_artifact": "toolchain-linux-amd64-clang",
            "to_artifact": "toolchain-linux-amd64-clang",
            "from_sha256": "a" * 64,
            "to_sha256": "b" * 64,
            "url": "https://example.invalid/delta.bin",
            "sha256": "c" * 64,
            "size": 12,
            "delta_format": "gnustep-delta-v1",
        }
        strategy = layered_update_strategy(installed, [target], delta_artifacts=[delta])
        self.assertTrue(strategy["ok"])
        self.assertEqual(strategy["strategies"][0]["strategy"], "full_artifact")
        self.assertEqual(strategy["planned_download_size"], 1000)
        self.assertEqual(strategy["failures"][0]["code"], "invalid_base_artifact")

    def test_layered_update_preflight_reports_revoked_artifact_and_missing_fallback(self):
        installed = {"toolchain_artifact_sha256": "a" * 64, "toolchain_version": "2026.04.0"}
        target = {
            "id": "toolchain-linux-amd64-clang",
            "kind": "toolchain",
            "version": "2026.04.1",
            "sha256": "b" * 64,
        }
        preflight = validate_layered_update_preflight(
            installed_state=installed,
            selected_artifacts=[target],
            revoked_artifacts=["toolchain-linux-amd64-clang"],
        )
        self.assertFalse(preflight["ok"])
        failure_reasons = {check["failure_reason"] for check in preflight["checks"]}
        self.assertIn("revoked_artifact", failure_reasons)
        self.assertIn("full_artifact_fallback_failure", failure_reasons)


    def test_repair_clears_stale_transactions_and_marks_interrupted_state(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "state").mkdir()
            (root / "packages").mkdir()
            (root / ".staging" / "pkg").mkdir(parents=True)
            (root / ".transactions" / "upgrade").mkdir(parents=True)
            (root / "state" / "setup-transaction.json").write_text("{}")
            (root / "state" / "cli-state.json").write_text('{"schema_version": 1, "status": "upgrading"}')
            payload = repair_managed_root(root)
            kinds = {repair["kind"] for repair in payload["repairs"]}
            codes = {issue["code"] for issue in payload["issues"]}
            self.assertIn("clear_staging", kinds)
            self.assertIn("clear_transactions", kinds)
            self.assertIn("clear_setup_transaction", kinds)
            self.assertIn("mark_needs_repair", kinds)
            self.assertIn("interrupted_lifecycle_action", codes)
            self.assertFalse((root / ".staging").exists())
            self.assertFalse((root / ".transactions").exists())
            self.assertFalse((root / "state" / "setup-transaction.json").exists())
            self.assertEqual(load_cli_state(root)["status"], "needs_repair")


if __name__ == "__main__":
    unittest.main()
