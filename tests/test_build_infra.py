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
    bundle_full_cli,
    component_inventory,
    current_support_matrix,
    debian_gcc_interop_plan,
    github_release_plan,
    linux_build_script,
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
    package_source_built_linux_toolchain_artifact,
    prepare_github_release,
    published_url_qualification_plan,
    qualify_full_cli_handoff,
    toolchain_manifest,
    release_manifest_from_matrix,
    qualify_release_install,
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
    release_key_rotation_drill,
    windows_extracted_toolchain_rebuild_plan,
)


class BuildInfraTests(unittest.TestCase):
    def test_matrix_contains_tier1_targets(self):
        payload = build_matrix()
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(len(payload["targets"]), 4)

    def test_release_manifest_generation(self):
        payload = release_manifest_from_matrix("0.1.0", "https://example.invalid/releases")
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["releases"][0]["version"], "0.1.0")
        self.assertEqual(len(payload["releases"][0]["artifacts"]), 8)
        linux_artifacts = [artifact for artifact in payload["releases"][0]["artifacts"] if artifact["os"] == "linux"]
        self.assertTrue(linux_artifacts)
        self.assertTrue(all(artifact["supported_distributions"] == ["debian"] for artifact in linux_artifacts))
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
        fedora_env = {"os": "linux", "arch": "amd64", "distribution_id": "fedora", "toolchain": {}}
        self.assertTrue(artifact_matches_host(debian_env, artifact))
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
        self.assertIn("make", host_package_names)
        self.assertIn("mingw-w64-clang-x86_64-clang", package_names)
        self.assertIn("mingw-w64-clang-x86_64-libdispatch", package_names)
        conflict_paths = [rule["path"] for rule in payload["conflict_rules"]]
        self.assertIn("clang64/include/Block.h", conflict_paths)

    def test_toolchain_manifest(self):
        payload = toolchain_manifest("linux-amd64-clang", "2026.04.0")
        self.assertEqual(payload["kind"], "managed-toolchain")
        self.assertIn("libs-corebase", payload["components"])
        windows_payload = toolchain_manifest("windows-amd64-msys2-clang64", "2026.04.0")
        self.assertIn("developer_entrypoints", windows_payload)
        self.assertIn("usr/bin/bash.exe", windows_payload["developer_entrypoints"]["build_shell"])
        self.assertIn("usr/bin/sha256sum.exe", windows_payload["developer_entrypoints"]["checksum_tool"])

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
        self.assertIn("$ProgressPreference = 'SilentlyContinue'", script)
        self.assertIn("pacman -Syuu", script)
        self.assertIn("pacman -S --noconfirm --needed make", script)
        self.assertIn("mingw-w64-clang-x86_64-clang", script)
        self.assertIn("--overwrite /clang64/include/Block.h", script)
        self.assertIn("mingw-w64-clang-x86_64-libdispatch", script)
        self.assertIn('& $bash -lc "true"', script)
        self.assertNotIn('\\"true\\"', script)
        self.assertIn("usr\\bin", script)
        self.assertIn("sha256sum.exe", script)
        self.assertIn("Get-ChildItem -Path (Join-Path $MsysRoot 'usr\\bin') -Include '*.exe','*.dll'", script)
        self.assertIn("No MSYS2 usr\\bin executable/DLL runtime files", script)
        self.assertIn("Copy-Item -Force $runtimeFile.FullName", script)
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
            payload = prepare_github_release(
                "danjboyd/gnustep-cli-new",
                "0.1.0",
                temp / "dist",
                "https://github.com/danjboyd/gnustep-cli-new/releases",
                cli_inputs={"linux-amd64-clang": cli_bundle},
                toolchain_inputs={"linux-amd64-clang": toolchain_dir},
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

    def test_toolchain_archive_audit_accepts_complete_windows_layout(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Path(tempdir) / "gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0-dev.zip"
            with __import__("zipfile").ZipFile(archive, "w") as zf:
                root = "gnustep-toolchain-windows-amd64-msys2-clang64-0.1.0-dev"
                zf.writestr(root + "/bin/gnustep-config", "tool")
                zf.writestr(root + "/bin/clang.exe", "clang")
                zf.writestr(root + "/clang64/bin/clang.exe", "clang")
                zf.writestr(root + "/usr/bin/bash.exe", "bash")
                zf.writestr(root + "/usr/bin/make.exe", "make")
                zf.writestr(root + "/usr/bin/sha256sum.exe", "sha256sum")
                zf.writestr(root + "/usr/bin/msys-2.0.dll", "runtime")
                zf.writestr(root + "/share/GNUstep/Makefiles/common.make", "common")
                zf.writestr(root + "/share/GNUstep/Makefiles/tool.make", "tool")
                zf.writestr(root + "/GNUstep.bat", "@echo off")
            payload = toolchain_archive_audit(archive, target_id="windows-amd64-msys2-clang64")
            self.assertTrue(payload["ok"])


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
                cli_inputs={"linux-amd64-clang": cli_bundle},
                toolchain_inputs={"linux-amd64-clang": toolchain_dir},
            )
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

    def test_package_artifact_build_plan(self):
        payload = package_artifact_build_plan(ROOT / "packages")
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["production_ready"])
        package_map = {package["id"]: package for package in payload["packages"]}
        self.assertIn("org.gnustep.tools-xctest", package_map)
        package = package_map["org.gnustep.tools-xctest"]
        self.assertFalse(package["production_ready"])
        self.assertFalse(package["source_verified"])
        self.assertIn("missing_verified_source_digest", package["policy_blockers"])
        artifact_ids = [artifact["id"] for artifact in package["artifacts"]]
        self.assertIn("tools-xctest-linux-amd64-clang", artifact_ids)
        self.assertIn("tools-xctest-openbsd-amd64-clang", artifact_ids)
        linux_artifact = next(artifact for artifact in package["artifacts"] if artifact["id"] == "tools-xctest-linux-amd64-clang")
        self.assertTrue(linux_artifact["provenance_required"])
        self.assertTrue(linux_artifact["signature_required"])
        self.assertFalse(linux_artifact["production_ready"])
        self.assertFalse(linux_artifact["publish"])
        self.assertIn("missing_verified_source_digest", linux_artifact["policy_blockers"])
        self.assertIn("missing_published_artifact_digest", linux_artifact["policy_blockers"])
        blocker_codes = [blocker["code"] for blocker in payload["policy_blockers"]]
        self.assertIn("missing_verified_source_digest", blocker_codes)
        self.assertIn("missing_published_artifact_digest", blocker_codes)

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

    def test_package_artifact_publication_gate_blocks_policy_placeholders(self):
        payload = package_artifact_publication_gate(ROOT / "packages")
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


if __name__ == "__main__":
    unittest.main()
