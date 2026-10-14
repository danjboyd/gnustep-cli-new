import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gnustep_cli_shared.custom_toolchain import (  # noqa: E402
    COMPONENT_ORDER,
    _component_steps,
    build_custom_toolchain,
    build_environment,
    check_custom_prefix,
    custom_toolchain_lock_from_source_lock,
    parse_build_id,
    validate_custom_toolchain_lock,
)


REVISION = "0" * 40


def _git(cwd: Path, *args: str) -> str:
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True, env=env).stdout.strip()


def _repo(root: Path, name: str) -> tuple[str, str]:
    repo = root / "upstream" / name
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    (repo / "README").write_text(f"{name}\n")
    _git(repo, "add", "README")
    _git(repo, "commit", "-q", "-m", "init")
    return repo.as_uri(), _git(repo, "rev-parse", "HEAD")


def _lock(components: list[dict]) -> dict:
    return {"schema_version": 1, "kind": "custom-toolchain-lock", "name": "test", "components": components}


def _component(name: str, **extra) -> dict:
    entry = {"name": name, "url": f"https://example.invalid/{name}.git", "revision": REVISION, "configure_args": [], "patches": []}
    entry.update(extra)
    return entry


class CustomToolchainLockTests(unittest.TestCase):
    def test_official_source_lock_converts_to_a_valid_custom_lock(self):
        source_lock = json.loads((ROOT / "toolchains" / "linux-amd64-clang" / "source-lock.json").read_text())
        lock = custom_toolchain_lock_from_source_lock(source_lock, "from-official")
        self.assertEqual([c["name"] for c in lock["components"]], COMPONENT_ORDER)
        with tempfile.TemporaryDirectory() as tmp:
            result = validate_custom_toolchain_lock(lock, Path(tmp) / "lock.json")
        self.assertTrue(result["ok"], result["errors"])

    def test_rejects_missing_required_components_and_bad_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = validate_custom_toolchain_lock(_lock([_component("libs-base"), _component("libobjc2")]), Path(tmp) / "lock.json")
        messages = " ".join(error["message"] for error in result["errors"])
        self.assertFalse(result["ok"])
        self.assertIn("required component libdispatch is missing", messages)
        self.assertIn("build order", messages)

    def test_rejects_unpinned_revisions_and_back_without_gui(self):
        components = [_component(n) for n in ["libobjc2", "libdispatch", "tools-make", "libs-base"]]
        components[3]["revision"] = "main"
        components.append(_component("libs-back"))
        with tempfile.TemporaryDirectory() as tmp:
            result = validate_custom_toolchain_lock(_lock(components), Path(tmp) / "lock.json")
        paths = {error["path"] for error in result["errors"]}
        self.assertIn("components[3].revision", paths)
        self.assertTrue(any("libs-back requires libs-gui" in e["message"] for e in result["errors"]))

    def test_patches_must_exist_and_match_their_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "lock.json"
            patch_file = Path(tmp) / "patches" / "fix.patch"
            patch_file.parent.mkdir()
            patch_file.write_text("diff\n")
            good = hashlib.sha256(patch_file.read_bytes()).hexdigest()
            base = [_component(n) for n in ["libobjc2", "libdispatch", "tools-make"]]
            ok = validate_custom_toolchain_lock(_lock(base + [_component("libs-base", patches=[{"path": "patches/fix.patch", "sha256": good}])]), lock_path)
            self.assertTrue(ok["ok"], ok["errors"])
            bad = validate_custom_toolchain_lock(_lock(base + [_component("libs-base", patches=[{"path": "patches/fix.patch", "sha256": "1" * 64}])]), lock_path)
            self.assertFalse(bad["ok"])
            self.assertIn("digest mismatch", bad["errors"][0]["message"])
            bare = validate_custom_toolchain_lock(_lock(base + [_component("libs-base", patches=["patches/fix.patch"])]), lock_path)
            self.assertFalse(bare["ok"])

    def test_patches_must_stay_inside_the_lock_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_dir = Path(tmp) / "lock"
            lock_dir.mkdir()
            outside = Path(tmp) / "outside.patch"
            outside.write_text("diff\n")
            digest = hashlib.sha256(outside.read_bytes()).hexdigest()
            base = [_component(n) for n in ["libobjc2", "libdispatch", "tools-make"]]
            result = validate_custom_toolchain_lock(
                _lock(base + [_component("libs-base", patches=[{"path": "../outside.patch", "sha256": digest}])]),
                lock_dir / "lock.json",
            )
            self.assertFalse(result["ok"])
            self.assertIn("inside the lock's directory", result["errors"][0]["message"])

    def test_install_domain_is_local_or_system(self):
        components = [_component(n) for n in ["libobjc2", "libdispatch", "tools-make", "libs-base"]]
        with tempfile.TemporaryDirectory() as tmp:
            for domain, valid in [("LOCAL", True), ("SYSTEM", True), ("USER", False), ("system", False)]:
                lock = _lock(components)
                lock["install_domain"] = domain
                result = validate_custom_toolchain_lock(lock, Path(tmp) / "lock.json")
                self.assertEqual(result["ok"], valid, domain)

    def test_container_section_is_validated(self):
        components = [_component(n) for n in ["libobjc2", "libdispatch", "tools-make", "libs-base"]]
        lock = _lock(components)
        lock["container"] = {"recipe": "linux-amd64-clang", "apt_packages": ["libgif-dev", "rm -rf /"]}
        with tempfile.TemporaryDirectory() as tmp:
            result = validate_custom_toolchain_lock(lock, Path(tmp) / "lock.json")
        self.assertEqual([e["path"] for e in result["errors"]], ["container.apt_packages"])


