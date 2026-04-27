import sys
import subprocess
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.compatibility import artifact_matches_host, evaluate_environment_against_artifact
from gnustep_cli_shared.build_infra import (
    assemble_linux_toolchain_artifact,
    build_matrix,
    compare_windows_msys2_inventories,
    delta_artifact_record,
    bundle_full_cli,
    component_inventory,
    current_support_matrix,
    debian_gcc_interop_plan,
    github_release_plan,
    dogfood_snapshot_manifest,
    dogfood_snapshot_version,
    validate_delta_artifact_record,
    linux_build_script,
    linux_cli_abi_audit,
    refresh_local_release_metadata,
    release_candidate_qualification_status,
    native_linux_validation_plan,
    msys2_assembly_script,
    msys2_input_manifest_template,
    MANAGED_PREFIX_PLACEHOLDER,
    msvc_status,
    openbsd_build_script,
    otvm_release_host_validation_plan,
    package_artifact_build_plan,
    package_artifact_publication_gate,
    package_tools_xctest_artifact,
    tools_xctest_release_gate,
    package_source_built_linux_toolchain_artifact,
    prepare_github_release,
    published_url_qualification_plan,
    qualify_full_cli_handoff,
    toolchain_manifest,
    release_manifest_from_matrix,
    reusable_artifact_reference,
    qualify_release_install,
    session_build_box_plan,
    stage_release_assets,
    source_lock_template,
    toolchain_tree_host_origin_audit,
    write_toolchain_metadata,
    toolchain_archive_audit,
    toolchain_plan,
    validate_input_manifest,
    validate_source_lock,
    verify_release_directory,
    release_trust_gate,
    controlled_release_gate,
    release_claim_consistency_gate,
    sign_release_metadata,
    write_release_manifest,
    write_release_provenance,
    write_windows_current_source_marker,
    write_release_evidence_bundle,
    validate_update_all_evidence,
    release_key_rotation_drill,
    phase12_production_hardening_status,
    phase13_update_hardening_status,
    windows_extracted_toolchain_rebuild_plan,
    windows_msys2_component_inventory,
)
from gnustep_cli_shared.smoke_harness import evidence_smoke_report


def managed_debian_doctor_payload():
    return {
        "status": "warning",
        "environment_classification": "no_toolchain",
        "native_toolchain_assessment": "unavailable",
        "summary": "No GNUstep toolchain detected.",
        "environment": {
            "os": "linux",
            "arch": "amd64",
            "distribution_id": "debian",
            "os_version": "debian-13",
            "bootstrap_prerequisites": {"curl": True, "wget": False},
            "native_toolchain": {"assessment": "unavailable"},
            "toolchain": {
                "present": False,
                "compiler_family": "unknown",
                "toolchain_flavor": "unknown",
                "objc_runtime": "unknown",
                "objc_abi": "unknown",
                "feature_flags": {},
            },
        },
    }


