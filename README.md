# GNUstep CLI

`gnustep` is a command-line tool for installing a modern GNUstep toolchain and
working with GNUstep projects. It covers both installing a toolchain and the
day-to-day commands you run on a project:

- **`setup`** installs a managed Clang + libobjc2 GNUstep toolchain into your
  home directory. No root is required, and system packages are left alone.
- **`doctor`** inspects your machine and tells you whether an existing GNUstep
  install is usable, what kind it is, and what to do next.
- **`new`**, **`build`**, **`run`**, and **`clean`** create and drive GNUstep
  projects. They are thin wrappers over GNUstep Make.
- **`install`**, **`remove`**, **`list`**, and **`search`** manage packages
  from a signed package index.
- **`update`** keeps the CLI, toolchain, and packages current through staged,
  verified updates that can be rolled back.

Every command supports `--json` for scripting, with a stable, versioned output
format.

## Install

On Debian 13 (trixie) `amd64`/`arm64`, Ubuntu 24.04 LTS `amd64`/`arm64` (arm64 from v0.1.6)
or Ubuntu 26.04 LTS `amd64`:

```sh
curl -fsSL https://github.com/danjboyd/gnustep-cli-new/releases/latest/download/gnustep-bootstrap.sh | sh -s -- setup --user
```

This fetches the bootstrap of the newest stable release. To install a specific
release instead, use `releases/download/v<version>/gnustep-bootstrap.sh`; each
release's bootstrap installs that release.

The bootstrap script is a small POSIX `sh` program that needs only `curl` or
`wget`. It downloads the signed release manifest, checks it against a pinned
trust root, picks the artifacts that match your machine, checks their
checksums, and installs them under `~/.local/share/gnustep-cli`. After that it
prints the `PATH` line to use in your current shell. Once setup finishes you
can delete the bootstrap script, because the installed `gnustep` handles
updates from then on.

```console
$ curl -fsSL .../gnustep-bootstrap.sh | sh -s -- setup --user
setup: host prerequisites are derived from https://github.com/gnustep/tools-scripts
setup: to install GNUstep host prerequisites, run: apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl ... clang lld libicu-dev ...
setup: rerun bootstrap with --yes to let setup install these prerequisites automatically
setup: managed installation completed
setup: scope=user root=/home/you/.local/share/gnustep-cli
next: Run this in the current shell:
  export PATH="/home/you/.local/share/gnustep-cli/bin:/home/you/.local/share/gnustep-cli/Tools:/home/you/.local/share/gnustep-cli/System/Tools:$PATH"
next: The bootstrap script is no longer required and may be deleted.
```

Want to check your machine before installing anything? Run
`sh gnustep-bootstrap.sh doctor`. It makes no changes.

## Quick start

```console
$ gnustep doctor
doctor: A compatible GNUstep toolchain was detected.
doctor: status=ok classification=toolchain_compatible
doctor: host=linux/amd64
doctor: toolchain=clang runtime=libobjc2 abi=modern

$ gnustep new --list-templates
gui-app
cli-tool
library

$ gnustep new cli-tool HelloTool && cd HelloTool
Project template created.

$ gnustep build
Making all for tool HelloTool...
 Compiling file main.m ...
 Linking tool HelloTool ...
build: GNUstep project build completed.
build: backend=gnustep-make
build: project_type=tool target=HelloTool

$ gnustep run
run: project_type=tool target=HelloTool
run: invocation=./obj/HelloTool
Hello from CLI tool
```

`build` and `run` work on any existing GNUstep Make project (any directory with
a `GNUmakefile`), not only projects made with `gnustep new`. Add `--help` to
any command for its options, and `--json` for machine-readable output.

Check for updates:

```console
$ gnustep update --check
update: No updates were found.
```

The package commands are `list`, `search`, `install` and `remove`. From v0.1.4,
stable releases advertise a signed package index, which currently contains only
Arlen. On v0.1.0 through v0.1.3 they only work with an index you pass explicitly:
`gnustep list --index <path-or-url>`.

From v0.1.5, `gnustep update --check` finds newer stable releases. An install from
v0.1.4 or earlier doesn't find them: run the bootstrap above once to move it to the
newest release.