class CustomToolchainPrefixTests(unittest.TestCase):
    def test_refuses_managed_roots_their_parents_and_relative_paths(self):
        with tempfile.TemporaryDirectory() as home:
            with patch.dict(os.environ, {"HOME": home}, clear=False):
                managed = Path(home) / ".local" / "share" / "gnustep-cli"
                for candidate in (managed, managed / "custom", Path(home) / ".local" / "share", Path(home)):
                    self.assertFalse(check_custom_prefix(candidate)["ok"], candidate)
                self.assertFalse(check_custom_prefix("relative/prefix")["ok"])
                self.assertFalse(check_custom_prefix("/opt/gnustep-cli")["ok"])
                self.assertFalse(check_custom_prefix("/usr")["ok"])
                self.assertTrue(check_custom_prefix(Path(home) / "toolchains" / "lindirstat")["ok"])

    def test_refuses_non_empty_prefix_not_built_by_the_builder(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"HOME": tmp}):
            prefix = Path(tmp) / "prefix"
            prefix.mkdir()
            (prefix / "unrelated").write_text("x")
            self.assertFalse(check_custom_prefix(prefix)["ok"])
            (prefix / "gnustep-toolchain-provenance.json").write_text("{}")
            self.assertTrue(check_custom_prefix(prefix)["ok"])