class BuildInfraTests(unittest.TestCase):
    def test_matrix_contains_tier1_targets(self):
        payload = build_matrix()
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(len(payload["targets"]), 7)

    def test_release_manifest_generation(self):
        payload = release_manifest_from_matrix("0.1.0", "https://example.invalid/releases")
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["releases"][0]["version"], "0.1.0")
        self.assertEqual(len(payload["releases"][0]["artifacts"]), 14)
        linux_artifacts = [artifact for artifact in payload["releases"][0]["artifacts"] if artifact["os"] == "linux"]
        self.assertTrue(linux_artifacts)
        distribution_by_id = {artifact["id"]: artifact["supported_distributions"] for artifact in linux_artifacts}
        self.assertEqual(distribution_by_id["cli-linux-amd64-clang"], ["debian"])
        self.assertEqual(distribution_by_id["toolchain-linux-amd64-clang"], ["debian"])
        self.assertEqual(distribution_by_id["cli-linux-ubuntu2404-amd64-clang"], ["ubuntu"])
        self.assertEqual(distribution_by_id["toolchain-linux-ubuntu2404-amd64-clang"], ["ubuntu"])
        version_by_id = {artifact["id"]: artifact["supported_os_versions"] for artifact in linux_artifacts}
        self.assertEqual(version_by_id["cli-linux-ubuntu2404-amd64-clang"], ["ubuntu-24.04"])
        self.assertEqual(version_by_id["toolchain-linux-ubuntu2404-amd64-clang"], ["ubuntu-24.04"])
        published_by_id = {artifact["id"]: artifact["published"] for artifact in linux_artifacts}
        self.assertTrue(published_by_id["cli-linux-ubuntu2404-amd64-clang"])
        self.assertTrue(published_by_id["toolchain-linux-ubuntu2404-amd64-clang"])
        self.assertTrue(all(artifact["portability_policy"] == "distribution-scoped" for artifact in linux_artifacts))

    def test_source_lock_template_for_linux(self):
        payload = source_lock_template("linux-amd64-clang")
        components = {component["name"]: component for component in payload["components"]}
        self.assertEqual(payload["strategy"], "source-build")
        self.assertIn("libdispatch", components)
        self.assertIn("libs-corebase", components)
        self.assertEqual(
            components["libobjc2"]["revision"],
            "b67709ad7851973fde127022d8ac6a710c82b1d5",
        )


    def test_arm64_managed_targets_have_source_locks_and_stay_unpublished_until_validated(self):
        for target_id in ("linux-arm64-clang", "openbsd-arm64-clang"):
            with self.subTest(target_id=target_id):
                lock = source_lock_template(target_id)
                validation = validate_source_lock(lock, target_id=target_id)
                manifest = toolchain_manifest(target_id, "2026.04.0")
                self.assertTrue(validation["ok"])
                self.assertEqual(lock["target"]["arch"], "arm64")
                self.assertEqual(lock["target"]["compiler_family"], "clang")
                self.assertEqual(lock["runtime"]["objc_runtime"], "libobjc2")
                self.assertFalse(manifest["published"])
                self.assertEqual(manifest["target"]["arch"], "arm64")


    def test_source_lock_validation_rejects_unpinned_revision(self):
        payload = source_lock_template("linux-amd64-clang")
        self.assertTrue(validate_source_lock(payload, target_id="linux-amd64-clang")["ok"])
        payload["components"][0]["revision"] = "TBD"
        result = validate_source_lock(payload, target_id="linux-amd64-clang")
        self.assertFalse(result["ok"])
        self.assertIn("revision", result["errors"][0]["path"])


    def test_linux_managed_artifact_is_debian_scoped_until_portability_is_closed(self):
        artifact = release_manifest_from_matrix("0.1.0", "https://example.invalid")["releases"][0]["artifacts"][0]
        debian_env = {"os": "linux", "arch": "amd64", "distribution_id": "debian", "toolchain": {}}
        ubuntu_env = {"os": "linux", "arch": "amd64", "distribution_id": "ubuntu", "os_version": "ubuntu-24.04", "toolchain": {}}
        ubuntu_2604_env = {"os": "linux", "arch": "amd64", "distribution_id": "ubuntu", "os_version": "ubuntu-26.04", "toolchain": {}}
        fedora_env = {"os": "linux", "arch": "amd64", "distribution_id": "fedora", "toolchain": {}}
        ubuntu_artifact = next(
            artifact
            for artifact in release_manifest_from_matrix("0.1.0", "https://example.invalid")["releases"][0]["artifacts"]
            if artifact["id"] == "cli-linux-ubuntu2404-amd64-clang"
        )
        self.assertTrue(artifact_matches_host(debian_env, artifact))
        self.assertFalse(artifact_matches_host(ubuntu_env, artifact))
        self.assertTrue(artifact_matches_host(ubuntu_env, ubuntu_artifact))
        self.assertFalse(artifact_matches_host(ubuntu_2604_env, ubuntu_artifact))
        self.assertFalse(artifact_matches_host(fedora_env, artifact))
        result = evaluate_environment_against_artifact(fedora_env, artifact)
        reason_codes = [reason["code"] for reason in result["reasons"]]
        self.assertIn("unsupported_distribution", reason_codes)

    def test_msys2_input_manifest_validation(self):
        payload = msys2_input_manifest_template()
        result = validate_input_manifest(payload, target_id="windows-amd64-msys2-clang64")
        self.assertTrue(result["ok"])
        payload["packages"] = payload["packages"][:-1]
        result = validate_input_manifest(payload, target_id="windows-amd64-msys2-clang64")
        self.assertFalse(result["ok"])

    def test_toolchain_host_origin_audit_detects_gnustep_paths(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            leaked = root / "System" / "Library" / "Makefiles" / "GNUstep.sh"
            leaked.parent.mkdir(parents=True)
            leaked.write_text("GNUSTEP_MAKEFILES=/usr/share/GNUstep/Makefiles\n")
            result = toolchain_tree_host_origin_audit(root)
            self.assertFalse(result["ok"])
            self.assertEqual(result["findings"][0]["pattern"], "/usr/share/GNUstep")

    def test_package_source_built_linux_toolchain_artifact_writes_policy_metadata(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            staging = temp / "staging"
            (staging / "System" / "Tools").mkdir(parents=True)
            (staging / "System" / "Tools" / "gnustep-config").write_text("#!/bin/sh\n")
            libdir = staging / "lib"
            libdir.mkdir(parents=True)
            (libdir / "libBlocksRuntime.so").write_text("blocks")
            (libdir / "libobjc.so.4.6").write_text("objc")
            pc = staging / "Local" / "Library" / "Libraries" / "pkgconfig" / "gnustep-base.pc"
            pc.parent.mkdir(parents=True)
            pc.write_text(f"Libs: -L{staging}/Local/Library/Libraries -L{Path.home()}/GNUstep/Library/Libraries\nCflags: -I{staging}/Local/Library/Headers -I{Path.home()}/GNUstep/Library/Headers\n")
            payload = package_source_built_linux_toolchain_artifact(staging, temp / "packaged")
            self.assertTrue(payload["ok"])
            packaged = Path(payload["output_root"])
            self.assertTrue((packaged / "source-lock.json").exists())
            self.assertTrue((packaged / "component-inventory.json").exists())
            manifest = __import__("json").loads((packaged / "toolchain-manifest.json").read_text())
            self.assertTrue(manifest["source_policy"]["production_eligible"])
            self.assertEqual(manifest["platform_policy"]["supported_distributions"], ["debian"])
            self.assertEqual(manifest["platform_policy"]["portability_policy"], "distribution-scoped")
            rewritten_pc = (packaged / "Local" / "Library" / "Libraries" / "pkgconfig" / "gnustep-base.pc").read_text()
            self.assertIn(MANAGED_PREFIX_PLACEHOLDER, rewritten_pc)
            self.assertNotIn(str(staging), rewritten_pc)
            self.assertNotIn(str(Path.home() / "GNUstep"), rewritten_pc)
            self.assertIn("-ldispatch", rewritten_pc)
            self.assertIn("-lBlocksRuntime", rewritten_pc)
            self.assertTrue((packaged / "lib" / "libBlocksRuntime.so.0").is_symlink())
            self.assertEqual((packaged / "lib" / "libBlocksRuntime.so.0").readlink(), Path("libBlocksRuntime.so"))
            self.assertTrue((packaged / "lib" / "libobjc.so.4").is_symlink())
            self.assertEqual((packaged / "lib" / "libobjc.so.4").readlink(), Path("libobjc.so.4.6"))
            metadata = __import__("json").loads((packaged / "toolchain-assembly.json").read_text())
            self.assertIn("lib/libBlocksRuntime.so.0", metadata["runtime_aliases"])
            self.assertIn("lib/libobjc.so.4", metadata["runtime_aliases"])

    def test_msys2_input_manifest_template(self):
        payload = msys2_input_manifest_template()
        host_package_names = [package["name"] for package in payload["host_packages"]]
        package_names = [package["name"] for package in payload["packages"]]
        self.assertEqual(payload["strategy"], "msys2-assembly")
        self.assertEqual(payload["installer"]["source_channel"], "msys2-installer")
        self.assertIn("msys2-installer/releases/latest/download/msys2-x86_64-latest.exe", payload["installer"]["url"])
        self.assertEqual(payload["root_layout"]["install_root"], "private-msys2-root")
        self.assertIn("var/lib/pacman/local", payload["root_layout"]["preserve"])
        self.assertIn("make", host_package_names)
        self.assertIn("mingw-w64-clang-x86_64-clang", package_names)
        self.assertIn("mingw-w64-clang-x86_64-libdispatch", package_names)
        self.assertIn("mingw-w64-clang-x86_64-cairo", package_names)
        self.assertIn("mingw-w64-clang-x86_64-fontconfig", package_names)
        self.assertIn("mingw-w64-clang-x86_64-freetype", package_names)
        self.assertIn("mingw-w64-clang-x86_64-pixman", package_names)
        conflict_paths = [rule["path"] for rule in payload["conflict_rules"]]
        self.assertIn("clang64/include/Block.h", conflict_paths)

    def test_toolchain_manifest(self):
        payload = toolchain_manifest("linux-amd64-clang", "2026.04.0")
        self.assertEqual(payload["kind"], "managed-toolchain")
        self.assertIn("libs-corebase", payload["components"])
        windows_payload = toolchain_manifest("windows-amd64-msys2-clang64", "2026.04.0")
        self.assertIn("developer_entrypoints", windows_payload)
        self.assertEqual(windows_payload["source_policy"]["assembly_input"], "official-msys2-installer")
        self.assertTrue(windows_payload["source_policy"]["private_root_required"])
        self.assertIn("clang64/bin/clang.exe", windows_payload["developer_entrypoints"]["compiler"])
        self.assertIn("usr/bin/bash.exe", windows_payload["developer_entrypoints"]["build_shell"])
        self.assertIn("usr/bin/sha256sum.exe", windows_payload["developer_entrypoints"]["checksum_tool"])
        self.assertIn("clang64/bin/openapp", windows_payload["developer_entrypoints"]["app_launcher"])

    def test_release_manifest_includes_trust_and_provenance_metadata(self):
        payload = release_manifest_from_matrix("0.1.0", "https://example.invalid/releases")
        self.assertEqual(payload["metadata_version"], 1)
        self.assertIn("trust", payload)
        self.assertIn("signatures", payload["trust"])
        self.assertEqual(payload["trust"]["root_version"], 1)
        self.assertNotEqual(payload["generated_at"], "TBD")
        artifact = payload["releases"][0]["artifacts"][0]
        self.assertIn("integrity", artifact)
        self.assertEqual(artifact["integrity"]["sha256"], "TBD")
        self.assertIn("provenance", artifact)
        self.assertEqual(artifact["provenance"]["build_system"], "project-controlled")

    def test_component_inventory(self):
        payload = component_inventory("openbsd-amd64-clang", "2026.04.0")
        self.assertEqual(payload["toolchain_version"], "2026.04.0")
        self.assertIn("components", payload)
        self.assertTrue(payload["components"])

    def test_toolchain_plan_windows_uses_otvm_validation(self):
        payload = toolchain_plan("windows-amd64-msys2-clang64")
        validation_ids = [step["id"] for step in payload["validation"]]
        self.assertIn("otvm-smoke", validation_ids)
        self.assertIn("gui-smoke", validation_ids)
        self.assertIn("gorm-build", validation_ids)
        self.assertIn("gorm-run", validation_ids)

    def test_linux_build_script_contains_pinned_components(self):
        script = linux_build_script(
            "linux-amd64-clang",
            "/tmp/install",
            "/tmp/sources",
            "/tmp/build",
        )
        self.assertIn("swift-corelibs-libdispatch", script)
        self.assertIn("libs-corebase", script)
        self.assertIn("checkout --detach", script)
        self.assertIn('ln -sfn "$PREFIX/include/objc"', script)
        self.assertIn('export CC=clang', script)
        self.assertIn('"${MAKE:-make}" install', script)

    def test_openbsd_build_script_contains_openbsd_specific_settings(self):
        script = openbsd_build_script(
            "openbsd-amd64-clang",
            "/tmp/install",
            "/tmp/sources",
            "/tmp/build",
        )
        self.assertIn('HOST_OS="openbsd"', script)
        self.assertIn('AUTOCONF_VERSION=${AUTOCONF_VERSION:-2.72}', script)
        self.assertIn('"${MAKE:-make}" install', script)

    def test_msys2_assembly_script_contains_pacman_install_steps(self):
        script = msys2_assembly_script("C:\\managed", "C:\\cache")
        self.assertIn("msys2-installer/releases/latest/download/msys2-x86_64-latest.exe", script)
        self.assertIn("Invoke-WebRequest", script)
        self.assertIn("[string]$MsysRoot = ''", script)
        self.assertIn("$MsysRoot = $Prefix", script)
        self.assertIn("$installingIntoManagedRoot", script)
        self.assertIn("$ProgressPreference = 'SilentlyContinue'", script)
        self.assertIn("pacman -Syuu", script)
        self.assertIn("pacman -S --noconfirm --needed make", script)
        self.assertIn("pacman -Qkk", script)
        self.assertIn("MSYS2 local package database integrity check failed.", script)
        self.assertIn("mingw-w64-clang-x86_64-clang", script)
        self.assertIn("--overwrite /clang64/include/Block.h", script)
        self.assertIn("mingw-w64-clang-x86_64-libdispatch", script)
        self.assertIn("mingw-w64-clang-x86_64-cairo", script)
        self.assertIn("$msysRootDirs = @('usr','etc','var')", script)
        self.assertIn("$clangPrefix = Join-Path $Prefix 'clang64'", script)
        self.assertNotIn("if (-not $installingIntoManagedRoot)", script)
        self.assertIn('& $bash -lc "true"', script)
        self.assertNotIn('\\"true\\"', script)
        self.assertIn("usr\\bin", script)
        self.assertIn("sha256sum.exe", script)
        self.assertIn("Get-ChildItem -Path (Join-Path $MsysRoot 'usr\\bin') -File", script)
        self.assertIn("No MSYS2 usr\\bin executable/DLL runtime files", script)
        self.assertIn("Copy-Item -Force $runtimeFile.FullName", script)
        self.assertIn("clang64\\share\\GNUstep\\Makefiles", script)
        self.assertIn("GNUstep.bat", script)
        self.assertIn("GNUstep.ps1", script)
        self.assertIn("MSYS2 managed toolchain assembly completed", script)

    def test_msvc_status_is_explicitly_not_ready(self):
        payload = msvc_status()
        self.assertFalse(payload["publish"])
        self.assertEqual(payload["status"], "deferred_for_v1")
        self.assertTrue(payload["blocking_areas"])

    def test_write_release_manifest(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output = Path(tempdir) / "release-manifest.json"
            write_release_manifest("0.1.0", "https://example.invalid/releases", output)
            self.assertTrue(output.exists())

    def test_assemble_linux_toolchain_artifact(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            original_exists = Path.exists
            original_copy2 = __import__("shutil").copy2
            runtime_binary = temp / "gnustep"
            runtime_binary.write_text("binary")
            makefiles = temp / "Makefiles"
            (makefiles / "GNUstep.sh").parent.mkdir(parents=True)
            (makefiles / "GNUstep.sh").write_text("makefiles")
            system_headers = temp / "system-headers" / "Foundation"
            system_headers.mkdir(parents=True)
            (system_headers / "Foundation.h").write_text("header")
            user_headers = temp / "user-headers" / "XCTest"
            user_headers.mkdir(parents=True)
            (user_headers / "XCTest.h").write_text("user-header")
            objc_headers = temp / "objc" 
            objc_headers.mkdir()
            (objc_headers / "objc.h").write_text("objc")
            system_tools = temp / "system-tools"
            system_tools.mkdir()
            (system_tools / "gnustep-config").write_text("tool")
            user_tools = temp / "user-tools"
            user_tools.mkdir()
            (user_tools / "xctest").write_text("user-tool")
            clang_binary = temp / "toolchain-bin" / "clang"
            clang_binary.parent.mkdir(parents=True)
            clang_binary.write_text("clang-binary")
            clang_resource_dir = temp / "toolchain-lib" / "clang" / "19"
            clang_resource_dir.mkdir(parents=True)
            (clang_resource_dir / "README.txt").write_text("resource")
            gcc_runtime_dir = temp / "gcc-runtime" / "14"
            gcc_runtime_dir.mkdir(parents=True)
            for name in ("crtbeginS.o", "crtendS.o", "libgcc.a", "libgcc_s.so"):
                (gcc_runtime_dir / name).write_text(name)
            system_lib = temp / "system-lib"
            (system_lib / "lib" / "x86_64-linux-gnu").mkdir(parents=True)
            (system_lib / "lib64").mkdir(parents=True)
            (system_lib / "usr" / "lib" / "x86_64-linux-gnu").mkdir(parents=True)
            for relative in (
                "lib/x86_64-linux-gnu/Scrt1.o",
                "lib/x86_64-linux-gnu/crti.o",
                "lib/x86_64-linux-gnu/crtn.o",
                "lib/x86_64-linux-gnu/libc.so.6",
                "lib/x86_64-linux-gnu/libgcc_s.so.1",
                "lib64/ld-linux-x86-64.so.2",
                "usr/lib/x86_64-linux-gnu/libc.so",
                "usr/lib/x86_64-linux-gnu/libc_nonshared.a",
                "usr/lib/x86_64-linux-gnu/libpthread.so",
                "usr/lib/x86_64-linux-gnu/libpthread_nonshared.a",
                "usr/lib/x86_64-linux-gnu/libdl.so",
                "usr/lib/x86_64-linux-gnu/libm.so",
                "usr/lib/x86_64-linux-gnu/librt.so",
            ):
                target = system_lib / relative
                target.write_text(relative)
            dep = temp / "libgnustep-base.so.1.31"
            dep.write_text("dep")
            clang_dep = temp / "libclang-cpp.so.19.1"
            clang_dep.write_text("clang-dep")

            def mocked_exists(path: Path) -> bool:
                if path.as_posix() in {
                    "/lib/x86_64-linux-gnu/Scrt1.o",
                    "/lib/x86_64-linux-gnu/crti.o",
                    "/lib/x86_64-linux-gnu/crtn.o",
                    "/lib/x86_64-linux-gnu/libc.so.6",
                    "/lib/x86_64-linux-gnu/libgcc_s.so.1",
                    "/lib64/ld-linux-x86-64.so.2",
                    "/usr/lib/x86_64-linux-gnu/libc.so",
                    "/usr/lib/x86_64-linux-gnu/libc_nonshared.a",
                    "/usr/lib/x86_64-linux-gnu/libpthread.so",
                    "/usr/lib/x86_64-linux-gnu/libpthread_nonshared.a",
                    "/usr/lib/x86_64-linux-gnu/libdl.so",
                    "/usr/lib/x86_64-linux-gnu/libm.so",
                    "/usr/lib/x86_64-linux-gnu/librt.so",
                }:
                    return True
                return original_exists(path)

            def mocked_copy2(src, dst, *args, **kwargs):
                source = str(src)
                if source.startswith(("/lib/", "/usr/lib/")):
                    if source.startswith("/usr/lib/x86_64-linux-gnu/"):
                        remapped = system_lib / "usr" / "lib" / "x86_64-linux-gnu" / Path(source).name
                    elif source.startswith("/lib/x86_64-linux-gnu/"):
                        remapped = system_lib / "lib" / "x86_64-linux-gnu" / Path(source).name
                    elif source.startswith("/lib64/"):
                        remapped = system_lib / "lib64" / Path(source).name
                    else:
                        remapped = Path(source)
                    Path(dst).write_bytes(remapped.read_bytes())
                    return str(dst)
                return original_copy2(src, dst, *args, **kwargs)

            with patch("gnustep_cli_shared.build_infra._linux_clang_binary", return_value=clang_binary), patch(
                "gnustep_cli_shared.build_infra._linux_clang_resource_dir", return_value=clang_resource_dir
            ), patch(
                "gnustep_cli_shared.build_infra._linux_gcc_runtime_dir", return_value=gcc_runtime_dir
            ), patch(
                "gnustep_cli_shared.build_infra._linux_shared_library_dependencies",
                side_effect=lambda path: [dep] if Path(path) == runtime_binary else [clang_dep],
            ), patch(
                "gnustep_cli_shared.build_infra.Path.exists",
                new=mocked_exists,
            ), patch(
                "gnustep_cli_shared.build_infra.shutil.copy2",
                side_effect=mocked_copy2,
            ):
                payload = assemble_linux_toolchain_artifact(
                    temp / "assembled",
                    runtime_binary=runtime_binary,
                    makefiles_dir=makefiles,
                    system_headers_dir=temp / "system-headers",
                    user_headers_dir=temp / "user-headers",
                    system_tools_dir=system_tools,
                    user_tools_dir=user_tools,
                    objc_headers_dir=objc_headers,
                )
            self.assertTrue(payload["ok"])
            self.assertFalse(payload["source_policy"]["production_eligible"])
            self.assertTrue(payload["host_origin_audit"]["ok"])
            assembled = Path(payload["output_root"])
            self.assertTrue((assembled / "source-lock.json").exists())
            self.assertTrue((assembled / "component-inventory.json").exists())
            self.assertTrue((assembled / "toolchain-manifest.json").exists())
            self.assertTrue((assembled / "System" / "Library" / "Makefiles" / "GNUstep.sh").exists())
            self.assertTrue((assembled / "System" / "Library" / "Headers" / "Foundation" / "Foundation.h").exists())
            self.assertTrue((assembled / "Library" / "Headers" / "XCTest" / "XCTest.h").exists())
            self.assertTrue((assembled / "include" / "objc" / "objc.h").exists())
            self.assertTrue((assembled / "System" / "Tools" / "gnustep-config").exists())
            self.assertTrue((assembled / "System" / "Tools" / "dpkg-architecture").exists())
            self.assertTrue((assembled / "System" / "Tools" / "clang").exists())
            self.assertTrue((assembled / "System" / "Tools" / "clang++").exists())
            self.assertTrue((assembled / "System" / "Tools" / "cc").exists())
            self.assertTrue((assembled / "System" / "LLVM" / "bin" / "clang").exists())
            self.assertTrue((assembled / "System" / "LLVM" / "bin" / "clang++").is_symlink())
            self.assertTrue((assembled / "System" / "LLVM" / "lib" / "clang" / "19" / "README.txt").exists())
            self.assertTrue((assembled / "System" / "Sysroot" / "usr" / "lib" / "gcc" / "x86_64-linux-gnu" / "14" / "crtbeginS.o").exists())
            self.assertTrue((assembled / "System" / "Sysroot" / "lib" / "x86_64-linux-gnu" / "Scrt1.o").exists())
            self.assertTrue((assembled / "System" / "Sysroot" / "usr" / "lib" / "x86_64-linux-gnu" / "libc.so").exists())
            self.assertTrue((assembled / "Tools" / "xctest").exists())
            self.assertTrue((assembled / "System" / "Library" / "Libraries" / "libgnustep-base.so.1.31").exists())
            self.assertTrue((assembled / "System" / "Library" / "Libraries" / "libclang-cpp.so.19.1").exists())
            self.assertIn(
                "DEB_HOST_MULTIARCH",
                (assembled / "System" / "Tools" / "dpkg-architecture").read_text(),
            )
            self.assertIn(
                "../LLVM/bin/clang",
                (assembled / "System" / "Tools" / "clang").read_text(),
            )
            self.assertIn(
                '--sysroot="$SYSROOT" -B"$GCC_RUNTIME_DIR" -L"$GCC_RUNTIME_DIR"',
                (assembled / "System" / "Tools" / "clang").read_text(),
            )

    def test_stage_release_assets(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            cli_binary = temp / "gnustep"
            cli_binary.write_text("binary")
            cli_bundle = temp / "cli-bundle"
            bundle_full_cli(cli_binary, cli_bundle, repo_root=ROOT)
            toolchain_dir = temp / "toolchain"
            toolchain_dir.mkdir()
            (toolchain_dir / "README.txt").write_text("toolchain")
            payload = stage_release_assets(
                "0.1.0",
                temp / "dist",
                "https://github.com/danjboyd/gnustep-cli/releases",
                cli_inputs={"linux-amd64-clang": cli_bundle},
                toolchain_inputs={"linux-amd64-clang": toolchain_dir},
            )
            self.assertTrue(payload["ok"])
            self.assertEqual(len(payload["artifacts"]), 2)
            release_dir = Path(payload["release_dir"])
            self.assertTrue((release_dir / "release-manifest.json").exists())
            self.assertTrue((release_dir / "SHA256SUMS").exists())
            self.assertTrue((release_dir / "release-provenance.json").exists())
            self.assertIn("release-provenance.json", (release_dir / "SHA256SUMS").read_text())
            self.assertTrue(release_trust_gate(release_dir, require_signatures=False)["ok"])
            self.assertFalse(release_trust_gate(release_dir, require_signatures=True)["ok"])
            filenames = {artifact["filename"] for artifact in payload["artifacts"]}
            self.assertIn("gnustep-cli-linux-amd64-clang-0.1.0.tar.gz", filenames)
            self.assertIn("gnustep-toolchain-linux-amd64-clang-0.1.0.tar.gz", filenames)
            toolchain_artifact = next(artifact for artifact in payload["artifacts"] if artifact["kind"] == "toolchain")
            self.assertTrue(all(artifact["published"] for artifact in payload["artifacts"]))
            self.assertIn("metadata", toolchain_artifact)
            self.assertIsNone(toolchain_artifact["metadata"]["lock_file"])

            windows_cli = temp / "windows-cli"
            (windows_cli / "bin").mkdir(parents=True)
            (windows_cli / "bin" / "gnustep.exe").write_text("exe")
            windows_payload = stage_release_assets(
                "0.1.0",
                temp / "windows-dist",
                "https://github.com/danjboyd/gnustep-cli/releases",
                cli_inputs={"windows-amd64-msys2-clang64": windows_cli},
            )
            import zipfile
            windows_release_dir = Path(windows_payload["release_dir"])
            with zipfile.ZipFile(windows_release_dir / "gnustep-cli-windows-amd64-msys2-clang64-0.1.0.zip") as archive:
                names = archive.namelist()
            self.assertIn("gnustep-cli-windows-amd64-msys2-clang64-0.1.0/bin/gnustep.exe", names)
            self.assertFalse(any("\\" in name for name in names))

    def test_stage_release_assets_copies_archive_inputs_without_wrapping(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            archive_root = temp / "archive-root"
            (archive_root / "bin").mkdir(parents=True)
            (archive_root / "bin" / "gnustep").write_text("binary")
            source_archive = temp / "prebuilt-cli.tar.gz"
            with tarfile.open(source_archive, "w:gz") as archive:
                archive.add(archive_root, arcname="prebuilt-cli")

            payload = stage_release_assets(
                "0.1.0-rc1",
                temp / "dist",
                "https://github.com/danjboyd/gnustep-cli/releases",
                cli_inputs={"linux-amd64-clang": source_archive},
            )
            release_dir = Path(payload["release_dir"])
            staged_archive = release_dir / "gnustep-cli-linux-amd64-clang-0.1.0-rc1.tar.gz"
            with tarfile.open(staged_archive, "r:gz") as archive:
                names = archive.getnames()
            self.assertIn("prebuilt-cli/bin/gnustep", names)
            self.assertNotIn("prebuilt-cli.tar.gz", "\n".join(names))

    def test_stage_release_assets_can_reuse_immutable_toolchain_artifact(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            cli_binary = temp / "gnustep"
            cli_binary.write_text("binary")
            cli_bundle = temp / "cli-bundle"
            bundle_full_cli(cli_binary, cli_bundle, repo_root=ROOT)
            reused_toolchain = {
                "id": "toolchain-linux-amd64-clang",
                "kind": "toolchain",
                "version": "2026.04.0",
                "os": "linux",
                "arch": "amd64",
                "compiler_family": "clang",
                "toolchain_flavor": "clang",
                "objc_runtime": "libobjc2",
                "objc_abi": "modern",
                "required_features": ["blocks"],
                "format": "tar.gz",
                "url": "https://github.com/example/old/gnustep-toolchain-linux-amd64-clang-2026.04.0.tar.gz",
                "sha256": "a" * 64,
                "integrity": {"sha256": "a" * 64},
                "size": 123456,
            }
            payload = stage_release_assets(
                "0.1.1",
                temp / "dist",
                "https://github.com/danjboyd/gnustep-cli/releases",
                cli_inputs={"linux-amd64-clang": cli_bundle},
                reused_toolchain_artifacts={"linux-amd64-clang": reused_toolchain},
            )
            self.assertTrue(payload["ok"])
            release_dir = Path(payload["release_dir"])
            manifest = json.loads((release_dir / "release-manifest.json").read_text())
            artifacts = manifest["releases"][0]["artifacts"]
            self.assertEqual(len(artifacts), 2)
            cli_artifact = next(artifact for artifact in artifacts if artifact["kind"] == "cli")
            toolchain_artifact = next(artifact for artifact in artifacts if artifact["kind"] == "toolchain")
            self.assertTrue(toolchain_artifact["reused"])
            self.assertNotIn("filename", toolchain_artifact)
            self.assertEqual(cli_artifact["requires_toolchain"]["artifact_id"], "toolchain-linux-amd64-clang")
            self.assertTrue(cli_artifact["requires_toolchain"]["reused"])
            verification = verify_release_directory(release_dir)
            self.assertTrue(verification["ok"])
            reused_result = next(result for result in verification["results"] if result.get("reused"))
            self.assertTrue(reused_result["immutable_reference_ok"])
            self.assertTrue(release_trust_gate(release_dir, require_signatures=False)["ok"])

    def test_reusable_artifact_reference_rejects_ambiguous_or_mutable_reference(self):
        artifact = {
            "id": "toolchain-linux-amd64-clang",
            "kind": "toolchain",
            "version": "2026.04.0",
            "os": "linux",
            "arch": "amd64",
            "url": "https://example.invalid/toolchain.tar.gz",
            "sha256": "TBD",
            "size": 10,
        }
        with self.assertRaises(ValueError):
            reusable_artifact_reference(artifact, expected_kind="toolchain", expected_target_id="linux-amd64-clang")

    def test_session_build_box_plan_covers_warm_builder_iteration(self):
        payload = session_build_box_plan(targets=["linux-amd64-clang", "windows-amd64-msys2-clang64"], ttl_hours=6)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["channel"], "dogfood")
        self.assertEqual(payload["ttl_hours"], 6)
        builder_by_target = {builder["target_id"]: builder for builder in payload["builders"]}
        self.assertEqual(builder_by_target["windows-amd64-msys2-clang64"]["otvm_profile"], "windows-2022")
        self.assertEqual(builder_by_target["windows-amd64-msys2-clang64"]["artifact"]["toolchain_layer"], "reuse-installed-compatible")
        step_ids = [step["id"] for step in payload["steps"]]
        self.assertIn("sync-source", step_ids)
        self.assertIn("publish-dogfood-manifest", step_ids)

    def test_dogfood_snapshot_version_orders_multiple_same_day_builds(self):
        first = dogfood_snapshot_version(
            "0.1.0",
            source_revision="abcdef1234567890",
            timestamp="2026-04-22T10:00:00Z",
            sequence=0,
        )
        second = dogfood_snapshot_version(
            "0.1.0",
            source_revision="abcdef1234567890",
            timestamp="2026-04-22T10:05:00Z",
            sequence=0,
        )
        third = dogfood_snapshot_version(
            "0.1.0",
            source_revision="abcdef1234567890",
            timestamp="2026-04-22T10:05:00Z",
            sequence=1,
        )
        self.assertLess(first, second)
        self.assertLess(second, third)
        self.assertEqual(first, "0.1.0-dogfood.20260422T100000Z.gabcdef123456.0")

    def test_dogfood_snapshot_manifest_reuses_toolchain_layer(self):
        cli = {
            "id": "cli-linux-amd64-clang",
            "kind": "cli",
            "version": "placeholder",
            "os": "linux",
            "arch": "amd64",
            "compiler_family": "clang",
            "toolchain_flavor": "clang",
            "objc_runtime": "libobjc2",
            "objc_abi": "modern",
            "format": "tar.gz",
            "url": "https://example.invalid/cli.tar.gz",
            "sha256": "c" * 64,
            "size": 11,
        }
        toolchain = {
            "id": "toolchain-linux-amd64-clang",
            "kind": "toolchain",
            "version": "2026.04.0",
            "os": "linux",
            "arch": "amd64",
            "compiler_family": "clang",
            "toolchain_flavor": "clang",
            "objc_runtime": "libobjc2",
            "objc_abi": "modern",
            "format": "tar.gz",
            "url": "https://example.invalid/toolchain.tar.gz",
            "sha256": "d" * 64,
            "size": 1000,
        }
        manifest = dogfood_snapshot_manifest(
            "0.1.0",
            "https://example.invalid/releases",
            source_revision="abcdef",
            timestamp="2026-04-22T11:00:00Z",
            cli_artifacts=[cli],
            reused_toolchain_artifacts=[toolchain],
        )
        release = manifest["releases"][0]
        self.assertEqual(manifest["channel"], "dogfood")
        self.assertIn("dogfood.20260422T110000Z", release["version"])
        cli_record = next(artifact for artifact in release["artifacts"] if artifact["kind"] == "cli")
        toolchain_record = next(artifact for artifact in release["artifacts"] if artifact["kind"] == "toolchain")
        self.assertEqual(cli_record["requires_toolchain"]["artifact_id"], "toolchain-linux-amd64-clang")
        self.assertTrue(toolchain_record["reused"])
        self.assertEqual(manifest["retention"]["keep_latest"], 12)

    def test_delta_artifact_record_uses_project_delta_envelope(self):
        source = {
            "id": "toolchain-linux-amd64-clang",
            "kind": "toolchain",
            "version": "2026.04.0",
            "os": "linux",
            "arch": "amd64",
            "compiler_family": "clang",
            "toolchain_flavor": "clang",
            "objc_runtime": "libobjc2",
            "objc_abi": "modern",
            "required_features": ["blocks"],
            "sha256": "a" * 64,
        }
        target = dict(source)
        target["version"] = "2026.04.1"
        target["sha256"] = "b" * 64
        target["url"] = "https://example.invalid/full.tar.gz"
        target["size"] = 1000
        delta = delta_artifact_record(
            delta_id="delta-toolchain-linux-amd64-clang-2026040-to-2026041",
            from_artifact=source,
            to_artifact=target,
            url="https://example.invalid/delta.bin",
            sha256="c" * 64,
            size=12,
        )
        self.assertEqual(delta["kind"], "toolchain-delta")
        self.assertEqual(delta["delta_format"], "gnustep-delta-v1")
        self.assertEqual(delta["from_sha256"], "a" * 64)
        self.assertEqual(delta["to_sha256"], "b" * 64)
        self.assertFalse(validate_delta_artifact_record(delta))

    def test_delta_artifact_record_rejects_target_mismatch(self):
        source = {"id": "toolchain-linux-amd64-clang", "kind": "toolchain", "sha256": "a" * 64}
        target = {"id": "toolchain-windows-amd64-msys2-clang64", "kind": "toolchain", "sha256": "b" * 64}
        with self.assertRaises(ValueError):
            delta_artifact_record(
                delta_id="bad-delta",
                from_artifact=source,
                to_artifact=target,
                url="https://example.invalid/delta.bin",
                sha256="c" * 64,
                size=12,
            )

    def test_windows_msys2_inventory_compare_detects_component_update(self):
        old = windows_msys2_component_inventory(
            toolchain_version="2026.04.0",
            packages=[
                {"name": "mingw-w64-clang-x86_64-gnustep-base", "version": "1", "package_sha256": "a", "installed_files_sha256": "aa", "layer": "base"},
                {"name": "make", "version": "1", "package_sha256": "b", "installed_files_sha256": "bb", "layer": "base"},
            ],
        )
        new = windows_msys2_component_inventory(
            toolchain_version="2026.04.1",
            packages=[
                {"name": "mingw-w64-clang-x86_64-gnustep-base", "version": "2", "package_sha256": "c", "installed_files_sha256": "cc", "layer": "base"},
                {"name": "make", "version": "1", "package_sha256": "b", "installed_files_sha256": "bb", "layer": "base"},
            ],
        )
        comparison = compare_windows_msys2_inventories(old, new)
        self.assertEqual(comparison["action"], "component_update")
        self.assertTrue(comparison["component_replacement_sufficient"])
        self.assertEqual(comparison["changed_packages"][0]["name"], "mingw-w64-clang-x86_64-gnustep-base")


    def test_release_metadata_signing_and_trust_gate(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            cli_binary = temp / "gnustep"
            cli_binary.write_text("binary")
            cli_bundle = temp / "cli-bundle"
            bundle_full_cli(cli_binary, cli_bundle, repo_root=ROOT)
            payload = stage_release_assets(
                "0.1.0",
                temp / "dist",
                "https://example.invalid/releases",
                cli_inputs={"linux-amd64-clang": cli_bundle},
            )
            release_dir = Path(payload["release_dir"])
            key = temp / "release-signing-key.pem"
            import subprocess
            subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(key)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            signed = sign_release_metadata(release_dir, key)
            self.assertTrue(signed["ok"])
            self.assertTrue((release_dir / "release-manifest.json.sig").exists())
            self.assertTrue((release_dir / "release-provenance.json.sig").exists())
            self.assertTrue(release_trust_gate(release_dir)["ok"])
            self.assertTrue(release_trust_gate(release_dir, trusted_public_key_path=release_dir / "release-signing-public.pem")["ok"])
            other_key = temp / "other-release-signing-key.pem"
            other_pub = temp / "other-release-signing-public.pem"
            subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(other_key)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["openssl", "pkey", "-in", str(other_key), "-pubout", "-out", str(other_pub)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertFalse(release_trust_gate(release_dir, trusted_public_key_path=other_pub)["ok"])
            (release_dir / "release-provenance.json").write_text("{}\n")
            self.assertFalse(release_trust_gate(release_dir)["ok"])


    def test_release_trust_gate_rejects_expired_metadata_and_revoked_artifacts(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            release_dir = temp / "release"
            release_dir.mkdir()
            artifact = release_dir / "artifact.tar.gz"
            artifact.write_text("artifact")
            manifest = {
                "schema_version": 1,
                "metadata_version": 1,
                "generated_at": "2026-01-01T00:00:00Z",
                "expires_at": "2000-01-01T00:00:00Z",
                "trust": {"root_version": 1, "signature_policy": "single-role-v1", "revoked_artifacts": ["cli-linux"]},
                "releases": [{"version": "0.1.0", "status": "active", "artifacts": [{"id": "cli-linux", "kind": "cli", "filename": artifact.name, "sha256": "placeholder"}]}],
            }
            (release_dir / "release-manifest.json").write_text(json.dumps(manifest) + "\n")
            (release_dir / "SHA256SUMS").write_text("")
            write_release_provenance(release_dir)
            gate = release_trust_gate(release_dir, require_signatures=False)
            checks = {check["id"]: check for check in gate["checks"]}
            self.assertFalse(gate["ok"])
            self.assertFalse(checks["metadata-not-expired"]["ok"])
            self.assertFalse(checks["revoked-artifacts-absent"]["ok"])

    def test_published_url_qualification_plan_covers_tier1_profiles(self):
        payload = published_url_qualification_plan("https://example.invalid/releases/v0.1.0", config_path="~/libvirt.toml")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["release_manifest_url"], "https://example.invalid/releases/v0.1.0/release-manifest.json")
        targets = {target["id"]: target for target in payload["targets"]}
        self.assertIn("debian-public-bootstrap-full-cli-package", targets)
        self.assertIn("openbsd-public-native-package-smoke", targets)
        self.assertIn("fedora-public-gcc-interop-smoke", targets)
        self.assertIn("arch-public-gcc-interop-smoke", targets)
        self.assertIn("windows-public-bootstrap-runtime-package", targets)
        self.assertEqual(targets["windows-public-bootstrap-runtime-package"]["profile"], "windows-2022")
        self.assertEqual(payload["cleanup_policy"], "destroy-on-exit")

    def test_published_url_qualification_plan_accepts_direct_manifest_url(self):
        payload = published_url_qualification_plan("https://example.invalid/releases/download/v0.1.0/release-manifest.json")
        self.assertEqual(
            payload["release_manifest_url"],
            "https://example.invalid/releases/download/v0.1.0/release-manifest.json",
        )

    def test_published_url_qualification_plan_converts_github_tag_url_to_asset_url(self):
        payload = published_url_qualification_plan("https://github.com/gnustep/tools/releases/tag/v0.1.0")
        self.assertEqual(
            payload["release_manifest_url"],
            "https://github.com/gnustep/tools/releases/download/v0.1.0/release-manifest.json",
        )

    def test_controlled_release_gate_combines_release_and_package_trust(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            cli_binary = temp / "gnustep"
            cli_binary.write_text("binary")
            cli_bundle = temp / "cli-bundle"
            bundle_full_cli(cli_binary, cli_bundle, repo_root=ROOT)
            payload = stage_release_assets(
                "0.1.0",
                temp / "dist",
                "https://example.invalid/releases",
                cli_inputs={"linux-amd64-clang": cli_bundle},
            )
            release_dir = Path(payload["release_dir"])
            release_key = temp / "release-key.pem"
            subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(release_key)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            self.assertTrue(sign_release_metadata(release_dir, release_key)["ok"])
            package_index = temp / "package-index.json"
            package_index.write_text(json.dumps({
                "schema_version": 1,
                "channel": "stable",
                "generated_at": "TBD",
                "metadata_version": 1,
                "expires_at": "TBD",
                "trust": {"root_version": 1, "signature_policy": "single-role-v1", "signatures": [], "revoked_packages": []},
                "packages": [],
            }) + "\n")
            from gnustep_cli_shared.package_repository import write_package_index_provenance
            write_package_index_provenance(package_index)
            gate = controlled_release_gate(
                release_dir,
                package_index_path=package_index,
                release_trust_root=release_dir / "release-signing-public.pem",
                allow_unsigned_package_index=True,
            )
            self.assertTrue(gate["ok"])
            check_ids = {check["id"] for check in gate["checks"]}
            self.assertIn("release-trust-gate", check_ids)
            self.assertIn("package-index-trust-gate", check_ids)


    def test_controlled_release_gate_can_include_tools_xctest_gate(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            cli_binary = temp / "gnustep"
            cli_binary.write_text("binary")
            cli_bundle = temp / "cli-bundle"
            bundle_full_cli(cli_binary, cli_bundle, repo_root=ROOT)
            payload = stage_release_assets(
                "0.1.0",
                temp / "dist",
                "https://example.invalid/releases",
                cli_inputs={"linux-amd64-clang": cli_bundle},
            )
            release_dir = Path(payload["release_dir"])
            release_key = temp / "release-key.pem"
            subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(release_key)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            self.assertTrue(sign_release_metadata(release_dir, release_key)["ok"])
            packages_dir = temp / "packages"
            package_dir = packages_dir / "org.gnustep.tools-xctest"
            package_dir.mkdir(parents=True)
            artifact_id = "tools-xctest-linux-amd64-clang"
            package_dir.joinpath("package.json").write_text(json.dumps({
                "schema_version": 1,
                "id": "org.gnustep.tools-xctest",
                "name": "tools-xctest",
                "version": "1.0.0",
                "kind": "cli-tool",
                "source": {"type": "git", "url": "https://github.com/gnustep/tools-xctest.git", "sha256": "a" * 64},
                "artifacts": [{"id": artifact_id, "os": "linux", "arch": "amd64", "compiler_family": "clang", "toolchain_flavor": "clang", "url": "https://example.invalid/tools-xctest.tar.gz", "sha256": "b" * 64, "publish": True, "status": "validated"}],
                "patches": [{"id": "add-apple-style-xctest-cli-filters", "path": "patches/add-apple-style-xctest-cli-filters.patch", "sha256": "c" * 64, "applies_to": [artifact_id]}],
            }) + "\n")
            evidence_dir = temp / "evidence"
            evidence_dir.mkdir()
            (evidence_dir / f"{artifact_id}.json").write_text(json.dumps({"ok": True, "package_id": "org.gnustep.tools-xctest", "artifact_id": artifact_id}) + "\n")
            gate = controlled_release_gate(
                release_dir,
                release_trust_root=release_dir / "release-signing-public.pem",
                tools_xctest_packages_dir=packages_dir,
                tools_xctest_evidence_dir=evidence_dir,
            )
            checks = {check["id"]: check for check in gate["checks"]}
            self.assertTrue(gate["ok"])
            self.assertTrue(checks["tools-xctest-release-gate"]["ok"])

    def test_controlled_release_gate_requires_explicit_trust_root(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            cli_binary = temp / "gnustep"
            cli_binary.write_text("binary")
            cli_bundle = temp / "cli-bundle"
            bundle_full_cli(cli_binary, cli_bundle, repo_root=ROOT)
            payload = stage_release_assets(
                "0.1.0",
                temp / "dist",
                "https://example.invalid/releases",
                cli_inputs={"linux-amd64-clang": cli_bundle},
            )
            release_dir = Path(payload["release_dir"])
            key = temp / "release-key.pem"
            subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(key)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            self.assertTrue(sign_release_metadata(release_dir, key)["ok"])
            gate = controlled_release_gate(release_dir)
            checks = {check["id"]: check for check in gate["checks"]}
            self.assertFalse(gate["ok"])
            self.assertFalse(checks["release-trust-root-present"]["ok"])

    def test_controlled_release_gate_requires_explicit_package_index_trust_root(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            cli_binary = temp / "gnustep"
            cli_binary.write_text("binary")
            cli_bundle = temp / "cli-bundle"
            bundle_full_cli(cli_binary, cli_bundle, repo_root=ROOT)
            payload = stage_release_assets(
                "0.1.0",
                temp / "dist",
                "https://example.invalid/releases",
                cli_inputs={"linux-amd64-clang": cli_bundle},
            )
            release_dir = Path(payload["release_dir"])
            release_key = temp / "release-key.pem"
            package_key = temp / "package-index-key.pem"
            subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(release_key)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(package_key)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            self.assertTrue(sign_release_metadata(release_dir, release_key)["ok"])
            package_index = temp / "package-index.json"
            package_index.write_text(json.dumps({
                "schema_version": 1,
                "channel": "stable",
                "generated_at": "TBD",
                "metadata_version": 1,
                "expires_at": "TBD",
                "trust": {"root_version": 1, "signature_policy": "single-role-v1", "signatures": [], "revoked_packages": []},
                "packages": [],
            }) + "\n")
            from gnustep_cli_shared.package_repository import sign_package_index_metadata
            self.assertTrue(sign_package_index_metadata(package_index, package_key)["ok"])
            gate = controlled_release_gate(
                release_dir,
                package_index_path=package_index,
                release_trust_root=release_dir / "release-signing-public.pem",
            )
            checks = {check["id"]: check for check in gate["checks"]}
            self.assertFalse(gate["ok"])
            self.assertFalse(checks["package-index-trust-root-present"]["ok"])
            self.assertTrue(checks["package-index-trust-gate"]["ok"])

    def test_release_claim_consistency_gate_requires_evidence(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            release_dir = temp / "release"
            release_dir.mkdir()
            (release_dir / "release-manifest.json").write_text(json.dumps({
                "schema_version": 1,
                "releases": [{
                    "version": "0.1.0",
                    "artifacts": [
                        {"id": "cli-linux-amd64-clang"},
                        {"id": "toolchain-linux-amd64-clang"},
                        {"id": "cli-windows-amd64-msys2-clang64"},
                        {"id": "toolchain-windows-amd64-msys2-clang64"},
                    ],
                }],
            }))
            gate = release_claim_consistency_gate(release_dir, require_windows_current_source=False)
            checks = {check["id"]: check for check in gate["checks"]}
            self.assertFalse(gate["ok"])
            self.assertFalse(checks["debian-otvm-smoke"]["ok"])
            for name in [
                "otvm-debian-13-gnome-wayland-smoke.json",
                "otvm-openbsd-7.8-fvwm-smoke.json",
                "otvm-windows-2022-smoke.json",
            ]:
                (release_dir / name).write_text('{"ok": true, "summary": "ok"}')
            gate = release_claim_consistency_gate(release_dir, require_windows_current_source=False)
            self.assertTrue(gate["ok"])


    def test_release_claim_consistency_gate_accepts_evidence_bundle_and_current_source_marker(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            release_dir = temp / "release"
            release_dir.mkdir()
            (release_dir / "release-manifest.json").write_text(json.dumps({
                "schema_version": 1,
                "releases": [{
                    "version": "0.1.0",
                    "artifacts": [
                        {"id": "cli-linux-amd64-clang"},
                        {"id": "toolchain-linux-amd64-clang"},
                        {"id": "cli-windows-amd64-msys2-clang64", "filename": "gnustep-cli-windows.zip"},
                        {"id": "toolchain-windows-amd64-msys2-clang64"},
                    ],
                }],
            }))
            for name in [
                "otvm-debian-13-gnome-wayland-smoke.json",
                "otvm-openbsd-7.8-fvwm-smoke.json",
                "otvm-windows-2022-smoke.json",
            ]:
                (release_dir / name).write_text('{"ok": true, "summary": "ok"}')
            marker = write_windows_current_source_marker(release_dir, source_revision="abc123", builder_identity="test")
            bundle = write_release_evidence_bundle(release_dir)
            gate = release_claim_consistency_gate(release_dir)
            checks = {check["id"]: check for check in gate["checks"]}
            self.assertTrue(marker["ok"])
            self.assertTrue(bundle["ok"])
            self.assertTrue(gate["ok"])
            self.assertTrue(checks["release-evidence-bundle"]["ok"])
            self.assertTrue(checks["windows-current-source-artifact"]["ok"])

    def test_release_claim_consistency_gate_accepts_hosted_evidence_names(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            release_dir = temp / "release"
            evidence_dir = temp / "hosted-evidence"
            release_dir.mkdir()
            evidence_dir.mkdir()
            (release_dir / "release-manifest.json").write_text(json.dumps({
                "schema_version": 1,
                "releases": [{
                    "version": "0.1.0",
                    "artifacts": [
                        {"id": "cli-linux-amd64-clang"},
                        {"id": "toolchain-linux-amd64-clang"},
                        {"id": "cli-windows-amd64-msys2-clang64"},
                        {"id": "toolchain-windows-amd64-msys2-clang64"},
                    ],
                }],
            }))
            for name in [
                "update-all-production-like.json",
                "openbsd-tier1-report.json",
                "windows-tier1-report-patched-gorm.json",
            ]:
                (evidence_dir / name).write_text('{"ok": true, "summary": "hosted evidence ok"}')
            gate = release_claim_consistency_gate(
                release_dir,
                evidence_dir=evidence_dir,
                require_windows_current_source=False,
            )
            checks = {check["id"]: check for check in gate["checks"]}
            self.assertTrue(gate["ok"])
            self.assertIn("update-all-production-like.json", checks["debian-otvm-smoke"]["path"])
            self.assertIn("openbsd-tier1-report.json", checks["openbsd-otvm-smoke"]["path"])
            self.assertIn("windows-tier1-report-patched-gorm.json", checks["windows-otvm-smoke"]["path"])

    def test_release_evidence_bundle_accepts_modern_gate_inputs(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            release_dir = temp / "release"
            release_dir.mkdir()
            smoke_report = temp / "smoke.json"
            smoke_report.write_text(json.dumps(evidence_smoke_report(
                suite_id="tier1-core",
                target_id="windows-amd64-msys2-clang64",
                release_source="dogfood",
                passed_scenario_ids=[
                    "bootstrap-install-usable-cli",
                    "new-cli-project-build-run",
                    "gorm-build-run",
                    "self-update-cli-only",
                ],
            )))
            update_all = temp / "update-all.json"
            update_all.write_text(json.dumps({
                "schema_version": 1,
                "ok": True,
                "summary": "update all --yes passed.",
                "production_like": True,
                "command": "gnustep update all --yes",
                "scopes": {"cli": True, "toolchain": True, "packages": True},
                "release_transition": {"from_version": "old", "to_version": "new"},
                "package_updates": [{"id": "org.gnustep.tools-xctest", "ok": True}],
                "result": {"ok": True},
            }))
            release_root = temp / "release-root.pem"
            package_root = temp / "package-root.pem"
            release_root.write_text("release-root")
            package_root.write_text("package-root")

            bundle = write_release_evidence_bundle(
                release_dir,
                smoke_report_paths=[smoke_report],
                update_all_evidence_path=update_all,
                release_trust_root=release_root,
                package_index_trust_root=package_root,
            )
            self.assertTrue(bundle["ok"])
            self.assertEqual({entry["id"] for entry in bundle["trust_roots"]}, {"release-trust-root", "package-index-trust-root"})
            self.assertIn("update-all-production-like", {entry["id"] for entry in bundle["evidence"]})

    def test_release_key_rotation_drill_rejects_cross_signed_metadata(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            cli_binary = temp / "gnustep"
            cli_binary.write_text("binary")
            cli_bundle = temp / "cli-bundle"
            bundle_full_cli(cli_binary, cli_bundle, repo_root=ROOT)
            payload = stage_release_assets(
                "0.1.0",
                temp / "dist",
                "https://example.invalid/releases",
                cli_inputs={"linux-amd64-clang": cli_bundle},
            )
            drill = release_key_rotation_drill(payload["release_dir"], work_dir=temp / "drill")
            checks = {check["id"]: check for check in drill["checks"]}
            self.assertTrue(drill["ok"])
            self.assertTrue(checks["new-root-rejects-old-signature"]["ok"])
            self.assertTrue(checks["old-root-rejects-new-signature"]["ok"])

    def test_phase12_status_reports_missing_host_backed_smoke(self):
        payload = phase12_production_hardening_status()
        checks = {check["id"]: check for check in payload["checks"]}
        self.assertFalse(payload["ok"])
        self.assertFalse(checks["release-dir-supplied"]["ok"])
        self.assertFalse(checks["host-backed-smoke-evidence"]["ok"])

    def test_phase13_status_requires_update_all_and_metadata_drills(self):
        payload = phase13_update_hardening_status()
        checks = {check["id"]: check for check in payload["checks"]}
        self.assertFalse(payload["ok"])
        self.assertFalse(checks["old-to-new-update-smoke-gate"]["ok"])
        self.assertFalse(checks["update-all-production-like-evidence"]["ok"])
        self.assertFalse(checks["signed-metadata-key-mismatch-drill"]["ok"])

    def test_phase12_and_phase13_status_can_pass_with_complete_evidence(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            cli_binary = temp / "gnustep"
            cli_binary.write_text("binary")
            cli_bundle = temp / "cli-bundle"
            bundle_full_cli(cli_binary, cli_bundle, repo_root=ROOT)
            staged = stage_release_assets(
                "0.1.0",
                temp / "dist",
                "https://example.invalid/releases",
                cli_inputs={"linux-amd64-clang": cli_bundle},
            )
            release_dir = Path(staged["release_dir"])
            release_key = temp / "release-key.pem"
            subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(release_key)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            self.assertTrue(sign_release_metadata(release_dir, release_key)["ok"])
            reports = []
            for target_id in ["windows-amd64-msys2-clang64", "openbsd-amd64-clang"]:
                report_path = temp / f"{target_id}.json"
                report_path.write_text(json.dumps(evidence_smoke_report(
                    suite_id="tier1-core",
                    target_id=target_id,
                    release_source="dogfood",
                    passed_scenario_ids=[
                        "bootstrap-install-usable-cli",
                        "new-cli-project-build-run",
                        "gorm-build-run",
                        "self-update-cli-only",
                    ],
                )))
                reports.append(report_path)
            update_all = temp / "update-all.json"
            update_all.write_text(json.dumps({
                "schema_version": 1,
                "ok": True,
                "summary": "update all --yes passed.",
                "production_like": True,
                "command": "gnustep update all --yes",
                "scopes": {"cli": True, "toolchain": True, "packages": True},
                "release_transition": {"from_version": "0.1.0-old", "to_version": "0.1.0"},
                "package_updates": [{"id": "org.gnustep.tools-xctest", "ok": True}],
                "result": {"ok": True},
            }))

            phase12 = phase12_production_hardening_status(
                release_dir=release_dir,
                release_trust_root=release_dir / "release-signing-public.pem",
                smoke_report_paths=reports,
            )
            phase13 = phase13_update_hardening_status(
                smoke_report_paths=reports,
                update_all_evidence_path=update_all,
                release_dir=release_dir,
            )
            self.assertTrue(phase12["ok"])
            self.assertTrue(phase13["ok"])

    def test_phase13_rejects_incomplete_update_all_evidence(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            update_all = temp / "update-all.json"
            update_all.write_text(json.dumps({"ok": True, "summary": "too weak"}))

            phase13 = phase13_update_hardening_status(update_all_evidence_path=update_all)
            checks = {check["id"]: check for check in phase13["checks"]}
            self.assertFalse(checks["update-all-production-like-evidence"]["ok"])
            failed = {
                check["id"]
                for check in checks["update-all-production-like-evidence"]["payload"]["validation_checks"]
                if not check["ok"]
            }
            self.assertIn("production-like", failed)
            self.assertIn("scope-packages", failed)

    def test_validate_update_all_evidence_command_payload(self):
        with tempfile.TemporaryDirectory() as tempdir:
            evidence = Path(tempdir) / "update-all.json"
            evidence.write_text(json.dumps({
                "schema_version": 1,
                "ok": True,
                "summary": "update all --yes passed.",
                "production_like": True,
                "command": "gnustep update all --yes",
                "scopes": {"cli": True, "toolchain": True, "packages": True},
                "release_transition": {"from_version": "old", "to_version": "new"},
                "package_updates": [{"id": "org.gnustep.tools-xctest", "ok": True}],
                "result": {"ok": True},
            }))
            payload = validate_update_all_evidence(evidence)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["command"], "validate-update-all-evidence")

    def test_build_infra_cli_exits_nonzero_for_failed_gate(self):
        with tempfile.TemporaryDirectory() as tempdir:
            release_dir = Path(tempdir) / "release"
            release_dir.mkdir()
            (release_dir / "release-manifest.json").write_text(json.dumps({
                "schema_version": 1,
                "releases": [{"version": "0.1.0", "artifacts": []}],
            }))
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "internal" / "build_infra.py"), "--json", "release-claim-consistency-gate", "--release-dir", str(release_dir)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 1)
            self.assertFalse(json.loads(proc.stdout)["ok"])

    def test_github_release_plan(self):
        with tempfile.TemporaryDirectory() as tempdir:
            release_dir = Path(tempdir)
            (release_dir / "a.tar.gz").write_text("a")
            (release_dir / "release-manifest.json").write_text("{}")
            payload = github_release_plan("danjboyd/gnustep-cli-new", "0.1.0", release_dir)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["tag"], "v0.1.0")
            self.assertIn("gh", payload["command_line"][0])
            self.assertIn("--repo", payload["command_line"])

    def test_prepare_github_release(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            cli_binary = temp / "gnustep"
            cli_binary.write_text(
                "#!/bin/sh\n"
                "case \"$1\" in\n"
                "  --version) printf '0.1.0-dev\\n' ;;\n"
                "  --help) printf 'gnustep <command> [options] [args]\\n' ;;\n"
                "  *) printf 'gnustep\\n' ;;\n"
                "esac\n"
            )
            cli_binary.chmod(0o755)
            cli_bundle = temp / "cli-bundle"
            bundle_full_cli(cli_binary, cli_bundle, repo_root=ROOT)
            toolchain_dir = temp / "toolchain"
            (toolchain_dir / "System" / "Tools").mkdir(parents=True)
            (toolchain_dir / "System" / "Tools" / "make").write_text("tool")
            write_toolchain_metadata(toolchain_dir, "linux-amd64-clang", "2026.04.0", production_eligible=True)
            with patch("gnustep_cli_shared.setup_planner.build_doctor_payload", return_value=managed_debian_doctor_payload()):
                payload = prepare_github_release(
                    "danjboyd/gnustep-cli-new",
                    "0.1.0",
                    temp / "dist",
                    "https://github.com/danjboyd/gnustep-cli-new/releases",
                    cli_inputs={
                        "linux-amd64-clang": cli_bundle,
                        "linux-ubuntu2404-amd64-clang": cli_bundle,
                    },
                    toolchain_inputs={
                        "linux-amd64-clang": toolchain_dir,
                        "linux-ubuntu2404-amd64-clang": toolchain_dir,
                    },
                    install_root=temp / "qualified",
                    handoff_install_root=temp / "handoff-root",
                )
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["command"], "prepare-github-release")
            self.assertTrue(payload["stage_release"]["ok"])
            self.assertTrue(payload["verify_release"]["ok"])
            self.assertTrue(payload["toolchain_archive_audits"])
            self.assertTrue(all(audit["ok"] for audit in payload["toolchain_archive_audits"]))
            self.assertTrue(payload["qualify_release"]["ok"])
            self.assertTrue(payload["qualify_full_cli_handoff"]["ok"])
            self.assertTrue(payload["otvm_host_validation_plan"]["ok"])
            self.assertTrue(Path(payload["otvm_host_validation_plan_path"]).exists())
            target_profiles = [target["profile"] for target in payload["otvm_host_validation_plan"]["targets"]]
            self.assertIn("debian-13-gnome-wayland", target_profiles)
            self.assertIn("openbsd-7.8-fvwm", target_profiles)
            self.assertIn("windows-2022", target_profiles)
            self.assertEqual(payload["github_release_plan"]["tag"], "v0.1.0")

    def test_toolchain_archive_audit_flags_missing_windows_build_inputs(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Path(tempdir) / "gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0-dev.zip"
            with __import__("zipfile").ZipFile(archive, "w") as zf:
                zf.writestr("gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0-dev/bin/gnustep-config", "tool")
            payload = toolchain_archive_audit(archive, target_id="windows-amd64-msys2-clang64")
            self.assertFalse(payload["ok"])
            failed = {check["id"] for check in payload["checks"] if check["required"] and not check["ok"]}
            self.assertIn("clang", failed)
            self.assertIn("clang64_prefix", failed)
            self.assertIn("bash", failed)
            self.assertIn("make", failed)
            self.assertIn("sha256sum", failed)
            self.assertIn("msys_runtime", failed)
            self.assertIn("common_make", failed)
            self.assertIn("openapp", failed)
            self.assertIn("msys_profile", failed)
            self.assertIn("pacman_local_db", failed)

    def test_toolchain_archive_audit_accepts_complete_windows_layout(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Path(tempdir) / "gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0-dev.zip"
            with __import__("zipfile").ZipFile(archive, "w") as zf:
                root = "gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0-dev"
                zf.writestr(root + "/bin/gnustep-config", "tool")
                zf.writestr(root + "/bin/clang.exe", "clang")
                zf.writestr(root + "/clang64/bin/clang.exe", "clang")
                zf.writestr(root + "/clang64/bin/openapp", "openapp")
                zf.writestr(root + "/usr/bin/bash.exe", "bash")
                zf.writestr(root + "/usr/bin/make.exe", "make")
                zf.writestr(root + "/usr/bin/sha256sum.exe", "sha256sum")
                zf.writestr(root + "/usr/bin/msys-2.0.dll", "runtime")
                zf.writestr(root + "/clang64/share/GNUstep/Makefiles/common.make", "common")
                zf.writestr(root + "/clang64/share/GNUstep/Makefiles/tool.make", "tool")
                zf.writestr(root + "/etc/profile", "profile")
                zf.writestr(root + "/var/lib/pacman/local/mingw-w64-clang-x86_64-gnustep-gui-0/desc", "desc")
                zf.writestr(root + "/GNUstep.bat", "@echo off")
            payload = toolchain_archive_audit(archive, target_id="windows-amd64-msys2-clang64")
            self.assertTrue(payload["ok"])

    def test_toolchain_archive_audit_flags_broken_pacman_local_db_entry(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Path(tempdir) / "gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0-dev.zip"
            with __import__("zipfile").ZipFile(archive, "w") as zf:
                root = "gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0-dev"
                zf.writestr(root + "/bin/gnustep-config", "tool")
                zf.writestr(root + "/bin/clang.exe", "clang")
                zf.writestr(root + "/clang64/bin/clang.exe", "clang")
                zf.writestr(root + "/clang64/bin/openapp", "openapp")
                zf.writestr(root + "/usr/bin/bash.exe", "bash")
                zf.writestr(root + "/usr/bin/make.exe", "make")
                zf.writestr(root + "/usr/bin/sha256sum.exe", "sha256sum")
                zf.writestr(root + "/usr/bin/msys-2.0.dll", "runtime")
                zf.writestr(root + "/clang64/share/GNUstep/Makefiles/common.make", "common")
                zf.writestr(root + "/clang64/share/GNUstep/Makefiles/tool.make", "tool")
                zf.writestr(root + "/etc/profile", "profile")
                zf.writestr(root + "/var/lib/pacman/local/mingw-w64-clang-x86_64-gnustep-gui-0/desc", "desc")
                zf.writestr(root + "/var/lib/pacman/local/mingw-w64-clang-x86_64-tcl-8.6.17-1/files", "files")
            payload = toolchain_archive_audit(archive, target_id="windows-amd64-msys2-clang64")
            self.assertFalse(payload["ok"])
            check_map = {check["id"]: check for check in payload["checks"]}
            self.assertFalse(check_map["pacman_local_db_integrity"]["ok"])
            self.assertIn(
                "mingw-w64-clang-x86_64-tcl-8.6.17-1",
                check_map["pacman_local_db_integrity"]["missing_desc_packages"],
            )


    def test_verify_and_qualify_release(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            cli_binary = temp / "gnustep"
            cli_binary.write_text("binary")
            cli_bundle = temp / "cli-bundle"
            bundle_full_cli(cli_binary, cli_bundle, repo_root=ROOT)
            toolchain_dir = temp / "toolchain"
            toolchain_dir.mkdir()
            (toolchain_dir / "README.txt").write_text("toolchain")
            staged = stage_release_assets(
                "0.1.0",
                temp / "dist",
                "https://github.com/danjboyd/gnustep-cli/releases",
                cli_inputs={"linux-amd64-clang": cli_bundle},
                toolchain_inputs={"linux-amd64-clang": toolchain_dir},
            )
            verification = verify_release_directory(staged["release_dir"])
            self.assertTrue(verification["ok"])
            qualified = qualify_release_install(staged["release_dir"], temp / "qualified")
            self.assertTrue(qualified["ok"])
            install_paths = [Path(item["install_path"]) for item in qualified["installs"]]
            self.assertEqual(len(install_paths), 2)
            for path in install_paths:
                self.assertTrue(path.exists())

    def test_qualify_full_cli_handoff(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            cli_binary = temp / "gnustep"
            cli_binary.write_text(
                "#!/bin/sh\n"
                "case \"$1\" in\n"
                "  --version) printf '0.1.0-dev\\n' ;;\n"
                "  --help) printf 'gnustep <command> [options] [args]\\n' ;;\n"
                "  *) printf 'gnustep\\n' ;;\n"
                "esac\n"
            )
            cli_binary.chmod(0o755)
            cli_bundle = temp / "cli-bundle"
            bundle_full_cli(cli_binary, cli_bundle, repo_root=ROOT)
            toolchain_dir = temp / "toolchain"
            (toolchain_dir / "System" / "Tools").mkdir(parents=True)
            (toolchain_dir / "System" / "Tools" / "make").write_text("tool")
            staged = stage_release_assets(
                "0.1.0",
                temp / "dist",
                "https://github.com/danjboyd/gnustep-cli/releases",
                cli_inputs={
                    "linux-amd64-clang": cli_bundle,
                    "linux-ubuntu2404-amd64-clang": cli_bundle,
                },
                toolchain_inputs={
                    "linux-amd64-clang": toolchain_dir,
                    "linux-ubuntu2404-amd64-clang": toolchain_dir,
                },
            )
            with patch("gnustep_cli_shared.setup_planner.build_doctor_payload", return_value=managed_debian_doctor_payload()):
                payload = qualify_full_cli_handoff(staged["release_dir"], temp / "handoff-root")
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["command"], "qualify-full-cli-handoff")
            self.assertTrue(payload["checks"])
            self.assertTrue(payload["command_results"])
            self.assertTrue(all(result["ok"] for result in payload["command_results"]))
            runtime_root = Path(payload["install_root"]) / "libexec" / "gnustep-cli"
            python_files = sorted(path.relative_to(runtime_root) for path in runtime_root.rglob("*.py"))
            self.assertEqual(python_files, [])
            check_map = {check["id"]: check for check in payload["checks"]}
            self.assertTrue(check_map["install.runtime_binary"]["ok"])
            self.assertTrue(check_map["install.state_file"]["ok"])
            self.assertTrue(check_map["install.state_file_valid"]["ok"])
            self.assertTrue(check_map["install.no_python_runtime_scripts"]["ok"])
            self.assertTrue(check_map["install.no_python_runtime_modules"]["ok"])

    def test_debian_gcc_interop_plan(self):
        payload = debian_gcc_interop_plan()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "debian-gcc-interop-plan")
        self.assertEqual(payload["host_requirements"]["distribution"], "debian")
        step_ids = [step["id"] for step in payload["steps"]]
        self.assertIn("build-full-cli", step_ids)
        self.assertIn("record-evidence", step_ids)

    def test_fedora_native_validation_plan(self):
        payload = native_linux_validation_plan("fedora")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["distribution"], "fedora")
        step_ids = [step["id"] for step in payload["steps"]]
        self.assertIn("run-doctor", step_ids)
        self.assertIn("run-setup", step_ids)
        self.assertIn("package-flow", step_ids)

    def test_arch_native_validation_plan(self):
        payload = native_linux_validation_plan("arch")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["distribution"], "arch")
        step_ids = [step["id"] for step in payload["steps"]]
        self.assertIn("run-doctor", step_ids)
        self.assertIn("run-setup", step_ids)
        self.assertIn("record-evidence", step_ids)

    def test_current_support_matrix(self):
        payload = current_support_matrix()
        self.assertTrue(payload["ok"])
        target_map = {target["id"]: target for target in payload["targets"]}
        self.assertEqual(target_map["openbsd-amd64-clang"]["status"], "validated_native_preferred")
        self.assertEqual(target_map["openbsd-amd64-clang"]["evidence_status"], "validated")
        self.assertEqual(target_map["fedora-amd64-clang"]["status"], "interoperability_only")
        self.assertEqual(target_map["fedora-amd64-clang"]["evidence_status"], "validated")
        self.assertEqual(target_map["debian-amd64-gcc"]["status"], "interoperability_only")
        self.assertEqual(target_map["debian-amd64-gcc"]["evidence_status"], "validated")
        self.assertEqual(target_map["arch-amd64-clang"]["status"], "interoperability_only")
        self.assertEqual(target_map["arch-amd64-clang"]["evidence_status"], "validated")
        self.assertEqual(target_map["windows-amd64-msys2-clang64"]["status"], "managed_target_staged_artifacts_validated")
        self.assertEqual(target_map["windows-amd64-msvc"]["status"], "deferred")

    def test_release_candidate_qualification_status(self):
        payload = release_candidate_qualification_status()
        self.assertTrue(payload["ok"])
        phase_status = {phase["phase"]: phase for phase in payload["phase_status"]}
        self.assertEqual(phase_status["12"]["status"], "completed_for_local_release_tooling")
        self.assertEqual(phase_status["13"]["status"], "completed_for_native_dogfood")
        self.assertEqual(phase_status["14"]["status"], "completed_for_current_command_surface")
        self.assertEqual(phase_status["18"]["status"], "completed_for_linux_amd64_and_staged_cross_platform_artifacts")
        self.assertIn("production", " ".join(phase_status["12"]["remaining"]))
        artifact_checks = {check["id"]: check for check in payload["artifact_checks"]}
        live_checks = {check["id"]: check for check in payload["live_host_checks"]}
        self.assertEqual(artifact_checks["regression-gate"]["status"], "completed")
        self.assertEqual(artifact_checks["artifact-package-flow-smoke"]["status"], "completed_for_staged_artifacts")
        self.assertEqual(live_checks["openbsd-native-qualification"]["status"], "completed")
        self.assertEqual(live_checks["debian-native-qualification"]["status"], "completed")
        self.assertFalse(live_checks["fedora-native-qualification"]["blocked"])
        self.assertFalse(live_checks["arch-native-qualification"]["blocked"])
        self.assertEqual(live_checks["windows-libvirt-readiness"]["status"], "completed")
        self.assertFalse(live_checks["windows-public-bootstrap-stability"]["blocked"])
        self.assertFalse(live_checks["windows-extracted-toolchain-rebuild"]["blocked"])
        self.assertEqual(artifact_checks["package-index-trust-gate"]["status"], "completed")

    def test_windows_extracted_toolchain_rebuild_plan_records_validated_manual_evidence(self):
        payload = windows_extracted_toolchain_rebuild_plan()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "validated_manual_live_evidence")
        self.assertEqual(payload["target"], "windows-amd64-msys2-clang64")
        self.assertIsNone(payload["blocked_by"])
        self.assertIn("<toolchain>/clang64/bin", payload["required_environment"]["path_entries"])
        self.assertIn("GNUSTEP_MAKEFILES", payload["required_environment"]["variables"])
        step_ids = [step["id"] for step in payload["validation_steps"]]
        self.assertIn("rebuild-full-cli", step_ids)
        self.assertIn("run-rebuilt-cli", step_ids)

    def test_package_tools_xctest_artifact_packages_installed_layout(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            source = temp / "src"
            source.mkdir()
            subprocess.run(["git", "-C", str(source), "init"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            subprocess.run(["git", "-C", str(source), "config", "user.email", "test@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(source), "config", "user.name", "Test"], check=True)
            (source / "README.md").write_text("tools-xctest fixture\n")
            subprocess.run(["git", "-C", str(source), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(source), "commit", "-m", "fixture"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            installed = temp / "GNUstep"
            (installed / "Tools").mkdir(parents=True)
            (installed / "Library" / "Headers" / "XCTest").mkdir(parents=True)
            (installed / "Library" / "Libraries").mkdir(parents=True)
            (installed / "Tools" / "xctest").write_text("#!/bin/sh\n")
            (installed / "Library" / "Headers" / "XCTest" / "XCTest.h").write_text("// header\n")
            (installed / "Library" / "Libraries" / "libXCTest.so").write_text("library\n")
            payload = package_tools_xctest_artifact(temp / "out", source_dir=source, installed_root=installed, version="9.9.9")
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["package_id"], "org.gnustep.tools-xctest")
            self.assertEqual(len(payload["source"]["sha256"]), 64)
            self.assertEqual(len(payload["artifact"]["sha256"]), 64)
            artifact_path = Path(payload["artifact"]["path"])
            self.assertTrue(artifact_path.exists())
            with tarfile.open(artifact_path, "r:gz") as archive:
                names = archive.getnames()
                launcher = archive.extractfile("./bin/xctest").read().decode()
            self.assertIn("./bin/xctest", names)
            self.assertIn("./libexec/xctest", names)
            self.assertIn("./Library/Headers/XCTest/XCTest.h", names)
            self.assertIn("./Library/Libraries/libXCTest.so", names)
            self.assertIn("LD_LIBRARY_PATH", launcher)
            self.assertIn("managed_root", launcher)
            self.assertIn("System/Library/Libraries", launcher)
            self.assertIn("libexec/xctest", launcher)

    def test_package_artifact_build_plan(self):
        payload = package_artifact_build_plan(ROOT / "packages")
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["production_ready"])
        self.assertEqual(payload["policy_blockers"], [])
        package_map = {package["id"]: package for package in payload["packages"]}
        self.assertIn("org.gnustep.tools-xctest", package_map)
        package = package_map["org.gnustep.tools-xctest"]
        self.assertTrue(package["production_ready"])
        self.assertTrue(package["source_verified"])
        artifact_ids = [artifact["id"] for artifact in package["artifacts"]]
        self.assertIn("tools-xctest-linux-amd64-clang", artifact_ids)
        self.assertIn("tools-xctest-linux-ubuntu2404-amd64-clang", artifact_ids)
        self.assertIn("tools-xctest-linux-arm64-clang", artifact_ids)
        self.assertIn("tools-xctest-openbsd-amd64-clang", artifact_ids)
        self.assertIn("tools-xctest-openbsd-arm64-clang", artifact_ids)
        self.assertIn("tools-xctest-windows-amd64-msys2-clang64", artifact_ids)
        linux_artifact = next(artifact for artifact in package["artifacts"] if artifact["id"] == "tools-xctest-linux-amd64-clang")
        ubuntu_artifact = next(artifact for artifact in package["artifacts"] if artifact["id"] == "tools-xctest-linux-ubuntu2404-amd64-clang")
        linux_arm64_artifact = next(artifact for artifact in package["artifacts"] if artifact["id"] == "tools-xctest-linux-arm64-clang")
        openbsd_artifact = next(artifact for artifact in package["artifacts"] if artifact["id"] == "tools-xctest-openbsd-amd64-clang")
        openbsd_arm64_artifact = next(artifact for artifact in package["artifacts"] if artifact["id"] == "tools-xctest-openbsd-arm64-clang")
        windows_artifact = next(artifact for artifact in package["artifacts"] if artifact["id"] == "tools-xctest-windows-amd64-msys2-clang64")
        self.assertTrue(linux_artifact["provenance_required"])
        self.assertTrue(linux_artifact["signature_required"])
        self.assertTrue(linux_artifact["production_ready"])
        self.assertTrue(linux_artifact["publish"])
        self.assertEqual(linux_artifact["patches"][0]["upstream_status"], "submitted")
        self.assertTrue(ubuntu_artifact["publish"])
        self.assertTrue(ubuntu_artifact["production_ready"])
        self.assertEqual(ubuntu_artifact["arch"], "amd64")
        self.assertEqual(ubuntu_artifact["toolchain_flavor"], "clang")
        self.assertEqual(linux_artifact["build_backend"], "gnustep-cli")
        self.assertEqual(linux_artifact["build_invocation"][:2], ["gnustep", "build"])
        self.assertTrue(openbsd_artifact["provenance_required"])
        self.assertTrue(openbsd_artifact["signature_required"])
        self.assertTrue(openbsd_artifact["production_ready"])
        self.assertTrue(openbsd_artifact["publish"])
        self.assertEqual(openbsd_artifact["patches"][0]["upstream_pr"], "https://github.com/gnustep/tools-xctest/pull/5")
        self.assertTrue(linux_arm64_artifact["publish"])
        self.assertEqual(linux_arm64_artifact["arch"], "arm64")
        self.assertFalse(openbsd_arm64_artifact["publish"])
        self.assertEqual(openbsd_arm64_artifact["arch"], "arm64")
        self.assertTrue(windows_artifact["publish"])
        self.assertEqual(windows_artifact["toolchain_flavor"], "msys2-clang64")

    def test_package_artifact_build_plan_allows_production_ready_manifest(self):
        with tempfile.TemporaryDirectory() as tempdir:
            packages_dir = Path(tempdir) / "packages"
            package_dir = packages_dir / "org.example.clean"
            package_dir.mkdir(parents=True)
            manifest = {
                "schema_version": 1,
                "id": "org.example.clean",
                "name": "Clean Example",
                "version": "1.0.0",
                "kind": "cli-tool",
                "source": {
                    "type": "archive",
                    "url": "https://example.invalid/sources/clean-1.0.0.tar.gz",
                    "sha256": "a" * 64,
                },
                "dependencies": [],
                "artifacts": [
                    {
                        "id": "clean-linux-amd64-clang",
                        "os": "linux",
                        "arch": "amd64",
                        "compiler_family": "clang",
                        "toolchain_flavor": "clang",
                        "url": "https://example.invalid/packages/clean-linux-amd64-clang.tar.gz",
                        "sha256": "b" * 64,
                    }
                ],
            }
            (package_dir / "package.json").write_text(json.dumps(manifest) + "\n")
            payload = package_artifact_build_plan(packages_dir)
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["production_ready"])
            self.assertEqual(payload["policy_blockers"], [])
            package = payload["packages"][0]
            artifact = package["artifacts"][0]
            self.assertTrue(package["source_verified"])
            self.assertTrue(package["production_ready"])
            self.assertTrue(artifact["source_verified"])
            self.assertTrue(artifact["artifact_verified"])
            self.assertTrue(artifact["production_ready"])
            self.assertTrue(artifact["publish"])

    def test_tools_xctest_release_gate_blocks_until_artifacts_are_rebuilt_and_dogfooded(self):
        payload = tools_xctest_release_gate(
            ROOT / "packages", evidence_dir=ROOT / "docs" / "validation" / "tools-xctest-release-20260420"
        )
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["phase"], "24.E-G")
        self.assertEqual(payload["required_patch"], "add-apple-style-xctest-cli-filters")
        blocker_codes = [blocker["code"] for blocker in payload["blockers"]]
        self.assertEqual(blocker_codes, [])
        targets = {target["id"]: target for target in payload["targets"]}
        self.assertEqual(targets["tools-xctest-linux-amd64-clang"]["selected_patches"], ["add-apple-style-xctest-cli-filters"])
        self.assertTrue(targets["tools-xctest-linux-amd64-clang"]["release_ready"])
        self.assertTrue(targets["tools-xctest-openbsd-amd64-clang"]["release_ready"])
        self.assertTrue(targets["tools-xctest-linux-arm64-clang"]["release_ready"])
        self.assertEqual(targets["tools-xctest-windows-amd64-msys2-clang64"]["format"], "zip")
        self.assertTrue(targets["tools-xctest-windows-amd64-msys2-clang64"]["release_ready"])
        self.assertEqual(targets["tools-xctest-openbsd-arm64-clang"]["dogfood_evidence"], "deferred")
        self.assertTrue(targets["tools-xctest-openbsd-arm64-clang"]["deferred_non_release_blocker"])
        self.assertIn("minimal XCTest bundle execution", payload["dogfood_checks"])

    def test_tools_xctest_release_gate_passes_with_publishable_artifact_and_evidence(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            packages_dir = temp / "packages"
            package_dir = packages_dir / "org.gnustep.tools-xctest"
            package_dir.mkdir(parents=True)
            artifact_id = "tools-xctest-linux-amd64-clang"
            manifest = {
                "schema_version": 1,
                "id": "org.gnustep.tools-xctest",
                "name": "tools-xctest",
                "version": "1.0.0",
                "kind": "cli-tool",
                "source": {"type": "git", "url": "https://github.com/gnustep/tools-xctest.git", "sha256": "a" * 64},
                "artifacts": [
                    {
                        "id": artifact_id,
                        "os": "linux",
                        "arch": "amd64",
                        "compiler_family": "clang",
                        "toolchain_flavor": "clang",
                        "url": "https://example.invalid/tools-xctest.tar.gz",
                        "sha256": "b" * 64,
                        "publish": True,
                        "status": "validated",
                    }
                ],
                "patches": [
                    {
                        "id": "add-apple-style-xctest-cli-filters",
                        "path": "patches/add-apple-style-xctest-cli-filters.patch",
                        "sha256": "c" * 64,
                        "applies_to": [artifact_id],
                    }
                ],
            }
            (package_dir / "package.json").write_text(json.dumps(manifest) + "\n")
            evidence_dir = temp / "evidence" / "tools-xctest"
            evidence_dir.mkdir(parents=True)
            (evidence_dir / f"{artifact_id}.json").write_text(json.dumps({
                "ok": True,
                "package_id": "org.gnustep.tools-xctest",
                "artifact_id": artifact_id,
                "checks": ["install", "xctest-smoke", "minimal-bundle", "remove"],
            }) + "\n")
            payload = tools_xctest_release_gate(packages_dir, evidence_dir=temp / "evidence")
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["blockers"], [])
            self.assertEqual(payload["targets"][0]["dogfood_evidence"], "accepted")
            self.assertTrue(payload["targets"][0]["release_ready"])

    def test_tools_xctest_release_gate_requires_manifest(self):
        with tempfile.TemporaryDirectory() as tempdir:
            payload = tools_xctest_release_gate(Path(tempdir) / "packages")
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["blockers"][0]["code"], "tools_xctest_manifest_missing")

    def test_package_artifact_publication_gate_blocks_policy_placeholders(self):
        with tempfile.TemporaryDirectory() as tempdir:
            packages_dir = Path(tempdir) / "packages"
            package_dir = packages_dir / "org.example.blocked"
            package_dir.mkdir(parents=True)
            (package_dir / "package.json").write_text(json.dumps({
                "schema_version": 1,
                "id": "org.example.blocked",
                "name": "Blocked Example",
                "version": "1.0.0",
                "kind": "cli-tool",
                "source": {"type": "archive", "url": "https://example.invalid/src.tar.gz", "sha256": "development-source-checksum-tbd"},
                "dependencies": [],
                "artifacts": [{
                    "id": "blocked-linux-amd64-clang",
                    "os": "linux",
                    "arch": "amd64",
                    "compiler_family": "clang",
                    "toolchain_flavor": "clang",
                    "url": "https://example.invalid/pkg.tar.gz",
                    "sha256": "published-artifact-checksum-tbd",
                }],
            }) + "\n")
            payload = package_artifact_publication_gate(packages_dir)
            self.assertFalse(payload["ok"])
            checks = {check["id"]: check for check in payload["checks"]}
            self.assertIn("package-artifacts-production-ready", checks)
            self.assertFalse(checks["package-artifacts-production-ready"]["ok"])
            blocker_codes = [blocker["code"] for blocker in checks["package-artifacts-production-ready"]["payload"]["policy_blockers"]]
            self.assertIn("missing_verified_source_digest", blocker_codes)
            self.assertIn("missing_published_artifact_digest", blocker_codes)

    def test_package_artifact_publication_gate_passes_clean_manifest(self):
        with tempfile.TemporaryDirectory() as tempdir:
            packages_dir = Path(tempdir) / "packages"
            package_dir = packages_dir / "org.example.clean"
            package_dir.mkdir(parents=True)
            (package_dir / "package.json").write_text(json.dumps({
                "schema_version": 1,
                "id": "org.example.clean",
                "name": "Clean Example",
                "version": "1.0.0",
                "kind": "cli-tool",
                "source": {"type": "archive", "url": "https://example.invalid/src.tar.gz", "sha256": "a" * 64},
                "dependencies": [],
                "artifacts": [{
                    "id": "clean-linux-amd64-clang",
                    "os": "linux",
                    "arch": "amd64",
                    "compiler_family": "clang",
                    "toolchain_flavor": "clang",
                    "url": "https://example.invalid/pkg.tar.gz",
                    "sha256": "b" * 64,
                }],
            }) + "\n")
            payload = package_artifact_publication_gate(packages_dir)
            self.assertTrue(payload["ok"])
            checks = {check["id"]: check for check in payload["checks"]}
            self.assertTrue(checks["package-artifacts-production-ready"]["ok"])

    def test_otvm_release_host_validation_plan(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            (temp / "release-manifest.json").write_text('{"schema_version":1,"releases":[{"version":"0.1.0","artifacts":[]}]}')
            payload = otvm_release_host_validation_plan(temp, config_path="~/custom-libvirt.toml")
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["config_path"], "~/custom-libvirt.toml")
            self.assertEqual(payload["guest_stage_roots"]["unix"], "/tmp/gnustep-smoke/release")
            targets = {target["id"]: target for target in payload["targets"]}
            self.assertEqual(targets["debian-release-artifact-smoke"]["profile"], "debian-13-gnome-wayland")
            self.assertEqual(targets["openbsd-native-packaged-smoke"]["profile"], "openbsd-7.8-fvwm")
            self.assertEqual(targets["windows-release-artifact-smoke"]["profile"], "windows-2022")
            self.assertIn("release-manifest.json", targets["windows-release-artifact-smoke"]["guest_release_manifest_path"])


    def test_linux_cli_abi_audit_rejects_legacy_objc_symbols(self):
        with tempfile.TemporaryDirectory() as tempdir:
            binary = Path(tempdir) / "gnustep"
            binary.write_text("binary")
            with patch("gnustep_cli_shared.build_infra.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = "                 U __objc_class_name_NSAutoreleasePool\n"
                run.return_value.stderr = ""
                payload = linux_cli_abi_audit(binary)
            self.assertFalse(payload["ok"])
            checks = {check["id"]: check for check in payload["checks"]}
            self.assertFalse(checks["no-legacy-gcc-objc-class-symbols"]["ok"])
            self.assertFalse(checks["modern-objc2-class-symbols"]["ok"])

    def test_linux_cli_abi_audit_accepts_modern_objc_symbols(self):
        with tempfile.TemporaryDirectory() as tempdir:
            binary = Path(tempdir) / "gnustep"
            binary.write_text("binary")
            with patch("gnustep_cli_shared.build_infra.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = "                 U ._OBJC_REF_CLASS_NSAutoreleasePool\n"
                run.return_value.stderr = ""
                payload = linux_cli_abi_audit(binary)
            self.assertTrue(payload["ok"])

    def test_refresh_local_release_metadata_updates_digests_and_trust_fields(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact = root / "gnustep-cli-linux-amd64-clang-0.1.0-dev.tar.gz"
            artifact.write_text("new artifact")
            manifest = {
                "schema_version": 1,
                "channel": "stable",
                "generated_at": "2026-04-20T00:00:00Z",
                "releases": [{
                    "version": "0.1.0-dev",
                    "status": "active",
                    "artifacts": [{
                        "id": "cli-linux-amd64-clang",
                        "kind": "cli",
                        "filename": artifact.name,
                        "sha256": "0" * 64,
                    }],
                }],
            }
            (root / "release-manifest.json").write_text(json.dumps(manifest) + "\n")
            payload = refresh_local_release_metadata(root)
            self.assertTrue(payload["ok"])
            refreshed = json.loads((root / "release-manifest.json").read_text())
            self.assertNotEqual(refreshed["releases"][0]["artifacts"][0]["sha256"], "0" * 64)
            self.assertEqual(refreshed["metadata_version"], 1)
            self.assertIn("expires_at", refreshed)
            self.assertTrue((root / "release-provenance.json").exists())
            self.assertIn(artifact.name, (root / "SHA256SUMS").read_text())

    def test_bundle_full_cli(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            binary = temp / "gnustep"
            binary.write_text("binary")
            payload = bundle_full_cli(binary, temp / "bundle", repo_root=ROOT)
            self.assertTrue(payload["ok"])
            self.assertTrue((temp / "bundle" / "bin" / "gnustep").exists())
            self.assertTrue((temp / "bundle" / "libexec" / "gnustep-cli" / "examples" / "release-manifest-v1.json").exists())
            self.assertFalse((temp / "bundle" / "libexec" / "gnustep-cli" / "scripts" / "internal").exists())
            self.assertFalse((temp / "bundle" / "libexec" / "gnustep-cli" / "src" / "gnustep_cli_shared").exists())
            launcher = (temp / "bundle" / "bin" / "gnustep").read_text()
            self.assertIn('export PATH="$INSTALL_ROOT/bin:$INSTALL_ROOT/Tools:$INSTALL_ROOT/System/Tools:$INSTALL_ROOT/Local/Tools:$PATH"', launcher)
            self.assertIn('export LD_LIBRARY_PATH="$INSTALL_ROOT/Library/Libraries:$INSTALL_ROOT/Local/Library/Libraries:$INSTALL_ROOT/System/Library/Libraries:$INSTALL_ROOT/lib:$INSTALL_ROOT/lib64:${LD_LIBRARY_PATH:-}"', launcher)
            self.assertIn('MANAGED_MAKEFILES="$INSTALL_ROOT/System/Library/Makefiles"', launcher)
            self.assertIn('gnustep-config --variable=GNUSTEP_MAKEFILES', launcher)
            self.assertIn('/usr/local/share/GNUstep/Makefiles', launcher)
            self.assertIn('[ -n "${GNUSTEP_MAKEFILES:-}" ]', launcher)


if __name__ == "__main__":
    unittest.main()
