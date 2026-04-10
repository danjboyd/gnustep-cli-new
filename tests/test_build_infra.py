import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.build_infra import (
    build_matrix,
    bundle_full_cli,
    component_inventory,
    debian_gcc_interop_plan,
    github_release_plan,
    linux_build_script,
    msys2_assembly_script,
    msys2_input_manifest_template,
    msvc_status,
    openbsd_build_script,
    qualify_full_cli_handoff,
    toolchain_manifest,
    release_manifest_from_matrix,
    qualify_release_install,
    stage_release_assets,
    source_lock_template,
    toolchain_plan,
    verify_release_directory,
    write_release_manifest,
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
            filenames = {artifact["filename"] for artifact in payload["artifacts"]}
            self.assertIn("gnustep-cli-linux-amd64-clang-0.1.0.tar.gz", filenames)
            self.assertIn("gnustep-toolchain-linux-amd64-clang-0.1.0.tar.gz", filenames)

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

    def test_debian_gcc_interop_plan(self):
        payload = debian_gcc_interop_plan()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "debian-gcc-interop-plan")
        self.assertEqual(payload["host_requirements"]["distribution"], "debian")
        step_ids = [step["id"] for step in payload["steps"]]
        self.assertIn("build-full-cli", step_ids)
        self.assertIn("record-evidence", step_ids)

    def test_bundle_full_cli(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            binary = temp / "gnustep"
            binary.write_text("binary")
            payload = bundle_full_cli(binary, temp / "bundle", repo_root=ROOT)
            self.assertTrue(payload["ok"])
            self.assertTrue((temp / "bundle" / "bin" / "gnustep").exists())
            self.assertTrue((temp / "bundle" / "libexec" / "gnustep-cli" / "scripts" / "internal" / "doctor.py").exists())
            self.assertTrue((temp / "bundle" / "libexec" / "gnustep-cli" / "src" / "gnustep_cli_shared" / "__init__.py").exists())


if __name__ == "__main__":
    unittest.main()
