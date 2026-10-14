"""Lock-driven custom GNUstep toolchain builds.

A custom toolchain lock pins each GNUstep component to a git URL and commit and
may add configure arguments and sha256-verified patches. The builder produces a
GNUstep-layout toolchain in a caller-chosen prefix using the same component
order and base build flags as the official managed Linux recipe
(toolchains/linux-amd64-clang/build-toolchain.sh), then writes provenance into
the prefix.

Custom toolchains are never official managed artifacts: locks may point at
forks and carry local patches, and the builder refuses the managed install
roots so it cannot overwrite an environment that `gnustep setup` owns.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


LOCK_KIND = "custom-toolchain-lock"
PROVENANCE_FILENAME = "gnustep-toolchain-provenance.json"
LOCK_COPY_DIRNAME = "gnustep-toolchain-lock"

# Build order and recipe kind for every component the builder knows. The first
# four are required; corebase, gui, and back are optional but keep this order.
COMPONENT_ORDER = [
    "libobjc2",
    "libdispatch",
    "tools-make",
    "libs-base",
    "libs-corebase",
    "libs-gui",
    "libs-back",
]
REQUIRED_COMPONENTS = ["libobjc2", "libdispatch", "tools-make", "libs-base"]
GNUSTEP_LIBRARIES = {"libs-base", "libs-corebase", "libs-gui", "libs-back"}
# GNUstep domains the libraries may install into. LOCAL is GNUstep Make's
# default and what the official recipe uses.
INSTALL_DOMAINS = ("LOCAL", "SYSTEM")

LIBOBJC2_BASE_ARGS = [
    "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
    "-DCMAKE_C_COMPILER=clang",
    "-DCMAKE_CXX_COMPILER=clang++",
    "-DCMAKE_OBJC_COMPILER=clang",
    "-DCMAKE_OBJCXX_COMPILER=clang++",
    "-DGNUSTEP_INSTALL_TYPE=NONE",
    "-DEMBEDDED_BLOCKS_RUNTIME=ON",
]
LIBDISPATCH_BASE_ARGS = [
    "-G",
    "Ninja",
    "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
    "-DCMAKE_C_COMPILER=clang",
    "-DCMAKE_CXX_COMPILER=clang++",
    "-DBUILD_TESTING=OFF",
]
TOOLS_MAKE_BASE_ARGS = [
    "--with-layout=gnustep",
    "--enable-native-objc-exceptions",
    "--enable-objc-arc",
    "--with-library-combo=ng-gnu-gnu",
]

_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def managed_install_roots() -> list[Path]:
    """Install roots owned by `gnustep setup`; custom builds must never use them."""
    roots = [Path("/opt/gnustep-cli")]
    home = os.environ.get("HOME")
    if home:
        roots.append(Path(home) / ".local" / "share" / "gnustep-cli")
    data_home = os.environ.get("XDG_DATA_HOME")
    if data_home:
        roots.append(Path(data_home) / "gnustep-cli")
    return [root.resolve() for root in roots]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _result(command: str, ok: bool, summary: str, **extra: Any) -> dict[str, Any]:
    payload = {"schema_version": 1, "command": command, "ok": ok, "status": "ok" if ok else "error", "summary": summary}
    payload.update(extra)
    return payload


def validate_custom_toolchain_lock(lock: dict[str, Any], lock_path: str | Path) -> dict[str, Any]:
    """Validate a custom toolchain lock; patch paths resolve relative to the lock file."""
    lock_file = Path(lock_path).resolve()
    errors: list[dict[str, str]] = []

    def add_error(path: str, message: str) -> None:
        errors.append({"path": path, "message": message})

    if lock.get("schema_version") != 1:
        add_error("schema_version", "custom toolchain lock schema_version must be 1")
    if lock.get("kind") != LOCK_KIND:
        add_error("kind", f"custom toolchain lock kind must be {LOCK_KIND}")
    if not isinstance(lock.get("name"), str) or not lock.get("name"):
        add_error("name", "custom toolchain lock needs a non-empty name")
    components = lock.get("components")
    if not isinstance(components, list) or not components:
        add_error("components", "custom toolchain lock must list components")
        components = []

    names = [component.get("name") for component in components if isinstance(component, dict)]
    unknown = [name for name in names if name not in COMPONENT_ORDER]
    if unknown:
        add_error("components", f"unknown components: {', '.join(map(str, unknown))}")
    for required in REQUIRED_COMPONENTS:
        if required not in names:
            add_error("components", f"required component {required} is missing")
    known = [name for name in names if name in COMPONENT_ORDER]
    if known != sorted(known, key=COMPONENT_ORDER.index) or len(set(known)) != len(known):
        add_error("components", f"components must appear once each in build order: {', '.join(COMPONENT_ORDER)}")
    if "libs-back" in names and "libs-gui" not in names:
        add_error("components", "libs-back requires libs-gui")
    if lock.get("install_domain", "LOCAL") not in INSTALL_DOMAINS:
        add_error("install_domain", f"install_domain must be one of: {', '.join(INSTALL_DOMAINS)}")

    container = lock.get("container")
    if container is not None:
        if not isinstance(container, dict):
            add_error("container", "container must be an object")
        else:
            recipe = container.get("recipe", "linux-amd64-clang")
            if not isinstance(recipe, str) or not re.match(r"^[a-z0-9][a-z0-9-]*$", recipe):
                add_error("container.recipe", "container.recipe must name a toolchains/<recipe> directory")
            packages = container.get("apt_packages", [])
            if not isinstance(packages, list) or not all(isinstance(p, str) and re.match(r"^[a-z0-9][a-z0-9+.-]*$", p) for p in packages):
                add_error("container.apt_packages", "container.apt_packages must be a list of Debian package names")

    for index, component in enumerate(components):
        where = f"components[{index}]"
        if not isinstance(component, dict):
            add_error(where, "component entry must be an object")
            continue
        url = component.get("url")
        if not isinstance(url, str) or not url:
            add_error(f"{where}.url", "component url is required")
        revision = component.get("revision")
        if not isinstance(revision, str) or not _REVISION_RE.match(revision):
            add_error(f"{where}.revision", "revision must be a pinned 40-character lowercase git commit")
        ref = component.get("ref")
        if ref is not None and (not isinstance(ref, str) or not ref):
            add_error(f"{where}.ref", "ref, when present, must be a branch or tag name")
        args = component.get("configure_args", [])
        if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
            add_error(f"{where}.configure_args", "configure_args must be a list of strings")
        patches = component.get("patches", [])
        if not isinstance(patches, list):
            add_error(f"{where}.patches", "patches must be a list")
            continue
        for patch_index, patch in enumerate(patches):
            patch_where = f"{where}.patches[{patch_index}]"
            if not isinstance(patch, dict) or not isinstance(patch.get("path"), str) or not isinstance(patch.get("sha256"), str):
                add_error(patch_where, "patch entries must be objects with path and sha256")
                continue
            if not _SHA256_RE.match(patch["sha256"]):
                add_error(f"{patch_where}.sha256", "sha256 must be 64 lowercase hex characters")
                continue
            patch_file = (lock_file.parent / patch["path"]).resolve()
            if lock_file.parent not in patch_file.parents:
                # The container wrapper mounts only the lock's directory.
                add_error(f"{patch_where}.path", f"patch must be inside the lock's directory {lock_file.parent}: {patch['path']}")
            elif not patch_file.is_file():
                add_error(f"{patch_where}.path", f"patch file not found: {patch_file}")
            elif _sha256_file(patch_file) != patch["sha256"]:
                add_error(f"{patch_where}.sha256", f"patch digest mismatch for {patch_file}")

    return _result(
        "validate-custom-toolchain-lock",
        not errors,
        "Custom toolchain lock is valid." if not errors else "Custom toolchain lock is invalid.",
        lock_path=str(lock_file),
        errors=errors,
    )


def check_custom_prefix(prefix: str | Path) -> dict[str, Any]:
    """Refuse prefixes that belong to the managed environment or are not ours to overwrite."""
    errors: list[dict[str, str]] = []
    raw = Path(prefix)
    if not raw.is_absolute():
        errors.append({"path": "prefix", "message": "prefix must be an absolute path"})
    resolved = raw.resolve()
    for root in managed_install_roots():
        if resolved == root or root in resolved.parents or resolved in root.parents:
            errors.append({"path": "prefix", "message": f"prefix overlaps the gnustep-cli managed install root {root}; choose a separate prefix"})
    if resolved == Path("/") or str(resolved) in {"/usr", "/usr/local", "/opt"}:
        errors.append({"path": "prefix", "message": "prefix must be a dedicated directory, not a system root"})
    if resolved.exists() and any(resolved.iterdir()) and not (resolved / PROVENANCE_FILENAME).exists():
        errors.append({"path": "prefix", "message": "prefix is not empty and was not created by the custom toolchain builder"})
    return _result(
        "check-custom-toolchain-prefix",
        not errors,
        "Prefix can be used." if not errors else "Prefix cannot be used.",
        prefix=str(resolved),
        errors=errors,
    )


def _component_steps(name: str, source: Path, prefix: Path, jobs: int, extra_args: list[str]) -> list[list[str]]:
    """Commands for one component, run from its source directory."""
    if name == "libobjc2":
        return [
            ["rm", "-rf", "build"],
            ["cmake", "-S", ".", "-B", "build", *LIBOBJC2_BASE_ARGS, f"-DCMAKE_INSTALL_PREFIX={prefix}", *extra_args],
            ["cmake", "--build", "build", f"-j{jobs}"],
            ["cmake", "--install", "build"],
        ]
    if name == "libdispatch":
        return [
            ["rm", "-rf", "build"],
            ["cmake", "-S", ".", "-B", "build", *LIBDISPATCH_BASE_ARGS, f"-DCMAKE_INSTALL_PREFIX={prefix}", f"-DCMAKE_PREFIX_PATH={prefix}", *extra_args],
            ["cmake", "--build", "build", f"-j{jobs}"],
            ["cmake", "--install", "build"],
        ]
    if name == "tools-make":
        return [
            ["./configure", f"--prefix={prefix}", *TOOLS_MAKE_BASE_ARGS, *extra_args],
            ["make", f"-j{jobs}"],
            ["make", "install"],
        ]
    if name in GNUSTEP_LIBRARIES:
        return [
            ["sh", "-c", "make distclean >/dev/null 2>&1 || true"],
            ["./configure", f"--prefix={prefix}", *extra_args],
            ["make", f"-j{jobs}"],
            ["make", "install"],
        ]
    raise ValueError(f"no build recipe for component {name}")


def build_environment(prefix: Path, base_env: dict[str, str] | None = None) -> dict[str, str]:
    """Environment for component builds, isolated from any host GNUstep installation."""
    source = dict(os.environ if base_env is None else base_env)
    env = {key: value for key, value in source.items() if not key.startswith("GNUSTEP_") and key not in {
        "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH", "LIBRARY_PATH", "CPATH", "PKG_CONFIG_PATH",
        "CPPFLAGS", "CFLAGS", "CXXFLAGS", "OBJCFLAGS", "OBJCXXFLAGS", "LDFLAGS",
    }}
    host_path = [entry for entry in source.get("PATH", "/usr/bin:/bin").split(":") if entry and "GNUstep" not in entry]
    env.update({
        "CC": "clang",
        "CXX": "clang++",
        "OBJC": "clang",
        "OBJCXX": "clang++",
        "PATH": ":".join([str(prefix / "System" / "Tools"), str(prefix / "bin"), *host_path]),
        "LD_LIBRARY_PATH": ":".join([str(prefix / "lib"), str(prefix / "lib64")]),
        "PKG_CONFIG_PATH": ":".join([str(prefix / "lib" / "pkgconfig"), str(prefix / "lib64" / "pkgconfig")]),
        "CPPFLAGS": f"-I{prefix / 'include'}",
        "CFLAGS": f"-I{prefix / 'include'}",
        "CXXFLAGS": f"-I{prefix / 'include'}",
        "OBJCFLAGS": f"-I{prefix / 'include'}",
        "OBJCXXFLAGS": f"-I{prefix / 'include'}",
        "LDFLAGS": f"-L{prefix / 'lib'} -L{prefix / 'lib64'}",
    })
    return env


def _wrap_for_gnustep(command: list[str], prefix: Path) -> list[str]:
    """Run a GNUstep library step with the toolchain's own GNUstep.sh sourced."""
    makefiles = prefix / "System" / "Library" / "Makefiles"
    script = (
        f"export GNUSTEP_MAKEFILES={shlex.quote(str(makefiles))}; set +u; "
        f". {shlex.quote(str(makefiles / 'GNUstep.sh'))}; set -u; exec \"$@\""
    )
    return ["sh", "-c", script, "sh", *command]


