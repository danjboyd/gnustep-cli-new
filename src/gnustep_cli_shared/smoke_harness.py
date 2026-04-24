from __future__ import annotations

from abc import ABC, abstractmethod
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SmokeRunnerProfile:
    id: str
    kind: str
    summary: str
    lease_managed: bool = False
    supports_reuse: bool = False
    remote_execution: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "summary": self.summary,
            "lease_managed": self.lease_managed,
            "supports_reuse": self.supports_reuse,
            "remote_execution": self.remote_execution,
        }


@dataclass(frozen=True)
class SmokeTargetProfile:
    id: str
    os: str
    arch: str
    compiler_family: str
    toolchain_flavor: str
    bootstrap_kind: str
    shell_kind: str
    path_style: str
    gui_available: bool
    managed_root_style: str
    runner_profile: str
    tags: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "os": self.os,
            "arch": self.arch,
            "compiler_family": self.compiler_family,
            "toolchain_flavor": self.toolchain_flavor,
            "bootstrap_kind": self.bootstrap_kind,
            "shell_kind": self.shell_kind,
            "path_style": self.path_style,
            "gui_available": self.gui_available,
            "managed_root_style": self.managed_root_style,
            "runner_profile": self.runner_profile,
            "tags": list(self.tags),
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class SmokeScenario:
    id: str
    summary: str
    supported_targets: tuple[str, ...]
    estimated_duration_minutes: int
    network_required: bool
    gui_required: bool
    isolated_prefix_required: bool
    destructive: bool
    artifact_prerequisites: tuple[str, ...] = field(default_factory=tuple)
    channel_prerequisites: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    fixture_policy: str = "pinned"
    assertions: tuple[str, ...] = field(default_factory=tuple)

    def supports_target(self, target_id: str) -> bool:
        return target_id in self.supported_targets

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "summary": self.summary,
            "supported_targets": list(self.supported_targets),
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "network_required": self.network_required,
            "gui_required": self.gui_required,
            "isolated_prefix_required": self.isolated_prefix_required,
            "destructive": self.destructive,
            "artifact_prerequisites": list(self.artifact_prerequisites),
            "channel_prerequisites": list(self.channel_prerequisites),
            "tags": list(self.tags),
            "fixture_policy": self.fixture_policy,
            "assertions": list(self.assertions),
        }


@dataclass(frozen=True)
class SmokeFixture:
    id: str
    kind: str
    summary: str
    provenance: dict[str, Any]
    expected_observations: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "summary": self.summary,
            "provenance": self.provenance,
            "expected_observations": self.expected_observations,
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class SmokeAssertionResult:
    id: str
    ok: bool
    summary: str
    severity: str = "error"
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "id": self.id,
            "ok": self.ok,
            "summary": self.summary,
            "severity": self.severity,
        }
        if self.details:
            payload["details"] = self.details
        return payload


@dataclass(frozen=True)
class SmokeCommandRecord:
    id: str
    command: list[str]
    cwd: str | None = None
    environment_hints: dict[str, str] = field(default_factory=dict)
    stdout_path: str | None = None
    stderr_path: str | None = None
    exit_code: int | None = None
    duration_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "id": self.id,
            "command": list(self.command),
            "cwd": self.cwd,
            "environment_hints": self.environment_hints,
            "stdout_path": self.stdout_path,
            "stderr_path": self.stderr_path,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
        }
        return payload


@dataclass(frozen=True)
class SmokeStepResult:
    id: str
    summary: str
    ok: bool
    assertions: tuple[SmokeAssertionResult, ...] = field(default_factory=tuple)
    commands: tuple[SmokeCommandRecord, ...] = field(default_factory=tuple)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "summary": self.summary,
            "ok": self.ok,
            "assertions": [assertion.to_dict() for assertion in self.assertions],
            "commands": [command.to_dict() for command in self.commands],
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class SmokeScenarioReport:
    scenario_id: str
    ok: bool
    summary: str
    fixture_ids: tuple[str, ...] = field(default_factory=tuple)
    steps: tuple[SmokeStepResult, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "ok": self.ok,
            "summary": self.summary,
            "fixture_ids": list(self.fixture_ids),
            "steps": [step.to_dict() for step in self.steps],
        }


@dataclass(frozen=True)
class SmokeRunReport:
    suite_id: str
    target_id: str
    runner_id: str
    release_under_test: dict[str, Any]
    fixture_references: tuple[str, ...]
    scenario_reports: tuple[SmokeScenarioReport, ...] = field(default_factory=tuple)
    evidence: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        overall_ok = all(report.ok for report in self.scenario_reports) if self.scenario_reports else True
        return {
            "schema_version": self.schema_version,
            "suite_id": self.suite_id,
            "target_id": self.target_id,
            "runner_id": self.runner_id,
            "release_under_test": self.release_under_test,
            "fixture_references": list(self.fixture_references),
            "overall_ok": overall_ok,
            "scenario_reports": [report.to_dict() for report in self.scenario_reports],
            "evidence": self.evidence,
        }