class CustomToolchainBuildTests(unittest.TestCase):
    def test_sources_only_fetches_pinned_commits_and_applies_verified_patches(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"HOME": tmp}):
            root = Path(tmp)
            components = []
            for name in ["libobjc2", "libdispatch", "tools-make", "libs-base"]:
                url, revision = _repo(root, name)
                components.append({"name": name, "url": url, "revision": revision, "configure_args": [], "patches": []})
            patch_text = "--- a/README\n+++ b/README\n@@ -1 +1,2 @@\n libs-base\n+patched\n"
            patch_file = root / "lock" / "patches" / "base.patch"
            patch_file.parent.mkdir(parents=True)
            patch_file.write_text(patch_text)
            components[3]["patches"] = [{"path": "patches/base.patch", "sha256": hashlib.sha256(patch_text.encode()).hexdigest()}]
            lock_path = root / "lock" / "lock.json"
            lock_path.write_text(json.dumps(_lock(components)))

            result = build_custom_toolchain(lock_path, root / "prefix", sources_only=True)
            self.assertTrue(result["ok"], result)
            base = next(c for c in result["components"] if c["name"] == "libs-base")
            self.assertEqual(base["resolved_commit"], components[3]["revision"])
            self.assertEqual(base["applied_patches"][0]["path"], "patches/base.patch")
            self.assertIn("patched", (Path(base["source_dir"]) / "README").read_text())
            self.assertFalse((root / "prefix").exists())

    def test_build_refuses_unknown_revision(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"HOME": tmp}):
            root = Path(tmp)
            components = []
            for name in ["libobjc2", "libdispatch", "tools-make", "libs-base"]:
                url, revision = _repo(root, name)
                components.append({"name": name, "url": url, "revision": revision, "configure_args": [], "patches": []})
            components[0]["revision"] = "f" * 40
            lock_path = root / "lock.json"
            lock_path.write_text(json.dumps(_lock(components)))
            result = build_custom_toolchain(lock_path, root / "prefix", sources_only=True)
            self.assertFalse(result["ok"])
            self.assertEqual(result["component"], "libobjc2")

    def test_build_refuses_managed_root_before_touching_it(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"HOME": tmp}):
            managed = Path(tmp) / ".local" / "share" / "gnustep-cli"
            managed.mkdir(parents=True)
            (managed / "marker").write_text("keep")
            lock_path = Path(tmp) / "lock.json"
            lock_path.write_text(json.dumps(_lock([_component(n) for n in ["libobjc2", "libdispatch", "tools-make", "libs-base"]])))
            result = build_custom_toolchain(lock_path, managed)
            self.assertFalse(result["ok"])
            self.assertEqual((managed / "marker").read_text(), "keep")

    def test_build_environment_drops_host_gnustep_settings(self):
        env = build_environment(Path("/opt/custom"), {
            "PATH": "/usr/GNUstep/System/Tools:/usr/bin:/bin",
            "LD_LIBRARY_PATH": "/usr/GNUstep/System/Library/Libraries",
            "GNUSTEP_MAKEFILES": "/usr/GNUstep/System/Library/Makefiles",
            "CFLAGS": "-I/usr/GNUstep/include",
        })
        self.assertNotIn("GNUSTEP_MAKEFILES", env)
        self.assertNotIn("GNUstep", env["PATH"].replace("/opt/custom", ""))
        self.assertEqual(env["LD_LIBRARY_PATH"], "/opt/custom/lib:/opt/custom/lib64")
        self.assertEqual(env["CFLAGS"], "-I/opt/custom/include")
        self.assertTrue(env["PATH"].startswith("/opt/custom/System/Tools:/opt/custom/bin:"))

    def test_configure_args_are_appended_after_base_flags(self):
        steps = _component_steps("libs-gui", Path("/src"), Path("/p"), 4, ["--disable-sound"])
        self.assertEqual(steps[1], ["./configure", "--prefix=/p", "--disable-sound"])
        objc = _component_steps("libobjc2", Path("/src"), Path("/p"), 4, ["-DTESTS=OFF"])
        self.assertEqual(objc[1][-2:], ["-DCMAKE_INSTALL_PREFIX=/p", "-DTESTS=OFF"])
        make = _component_steps("tools-make", Path("/src"), Path("/p"), 4, ["--enable-debug-by-default"])
        self.assertIn("--with-layout=gnustep", make[0])
        self.assertEqual(make[0][-1], "--enable-debug-by-default")

    def test_parse_build_id(self):
        notes = "Displaying notes found in: .note.gnu.build-id\n  Owner  Data size  Description\n  GNU  0x00000014  NT_GNU_BUILD_ID (unique build ID bitstring)\n    Build ID: 3f65a649e63a0011223344556677889900aabbcc\n"
        self.assertEqual(parse_build_id(notes), "3f65a649e63a0011223344556677889900aabbcc")
        self.assertIsNone(parse_build_id("no notes"))


class CustomToolchainCiLockTests(unittest.TestCase):
    def test_ci_lock_uses_official_pins_with_gui_flags_and_a_verified_patch(self):
        script = ROOT / "scripts" / "ci" / "write-custom-toolchain-ci-lock.py"
        source_lock = json.loads((ROOT / "toolchains" / "linux-amd64-clang" / "source-lock.json").read_text())
        official = {component["name"]: component["revision"] for component in source_lock["components"]}
        with tempfile.TemporaryDirectory() as tmp:
            out = subprocess.run([sys.executable, str(script), tmp], check=True, capture_output=True, text=True)
            lock_path = Path(out.stdout.strip())
            lock = json.loads(lock_path.read_text())
            self.assertTrue(validate_custom_toolchain_lock(lock, lock_path)["ok"])
            components = {component["name"]: component for component in lock["components"]}
            self.assertEqual(list(components), COMPONENT_ORDER)
            for name, component in components.items():
                self.assertEqual(component["revision"], official[name])
            self.assertIn("--disable-cups", components["libs-gui"]["configure_args"])
            self.assertEqual(lock["install_domain"], "SYSTEM")
            [objc_patch] = components["libobjc2"]["patches"]
            patch_bytes = (lock_path.parent / objc_patch["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(patch_bytes).hexdigest(), objc_patch["sha256"])


if __name__ == "__main__":
    unittest.main()
