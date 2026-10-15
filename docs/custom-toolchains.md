# Custom GNUstep Toolchains

A custom toolchain is a GNUstep toolchain built from a **custom toolchain lock**:
a JSON file, usually kept in the consuming project's repository, that pins every
component to a git URL and commit and may add configure arguments and patches.
Use it when an application needs GNUstep libraries that differ from the official
managed recipe, for example a libs-gui built with fewer optional dependencies or
a libs-back carrying theme patches.

Custom toolchains are **not official gnustep-cli artifacts**. Locks may point at
forks and carry local patches, so their output is never published as a managed
toolchain, and `gnustep setup` / `gnustep update` never manage it. The builder
marks this in the provenance it writes (`"official": false`).

## Lock format

```json
{
  "schema_version": 1,
  "kind": "custom-toolchain-lock",
  "name": "lindirstat",
  "install_domain": "LOCAL",
  "container": {
    "recipe": "linux-amd64-clang",
    "apt_packages": []
  },
  "components": [
    {"name": "libobjc2", "url": "https://github.com/gnustep/libobjc2.git", "revision": "<40-hex commit>", "configure_args": [], "patches": []},
    {"name": "libdispatch", "url": "...", "revision": "...", "configure_args": [], "patches": []},
    {"name": "tools-make", "url": "...", "revision": "...", "configure_args": [], "patches": []},
    {"name": "libs-base", "url": "...", "revision": "...", "configure_args": [], "patches": []},
    {"name": "libs-corebase", "url": "...", "revision": "...", "configure_args": [], "patches": []},
    {
      "name": "libs-gui",
      "url": "https://github.com/<fork>/libs-gui.git",
      "ref": "csd-series",
      "revision": "<40-hex commit on that branch>",
      "configure_args": ["--disable-movie", "--disable-sound"],
      "patches": []
    },
    {
      "name": "libs-back",
      "url": "...",
      "revision": "...",
      "configure_args": [],
      "patches": [{"path": "patches/libs-back/0001-adwaita-csd.patch", "sha256": "<64-hex>"}]
    }
  ]
}
```

- Components build in this order: `libobjc2`, `libdispatch`, `tools-make`,
  `libs-base`, `libs-corebase`, `libs-gui`, `libs-back`. The first four are
  required. `libs-corebase`, `libs-gui`, and `libs-back` are optional, and
  `libs-back` requires `libs-gui`.
- `revision` must be a full commit. `ref` is optional; it names the branch or
  tag to fetch when the server does not allow fetching a bare commit. The
  checked-out commit must equal `revision`.
- `configure_args` are appended after the official recipe's base flags. They are
  CMake arguments for `libobjc2` and `libdispatch`, and `./configure` arguments
  for `tools-make` and the GNUstep libraries.
- `patches` are applied in order with `git apply`. Paths are relative to the lock
  file and must stay inside the lock's directory (the container wrapper mounts
  only that directory), and each patch's sha256 is checked before it is applied.
- `install_domain` is optional: `LOCAL` (the default, as in the official
  recipe) or `SYSTEM`. It sets `GNUSTEP_INSTALLATION_DOMAIN` for the GNUstep
  libraries, so libs-base, libs-corebase, libs-gui, and libs-back install under
  `<prefix>/Local/Library/...` or `<prefix>/System/Library/...`. Packagers that
  relocate a single GNUstep domain usually want `SYSTEM`. The value is recorded
  in the provenance.
- `container.apt_packages` lists extra Debian packages to install in the build
  image. libs-gui and libs-back enable optional features based on the libraries
  they find at configure time, so record those inputs here instead of relying on
  whatever happens to be installed.

To start from the official pins, convert an official source lock:

```sh
PYTHONPATH=src python3 -c 'import json,sys; from gnustep_cli_shared.custom_toolchain import custom_toolchain_lock_from_source_lock as f; print(json.dumps(f(json.load(open("toolchains/linux-amd64-clang/source-lock.json")), "my-app"), indent=2))' > my-app-toolchain.lock.json
```

## Building

Validate a lock:

```sh
python3 scripts/internal/build_infra.py --json validate-custom-toolchain-lock --lock path/to/gnustep-toolchain.lock.json
```

Build in the pinned Debian 13 image (recommended for release builds):

```sh
scripts/dev/build-custom-toolchain-in-container.sh path/to/gnustep-toolchain.lock.json /abs/path/to/prefix
```

The wrapper runs `docker` directly, so the invoking user needs Docker access.
On a GitHub-hosted `ubuntu-latest` runner a full seven-component build takes
about two minutes, including building the image; the Custom Toolchain
workflow (`.github/workflows/custom-toolchain.yml`) runs exactly this and is a
working example of a CI job, including smoke tests and caching-friendly
outputs. Cache the prefix keyed on the sha256 of the lock and its patches.

Build natively on the current host:

```sh
python3 scripts/internal/build_infra.py --json build-custom-toolchain \
  --lock path/to/gnustep-toolchain.lock.json --prefix /abs/path/to/prefix [--jobs N] [--work-dir DIR]
```

Add `--sources-only` to fetch, verify, and patch the sources without building.
Native builds strip `GNUSTEP_*`, `LD_LIBRARY_PATH`, compiler flag variables, and
`GNUstep` `PATH` entries from the environment, so a host GNUstep installation is
not picked up. They do still see the host's libraries, so optional features can
differ from a container build.

The prefix must be an absolute path. It must not overlap the gnustep-cli
managed roots (`~/.local/share/gnustep-cli`, `/opt/gnustep-cli`), and it must be
either empty or a previous custom toolchain build, which is replaced. Sources and
per-component logs go to `<prefix-parent>/.<prefix-name>-build` unless you pass
`--work-dir`.

## Using the toolchain

```sh
. /abs/path/to/prefix/System/Library/Makefiles/GNUstep.sh
export LD_LIBRARY_PATH=/abs/path/to/prefix/lib:$LD_LIBRARY_PATH
```

`<prefix>/lib` holds libobjc2, libdispatch, and BlocksRuntime, and `GNUstep.sh`
does not add it to the loader path. Link with `-L<prefix>/lib` when a link
step needs libdispatch.

## Provenance

`<prefix>/gnustep-toolchain-provenance.json` records:

- `official: false`
- the lock path and sha256, plus a copy of the lock and its patches under
  `<prefix>/gnustep-toolchain-lock/`
- for every component: URL, ref, pinned revision, resolved commit, configure
  arguments, and applied patches with their sha256
- the build host: distribution, glibc, kernel, compiler, cmake, make, and
  whether the build ran in a container
- `install_domain`: `LOCAL` or `SYSTEM`
- `elf_files`: every ELF file in the prefix (libraries, bundles, tools), keyed
  by prefix-relative path, with its `sha256` and GNU `build_id` (`null` when
  the file has none), so packagers can check that what they bundle is what
  was built. The build ID survives copying and relocation; the sha256 changes
  if a packager strips or patches the file, so compare build IDs first.
- `elf_build_ids`: the same build IDs as a flat path-to-ID map