class SmokeRunner(ABC):
    def __init__(self, profile: SmokeRunnerProfile) -> None:
        self.profile = profile

    @abstractmethod
    def execution_plan(
        self,
        *,
        target: SmokeTargetProfile,
        release_source: str,
        scenario_ids: list[str],
        reuse_existing: bool = False,
        ttl_hours: int | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class LocalProcessRunner(SmokeRunner):
    def execution_plan(
        self,
        *,
        target: SmokeTargetProfile,
        release_source: str,
        scenario_ids: list[str],
        reuse_existing: bool = False,
        ttl_hours: int | None = None,
    ) -> dict[str, Any]:
        return {
            "runner_id": self.profile.id,
            "kind": self.profile.kind,
            "target_id": target.id,
            "release_source": release_source,
            "reuse_existing": False,
            "ttl_hours": None,
            "transport": {"mode": "local-subprocess"},
            "stage_actions": [
                "prepare-temp-root",
                "copy-or-reference-release-input",
                "run-scenarios-locally",
                "write-report-json",
            ],
        }


class SSHSmokeRunner(SmokeRunner):
    def execution_plan(
        self,
        *,
        target: SmokeTargetProfile,
        release_source: str,
        scenario_ids: list[str],
        reuse_existing: bool = False,
        ttl_hours: int | None = None,
    ) -> dict[str, Any]:
        return {
            "runner_id": self.profile.id,
            "kind": self.profile.kind,
            "target_id": target.id,
            "release_source": release_source,
            "reuse_existing": reuse_existing,
            "ttl_hours": ttl_hours,
            "transport": {
                "mode": "ssh",
                "requires": ["host", "username", "ssh-key"],
            },
            "stage_actions": [
                "prepare-remote-workdir",
                "upload-release-input",
                "upload-fixtures-and-runner-shim",
                "execute-scenarios-over-ssh",
                "download-report-and-artifacts",
            ],
            "cleanup_policy": {
                "destroy_lease": False,
                "remove_remote_workdir": True,
            },
        }


class OTVMSmokeRunner(SmokeRunner):
    def execution_plan(
        self,
        *,
        target: SmokeTargetProfile,
        release_source: str,
        scenario_ids: list[str],
        reuse_existing: bool = False,
        ttl_hours: int | None = None,
    ) -> dict[str, Any]:
        lease_profile = target.metadata.get("otvm_profile", target.id)
        return {
            "runner_id": self.profile.id,
            "kind": self.profile.kind,
            "target_id": target.id,
            "release_source": release_source,
            "reuse_existing": reuse_existing,
            "ttl_hours": ttl_hours or 2,
            "transport": {
                "mode": "otvm-lease",
                "lease_profile": lease_profile,
                "requires": ["otvm-config", "ssh-key"],
            },
            "stage_actions": [
                "preflight-target-profile",
                "create-or-reuse-lease",
                "stage-release-input-to-lease",
                "stage-smoke-runner-and-fixtures",
                "execute-scenarios-via-ssh",
                "collect-report-json-and-failure-artifacts",
                "destroy-lease-unless-reused-or-debugging",
            ],
            "cleanup_policy": {
                "destroy_on_success": not reuse_existing,
                "destroy_on_failure": not reuse_existing,
                "reap_backstop_required": True,
            },
        }


RUNNER_PROFILES: tuple[SmokeRunnerProfile, ...] = (
    SmokeRunnerProfile(
        id="local-process",
        kind="local",
        summary="Runs smoke steps on the local host with direct subprocess execution.",
    ),
    SmokeRunnerProfile(
        id="ssh-host",
        kind="ssh",
        summary="Runs smoke steps on a pre-provisioned remote host over SSH.",
        supports_reuse=True,
        remote_execution=True,
    ),
    SmokeRunnerProfile(
        id="otvm-lease",
        kind="otvm",
        summary="Runs smoke steps on a short-lived or reused OracleTestVMs lease.",
        lease_managed=True,
        supports_reuse=True,
        remote_execution=True,
    ),
)


TARGET_PROFILES: tuple[SmokeTargetProfile, ...] = (
    SmokeTargetProfile(
        id="windows-amd64-msys2-clang64",
        os="windows",
        arch="amd64",
        compiler_family="clang",
        toolchain_flavor="msys2-clang64",
        bootstrap_kind="powershell",
        shell_kind="powershell",
        path_style="windows",
        gui_available=True,
        managed_root_style="user-localappdata",
        runner_profile="otvm-lease",
        tags=("tier1", "managed", "gui", "dogfood"),
        metadata={
            "bootstrap_script": "scripts/bootstrap/gnustep-bootstrap.ps1",
            "expected_objc_runtime": "libobjc2",
            "expected_install_root_hint": "%LOCALAPPDATA%/gnustep-cli",
            "path_separator": ";",
            "gui_launch_contract": "launch-and-stay-alive-briefly",
            "otvm_profile": "windows-2022",
        },
    ),
    SmokeTargetProfile(
        id="openbsd-amd64-clang",
        os="openbsd",
        arch="amd64",
        compiler_family="clang",
        toolchain_flavor="clang",
        bootstrap_kind="posix-sh",
        shell_kind="sh",
        path_style="posix",
        gui_available=True,
        managed_root_style="user-home-local",
        runner_profile="otvm-lease",
        tags=("tier1", "managed", "gui", "dogfood"),
        metadata={
            "bootstrap_script": "scripts/bootstrap/gnustep-bootstrap.sh",
            "expected_objc_runtime": "libobjc2",
            "expected_install_root_hint": "$HOME/.local/share/gnustep-cli",
            "path_separator": ":",
            "gui_launch_contract": "launch-and-stay-alive-briefly",
            "otvm_profile": "openbsd-7.8-fvwm",
        },
    ),
)


FIXTURES: tuple[SmokeFixture, ...] = (
    SmokeFixture(
        id="gorm-upstream-pinned",
        kind="upstream-git",
        summary="Pinned Gorm source revision for real-application smoke validation.",
        provenance={
            "repository_url": "https://github.com/gnustep/apps-gorm.git",
            "reference_type": "tag",
            "reference": "gorm-1_5_0",
            "commit": "a8cd1792e08a50dd9900474373e6ca8daad4a4a9",
            "mutable": False,
        },
        expected_observations={
            "project_type": "app",
            "launch_contract": "launch-and-stay-alive-briefly",
        },
        tags=("gui", "gorm", "pinned"),
    ),
    SmokeFixture(
        id="gorm-windows-private-ivar-patch",
        kind="source-patch",
        summary="Windows-only patch for the pinned Gorm smoke fixture that removes private NSMatrix selected-cell ivar access.",
        provenance={
            "applies_to_fixture": "gorm-upstream-pinned",
            "target_id": "windows-amd64-msys2-clang64",
            "patch_path": "docs/smoke-fixtures/gorm-1_5_0-windows-private-ivar.patch",
            "reason": "The pinned Gorm tag references the private GNUstep GUI ivar NSMatrix._selectedCells; Windows libobjc2/lld does not export that ivar offset for this build.",
            "mutable": False,
        },
        expected_observations={
            "removes_symbol_reference": "__objc_ivar_offset_NSMatrix._selectedCells",
            "preserves_launch_contract": "launch-and-stay-alive-briefly",
        },
        tags=("gui", "gorm", "windows", "patch"),
    ),
    SmokeFixture(
        id="generated-cli-template-output",
        kind="repo-fixture",
        summary="Expected output contract for a freshly generated CLI sample project.",
        provenance={
            "source": "project-template",
            "template_kind": "cli-tool",
            "mutable": False,
        },
        expected_observations={
            "run_stdout_contains": "Hello from CLI tool",
        },
        tags=("workflow", "new", "run"),
    ),
    SmokeFixture(
        id="cli-only-update-channel",
        kind="channel-policy",
        summary="Pinned policy record for CLI-only dogfood update smoke.",
        provenance={
            "channel": "dogfood",
            "requires_base_release": True,
            "requires_target_release": True,
            "mutable": True,
        },
        expected_observations={
            "update_plan_layer_kind": "cli_only",
            "toolchain_reuse_expected": True,
        },
        tags=("update", "dogfood", "layered-artifacts"),
    ),
)


CORE_SCENARIOS: tuple[SmokeScenario, ...] = (
    SmokeScenario(
        id="bootstrap-install-usable-cli",
        summary="Run the bootstrap installer into a user-scoped root and prove the installed CLI is usable.",
        supported_targets=tuple(target.id for target in TARGET_PROFILES),
        estimated_duration_minutes=8,
        network_required=True,
        gui_required=False,
        isolated_prefix_required=True,
        destructive=True,
        artifact_prerequisites=("release-manifest", "cli-artifact", "toolchain-artifact"),
        channel_prerequisites=("dogfood-or-staged",),
        tags=("core", "bootstrap", "install"),
        assertions=(
            "bootstrap-command-succeeds",
            "installed-gnustep-exists",
            "gnustep-help-succeeds",
            "gnustep-version-succeeds",
            "doctor-json-command-metadata-is-doctor",
        ),
    ),
    SmokeScenario(
        id="new-cli-project-build-run",
        summary="Create a fresh CLI project, build it, and run the generated sample output.",
        supported_targets=tuple(target.id for target in TARGET_PROFILES),
        estimated_duration_minutes=6,
        network_required=False,
        gui_required=False,
        isolated_prefix_required=True,
        destructive=True,
        artifact_prerequisites=("installed-cli",),
        tags=("core", "workflow", "new", "build", "run"),
        assertions=(
            "new-command-succeeds",
            "build-command-succeeds",
            "run-command-succeeds",
            "sample-output-matches-expected-text",
        ),
    ),
    SmokeScenario(
        id="gorm-build-run",
        summary="Build and launch a pinned Gorm revision as a real GNUstep application smoke test.",
        supported_targets=tuple(target.id for target in TARGET_PROFILES),
        estimated_duration_minutes=15,
        network_required=True,
        gui_required=True,
        isolated_prefix_required=True,
        destructive=True,
        artifact_prerequisites=("installed-cli",),
        tags=("core", "gui", "real-app", "gorm"),
        fixture_policy="pinned-upstream-revision",
        assertions=(
            "gorm-source-revision-is-pinned",
            "gorm-build-succeeds",
            "gorm-launch-succeeds",
            "gorm-process-stays-alive-briefly",
        ),
    ),
    SmokeScenario(
        id="self-update-cli-only",
        summary="Install an older release, verify a newer CLI-only update, apply it, and rerun a basic workflow.",
        supported_targets=tuple(target.id for target in TARGET_PROFILES),
        estimated_duration_minutes=12,
        network_required=True,
        gui_required=False,
        isolated_prefix_required=True,
        destructive=True,
        artifact_prerequisites=("base-release", "target-release", "release-manifest"),
        channel_prerequisites=("dogfood",),
        tags=("core", "update", "layered-artifacts"),
        assertions=(
            "update-check-detects-newer-release",
            "update-plan-identifies-cli-only-layer",
            "update-apply-succeeds",
            "post-update-version-matches-target-release",
            "post-update-build-run-smoke-succeeds",
        ),
    ),
)


SUITES: dict[str, dict[str, Any]] = {
    "quick": {
        "id": "quick",
        "summary": "Single-target quick smoke suite for active iteration.",
        "mode": "developer",
        "release_gate_usage": "none",
        "scenario_ids": (
            "bootstrap-install-usable-cli",
            "new-cli-project-build-run",
        ),
    },
    "tier1-core": {
        "id": "tier1-core",
        "summary": "Canonical Tier 1 smoke scenarios for all active Tier 1 targets.",
        "mode": "qualification",
        "release_gate_usage": "dogfood-and-rc",
        "scenario_ids": tuple(scenario.id for scenario in CORE_SCENARIOS),
    },
    "release": {
        "id": "release",
        "summary": "Release-proving smoke suite across the current Tier 1 managed targets.",
        "mode": "release",
        "release_gate_usage": "stable-publication",
        "scenario_ids": tuple(scenario.id for scenario in CORE_SCENARIOS),
    },
}


RELEASE_GATE_POLICIES: dict[str, dict[str, Any]] = {
    "dogfood": {
        "id": "dogfood",
        "summary": "Dogfood publication gate for the active validation target set.",
        "required_suite": "tier1-core",
        "allow_scoped_targets": True,
        "require_all_overall_ok": True,
    },
    "release-candidate": {
        "id": "release-candidate",
        "summary": "Release-candidate smoke gate across the declared Tier 1 target set.",
        "required_suite": "tier1-core",
        "allow_scoped_targets": False,
        "require_all_overall_ok": True,
    },
    "stable": {
        "id": "stable",
        "summary": "Stable-publication smoke gate across the full Tier 1 managed matrix.",
        "required_suite": "release",
        "allow_scoped_targets": False,
        "require_all_overall_ok": True,
    },
}


def runner_profiles() -> list[dict[str, Any]]:
    return [profile.to_dict() for profile in RUNNER_PROFILES]


def fixture_catalog() -> list[dict[str, Any]]:
    return [fixture.to_dict() for fixture in FIXTURES]


def fixture_record(fixture_id: str) -> dict[str, Any]:
    for fixture in FIXTURES:
        if fixture.id == fixture_id:
            return fixture.to_dict()
    raise ValueError(f"unknown smoke fixture: {fixture_id}")


def target_profiles() -> list[dict[str, Any]]:
    return [target.to_dict() for target in TARGET_PROFILES]


def target_profile(target_id: str) -> dict[str, Any]:
    for target in TARGET_PROFILES:
        if target.id == target_id:
            return target.to_dict()
    raise ValueError(f"unknown smoke target: {target_id}")


def smoke_scenarios() -> list[dict[str, Any]]:
    return [scenario.to_dict() for scenario in CORE_SCENARIOS]


def smoke_scenario(scenario_id: str) -> dict[str, Any]:
    for scenario in CORE_SCENARIOS:
        if scenario.id == scenario_id:
            return scenario.to_dict()
    raise ValueError(f"unknown smoke scenario: {scenario_id}")


def validate_smoke_catalog() -> dict[str, Any]:
    target_ids = {target.id for target in TARGET_PROFILES}
    runner_ids = {runner.id for runner in RUNNER_PROFILES}
    fixture_ids = {fixture.id for fixture in FIXTURES}
    errors: list[dict[str, str]] = []

    for target in TARGET_PROFILES:
        if target.runner_profile not in runner_ids:
            errors.append(
                {
                    "kind": "unknown_runner_profile",
                    "target_id": target.id,
                    "runner_profile": target.runner_profile,
                }
            )

    for scenario in CORE_SCENARIOS:
        if not scenario.supported_targets:
            errors.append({"kind": "scenario_has_no_targets", "scenario_id": scenario.id})
            continue
        for target_id in scenario.supported_targets:
            if target_id not in target_ids:
                errors.append(
                    {
                        "kind": "unknown_supported_target",
                        "scenario_id": scenario.id,
                        "target_id": target_id,
                    }
                )
        if scenario.gui_required:
            unsupported = [
                target_id
                for target_id in scenario.supported_targets
                if not next(target for target in TARGET_PROFILES if target.id == target_id).gui_available
            ]
            for target_id in unsupported:
                errors.append(
                    {
                        "kind": "gui_required_on_headless_target",
                        "scenario_id": scenario.id,
                        "target_id": target_id,
                    }
                )
        if scenario.id == "gorm-build-run" and "gorm-upstream-pinned" not in fixture_ids:
            errors.append({"kind": "missing_required_fixture", "scenario_id": scenario.id, "fixture_id": "gorm-upstream-pinned"})
        if scenario.id == "new-cli-project-build-run" and "generated-cli-template-output" not in fixture_ids:
            errors.append({"kind": "missing_required_fixture", "scenario_id": scenario.id, "fixture_id": "generated-cli-template-output"})
        if scenario.id == "self-update-cli-only" and "cli-only-update-channel" not in fixture_ids:
            errors.append({"kind": "missing_required_fixture", "scenario_id": scenario.id, "fixture_id": "cli-only-update-channel"})

    for suite_id, suite in SUITES.items():
        for scenario_id in suite["scenario_ids"]:
            if scenario_id not in {scenario.id for scenario in CORE_SCENARIOS}:
                errors.append(
                    {
                        "kind": "unknown_suite_scenario",
                        "suite_id": suite_id,
                        "scenario_id": scenario_id,
                    }
                )

    return {
        "schema_version": 1,
        "ok": not errors,
        "status": "ok" if not errors else "error",
        "targets": len(TARGET_PROFILES),
        "scenarios": len(CORE_SCENARIOS),
        "fixtures": len(FIXTURES),
        "errors": errors,
    }


def suite_definition(suite_id: str) -> dict[str, Any]:
    suite = SUITES.get(suite_id)
    if suite is None:
        raise ValueError(f"unknown smoke suite: {suite_id}")
    return {
        "id": suite["id"],
        "summary": suite["summary"],
        "mode": suite.get("mode", "developer"),
        "release_gate_usage": suite.get("release_gate_usage", "none"),
        "scenario_ids": list(suite["scenario_ids"]),
    }


def suite_catalog() -> list[dict[str, Any]]:
    return [suite_definition(suite_id) for suite_id in SUITES]


def runner_profile(runner_id: str) -> dict[str, Any]:
    for runner in RUNNER_PROFILES:
        if runner.id == runner_id:
            return runner.to_dict()
    raise ValueError(f"unknown smoke runner: {runner_id}")


def release_gate_policy(gate_id: str) -> dict[str, Any]:
    policy = RELEASE_GATE_POLICIES.get(gate_id)
    if policy is None:
        raise ValueError(f"unknown smoke release gate: {gate_id}")
    return {
        "id": policy["id"],
        "summary": policy["summary"],
        "required_suite": policy["required_suite"],
        "allow_scoped_targets": policy["allow_scoped_targets"],
        "require_all_overall_ok": policy["require_all_overall_ok"],
    }


def release_gate_catalog() -> list[dict[str, Any]]:
    return [release_gate_policy(gate_id) for gate_id in RELEASE_GATE_POLICIES]


def instantiate_runner(runner_id: str) -> SmokeRunner:
    for runner in RUNNER_PROFILES:
        if runner.id == runner_id:
            if runner.id == "local-process":
                return LocalProcessRunner(runner)
            if runner.id == "ssh-host":
                return SSHSmokeRunner(runner)
            if runner.id == "otvm-lease":
                return OTVMSmokeRunner(runner)
    raise ValueError(f"unknown smoke runner: {runner_id}")


def smoke_plan(
    suite_id: str = "tier1-core",
    target_ids: list[str] | None = None,
    scenario_ids: list[str] | None = None,
) -> dict[str, Any]:
    validation = validate_smoke_catalog()
    if not validation["ok"]:
        raise ValueError("smoke catalog validation failed")

    suite = suite_definition(suite_id)
    selected_targets = target_ids or [target.id for target in TARGET_PROFILES]
    known_targets = {target.id: target for target in TARGET_PROFILES}
    known_scenarios = {scenario.id: scenario for scenario in CORE_SCENARIOS}
    selected_scenarios = scenario_ids or list(suite["scenario_ids"])
    target_payloads: list[dict[str, Any]] = []

    for target_id in selected_targets:
        target = known_targets.get(target_id)
        if target is None:
            raise ValueError(f"unknown smoke target: {target_id}")
        applicable_scenarios = []
        for scenario_id in selected_scenarios:
            scenario = known_scenarios.get(scenario_id)
            if scenario is None:
                raise ValueError(f"unknown smoke scenario: {scenario_id}")
            if scenario.supports_target(target_id):
                applicable_scenarios.append(
                    {
                        "id": scenario.id,
                        "summary": scenario.summary,
                        "estimated_duration_minutes": scenario.estimated_duration_minutes,
                        "gui_required": scenario.gui_required,
                        "network_required": scenario.network_required,
                        "tags": list(scenario.tags),
                    }
                )
        target_payloads.append(
            {
                "target": target.to_dict(),
                "runner": next(
                    runner.to_dict() for runner in RUNNER_PROFILES if runner.id == target.runner_profile
                ),
                "scenarios": applicable_scenarios,
            }
        )

    return {
        "schema_version": 1,
        "suite": suite,
        "targets": target_payloads,
        "summary": f"Planned {len(selected_scenarios)} scenario(s) across {len(selected_targets)} target(s).",
    }


def workflow_plan(
    *,
    suite_id: str,
    target_ids: list[str] | None = None,
    release_source: str = "dist-or-manifest-unspecified",
    reuse_existing_runner: bool = False,
    ttl_hours: int | None = None,
) -> dict[str, Any]:
    plan = smoke_plan(suite_id=suite_id, target_ids=target_ids)
    commands = [
        {
            "id": "validate-catalog",
            "command": ["python3", "scripts/dev/run-smoke-tests.py", "--validate-only"],
        }
    ]
    for target in plan["targets"]:
        commands.append(
            {
                "id": f"runner-plan-{target['target']['id']}",
                "command": [
                    "python3",
                    "scripts/dev/run-smoke-tests.py",
                    "--runner-plan",
                    "--target",
                    target["target"]["id"],
                    "--suite",
                    suite_id,
                    "--release-source",
                    release_source,
                ]
                + (["--reuse-existing-runner"] if reuse_existing_runner else [])
                + (["--ttl-hours", str(ttl_hours)] if ttl_hours is not None else []),
            }
        )
        commands.append(
            {
                "id": f"report-template-{target['target']['id']}",
                "command": [
                    "python3",
                    "scripts/dev/run-smoke-tests.py",
                    "--report-template",
                    "--target",
                    target["target"]["id"],
                    "--suite",
                    suite_id,
                    "--release-source",
                    release_source,
                ],
            }
        )
    return {
        "schema_version": 1,
        "suite": suite_definition(suite_id),
        "targets": [target["target"]["id"] for target in plan["targets"]],
        "release_source": release_source,
        "commands": commands,
        "summary": f"Developer workflow plan generated for suite {suite_id}.",
    }


def runner_execution_plan(
    *,
    target_id: str,
    release_source: str,
    scenario_ids: list[str] | None = None,
    reuse_existing: bool = False,
    ttl_hours: int | None = None,
) -> dict[str, Any]:
    target = next((target for target in TARGET_PROFILES if target.id == target_id), None)
    if target is None:
        raise ValueError(f"unknown smoke target: {target_id}")
    selected_scenarios = scenario_ids or [scenario.id for scenario in CORE_SCENARIOS if scenario.supports_target(target_id)]
    runner = instantiate_runner(target.runner_profile)
    return runner.execution_plan(
        target=target,
        release_source=release_source,
        scenario_ids=selected_scenarios,
        reuse_existing=reuse_existing,
        ttl_hours=ttl_hours,
    )


def fixture_references_for_scenarios(scenario_ids: list[str], *, target_id: str | None = None) -> list[dict[str, Any]]:
    required_fixture_ids: list[str] = []
    for scenario_id in scenario_ids:
        if scenario_id == "gorm-build-run":
            required_fixture_ids.append("gorm-upstream-pinned")
            if target_id == "windows-amd64-msys2-clang64":
                required_fixture_ids.append("gorm-windows-private-ivar-patch")
        elif scenario_id == "new-cli-project-build-run":
            required_fixture_ids.append("generated-cli-template-output")
        elif scenario_id == "self-update-cli-only":
            required_fixture_ids.append("cli-only-update-channel")
    seen: set[str] = set()
    ordered_ids = [fixture_id for fixture_id in required_fixture_ids if not (fixture_id in seen or seen.add(fixture_id))]
    return [fixture_record(fixture_id) for fixture_id in ordered_ids]


def empty_smoke_report(
    *,
    suite_id: str,
    target_id: str,
    release_source: str,
    release_identity: dict[str, Any] | None = None,
    scenario_ids: list[str] | None = None,
) -> dict[str, Any]:
    target = next((target for target in TARGET_PROFILES if target.id == target_id), None)
    if target is None:
        raise ValueError(f"unknown smoke target: {target_id}")
    scenarios = scenario_ids or [scenario.id for scenario in CORE_SCENARIOS if scenario.supports_target(target_id)]
    report = SmokeRunReport(
        suite_id=suite_id,
        target_id=target_id,
        runner_id=target.runner_profile,
        release_under_test=release_identity or {"source": release_source},
        fixture_references=tuple(fixture["id"] for fixture in fixture_references_for_scenarios(scenarios, target_id=target_id)),
        scenario_reports=tuple(
            SmokeScenarioReport(
                scenario_id=scenario_id,
                ok=False,
                summary="Scenario has not been executed yet.",
                fixture_ids=tuple(fixture["id"] for fixture in fixture_references_for_scenarios([scenario_id], target_id=target_id)),
            )
            for scenario_id in scenarios
        ),
        evidence={
            "target_profile": target.to_dict(),
            "runner_execution_plan": runner_execution_plan(
                target_id=target_id,
                release_source=release_source,
                scenario_ids=scenarios,
            ),
            "fixtures": fixture_references_for_scenarios(scenarios, target_id=target_id),
        },
    )
    return report.to_dict()


def load_smoke_report(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if payload.get("schema_version") != 1:
        raise ValueError(f"unsupported smoke report schema: {payload.get('schema_version')}")
    return payload


def _load_evidence_files(paths: list[str | Path]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for raw_path in paths:
        path = Path(raw_path)
        payload: dict[str, Any] | None = None
        ok = path.exists()
        summary = "Evidence file is present." if ok else "Evidence file is missing."
        if ok:
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
                ok = bool(payload.get("ok", True))
                summary = payload.get("summary", summary)
            except Exception as exc:
                ok = False
                summary = f"Evidence file is invalid JSON: {exc}"
        evidence.append(
            {
                "path": str(path),
                "ok": ok,
                "summary": summary,
                "payload_command": payload.get("command") if isinstance(payload, dict) else None,
            }
        )
    return evidence


def evidence_smoke_report(
    *,
    suite_id: str,
    target_id: str,
    release_source: str,
    passed_scenario_ids: list[str],
    evidence_paths: list[str | Path] | None = None,
    release_identity: dict[str, Any] | None = None,
    summary: str | None = None,
) -> dict[str, Any]:
    target = next((target for target in TARGET_PROFILES if target.id == target_id), None)
    if target is None:
        raise ValueError(f"unknown smoke target: {target_id}")
    suite = suite_definition(suite_id)
    expected_scenarios = [scenario_id for scenario_id in suite["scenario_ids"] if smoke_scenario(scenario_id)["supported_targets"] and target_id in smoke_scenario(scenario_id)["supported_targets"]]
    passed = set(passed_scenario_ids)
    unknown = sorted(passed - {scenario.id for scenario in CORE_SCENARIOS})
    if unknown:
        raise ValueError(f"unknown smoke scenario(s): {', '.join(unknown)}")
    evidence_files = _load_evidence_files(evidence_paths or [])
    scenario_reports = []
    for scenario_id in expected_scenarios:
        scenario_ok = scenario_id in passed
        scenario_reports.append(
            SmokeScenarioReport(
                scenario_id=scenario_id,
                ok=scenario_ok,
                summary=(
                    "Scenario passed with supplied live evidence."
                    if scenario_ok
                    else "Scenario has no supplied live passing evidence."
                ),
                fixture_ids=tuple(fixture["id"] for fixture in fixture_references_for_scenarios([scenario_id], target_id=target_id)),
                steps=(
                    SmokeStepResult(
                        id="evidence-import",
                        summary="Imported externally collected live smoke evidence.",
                        ok=scenario_ok and all(item["ok"] for item in evidence_files),
                        evidence={
                            "evidence_files": evidence_files,
                            "imported_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                        },
                    ),
                ),
            )
        )
    report = SmokeRunReport(
        suite_id=suite_id,
        target_id=target_id,
        runner_id=target.runner_profile,
        release_under_test=release_identity or {"source": release_source},
        fixture_references=tuple(
            fixture["id"]
            for fixture in fixture_references_for_scenarios(expected_scenarios, target_id=target_id)
        ),
        scenario_reports=tuple(scenario_reports),
        evidence={
            "summary": summary or "Smoke report imported from live evidence.",
            "target_profile": target.to_dict(),
            "evidence_files": evidence_files,
        },
    )
    return report.to_dict()


def evaluate_release_gate(
    *,
    gate_id: str,
    report_paths: list[str | Path],
    expected_targets: list[str] | None = None,
) -> dict[str, Any]:
    policy = release_gate_policy(gate_id)
    reports = [load_smoke_report(path) for path in report_paths]
    findings: list[dict[str, Any]] = []
    reports_by_target = {report["target_id"]: report for report in reports}
    actual_targets = sorted(reports_by_target.keys())
    required_targets = sorted(expected_targets or [])
    ok = True

    for report in reports:
        report_scenarios = {
            scenario.get("scenario_id")
            for scenario in report.get("scenario_reports", [])
            if scenario.get("scenario_id")
        }
        required_scenarios = set(suite_definition(policy["required_suite"])["scenario_ids"])
        if report.get("suite_id") != policy["required_suite"]:
            ok = False
            findings.append(
                {
                    "kind": "wrong_suite",
                    "target_id": report.get("target_id"),
                    "required_suite": policy["required_suite"],
                    "actual_suite": report.get("suite_id"),
                }
            )
        missing_scenarios = sorted(required_scenarios - report_scenarios)
        if missing_scenarios:
            ok = False
            findings.append(
                {
                    "kind": "missing_scenarios",
                    "target_id": report.get("target_id"),
                    "scenario_ids": missing_scenarios,
                }
            )
        if policy["require_all_overall_ok"] and not report.get("overall_ok", False):
            ok = False
            findings.append(
                {
                    "kind": "report_failed",
                    "target_id": report.get("target_id"),
                    "summary": "Smoke report did not pass.",
                }
            )

    if required_targets:
        missing_targets = [target_id for target_id in required_targets if target_id not in reports_by_target]
        if missing_targets:
            ok = False
            findings.append(
                {
                    "kind": "missing_targets",
                    "target_ids": missing_targets,
                }
            )
        if not policy["allow_scoped_targets"]:
            extra_targets = [target_id for target_id in actual_targets if target_id not in required_targets]
            if extra_targets:
                findings.append(
                    {
                        "kind": "extra_targets",
                        "target_ids": extra_targets,
                    }
                )

    return {
        "schema_version": 1,
        "gate": policy,
        "ok": ok,
        "status": "ok" if ok else "error",
        "reports_evaluated": len(reports),
        "actual_targets": actual_targets,
        "required_targets": required_targets,
        "findings": findings,
        "summary": (
            f"{policy['id']} smoke gate passed."
            if ok
            else f"{policy['id']} smoke gate failed."
        ),
    }


def phase26_exit_status(report_paths: list[str | Path] | None = None) -> dict[str, Any]:
    report_paths = report_paths or []
    target_ids = [target.id for target in TARGET_PROFILES]
    checks = [
        {
            "id": "framework-present",
            "ok": True,
            "summary": "Smoke harness framework, suites, targets, and fixtures are defined in the repository.",
        },
        {
            "id": "canonical-scenarios-present",
            "ok": {scenario.id for scenario in CORE_SCENARIOS}
            == {
                "bootstrap-install-usable-cli",
                "new-cli-project-build-run",
                "gorm-build-run",
                "self-update-cli-only",
            },
            "summary": "Canonical Tier 1 smoke scenarios are registered.",
        },
        {
            "id": "tier1-targets-present",
            "ok": set(target_ids) == {"windows-amd64-msys2-clang64", "openbsd-amd64-clang"},
            "summary": "Current active Tier 1 managed targets are represented in the harness.",
        },
        {
            "id": "developer-workflow-surface",
            "ok": True,
            "summary": "Developer workflow planning and report-template surfaces are available through scripts/dev/run-smoke-tests.py.",
        },
    ]
    if report_paths:
        gate = evaluate_release_gate(
            gate_id="release-candidate",
            report_paths=report_paths,
            expected_targets=target_ids,
        )
        checks.append(
            {
                "id": "tier1-reports-pass",
                "ok": gate["ok"],
                "summary": "Tier 1 smoke reports satisfy the release-candidate gate."
                if gate["ok"]
                else "Tier 1 smoke reports do not yet satisfy the release-candidate gate.",
                "details": gate,
            }
        )
    else:
        checks.append(
            {
                "id": "tier1-reports-pass",
                "ok": False,
                "summary": "No smoke reports were supplied, so live Phase 26 exit criteria cannot yet be proven.",
            }
        )
    overall_ok = all(check["ok"] for check in checks)
    return {
        "schema_version": 1,
        "command": "phase26-exit-status",
        "ok": overall_ok,
        "status": "ok" if overall_ok else "warning",
        "checks": checks,
        "summary": (
            "Phase 26 exit criteria are satisfied."
            if overall_ok
            else "Phase 26 infrastructure is present, but live target evidence is still required."
        ),
    }
