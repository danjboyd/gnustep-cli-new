# Build, Run, New, And Package Tooling

This document records the Phase 7-9 implementation baseline and the required
multi-backend direction for GNUstep project workflows.

## Build Backend Model

`build` and `run` are GNUstep project commands. They must not be modeled as
GNUstep-Make-only commands, even though GNUstep Make is the first implemented
backend.

Supported backend records should include at least:

- stable backend ID
- detection marker
- support status for build, clean, and run
- selected invocation
- detection reason
- backend stdout/stderr and exit status when executed

Initial backend IDs:

- `gnustep-make`
- `cmake`
- `xcode-buildtool`

A user-facing selector alias `xcode` may map to `xcode-buildtool`, but JSON
should use the precise backend ID.

## Backend Detection

Detection markers:

- `GNUmakefile` -> `gnustep-make`
- `CMakeLists.txt` -> `cmake`
- `*.xcodeproj` -> `xcode-buildtool`
- `*.xcworkspace` -> future `xcode-buildtool` candidate after workspace behavior is validated

If exactly one supported marker is present, the CLI may auto-select that
backend. If multiple supported markers are present, the CLI should fail clearly
unless the user supplies `--build-system <id>`.

## GNUstep Make Backend

`GNUmakefile` is sufficient to mark a project as buildable by the
`gnustep-make` backend. `gnustep build` must not reject a GNUstep Make project
because the top-level makefile lacks direct `TOOL_NAME`, `APP_NAME`, or
`LIBRARY_NAME` assignments.

Classification hints:

- `TOOL_NAME` -> `project_type=tool`
- `APP_NAME` -> `project_type=app`
- `LIBRARY_NAME` -> `project_type=library`
- `SUBPROJECTS` or `aggregate.make` -> `project_type=aggregate`
- otherwise -> `project_type=unknown`

Classification is advisory for `build`; it must not block invoking `make`.
GNUstep Make remains the source of truth for whether the project is valid and
buildable.

Implementation status: the aggregate-project bug is fixed in both the shared
Python detector and the native Objective-C detector. A Gorm-style makefile with
`SUBPROJECTS` and `aggregate.make` is now classified as `aggregate` and remains
buildable.

Build invocation:

```text
make
```

Clean invocation:

```text
make clean
```

## CMake Backend Target

CMake is a core planned backend, not a speculative extension.

Marker:

```text
CMakeLists.txt
```

Planned configure/build/clean invocations:

```text
cmake -S <project-dir> -B <build-dir>
cmake --build <build-dir>
cmake --build <build-dir> --target clean
```

The CLI should wrap CMake and preserve CMake output rather than attempting to
parse or reinterpret CMake project language.

## libs-xcode/buildtool Backend Target

libs-xcode/buildtool is a core planned Xcode-project backend.

Backend ID:

```text
xcode-buildtool
```

Tool:

```text
buildtool
```

Markers:

```text
*.xcodeproj
*.xcworkspace    # future candidate after validation
```

Planned build/clean invocations should follow validated buildtool behavior. The
initial target model is:

```text
buildtool build <project.xcodeproj>
buildtool clean <project.xcodeproj>
```

If upstream buildtool's documented default invocation is more reliable for a
validated platform, the CLI may invoke `buildtool` from the project directory
instead while still reporting `backend=xcode-buildtool` and the exact
invocation in JSON.

Generation support such as makefile or CMake generation should be tracked as a
separate capability from direct build execution.

## Run

`run` currently plans execution for GNUstep Make projects when a runnable target
can be identified:

- tools via direct execution from `./obj/<tool-name>`
- apps via `openapp <AppName>.app`

Aggregate and unknown GNUstep Make projects are buildable, but they are not
runnable by default. `gnustep run` should fail with a targeted message asking
for a specific runnable target once target selection is supported.

## JSON Shape

Build/run JSON should include:

- `schema_version`
- `command`
- `ok`
- `status`
- `summary`
- `project.supported`
- `project.project_dir`
- `project.build_systems`
- `project.selected_build_system`
- `project.project_type`
- `project.detection_reason`
- `backend`
- `invocation`
- backend `stdout`, `stderr`, and `exit_status` when executed

Consumers must never need to parse human-readable output to determine backend
selection, ambiguity, project type, or backend failure details.

## New

`new` currently supports:

- `gui-app`
- `cli-tool`
- `library`

Generated projects include a minimal `package.json` placeholder to support later
packaging work. Initial templates may remain GNUstep Make templates, but the
project model must not prevent later CMake or xcode-buildtool templates.

## Package Tooling

- `gnustep package init` creates a package manifest skeleton.
- `gnustep package validate` checks required core fields and kind-specific requirements.
- Validation currently enforces the basic policy shape already defined in `AGENTS.md`.
