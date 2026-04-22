#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.build_infra import build_matrix, release_manifest_from_matrix, write_release_manifest
from gnustep_cli_shared.build_infra import (
    package_artifact_build_plan,
    package_artifact_publication_gate,
    package_tools_xctest_artifact,
    tools_xctest_release_gate,
    build_linux_cli_against_managed_toolchain,
    linux_cli_abi_audit,
    refresh_local_release_metadata,
    assemble_linux_toolchain_artifact,
    package_source_built_linux_toolchain_artifact,
    component_inventory,
    debian_gcc_interop_plan,
    bundle_full_cli,
    github_release_plan,
    linux_build_script,
    msys2_assembly_script,
    msys2_input_manifest_template,
    msvc_status,
    openbsd_build_script,
    otvm_release_host_validation_plan,
    qualify_full_cli_handoff,
    publish_github_release,
    prepare_github_release,
    published_url_qualification_plan,
    toolchain_archive_audit,
    toolchain_tree_host_origin_audit,
    validate_input_manifest,
    validate_source_lock,
    qualify_release_install,
    stage_release_assets,
    source_lock_template,
    toolchain_manifest,
    toolchain_plan,
    verify_release_directory,
    windows_extracted_toolchain_rebuild_plan,
    release_trust_gate,
    release_claim_consistency_gate,
    controlled_release_gate,
    compare_windows_msys2_inventories,
    delta_artifact_record,
    dogfood_snapshot_manifest,
    dogfood_snapshot_version,
    sign_release_metadata,
    windows_msys2_component_inventory,
    write_release_provenance,
    write_windows_current_source_marker,
    write_release_evidence_bundle,
    release_key_rotation_drill,
    session_build_box_plan,
)


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--json", action="store_true")
    subparsers = parser.add_subparsers(dest="subcommand")

    subparsers.add_parser("matrix", add_help=False)

    manifest = subparsers.add_parser("manifest", add_help=False)
    manifest.add_argument("--version", required=True)
    manifest.add_argument("--base-url", required=True)
    manifest.add_argument("--output")

    stage_release = subparsers.add_parser("stage-release", add_help=False)
    stage_release.add_argument("--version", required=True)
    stage_release.add_argument("--base-url", required=True)
    stage_release.add_argument("--output-dir", required=True)
    stage_release.add_argument("--channel", default="stable")
    stage_release.add_argument("--cli-input", action="append", default=[])
    stage_release.add_argument("--toolchain-input", action="append", default=[])
    stage_release.add_argument("--reuse-toolchain-artifact", action="append", default=[])

    bundle_cli = subparsers.add_parser("bundle-cli", add_help=False)
    bundle_cli.add_argument("--binary", required=True)
    bundle_cli.add_argument("--output-dir", required=True)
    bundle_cli.add_argument("--repo-root")

    managed_cli = subparsers.add_parser("build-linux-cli-against-managed-toolchain", add_help=False)
    managed_cli.add_argument("--toolchain-archive", required=True)
    managed_cli.add_argument("--output-archive", required=True)
    managed_cli.add_argument("--version", default="0.1.0-dev")
    managed_cli.add_argument("--target", default="linux-amd64-clang")
    managed_cli.add_argument("--repo-root")
    managed_cli.add_argument("--work-dir")
    managed_cli.add_argument("--release-dir")
    managed_cli.add_argument("--private-key")

    linux_cli_abi = subparsers.add_parser("linux-cli-abi-audit", add_help=False)
    linux_cli_abi.add_argument("--binary", required=True)

    refresh_release = subparsers.add_parser("refresh-local-release-metadata", add_help=False)
    refresh_release.add_argument("--release-dir", required=True)
    refresh_release.add_argument("--private-key")

    assemble_linux_toolchain = subparsers.add_parser("assemble-linux-toolchain", add_help=False)
    assemble_linux_toolchain.add_argument("--runtime-binary", required=True)
    assemble_linux_toolchain.add_argument("--output-dir", required=True)

    package_linux_toolchain = subparsers.add_parser("package-source-built-linux-toolchain", add_help=False)
    package_linux_toolchain.add_argument("--staging-prefix", required=True)
    package_linux_toolchain.add_argument("--output-dir", required=True)
    package_linux_toolchain.add_argument("--toolchain-version", default="2026.04.0")
    package_linux_toolchain.add_argument("--target", default="linux-amd64-clang")

    host_origin_audit = subparsers.add_parser("toolchain-host-origin-audit", add_help=False)
    host_origin_audit.add_argument("--toolchain-root", required=True)

    github_plan = subparsers.add_parser("github-release-plan", add_help=False)
    github_plan.add_argument("--repo", required=True)
    github_plan.add_argument("--version", required=True)
    github_plan.add_argument("--release-dir", required=True)
    github_plan.add_argument("--channel", default="stable")
    github_plan.add_argument("--title")

    github_publish = subparsers.add_parser("github-release-publish", add_help=False)
    github_publish.add_argument("--repo", required=True)
    github_publish.add_argument("--version", required=True)
    github_publish.add_argument("--release-dir", required=True)
    github_publish.add_argument("--channel", default="stable")
    github_publish.add_argument("--title")

    prepare_release = subparsers.add_parser("prepare-github-release", add_help=False)
    prepare_release.add_argument("--repo", required=True)
    prepare_release.add_argument("--version", required=True)
    prepare_release.add_argument("--base-url", required=True)
    prepare_release.add_argument("--output-dir", required=True)
    prepare_release.add_argument("--channel", default="stable")
    prepare_release.add_argument("--title")
    prepare_release.add_argument("--install-root")
    prepare_release.add_argument("--handoff-install-root")
    prepare_release.add_argument("--cli-input", action="append", default=[])
    prepare_release.add_argument("--toolchain-input", action="append", default=[])
    prepare_release.add_argument("--reuse-toolchain-artifact", action="append", default=[])

    session_builders = subparsers.add_parser("session-build-box-plan", add_help=False)
    session_builders.add_argument("--target", action="append", default=[])
    session_builders.add_argument("--ttl-hours", type=int, default=8)
    session_builders.add_argument("--channel", default="dogfood")
    session_builders.add_argument("--repo-root", default=".")
    session_builders.add_argument("--otvm-config", default="~/oracletestvms-libvirt.toml")

    dogfood_version = subparsers.add_parser("dogfood-snapshot-version", add_help=False)
    dogfood_version.add_argument("--base-version", required=True)
    dogfood_version.add_argument("--source-revision")
    dogfood_version.add_argument("--timestamp")
    dogfood_version.add_argument("--sequence", type=int, default=0)

    delta_record = subparsers.add_parser("delta-artifact-record", add_help=False)
    delta_record.add_argument("--id", required=True)
    delta_record.add_argument("--from-artifact", required=True)
    delta_record.add_argument("--to-artifact", required=True)
    delta_record.add_argument("--url", required=True)
    delta_record.add_argument("--sha256", required=True)
    delta_record.add_argument("--size", type=int, required=True)
    delta_record.add_argument("--algorithm", default="metadata-only")

    windows_inventory = subparsers.add_parser("windows-msys2-component-inventory", add_help=False)
    windows_inventory.add_argument("--toolchain-version", required=True)

    compare_windows_inventory = subparsers.add_parser("compare-windows-msys2-inventories", add_help=False)
    compare_windows_inventory.add_argument("--old", required=True)
    compare_windows_inventory.add_argument("--new", required=True)

    verify_release = subparsers.add_parser("verify-release", add_help=False)
    verify_release.add_argument("--release-dir", required=True)


    release_provenance = subparsers.add_parser("release-provenance", add_help=False)
    release_provenance.add_argument("--release-dir", required=True)

    sign_release = subparsers.add_parser("sign-release-metadata", add_help=False)
    sign_release.add_argument("--release-dir", required=True)
    sign_release.add_argument("--private-key", required=True)
    sign_release.add_argument("--public-key")

    trust_gate = subparsers.add_parser("release-trust-gate", add_help=False)
    trust_gate.add_argument("--release-dir", required=True)
    trust_gate.add_argument("--allow-unsigned", action="store_true")
    trust_gate.add_argument("--trusted-public-key")

    claim_gate = subparsers.add_parser("release-claim-consistency-gate", add_help=False)
    claim_gate.add_argument("--release-dir", required=True)
    claim_gate.add_argument("--evidence-dir")
    claim_gate.add_argument("--allow-stale-windows-artifact", action="store_true")

    windows_marker = subparsers.add_parser("windows-current-source-marker", add_help=False)
    windows_marker.add_argument("--release-dir", required=True)
    windows_marker.add_argument("--artifact-id", default="cli-windows-amd64-msys2-clang64")
    windows_marker.add_argument("--source-revision")
    windows_marker.add_argument("--builder-identity", default="local")

    evidence_bundle = subparsers.add_parser("release-evidence-bundle", add_help=False)
    evidence_bundle.add_argument("--release-dir", required=True)
    evidence_bundle.add_argument("--evidence-dir")

    key_rotation_drill = subparsers.add_parser("release-key-rotation-drill", add_help=False)
    key_rotation_drill.add_argument("--release-dir", required=True)
    key_rotation_drill.add_argument("--work-dir")

    controlled_gate = subparsers.add_parser("controlled-release-gate", add_help=False)
    controlled_gate.add_argument("--release-dir", required=True)
    controlled_gate.add_argument("--package-index")
    controlled_gate.add_argument("--release-trust-root")
    controlled_gate.add_argument("--package-index-trust-root")
    controlled_gate.add_argument("--allow-unsigned-package-index", action="store_true")
    controlled_gate.add_argument("--tools-xctest-packages-dir")
    controlled_gate.add_argument("--tools-xctest-evidence-dir")

    toolchain_audit = subparsers.add_parser("toolchain-archive-audit", add_help=False)
    toolchain_audit.add_argument("--archive", required=True)
    toolchain_audit.add_argument("--target")

    package_plan = subparsers.add_parser("package-artifact-build-plan", add_help=False)
    package_plan.add_argument("--packages-dir", required=True)

    package_gate = subparsers.add_parser("package-artifact-publication-gate", add_help=False)
    package_gate.add_argument("--packages-dir", required=True)

    tools_xctest_gate = subparsers.add_parser("tools-xctest-release-gate", add_help=False)
    tools_xctest_gate.add_argument("--packages-dir", required=True)
    tools_xctest_gate.add_argument("--evidence-dir")

    tools_xctest_artifact = subparsers.add_parser("package-tools-xctest-artifact", add_help=False)
    tools_xctest_artifact.add_argument("--output-dir", required=True)
    tools_xctest_artifact.add_argument("--source-dir")
    tools_xctest_artifact.add_argument("--source-url", default="https://github.com/gnustep/tools-xctest.git")
    tools_xctest_artifact.add_argument("--source-revision")
    tools_xctest_artifact.add_argument("--installed-root")
    tools_xctest_artifact.add_argument("--target", default="linux-amd64-clang")
    tools_xctest_artifact.add_argument("--version", default="0.1.0")
    tools_xctest_artifact.add_argument("--rebuild", action="store_true")

    otvm_release_validation = subparsers.add_parser("otvm-release-host-validation-plan", add_help=False)
    otvm_release_validation.add_argument("--release-dir", required=True)
    otvm_release_validation.add_argument("--config-path", default="~/oracletestvms-libvirt.toml")

    published_url_validation = subparsers.add_parser("published-url-qualification-plan", add_help=False)
    published_url_validation.add_argument("--release-url", required=True)
    published_url_validation.add_argument("--config-path", default="~/oracletestvms-libvirt.toml")

    qualify_release = subparsers.add_parser("qualify-release", add_help=False)
    qualify_release.add_argument("--release-dir", required=True)
    qualify_release.add_argument("--install-root", required=True)

    qualify_handoff = subparsers.add_parser("qualify-full-cli-handoff", add_help=False)
    qualify_handoff.add_argument("--release-dir", required=True)
    qualify_handoff.add_argument("--install-root", required=True)

    source_lock = subparsers.add_parser("source-lock", add_help=False)
    source_lock.add_argument("--target", required=True)

    validate_source_lock_cmd = subparsers.add_parser("validate-source-lock", add_help=False)
    validate_source_lock_cmd.add_argument("--path", required=True)
    validate_source_lock_cmd.add_argument("--target")

    msys2_manifest = subparsers.add_parser("msys2-input-manifest", add_help=False)

    validate_input_manifest_cmd = subparsers.add_parser("validate-input-manifest", add_help=False)
    validate_input_manifest_cmd.add_argument("--path", required=True)
    validate_input_manifest_cmd.add_argument("--target")

    subparsers.add_parser("debian-gcc-interop-plan", add_help=False)

    inventory = subparsers.add_parser("component-inventory", add_help=False)
    inventory.add_argument("--target", required=True)
    inventory.add_argument("--toolchain-version", required=True)

    manifest_cmd = subparsers.add_parser("toolchain-manifest", add_help=False)
    manifest_cmd.add_argument("--target", required=True)
    manifest_cmd.add_argument("--toolchain-version", required=True)

    toolchain = subparsers.add_parser("toolchain-plan", add_help=False)
    toolchain.add_argument("--target", required=True)

    linux_script = subparsers.add_parser("linux-build-script", add_help=False)
    linux_script.add_argument("--target", required=True)
    linux_script.add_argument("--prefix", required=True)
    linux_script.add_argument("--sources-dir", required=True)
    linux_script.add_argument("--build-root", required=True)

    openbsd_script = subparsers.add_parser("openbsd-build-script", add_help=False)
    openbsd_script.add_argument("--target", required=True)
    openbsd_script.add_argument("--prefix", required=True)
    openbsd_script.add_argument("--sources-dir", required=True)
    openbsd_script.add_argument("--build-root", required=True)

    msys2_script = subparsers.add_parser("msys2-assembly-script", add_help=False)
    msys2_script.add_argument("--prefix", required=True)
    msys2_script.add_argument("--cache-dir", required=True)

    subparsers.add_parser("msvc-status", add_help=False)
    subparsers.add_parser("windows-extracted-toolchain-rebuild-plan", add_help=False)

    args = parser.parse_args()
    def mapping(values: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        for item in values:
            target, path = item.split("=", 1)
            result[target] = path
        return result

    if args.subcommand == "matrix":
        payload = build_matrix()
    elif args.subcommand == "manifest":
        if args.output:
            output = write_release_manifest(args.version, args.base_url, args.output)
            payload = {"schema_version": 1, "command": "build-infra", "ok": True, "status": "ok", "output": str(output)}
        else:
            payload = release_manifest_from_matrix(args.version, args.base_url)
    elif args.subcommand == "stage-release":
        payload = stage_release_assets(
            args.version,
            args.output_dir,
            args.base_url,
            cli_inputs=mapping(args.cli_input),
            toolchain_inputs=mapping(args.toolchain_input),
            reused_toolchain_artifacts=mapping(args.reuse_toolchain_artifact),
            channel=args.channel,
        )
    elif args.subcommand == "session-build-box-plan":
        payload = session_build_box_plan(
            targets=args.target or None,
            ttl_hours=args.ttl_hours,
            channel=args.channel,
            repo_root=args.repo_root,
            otvm_config=args.otvm_config,
        )
    elif args.subcommand == "dogfood-snapshot-version":
        version = dogfood_snapshot_version(
            args.base_version,
            source_revision=args.source_revision,
            timestamp=args.timestamp,
            sequence=args.sequence,
        )
        payload = {"schema_version": 1, "command": "dogfood-snapshot-version", "ok": True, "status": "ok", "version": version}
    elif args.subcommand == "delta-artifact-record":
        payload = {
            "schema_version": 1,
            "command": "delta-artifact-record",
            "ok": True,
            "status": "ok",
            "artifact": delta_artifact_record(
                delta_id=args.id,
                from_artifact=json.loads(Path(args.from_artifact).read_text()),
                to_artifact=json.loads(Path(args.to_artifact).read_text()),
                url=args.url,
                sha256=args.sha256,
                size=args.size,
                algorithm=args.algorithm,
            ),
        }
    elif args.subcommand == "bundle-cli":
        payload = bundle_full_cli(args.binary, args.output_dir, repo_root=args.repo_root)
    elif args.subcommand == "assemble-linux-toolchain":
        payload = assemble_linux_toolchain_artifact(
            args.output_dir,
            runtime_binary=args.runtime_binary,
        )
    elif args.subcommand == "package-source-built-linux-toolchain":
        payload = package_source_built_linux_toolchain_artifact(
            args.staging_prefix,
            args.output_dir,
            toolchain_version=args.toolchain_version,
            target_id=args.target,
        )
    elif args.subcommand == "toolchain-host-origin-audit":
        payload = toolchain_tree_host_origin_audit(args.toolchain_root)
    elif args.subcommand == "github-release-plan":
        payload = github_release_plan(
            args.repo,
            args.version,
            args.release_dir,
            channel=args.channel,
            title=args.title,
        )
    elif args.subcommand == "github-release-publish":
        payload = publish_github_release(
            args.repo,
            args.version,
            args.release_dir,
            channel=args.channel,
            title=args.title,
        )
    elif args.subcommand == "prepare-github-release":
        payload = prepare_github_release(
            args.repo,
            args.version,
            args.output_dir,
            args.base_url,
            cli_inputs=mapping(args.cli_input),
            toolchain_inputs=mapping(args.toolchain_input),
            reused_toolchain_artifacts=mapping(args.reuse_toolchain_artifact),
            install_root=args.install_root,
            handoff_install_root=args.handoff_install_root,
            channel=args.channel,
            title=args.title,
        )
    elif args.subcommand == "verify-release":
        payload = verify_release_directory(args.release_dir)
    elif args.subcommand == "release-provenance":
        path = write_release_provenance(args.release_dir)
        payload = {"schema_version": 1, "command": "release-provenance", "ok": True, "status": "ok", "provenance_path": str(path)}
    elif args.subcommand == "sign-release-metadata":
        payload = sign_release_metadata(args.release_dir, args.private_key, public_key_path=args.public_key)
    elif args.subcommand == "release-trust-gate":
        payload = release_trust_gate(args.release_dir, require_signatures=not args.allow_unsigned, trusted_public_key_path=args.trusted_public_key)
    elif args.subcommand == "release-claim-consistency-gate":
        payload = release_claim_consistency_gate(
            args.release_dir,
            evidence_dir=args.evidence_dir,
            require_windows_current_source=not args.allow_stale_windows_artifact,
        )
    elif args.subcommand == "windows-current-source-marker":
        payload = write_windows_current_source_marker(
            args.release_dir,
            artifact_id=args.artifact_id,
            source_revision=args.source_revision,
            builder_identity=args.builder_identity,
        )
    elif args.subcommand == "release-evidence-bundle":
        payload = write_release_evidence_bundle(args.release_dir, evidence_dir=args.evidence_dir)
    elif args.subcommand == "release-key-rotation-drill":
        payload = release_key_rotation_drill(args.release_dir, work_dir=args.work_dir)
    elif args.subcommand == "controlled-release-gate":
        payload = controlled_release_gate(
            args.release_dir,
            package_index_path=args.package_index,
            release_trust_root=args.release_trust_root,
            package_index_trust_root=args.package_index_trust_root,
            allow_unsigned_package_index=args.allow_unsigned_package_index,
            tools_xctest_packages_dir=args.tools_xctest_packages_dir,
            tools_xctest_evidence_dir=args.tools_xctest_evidence_dir,
        )
    elif args.subcommand == "toolchain-archive-audit":
        payload = toolchain_archive_audit(args.archive, target_id=args.target)
    elif args.subcommand == "package-artifact-build-plan":
        payload = package_artifact_build_plan(args.packages_dir)
    elif args.subcommand == "package-artifact-publication-gate":
        payload = package_artifact_publication_gate(args.packages_dir)
    elif args.subcommand == "tools-xctest-release-gate":
        payload = tools_xctest_release_gate(args.packages_dir, evidence_dir=args.evidence_dir)
    elif args.subcommand == "package-tools-xctest-artifact":
        payload = package_tools_xctest_artifact(
            args.output_dir,
            source_dir=args.source_dir,
            source_url=args.source_url,
            source_revision=args.source_revision,
            installed_root=args.installed_root,
            target_id=args.target,
            version=args.version,
            rebuild=args.rebuild,
        )
    elif args.subcommand == "build-linux-cli-against-managed-toolchain":
        payload = build_linux_cli_against_managed_toolchain(
            args.toolchain_archive,
            args.output_archive,
            version=args.version,
            target_id=args.target,
            repo_root=args.repo_root,
            work_dir=args.work_dir,
            release_dir=args.release_dir,
            private_key=args.private_key,
        )
    elif args.subcommand == "linux-cli-abi-audit":
        payload = linux_cli_abi_audit(args.binary)
    elif args.subcommand == "refresh-local-release-metadata":
        payload = refresh_local_release_metadata(args.release_dir, private_key_path=args.private_key)
    elif args.subcommand == "otvm-release-host-validation-plan":
        payload = otvm_release_host_validation_plan(args.release_dir, config_path=args.config_path)
    elif args.subcommand == "published-url-qualification-plan":
        payload = published_url_qualification_plan(args.release_url, config_path=args.config_path)
    elif args.subcommand == "qualify-release":
        payload = qualify_release_install(args.release_dir, args.install_root)
    elif args.subcommand == "qualify-full-cli-handoff":
        payload = qualify_full_cli_handoff(args.release_dir, args.install_root)
    elif args.subcommand == "source-lock":
        payload = source_lock_template(args.target)
    elif args.subcommand == "validate-source-lock":
        payload = validate_source_lock(json.loads(Path(args.path).read_text()), target_id=args.target)
    elif args.subcommand == "msys2-input-manifest":
        payload = msys2_input_manifest_template()
    elif args.subcommand == "validate-input-manifest":
        payload = validate_input_manifest(json.loads(Path(args.path).read_text()), target_id=args.target)
    elif args.subcommand == "debian-gcc-interop-plan":
        payload = debian_gcc_interop_plan()
    elif args.subcommand == "component-inventory":
        payload = component_inventory(args.target, args.toolchain_version)
    elif args.subcommand == "windows-msys2-component-inventory":
        payload = windows_msys2_component_inventory(toolchain_version=args.toolchain_version)
    elif args.subcommand == "compare-windows-msys2-inventories":
        payload = compare_windows_msys2_inventories(
            json.loads(Path(args.old).read_text()),
            json.loads(Path(args.new).read_text()),
        )
    elif args.subcommand == "toolchain-manifest":
        payload = toolchain_manifest(args.target, args.toolchain_version)
    elif args.subcommand == "toolchain-plan":
        payload = toolchain_plan(args.target)
    elif args.subcommand == "linux-build-script":
        script = linux_build_script(args.target, args.prefix, args.sources_dir, args.build_root)
        if args.json:
            payload = {"schema_version": 1, "command": "build-infra", "ok": True, "status": "ok", "script": script}
        else:
            print(script)
            return 0
    elif args.subcommand == "openbsd-build-script":
        script = openbsd_build_script(args.target, args.prefix, args.sources_dir, args.build_root)
        if args.json:
            payload = {"schema_version": 1, "command": "build-infra", "ok": True, "status": "ok", "script": script}
        else:
            print(script)
            return 0
    elif args.subcommand == "msys2-assembly-script":
        script = msys2_assembly_script(args.prefix, args.cache_dir)
        if args.json:
            payload = {"schema_version": 1, "command": "build-infra", "ok": True, "status": "ok", "script": script}
        else:
            print(script)
            return 0
    elif args.subcommand == "msvc-status":
        payload = msvc_status()
    elif args.subcommand == "windows-extracted-toolchain-rebuild-plan":
        payload = windows_extracted_toolchain_rebuild_plan()
    else:
        print(
            "build-infra: expected 'matrix', 'manifest', 'bundle-cli', 'source-lock', "
            "'assemble-linux-toolchain', 'package-source-built-linux-toolchain', 'toolchain-host-origin-audit', "
            "'stage-release', 'github-release-plan', 'github-release-publish', "
            "'prepare-github-release', 'session-build-box-plan', 'dogfood-snapshot-version', 'delta-artifact-record', 'package-artifact-publication-gate', 'tools-xctest-release-gate', 'package-tools-xctest-artifact', 'build-linux-cli-against-managed-toolchain', 'linux-cli-abi-audit', 'refresh-local-release-metadata', 'published-url-qualification-plan', "
            "'verify-release', 'qualify-release', 'qualify-full-cli-handoff', 'windows-current-source-marker', 'release-evidence-bundle', 'release-key-rotation-drill', "
            "'validate-source-lock', 'msys2-input-manifest', 'validate-input-manifest', 'component-inventory', 'windows-msys2-component-inventory', 'compare-windows-msys2-inventories', 'toolchain-manifest', "
            "'toolchain-plan', 'linux-build-script', 'openbsd-build-script', "
            "'msys2-assembly-script', 'toolchain-archive-audit', 'debian-gcc-interop-plan', 'windows-extracted-toolchain-rebuild-plan', or 'msvc-status'",
            file=sys.stderr,
        )
        return 2

    if args.json:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print("Build infrastructure payload generated.")
    if isinstance(payload, dict) and payload.get("ok") is False:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
