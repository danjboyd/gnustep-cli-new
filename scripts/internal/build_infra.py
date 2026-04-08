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
    component_inventory,
    github_release_plan,
    linux_build_script,
    msys2_assembly_script,
    msys2_input_manifest_template,
    msvc_status,
    openbsd_build_script,
    publish_github_release,
    qualify_release_install,
    stage_release_assets,
    source_lock_template,
    toolchain_manifest,
    toolchain_plan,
    verify_release_directory,
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

    verify_release = subparsers.add_parser("verify-release", add_help=False)
    verify_release.add_argument("--release-dir", required=True)

    qualify_release = subparsers.add_parser("qualify-release", add_help=False)
    qualify_release.add_argument("--release-dir", required=True)
    qualify_release.add_argument("--install-root", required=True)

    source_lock = subparsers.add_parser("source-lock", add_help=False)
    source_lock.add_argument("--target", required=True)

    msys2_manifest = subparsers.add_parser("msys2-input-manifest", add_help=False)

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
            channel=args.channel,
        )
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
    elif args.subcommand == "verify-release":
        payload = verify_release_directory(args.release_dir)
    elif args.subcommand == "qualify-release":
        payload = qualify_release_install(args.release_dir, args.install_root)
    elif args.subcommand == "source-lock":
        payload = source_lock_template(args.target)
    elif args.subcommand == "msys2-input-manifest":
        payload = msys2_input_manifest_template()
    elif args.subcommand == "component-inventory":
        payload = component_inventory(args.target, args.toolchain_version)
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
    else:
        print(
            "build-infra: expected 'matrix', 'manifest', 'source-lock', "
            "'stage-release', 'github-release-plan', 'github-release-publish', "
            "'verify-release', 'qualify-release', "
            "'msys2-input-manifest', 'component-inventory', 'toolchain-manifest', "
            "'toolchain-plan', 'linux-build-script', 'openbsd-build-script', "
            "'msys2-assembly-script', or 'msvc-status'",
            file=sys.stderr,
        )
        return 2

    if args.json:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print("Build infrastructure payload generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