From v0.1.7, `gnustep update --yes` installs the newer release that the check
found, and fails if it couldn't. v0.1.5 and v0.1.6 instead reinstall the current
release and still report success, so move an install on either of those once by
naming the new release's manifest:

```sh
gnustep update --yes --manifest https://github.com/danjboyd/gnustep-cli-new/releases/download/v0.1.7/release-manifest.json
```

or run the bootstrap above again. Later updates work without `--manifest`.

On Windows, `gnustep update` in v0.1.5 and v0.1.6 doesn't complete a CLI update, with or
without `--manifest`: in testing it stopped with "Candidate release failed post-upgrade
smoke validation" and left the install unchanged. Run the bootstrap above again instead.

## Already have GNUstep?

You don't have to use the managed toolchain. `gnustep doctor` detects existing
installs (distro packages, `/usr/GNUstep`, custom prefixes) and classifies
them:

- **compatible**: the CLI uses your toolchain as it is.
- **incompatible**: the toolchain works, but it can't use the published
  binaries. A typical example is a distro GCC + `gcc_libobjc` toolchain, which
  lacks blocks, ARC, and the modern runtime. `doctor` explains what is missing
  and offers the managed Clang toolchain.
- **broken**: GNUstep is present but doesn't compile, link, or run.
  `doctor --full` runs real compile/link/run probes to show why.

## Supported platforms

| Platform | Status |
| --- | --- |
| Debian 13 `amd64`, `arm64` | Managed toolchain via the `sh` bootstrap |
| Ubuntu 26.04 LTS `amd64` | Managed toolchain via the `sh` bootstrap |
| Ubuntu 24.04 LTS `amd64` | Managed toolchain via the `sh` bootstrap (since v0.1.2) |
| Ubuntu 24.04 LTS `arm64` | Managed toolchain via the `sh` bootstrap (from v0.1.6) |
| OpenBSD `amd64` | Uses OpenBSD's native GNUstep packages |
| Windows `amd64` (MSYS2 `clang64`) | CLI and toolchain artifacts are published; the PowerShell installer is in preview |
| Fedora, Arch | `doctor` detection; native GCC toolchains are interoperability-only |
| Debian 12, macOS | Not supported |

The managed toolchain is built from pinned upstream sources: tools-make,
libobjc2, libdispatch, libs-base, libs-corebase, libs-gui, and libs-back. Pins,
checksums, and build flags are recorded in the release metadata. Known issues,
including the libobjc2 `@synchronized` first-lock race that is fixed upstream
and waiting on a tagged release, are in
[docs/support-matrix.md](docs/support-matrix.md).

## Documentation

- [Support matrix and known issues](docs/support-matrix.md)
- [Custom toolchains](docs/custom-toolchains.md)
- [Windows integration](docs/windows-integration.md)
- [Release status and validation evidence](docs/release-status.md)
- [Design and architecture policy](AGENTS.md)
- [Implementation roadmap](docs/implementation-roadmap.md)

## Development

The full CLI is an Objective-C/GNUstep application in `src/full-cli`. The
bootstrap scripts are in `scripts/bootstrap/`, and the shared schemas and
policy are in `schemas/` and `src/gnustep_cli_shared`.

Run the Python/shared test suite:

```bash
python3 -m unittest discover -s tests
```

Run the native Objective-C `tools-xctest` suite:

```bash
. ./scripts/dev/activate-tools-xctest.sh
./scripts/dev/run-native-tests.sh
```

Run the full regression gate:

```bash
python3 -c 'import sys; sys.path.insert(0, "src"); from gnustep_cli_shared.qa import regression_suite; import json; print(json.dumps(regression_suite(), indent=2))'
```

The committed package index must match the package manifests:

```bash
python3 scripts/internal/package_repo.py --json packages --output /tmp/package-index.json >/dev/null
diff -u packages/package-index.json /tmp/package-index.json
```

New features and bug fixes need automated tests in the same change. GitHub
Actions runs both suites on every push and pull request.

## License

GNUstep CLI is licensed under the GNU Lesser General Public License, version
2.1 or (at your option) any later version. See [LICENSE](LICENSE).