def _run(command: list[str], cwd: Path, env: dict[str, str], log: Path) -> int:
    with log.open("a") as handle:
        handle.write(f"$ (cd {cwd} && {shlex.join(command)})\n")
        handle.flush()
        return subprocess.run(command, cwd=cwd, env=env, stdout=handle, stderr=subprocess.STDOUT, check=False).returncode


def fetch_component_source(component: dict[str, Any], sources_dir: Path, lock_dir: Path, log: Path) -> dict[str, Any]:
    """Fetch a pinned commit, verify it, and apply the component's verified patches."""
    name = component["name"]
    destination = sources_dir / name
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    git = ["git", "-c", "advice.detachedHead=false", "-C", str(destination)]
    steps = [git + ["init", "-q"], git + ["remote", "add", "origin", component["url"]]]
    for step in steps:
        if _run(step, destination, env, log) != 0:
            return {"ok": False, "name": name, "message": f"git setup failed for {name}"}
    revision = component["revision"]
    if _run(git + ["fetch", "-q", "--depth", "1", "origin", revision], destination, env, log) != 0:
        # Not every server allows fetching an arbitrary commit; fall back to the
        # declared ref (or every branch) and require the commit to be present.
        refspec = component.get("ref") or "+refs/heads/*:refs/remotes/origin/*"
        if _run(git + ["fetch", "-q", "origin", refspec], destination, env, log) != 0:
            return {"ok": False, "name": name, "message": f"could not fetch {component['url']}"}
    if _run(git + ["checkout", "-q", "--detach", revision], destination, env, log) != 0:
        return {"ok": False, "name": name, "message": f"revision {revision} is not available from {component['url']}"}
    head = subprocess.run(git + ["rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip()
    if head != revision:
        return {"ok": False, "name": name, "message": f"checked out {head}, expected {revision}"}
    applied = []
    for patch in component.get("patches", []):
        patch_file = (lock_dir / patch["path"]).resolve()
        digest = _sha256_file(patch_file)
        if digest != patch["sha256"]:
            return {"ok": False, "name": name, "message": f"patch digest mismatch for {patch_file}"}
        if _run(git + ["apply", "--whitespace=nowarn", str(patch_file)], destination, env, log) != 0:
            return {"ok": False, "name": name, "message": f"patch {patch['path']} does not apply to {name}@{revision}"}
        applied.append({"path": patch["path"], "sha256": digest})
    return {"ok": True, "name": name, "source_dir": str(destination), "resolved_commit": head, "applied_patches": applied}


def _command_output(command: list[str]) -> str | None:
    try:
        proc = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        return None
    return (proc.stdout or proc.stderr).strip().splitlines()[0] if (proc.stdout or proc.stderr).strip() else None


def build_host_identity() -> dict[str, Any]:
    os_release: dict[str, str] = {}
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                os_release[key] = value.strip('"')
    except OSError:
        pass
    return {
        "distribution": os_release.get("PRETTY_NAME"),
        "os_version": f"{os_release.get('ID', '')}-{os_release.get('VERSION_ID', '')}" if os_release else None,
        "machine": platform.machine(),
        "kernel": platform.release(),
        "glibc": platform.libc_ver()[1] or None,
        "clang": _command_output(["clang", "--version"]),
        "cmake": _command_output(["cmake", "--version"]),
        "make": _command_output(["make", "--version"]),
        "container": Path("/.dockerenv").exists(),
    }


def parse_build_id(readelf_notes: str) -> str | None:
    match = re.search(r"Build ID:\s*([0-9a-f]+)", readelf_notes)
    return match.group(1) if match else None


def elf_build_ids(prefix: Path) -> dict[str, str]:
    """Map prefix-relative ELF paths (libraries, bundles, tools) to GNU build IDs."""
    ids: dict[str, str] = {}
    for path in sorted(prefix.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            with path.open("rb") as handle:
                if handle.read(4) != b"\x7fELF":
                    continue
        except OSError:
            continue
        notes = subprocess.run(["readelf", "-n", str(path)], capture_output=True, text=True, check=False).stdout
        build_id = parse_build_id(notes)
        if build_id:
            ids[str(path.relative_to(prefix))] = build_id
    return ids


def build_custom_toolchain(
    lock_path: str | Path,
    prefix: str | Path,
    *,
    work_dir: str | Path | None = None,
    jobs: int | None = None,
    sources_only: bool = False,
) -> dict[str, Any]:
    """Build the toolchain a custom lock describes into prefix and write provenance."""
    command = "build-custom-toolchain"
    lock_file = Path(lock_path).resolve()
    try:
        lock = json.loads(lock_file.read_text())
    except (OSError, ValueError) as error:
        return _result(command, False, f"Could not read custom toolchain lock: {error}", lock_path=str(lock_file))
    validation = validate_custom_toolchain_lock(lock, lock_file)
    if not validation["ok"]:
        return _result(command, False, "Custom toolchain lock is invalid.", lock_path=str(lock_file), errors=validation["errors"])
    prefix_check = check_custom_prefix(prefix)
    if not prefix_check["ok"]:
        return _result(command, False, "Prefix cannot be used.", prefix=prefix_check["prefix"], errors=prefix_check["errors"])

    prefix_dir = Path(prefix_check["prefix"])
    work = Path(work_dir).resolve() if work_dir else prefix_dir.parent / f".{prefix_dir.name}-build"
    sources_dir = work / "sources"
    logs_dir = work / "logs"
    sources_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    jobs = jobs or os.cpu_count() or 4
    started = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    fetched: list[dict[str, Any]] = []
    for component in lock["components"]:
        result = fetch_component_source(component, sources_dir, lock_file.parent, logs_dir / f"{component['name']}.log")
        if not result["ok"]:
            return _result(command, False, result["message"], component=component["name"], log=str(logs_dir / f"{component['name']}.log"))
        fetched.append(result)
    if sources_only:
        return _result(command, True, "Sources fetched, verified, and patched.", prefix=str(prefix_dir), work_dir=str(work), components=fetched)

    if prefix_dir.exists():
        shutil.rmtree(prefix_dir)
    prefix_dir.mkdir(parents=True)
    env = build_environment(prefix_dir)
    install_domain = lock.get("install_domain", "LOCAL")
    for component, source in zip(lock["components"], fetched):
        name = component["name"]
        log = logs_dir / f"{name}.log"
        step_env = env
        if name in GNUSTEP_LIBRARIES:
            step_env = dict(env, GNUSTEP_INSTALLATION_DOMAIN=install_domain)
        for step in _component_steps(name, Path(source["source_dir"]), prefix_dir, jobs, component.get("configure_args", [])):
            if name in GNUSTEP_LIBRARIES:
                step = _wrap_for_gnustep(step, prefix_dir)
            if _run(step, Path(source["source_dir"]), step_env, log) != 0:
                return _result(command, False, f"{name} build step failed: {shlex.join(step)}", component=name, log=str(log))
        if name == "tools-make":
            # Expose the libobjc2 runtime headers through the GNUstep header domain,
            # as the official recipe does.
            headers = prefix_dir / "Local" / "Library" / "Headers"
            headers.mkdir(parents=True, exist_ok=True)
            objc_link = headers / "objc"
            if objc_link.is_symlink() or objc_link.exists():
                objc_link.unlink()
            objc_link.symlink_to(prefix_dir / "include" / "objc")
            for header in ("Block.h", "Block_private.h"):
                if (prefix_dir / "include" / header).exists():
                    shutil.copy2(prefix_dir / "include" / header, headers / header)

    lock_copy = prefix_dir / LOCK_COPY_DIRNAME
    lock_copy.mkdir()
    shutil.copy2(lock_file, lock_copy / lock_file.name)
    for component in lock["components"]:
        for patch in component.get("patches", []):
            destination = lock_copy / "patches" / component["name"] / Path(patch["path"]).name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2((lock_file.parent / patch["path"]).resolve(), destination)

    provenance = {
        "schema_version": 1,
        "kind": "custom-gnustep-toolchain-provenance",
        "official": False,
        "official_note": "Built from a custom toolchain lock; not an official gnustep-cli managed artifact.",
        "name": lock["name"],
        "prefix": str(prefix_dir),
        "built_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "build_started_at": started,
        "lock": {
            "path": str(lock_file),
            "sha256": _sha256_file(lock_file),
            "copy": f"{LOCK_COPY_DIRNAME}/{lock_file.name}",
        },
        "build_host": build_host_identity(),
        "container": lock.get("container"),
        "install_domain": install_domain,
        "components": [
            {
                "name": component["name"],
                "url": component["url"],
                "ref": component.get("ref"),
                "revision": component["revision"],
                "resolved_commit": source["resolved_commit"],
                "configure_args": component.get("configure_args", []),
                "applied_patches": source["applied_patches"],
            }
            for component, source in zip(lock["components"], fetched)
        ],
        "elf_build_ids": elf_build_ids(prefix_dir),
    }
    (prefix_dir / PROVENANCE_FILENAME).write_text(json.dumps(provenance, indent=2) + "\n")
    return _result(
        command,
        True,
        "Custom toolchain built.",
        prefix=str(prefix_dir),
        provenance=str(prefix_dir / PROVENANCE_FILENAME),
        work_dir=str(work),
        elf_count=len(provenance["elf_build_ids"]),
    )


def custom_toolchain_lock_from_source_lock(source_lock: dict[str, Any], name: str) -> dict[str, Any]:
    """Start a custom lock from an official source lock (same pins, no changes)."""
    return {
        "schema_version": 1,
        "kind": LOCK_KIND,
        "name": name,
        "based_on": source_lock.get("target", {}).get("id"),
        "components": [
            {
                "name": component["name"],
                "url": component["url"],
                "revision": component["revision"],
                "configure_args": list(component.get("configure_args", [])),
                "patches": [],
            }
            for component in source_lock.get("components", [])
            if component.get("name") in COMPONENT_ORDER
        ],
    }
