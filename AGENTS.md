# AGENTS.md

## Project Purpose
- This repository is a fresh start for a new GNUstep CLI.
- The existing repository at `../gnustep-cli` is reference material only.
- Reuse prior discoveries from `../gnustep-cli` when helpful, but do not inherit its architecture by default.
- This project is intentionally rethinking the philosophy and design of the GNUstep CLI rather than incrementally evolving the old implementation.

## Top-Level Product Model
- The product has two separate interfaces:
- A bootstrap interface.
- A full interface.
- These two interfaces should appear to be the same CLI from the user's point of view.
- The bootstrap interface exists to get the user onto the full interface and to provide `doctor`.
- The full interface is the long-term CLI and should contain the actual feature implementation.

## Bootstrap Interface
- The bootstrap interface must support exactly two real operations:
- Install the full interface and its dependencies.
- Run `gnustep doctor`.
- The bootstrap interface should also expose the full command surface in help and command discovery even when most commands are unavailable.
- Unsupported commands in bootstrap must fail clearly and explain that the full interface/toolchain must be installed first.
- `--help` on bootstrap should show the full CLI shape, not a reduced bootstrap-only help view.
- The bootstrap installer should install the full interface into a user-specified directory.
- The default installation layout should follow GNUstep-style directory conventions.
- After installation, bootstrap should offer to make the installed binaries available on the default command path for future terminal sessions.

## Full Interface
- The full interface must be written as an Objective-C/GNUstep application.
- This is a deliberate project constraint, not an incidental implementation detail.
- Reasons:
- Adoption by the GNUstep development team is critical to project success.
- The codebase should primarily use technologies that GNUstep developers are likely to accept and contribute to.
- The full interface should begin with a deliberately small command set:
- `setup`
- `doctor`
- `build`
- `run`
- `new`
- `install`
- `remove`
- Do not expand command scope aggressively before these commands work well.
- `install` and `remove` will become a GNUstep package manager, but the package-manager design should be scoped in a later session.

## Bootstrap Language Strategy
- The bootstrap interface must not depend on GNUstep being preinstalled.
- Prefer an interpreted language or scripting environment so the project does not need to ship bootstrap binaries for every OS and CPU architecture.
- If necessary, separate bootstrap implementations for Windows and non-Windows are acceptable.
- Do not force a single bootstrap language across all platforms if doing so harms reliability or violates the base-install requirement.
- The bootstrap implementation choice for now is:
- Non-Windows bootstrap: POSIX `sh`.
- Windows bootstrap: PowerShell.
- On the `sh` side, network installation may rely on `curl` or `wget`.
- If neither `curl` nor `wget` is present, bootstrap must fail immediately with a clear error explaining that one of them is required to proceed.
- The bootstrap application should be treated as ephemeral.
- Once it has installed the full CLI and toolchain successfully, it is no longer required.
- It should be suitable for use as a copy/paste installer flow from the project website or similar distribution channels.
- Bootstrap should install the full CLI, help the user make it available on their command path, explain the next steps, and then explicitly tell the user that the bootstrap script may be deleted.
- Bootstrap should not become a permanent wrapper around the full CLI after installation.

## User Experience Contract
- Bootstrap and full should behave as similarly as possible.
- Help output, command names, option names, exit behavior, and user-facing terminology should be consistent between bootstrap and full.
- Differences should mostly be limited to capability availability.
- A user should not feel like they are learning two unrelated programs.
- If bootstrap modifies shell startup files for future PATH setup, it must also print the exact command the user can run in the current shell to use the installed CLI immediately.
- Do not assume bootstrap can reliably modify the live environment of the parent shell process for the current session.

## CLI Contract
- The top-level command form for v1 should be:
- `gnustep <command> [options] [args]`
- Do not introduce alternate top-level syntaxes in v1.
- Keep aliases minimal or avoid them entirely at first.
- The initial command set is:
- `setup`
- `doctor`
- `build`
- `run`
- `new`
- `install`
- `remove`
- The initial global options should be:
- `--help`
- `--version`
- `--json`
- `--verbose`
- `--quiet`
- `--yes`
- `gnustep --help` should show the full command list in both bootstrap and full.
- `gnustep <command> --help` should work consistently in both bootstrap and full, even for commands that are unavailable in bootstrap.

## Output Policy
- Human-readable output is the default output mode.
- Human-readable output is intended for people and is not a stability contract.
- Machine-readable output should be available through `--json`.
- `--json` output is a compatibility contract and should be treated as stable and versioned.
- Prefer providing a common JSON response envelope across commands rather than having completely unrelated JSON formats.
- Every JSON response should include a schema or format version field.
- Internal code must not parse human-readable output; machine-readable output should be generated from structured data directly.
- If a command has limited structured output in early versions, prefer returning a minimal common JSON envelope rather than rejecting `--json`.

## Exit Code Policy
- Keep the exit-code model intentionally small and consistent.
- Recommended v1 meanings:
- `0`: success.
- `1`: operational failure or requested action failed.
- `2`: usage or argument error.
- `3`: environment failure, unmet prerequisite, or command unavailable in bootstrap.
- `4`: compatibility or toolchain mismatch.
- `5`: internal error.
- Bootstrap should use the same exit-code meanings as the full CLI whenever possible.

## Tooling Philosophy
- The CLI should be a thin orchestration layer over existing GNUstep tools whenever possible.
- Do not reinvent existing GNUstep tooling just to centralize behavior inside this project.
- For the initial release:
- `build` and `run` should support GNUstep Make only.
- The CLI should wrap existing tools such as GNUstep Make and `openapp` rather than replacing them.
- Future versions may add support for other build systems such as CMake if those prove important in real GNUstep projects.

## Doctor Is a First-Class Feature
- `doctor` must be fully supported in both bootstrap and full interfaces.
- `doctor` is not a secondary diagnostic command; it is core product functionality.
- `doctor` should be defined before much of the rest of the CLI architecture, because it drives setup behavior and toolchain decisions.
- "Fully supported" does not mean both interfaces run every possible diagnostic probe.
- Bootstrap `doctor` is an installer-oriented environment classifier.
- Full `doctor` is the deep diagnostic interface and may execute richer validation that would not make sense in bootstrap.

## Shared Doctor Architecture
- Bootstrap and full must not have independent interpretations of system health.
- Because bootstrap may be implemented in shell while full is Objective-C, do not try to share `doctor` by sharing code in one implementation language.
- Instead, share `doctor` through a common specification, data model, and policy definition.
- Implement separate runners/executors for bootstrap and full against the same underlying `doctor` specification.
- The shared source of truth for `doctor` should describe checks declaratively whenever practical.
- Each check definition should describe applicability and execution capability explicitly rather than assuming both interfaces can run it.
- Keep one stable `doctor` vocabulary, one JSON envelope shape, and one set of check identifiers across interfaces.

## Doctor Scope Split
- Bootstrap `doctor` should answer the questions needed before or during installation.
- Full `doctor` should answer the deeper questions needed after installation and during ongoing CLI use.
- Bootstrap `doctor` should focus on:
- host identity
- downloader and bootstrap prerequisites
- privilege and install-target suitability
- PATH and shell-context issues relevant to setup
- coarse existing-toolchain detection
- coarse compatibility classification for managed artifact selection
- immediate next-step guidance for setup
- Full `doctor` should additionally handle:
- deep toolchain/runtime/ABI/feature detection
- compile/link/run probes when appropriate
- managed-install integrity and repair-oriented diagnostics
- package and workflow compatibility checks
- project or workspace diagnostics where applicable
- Do not force bootstrap to become a permanent all-purpose diagnostics wrapper after installation.

## Doctor Responsibilities
- `doctor` should inspect the local machine and answer:
- Is GNUstep present?
- Is a GNUstep toolchain already installed?
- What kind of toolchain is it?
- Is it working?
- Is it compatible with this CLI's published binaries and managed environment?
- Is the install target writable and usable?
- Is the machine ready for the requested CLI workflows?
- `doctor` should detect and classify existing toolchains rather than just reporting pass/fail.
- `doctor` should be treated as the canonical environment classifier for the CLI, not merely a lightweight preflight check.
- `doctor` should tell the user not only what is wrong, but also what the next sensible action is.
- In bootstrap, these responsibilities should be interpreted in terms of setup and managed-install readiness first.
- In the full CLI, these responsibilities extend to deep validation of the selected environment and installed toolchain.

## Doctor Execution Model
- `doctor` should run as a sequence of ordered phases.
- Recommended v1 phases:
- System identity.
- Tool discovery.
- GNUstep/toolchain classification.
- Functional validation.
- Compatibility evaluation.
- Remediation / next steps.
- System identity should detect the basic host environment such as OS, architecture, shell/path context, and other facts that influence installation and compatibility.
- Tool discovery should locate relevant external tools and prerequisites.
- On Unix-like bootstrap implementations, this includes checking for `curl` and `wget`.
- GNUstep/toolchain classification should determine whether GNUstep is present and what kind of toolchain is installed.
- Functional validation should distinguish between "installed" and "actually usable".
- Compatibility evaluation should compare the detected environment against the project's supported artifact/runtime matrix.
- Remediation should produce concrete next-step guidance for the user.
- Bootstrap may stop after coarse classification when that is sufficient to drive setup safely.
- Full `doctor` should be able to continue into richer validation phases.

## Doctor Behavior Rules
- `doctor` should be mostly read-only.
- `doctor` may perform narrowly scoped active validation when necessary, such as compiling and linking a minimal Objective-C probe program.
- `doctor` should not become a general-purpose repair or mutation command.
- Active validation should exist to confirm that a detected toolchain is actually functional, not merely present on disk.
- Active validation such as compile/link/run probes is primarily a full-CLI responsibility.
- Bootstrap should only run active validation when the check is narrowly scoped, cheap, and directly relevant to setup decisions.
- `doctor` output should separate:
- Overall health status.
- Environment classification.
- Individual checks and their results.
- Recommended next actions.
- Recommended environment classification states include:
- `no_toolchain`
- `toolchain_compatible`
- `toolchain_incompatible`
- `toolchain_broken`
- Recommended high-level overall result states include:
- `ok`
- `warning`
- `error`

## Doctor JSON Contract
- `doctor --json` should emit one stable, versioned JSON envelope.
- The JSON output should include five major sections:
- command metadata
- overall result
- detected environment
- check results
- remediation / next actions
- Recommended top-level fields include:
- `schema_version`
- `command`
- `cli_version`
- `ok`
- `status`
- `environment_classification`
- `summary`
- `status` should use stable values such as:
- `ok`
- `warning`
- `error`
- `environment_classification` should use stable values such as:
- `no_toolchain`
- `toolchain_compatible`
- `toolchain_incompatible`
- `toolchain_broken`

## Doctor Environment Section
- The `environment` section should contain detected or normalized facts, not high-level conclusions.
- It should capture host facts such as OS, architecture, layout detection, install prefixes, shell family, and toolchain facts.
- Toolchain facts should include compiler family, compiler version, toolchain flavor, Objective-C runtime, ABI, presence of GNUstep components, compile/link/run capability, and feature flags.
- On bootstrap-capable platforms, the environment section may also include bootstrap prerequisites such as downloader availability.

## Doctor Compatibility Section
- The `compatibility` section should report evaluation against a target artifact or requirement set.
- It should include:
- whether the environment is compatible
- the target kind and target identifier, when applicable
- machine-readable reasons for incompatibility
- warnings
- Keep compatibility conclusions separate from raw environment facts.

## Doctor Checks Section
- The `checks` section should contain the execution trace of individual doctor checks.
- Each check entry should include at least:
- `id`
- `title`
- `status`
- `severity`
- `message`
- Additional fields such as `details`, `duration_ms`, or `evidence` may be added later if useful.

## Doctor Actions Section
- The `actions` section should provide structured remediation and next-step guidance.
- `doctor` should not merely diagnose problems; it should propose the next sensible actions.
- Action entries should include a stable action kind, a priority or ordering hint, and a human-readable message.
- Recommended action kinds may include:
- `install_managed_toolchain`
- `use_existing_toolchain`
- `rerun_with_elevated_privileges`
- `install_downloader`
- `fix_path`
- `report_bug`

## Doctor JSON Rules
- Always emit the major sections of the JSON envelope even when some sections are empty.
- Machine-readable consumers must never need to parse English prose to understand results.
- Human-readable messages are useful, but the underlying state, reasons, warnings, and next actions must be represented structurally.
- Bootstrap and full should emit the same top-level JSON shape even when they do not execute the same subset of checks.
- Checks that are defined by the shared spec but not executable in bootstrap should be represented structurally as not run or unavailable in bootstrap rather than silently omitted when their absence would be misleading.

## Doctor Check Model
- Doctor checks should be represented in a common structured form rather than being scattered as ad hoc imperative logic.
- Each check should ideally define at least:
- A stable check identifier.
- A human-readable title.
- Applicability by platform.
- Applicability by interface: `bootstrap`, `full`, or both.
- Execution tier such as `bootstrap_required`, `bootstrap_optional`, or `full_only`.
- Severity: info, warning, error.
- Probe method or command.
- Expected condition.
- Failure message.
- Remediation guidance.
- This structured check model is the shared contract between bootstrap and full.

## Toolchain Detection Requirements
- If a machine already has a GNUstep toolchain installed by some other means, the CLI must inspect it rather than ignoring it.
- Detection should identify at least:
- Compiler family, such as `clang` or `gcc`.
- Compiler version when practical.
- Objective-C runtime characteristics, including whether `libobjc2` is present.
- GNUstep Make presence.
- Relevant GNUstep libraries/frameworks presence.
- Target architecture.
- Installation prefix or prefixes.
- Whether a minimal compile/link test succeeds.
- `doctor` should distinguish among:
- No toolchain detected.
- Existing toolchain detected and working.
- Existing toolchain detected but broken.
- Existing toolchain detected and working but incompatible with this CLI's published binaries.

## Compatibility Policy
- A working external toolchain is not automatically good enough.
- The CLI must determine whether the detected toolchain is compatible with the prebuilt binaries and runtime assumptions distributed by this project.
- Compatibility must be treated as a formal matrix, not as an informal guess.
- At minimum, compatibility evaluation should consider:
- OS.
- CPU architecture.
- Compiler family.
- Objective-C runtime / ABI expectations.
- GNUstep runtime assumptions relevant to shipped binaries.
- If the user has an existing working toolchain and it is compatible, the CLI should offer the option to use it instead of forcing a managed install.
- If the user has an existing working toolchain but it is incompatible with the binaries this project provides, the CLI must stop and explain the mismatch clearly.
- Example: if the machine has a GCC-based GNUstep environment but available prebuilt artifacts require Clang plus `libobjc2`, the CLI must treat that as an incompatibility and must not proceed as if the setup were valid.
- Never silently mix an external toolchain with managed binary artifacts unless that combination is explicitly marked as supported by the compatibility rules.
- Support should be artifact-backed, not aspirational.
- A toolchain/runtime combination is supported when the project has validated binaries for it or has otherwise explicitly marked it as supported.
- There is no policy reason to exclude GCC toolchains categorically, but GCC support requires corresponding validated builds and compatibility checks.
- If the full CLI is intended to run across both GCC and Clang ecosystems, the Objective-C source should avoid unnecessary reliance on language/runtime features that would make GCC builds impossible, unless the project explicitly chooses to maintain separate implementations or feature tiers.
- Compatibility needs to be evaluated separately at three layers:
- CLI compatibility.
- Toolchain compatibility.
- Package compatibility.
- A machine may be able to run the CLI while still being unable to use a particular package, depending on the package's declared requirements.
- Package metadata should eventually declare runtime/toolchain requirements such as whether `libobjc2` is required.
- The package manager must prevent installation or use of packages whose runtime/toolchain requirements are not satisfied by the selected environment.

## Compatibility Matrix Schema
- The compatibility system should be built around three related record types:
- An artifact record describing what the project publishes.
- An environment record describing what `doctor` detects on the local machine.
- A requirement record describing what the CLI itself or an installable package requires.
- Compatibility decisions should be expressed in terms of whether a detected environment satisfies a requirement and whether a published artifact targets that environment.
- Keep the schema explicit and data-driven rather than encoding compatibility as scattered special-case logic.

## Environment Record
- The detected environment should capture normalized facts such as:
- `os`
- `os_version` when useful
- `arch`
- `libc_family` when relevant on Linux
- `compiler_family`
- `compiler_version`
- `objc_runtime`
- `objc_abi`
- `gnustep_make`
- `gnustep_base`
- `gnustep_gui` when relevant
- `install_prefixes`
- `can_compile`
- `can_link`
- `can_run`
- `feature_flags`
- Recommended normalized values include:
- `os`: `linux`, `openbsd`, `windows`, later `macos`
- `compiler_family`: `clang`, `gcc`
- `objc_runtime`: `libobjc2`, `gcc_libobjc`, `unknown`
- `objc_abi`: `modern`, `legacy`, `unknown`

## Feature Flags
- Do not infer all capability from compiler family alone.
- The environment model should include explicit capability flags where practical.
- Early examples include:
- `objc2_syntax`
- `blocks`
- `arc`
- `nonfragile_abi`
- `associated_objects`
- `exceptions`
- This allows the CLI to explain compatibility in terms of actual capabilities rather than only toolchain brand names.

## Artifact Record
- Published artifacts should describe the environment they target.
- An artifact record should include fields such as:
- `name`
- `kind`
- `version`
- `os`
- `arch`
- `compiler_family`
- `objc_runtime`
- `objc_abi`
- `required_features`
- `gnustep_version_range` when needed
- `channel`
- integrity or signing metadata such as checksums and signatures
- The `kind` field should distinguish at least:
- `cli`
- `toolchain`
- later `package`

## Requirement Record
- Requirements for the CLI itself or for packages should be represented explicitly rather than as prose.
- A requirement record should include fields such as:
- `supported_os`
- `supported_arch`
- `supported_compiler_families`
- `supported_objc_runtimes`
- `supported_objc_abi`
- `required_features`
- `forbidden_features` when useful
- `gnustep_version_range` when needed
- Package compatibility should be evaluated primarily against these requirement records.

## Compatibility Evaluation Rules
- Separate detected facts from derived classification.
- Example detected facts:
- compiler family is `gcc`
- Objective-C runtime is `gcc_libobjc`
- `blocks` support is `false`
- Example derived result:
- environment classification is `toolchain_incompatible`
- reason is `missing_required_feature: blocks`
- Prefer capability-based compatibility checks over family-name checks when practical.
- Still retain compiler/runtime family in the model for artifact selection and clear user messaging.
- A standard compatibility result should include:
- Whether the environment is compatible.
- Reasons for incompatibility.
- Warnings.
- The selected artifact, if any.
- Suggested remediation.
- Do not hardcode distro-specific policy into the matrix itself.
- Debian or other distro behavior should appear as detected environment facts, not as special schema branches.

## Minimum Viable Matrix Dimensions
- At minimum, v1 compatibility decisions should consider:
- OS
- architecture
- compiler family
- Objective-C runtime
- Objective-C ABI level
- feature flags
- whether the environment can compile/link/run
- whether GNUstep Make is present

## Managed Artifact Targets
- The artifact target model should treat compiler/toolchain as a first-class dimension, not merely OS and architecture.
- Distinct managed targets may exist for combinations such as:
- `linux/amd64/clang`
- `openbsd/amd64/clang`
- `windows/amd64/msys2-clang64`
- `windows/amd64/msvc`
- In v1, the intended first-class managed artifact targets are:
- Linux `amd64` with Clang
- OpenBSD `amd64` with Clang
- Windows `amd64` with MSYS2 `clang64`
- Windows `amd64` with MSVC
- These targets should be treated as Tier 1 managed-install targets for the initial release.
- Anything outside this set may still be detected and classified by `doctor`, but should not be implied to be fully supported for managed installation in v1.

## GCC Support Policy
- GCC-based GNUstep environments should not be rejected as a matter of ideology.
- However, support claims must remain artifact-backed and capability-based.
- In v1, GCC support should be treated primarily as detection and interoperability support rather than guaranteed managed artifact coverage.
- The CLI should detect existing GCC-based GNUstep environments, classify their capabilities, and use them when they satisfy the requirements of the requested operation.
- If a GCC-based environment lacks capabilities required by a CLI feature, managed artifact, or package, the CLI must explain that clearly.
- If a workflow requires Clang-era or `libobjc2`-dependent capabilities, the CLI should say so explicitly and offer installation of a supported managed Clang-based toolchain when available.
- Do not claim blanket GCC support unless validated GCC-targeted artifacts are actually published and tested.

## Release Manifest and Artifact Index
- Bootstrap, `setup`, and future upgrade logic should consume a machine-readable release manifest rather than scraping release pages or inferring meaning from filenames.
- The release manifest should be authoritative for artifact discovery, compatibility matching, and verification.
- The initial official artifact store for v1 should be GitHub Releases.
- GitHub Releases should host the published full CLI artifacts, managed toolchain artifacts, checksums, and related release assets unless and until a different official artifact store is adopted explicitly.
- Even when GitHub Releases is the storage layer, bootstrap and setup should discover artifacts through the release manifest rather than scraping GitHub release pages or inferring semantics from asset names alone.
- The manifest format should be JSON and should be versioned from the beginning.
- Prefer one top-level manifest per release channel.
- Recommended top-level manifest fields include:
- `schema_version`
- `channel`
- `generated_at`
- `releases`
- Each release entry should include fields such as:
- `version`
- `notes_url`
- `status`
- `artifacts`
- Each artifact entry should include fields such as:
- `id`
- `kind`
- `version`
- `os`
- `arch`
- `compiler_family`
- `toolchain_flavor`
- `objc_runtime`
- `objc_abi`
- `required_features`
- `format`
- `url`
- integrity metadata such as `sha256`
- optional signature metadata
- optional size
- optional minimum bootstrap or installer version
- The `toolchain_flavor` field is important and should remain distinct from `compiler_family`, especially on Windows where environments such as `msys2-clang64` and `msvc` must not be conflated.
- Recommended initial artifact kinds include:
- `cli`
- `toolchain`
- Additional kinds such as `package-index` or `package` can be added later.
- The manifest may also include an explicit `requirements` object per artifact so that artifact selection can be driven by the same compatibility model used elsewhere in the project.
- Keep the initial manifest explicit and easy to debug even if that means some redundancy.
- Bootstrap and setup selection flow should conceptually be:
- fetch manifest
- validate schema version
- choose release/channel
- run `doctor`
- match environment against artifact requirements
- verify checksum/signature
- install the selected artifacts

## Package Acceptance and Build Policy
- Official packages should be accepted or rejected based on declarative metadata, automated validation, and human review.
- A package should be accepted into the official repository only when:
- required package metadata is present and valid
- compatibility requirements are correctly declared
- package-kind-specific policy checks pass
- integration assets and integration metadata are complete where required
- installation and removal behavior are clean and trackable
- a human reviewer approves the package
- A package should be rejected when metadata is missing or malformed, compatibility declarations are incorrect, integration requirements are incomplete, install/remove behavior is unsafe, or overall package quality is not adequate for the official repository.
- For official packages, the preferred model is source submission plus official builds.
- Maintainers should submit source provenance and package metadata rather than being required to provide the canonical official binaries themselves.
- Official build infrastructure should build package artifacts for supported targets, run validation and install/remove checks, and publish the resulting validated binaries into the official package index.
- Binary installation for end users may be the primary consumption path, while official package production should still be based on controlled builds and validation from source.
- Avoid relying exclusively on maintainer-provided prebuilt binaries for official package publication unless a stronger provenance and verification model is introduced later.

## Official Package Repository Layout
- Maintain one official package repository as the canonical source of package definitions.
- Organize the repository so that each package has its own directory named by a stable package identifier.
- A recommended layout is:
- `packages/<package-id>/package.json`
- optional `packages/<package-id>/README.md`
- optional `packages/<package-id>/assets/`
- optional `packages/<package-id>/patches/`
- optional `packages/<package-id>/tests/`
- `schemas/` for manifest schemas and validation rules
- `docs/` for submission and review documentation
- Keep canonical package definitions declarative and human-reviewable.
- Do not require maintainers to edit a giant central index file by hand.
- The published package index should be generated from package directories rather than maintained manually.

## Package Submission Workflow
- Package submission should happen through pull requests against the official package repository.
- The intended maintainer flow is:
- create or update a package directory
- run local package validation tooling
- open a pull request
- let CI run validation/build/install/remove checks
- receive human review
- merge and publish if approved
- Provide maintainer-facing CLI support such as:
- `gnustep package init`
- `gnustep package validate`
- Prefer a workflow where maintainers can get close to CI-green locally before opening a pull request.
- Pull requests should modify package-scoped files and assets, not hand-edited generated indexes.

## Package CI and Review Workflow
- CI for package submissions should be staged so failures are understandable.
- Recommended stages include:
- lint
- validate
- build
- verify
- Lint should cover schema validation, required metadata, package-kind policy, and basic asset presence.
- Validate should cover compatibility metadata, integration metadata, launcher/icon rules, and install layout policy.
- Build should fetch source and build official artifacts for relevant supported targets.
- Verify should install into a staging prefix, run smoke checks, remove the package, and confirm cleanup behavior where practical.
- Human review should focus on package fit, polish, defaults, and whether the package belongs in the official ecosystem.
- Humans should not be responsible for repetitive checks that automation can perform reliably.

## Package Publication Rules
- Publishing should happen from trusted merged package definitions, not directly from unreviewed pull requests.
- After merge, project-controlled automation should build or finalize trusted artifacts, publish them to the official artifact store, and regenerate the published package index or manifest.
- In v1, the default official artifact store should be GitHub Releases unless a different publication backend is explicitly adopted.
- Version updates should be ordinary pull requests updating the existing package directory, source metadata, and any related assets or compatibility declarations.

## Package Manifest Structure
- Use one common package manifest format with a small required core plus kind-specific required sections.
- This should provide one schema to teach, one validation system to implement, and one repository format to review.
- The initial package kinds should be:
- `gui-app`
- `cli-tool`
- `library`
- `template`
- Do not introduce additional package kinds in early versions unless a concrete need appears.

## Package Manifest Required Core
- Every package manifest should require at least:
- `schema_version`
- `id`
- `name`
- `version`
- `kind`
- `summary`
- `license`
- `maintainers`
- `source`
- `requirements`
- `artifacts`
- These fields are the minimum needed for identity, provenance, compatibility, and installation.
- Recommended but not strictly required fields include:
- `description`
- `homepage`
- `issues_url`
- `project_url`
- `dependencies`
- `provides`
- `conflicts`
- `replaces`

## Package Manifest Source, Requirements, and Artifacts
- The `source` section should require provenance fields such as:
- `type`
- `url`
- `sha256`
- The `requirements` section should reuse the same compatibility vocabulary as the CLI and should require fields such as:
- `supported_os`
- `supported_arch`
- `supported_compiler_families`
- `supported_objc_runtimes`
- `supported_objc_abi`
- `required_features`
- `forbidden_features`
- The `artifacts` section should describe installable payloads and should require fields such as:
- `id`
- `os`
- `arch`
- `compiler_family`
- `toolchain_flavor`
- `objc_runtime`
- `objc_abi`
- `url`
- `sha256`

## Kind-Specific Package Requirements
- `gui-app` packages should require:
- `integration.display_name`
- `integration.icon`
- `integration.categories`
- `integration.launcher`
- `install.primary_executable`
- `cli-tool` packages should require:
- `install.executables`
- `library` packages should require:
- `install.library_files`
- `install.headers` when the package exposes public headers
- `template` packages should require:
- `install.template_root`
- metadata describing the type of template being installed
- GUI integration requirements should not apply to `cli-tool`, `library`, or `template` packages unless there is a specific reason.

## Package Install Section
- The package manifest should include a controlled `install` section.
- The `install` section should describe intent and trackable outputs rather than embedding arbitrary imperative packaging logic.
- Relevant fields may include:
- `strategy`
- `prefix_layout`
- `primary_executable` or equivalent
- declared executable, library, header, or template paths
- file ownership or tracking information needed to build an installed-files manifest
- Avoid arbitrary install scripting or unconstrained post-install hooks in v1.

## Package Integration Policy
- Maintainers should declare integration intent and supply required assets, but the packaging system should generate standard platform integration artifacts where practical.
- For `gui-app` packages, the maintainer should provide icon and display metadata while repository tooling generates or standardizes desktop/start-menu integration artifacts.
- This is how the project should balance low submission friction with consistent package quality.

## Package Validation Blocking Rules
- Validation and review should fail when required fields for the package kind are missing.
- Validation and review should fail when compatibility metadata is invalid or incomplete.
- Validation and review should fail when a `gui-app` lacks required launcher or icon metadata.
- Validation and review should fail when a `cli-tool` lacks declared executables.
- Validation and review should fail when the install section cannot produce a clean, trackable installed-files manifest.
- Validation and review should fail when unsupported arbitrary install hooks or similarly unconstrained behavior are introduced into the package format.

## Setup Command Contract
- `setup` should be the primary onboarding command in both bootstrap and full interfaces.
- In bootstrap, `setup` should perform the full installation handoff into the managed environment.
- In the full CLI, `setup` should primarily re-evaluate environment state, install or switch managed components when needed, and repair incomplete managed installations.
- The recommended high-level `setup` flow is:
- run `doctor`
- classify existing toolchain and compatibility state
- determine install scope and target root
- enforce privilege rules for the requested scope
- fetch the release manifest
- select the appropriate CLI and toolchain artifacts
- verify integrity metadata
- install into the managed GNUstep layout
- offer PATH integration
- print next steps
- `setup` should not duplicate environment-detection logic outside the shared `doctor` model.
- `setup --json` should report the selected plan, selected artifacts, final outcome, and next actions in machine-readable form.

## Build Command Policy
- `build` should be a thin wrapper around GNUstep Make in the initial implementation.
- Do not attempt to replace GNUstep Make with custom build orchestration in v1.
- `build` should operate on the current project directory by default.
- Project discovery should be conservative and convention-based.
- If the current directory does not look like a supported GNUstep Make project, `build` should fail clearly rather than guessing aggressively.
- `build` may later gain explicit project-file or project-root arguments, but v1 should prioritize predictable behavior over flexible inference.
- `build --json` should report the detected project type, invoked backend, exit status, and key produced outputs when practical.

## Run Command Policy
- `run` should be a thin wrapper over the existing GNUstep execution model such as `openapp` where appropriate.
- `run` should default to running the primary build product of the current project.
- If the target to run is ambiguous, `run` should fail clearly and explain how to disambiguate.
- `run` should not attempt to invent a parallel process model beyond what existing GNUstep tools and conventions already support.
- `run --json` should report what target was selected, what execution backend was used, and the resulting exit status.

## New Command Policy
- `new` should create only a very small set of high-quality templates in v1.
- Prefer a few polished templates over many mediocre ones.
- Recommended initial template targets are:
- a GUI application
- a command-line tool
- possibly a library template if it can be done cleanly
- `new` should generate projects that already align with the packaging and integration expectations of this CLI where practical.
- Generated projects should include enough metadata or placeholders to make later package submission easier.
- Do not overdesign the template system in v1; keep it explicit and curated.

## Package Dependency Policy
- Keep dependency handling intentionally simple in v1.
- Dependencies should be declared explicitly in package metadata using package identifiers and conservative version constraints.
- Prefer exact or minimum-version constraints in early versions.
- Avoid a complex SAT-style dependency solver in v1.
- Package installation should fail clearly when dependencies are missing, unsatisfied, or incompatible with the selected environment.
- Dependency rules should remain deterministic and easy to explain.

## Package Index Schema Policy
- The published package index should be generated from the official package repository.
- The package index format should be JSON and versioned.
- It should contain enough information for package discovery, compatibility matching, dependency resolution, and artifact selection.
- Recommended top-level fields include:
- `schema_version`
- `channel`
- `generated_at`
- `packages`
- Each package entry should include core metadata, compatibility requirements, available artifacts, and dependency declarations.
- Keep the package index readable and explicit even if that introduces some redundancy.

## Package Install Transaction Policy
- Package installation should be transactional to the extent practical.
- The installer should stage work, verify artifacts, and only finalize the install when all required steps succeed.
- Installed files must be tracked in a manifest so removal and upgrade operations are reliable.
- Partial installs should be either rolled back automatically or left in a clearly recoverable state with explicit remediation instructions.
- Package installation should target the managed environment only, not arbitrary system locations.

## Package Remove Semantics
- `remove` should only remove files owned by the selected managed package installation.
- Removal should consult the installed-files manifest and must not delete unrelated files.
- If a package is still required by installed dependents, `remove` should fail clearly unless and until a deliberate override policy is designed.
- Removal should clean up generated integration artifacts such as launchers and shortcuts that belong to the package.
- Removal should leave the managed environment consistent and auditable.

## Official Build and Release Infrastructure
- Official artifacts for the CLI, toolchains, and packages should be built by project-controlled automation.
- Build infrastructure should produce reproducible or at least consistently generated release artifacts for supported targets.
- Build pipelines should run validation, smoke tests, install tests, and removal tests where practical before publication.
- Supported targets should map directly to explicit build jobs rather than loose best-effort behavior.
- The project should prefer controlled CI/release infrastructure over ad hoc maintainer-local release processes.

## Artifact Hosting and Verification
- Official artifacts should be hosted from a stable project-controlled location.
- Every published artifact must have checksum metadata, at minimum.
- Signature support should be added when practical, but checksum verification is the minimum requirement.
- Bootstrap and the full CLI should verify integrity metadata before installation.
- Artifact URLs should be discoverable through the release manifest and package index rather than hardcoded in client logic.

## Update and Upgrade Policy
- The full CLI and managed toolchains should be independently versioned even if `setup` commonly installs them together.
- Upgrades should consult the release manifest and package index rather than relying on implicit latest-version behavior alone.
- Upgrade operations should preserve the managed environment or fail in a recoverable way.
- Do not perform silent major behavior changes during upgrade without explicit user action.
- Keep downgrade support out of scope for v1 unless a concrete need forces it.

## Configuration Model
- Prefer a small explicit configuration model in v1.
- Configuration should support at least:
- default install scope
- default managed root
- selected release channel
- selected toolchain preference when more than one compatible choice exists
- preferred package source or package channel later
- Configuration precedence should be:
- command-line flags
- environment variables
- config files
- built-in defaults
- Configuration storage should follow the platform-specific config locations already defined for this project.

## Logging and Diagnostics
- Human-readable logging should default to concise, actionable output.
- `--verbose` should increase diagnostic detail.
- `--quiet` should suppress nonessential informational output.
- `--json` should provide structured output instead of interleaved human logging for command results.
- Internal diagnostic logs may be written to project-controlled state or log locations later, but the initial focus should be on high-quality command output and reproducible failure messages.

## Test Strategy
- The project should maintain automated tests for both bootstrap and full CLI behavior.
- Shared policy and schema logic should be tested independently from command runners where practical.
- The test strategy should include:
- unit tests for parsing, selection, and compatibility logic
- integration tests for `doctor`, `setup`, `build`, `run`, and package operations
- staging/install/remove tests against managed prefixes
- matrix validation across the supported Tier 1 targets
- Test coverage should focus first on environment detection, artifact selection, install/remove safety, and package validation rules.

## Windows Integration Policy
- Windows is a first-class target with distinct managed environments for MSYS2 `clang64` and MSVC.
- The Windows bootstrap implementation should use PowerShell.
- For GUI packages on Windows, the package system should manage Start Menu integration and related shell-visible metadata where appropriate.
- Global Windows installs should follow the same privilege policy as other platforms: require that the process is already elevated, and fail clearly otherwise.
- Do not collapse MSYS2 and MSVC into one generic Windows environment in compatibility logic or artifact selection.

## Schema Drafting Policy
- The release manifest schema, package manifest schema, package index schema, and doctor JSON schema should each be written down explicitly as versioned JSON contracts.
- Keep the initial schemas narrow, explicit, and debuggable.
- Prefer compatibility-preserving evolution over frequent breaking schema changes.
- When a schema changes incompatibly, bump its schema version clearly and handle mismatches explicitly.

## Governance and Review Policy
- Official package acceptance should remain curated.
- The project should prefer a smaller high-quality official package set over a larger low-quality one.
- Supported targets should be defined explicitly and reviewed deliberately rather than expanding informally.
- Human review should focus on quality, ecosystem fit, and user experience while automation handles mechanical policy checks.
- Reuse from `../gnustep-cli` is allowed when helpful, but all reused behavior should still satisfy the design constraints documented in this file.

## User Education and Migration Messaging
- The CLI should anticipate common beginner mistakes and explain them clearly.
- One expected case is a user on Debian or a similar system who installs GNUstep packages from the distro repositories and ends up with a GCC-based toolchain.
- If bootstrap or full detects that the user has only a GCC-based GNUstep toolchain installed, the CLI should explain in plain language that this environment may not support Objective-C 2.0 features such as blocks.
- In that situation, the CLI should also explain that those features require a Clang-based toolchain with the appropriate runtime support and should offer installation of a supported Clang-based managed toolchain when available.
- This messaging should be explicit and educational, not merely a terse incompatibility error.

## Setup Flow Expectations
- `setup` and `doctor` are the only commands that should function in bootstrap.
- `setup` should rely on `doctor` output and compatibility classification rather than duplicating environment-detection logic.
- The expected high-level flow is:
- Detect existing toolchain state.
- Classify health and compatibility.
- If no toolchain exists, offer installation.
- If a compatible toolchain exists, offer the user the choice to use it or install a managed one.
- If an incompatible toolchain exists, explain why it cannot be used with the published binaries and offer supported alternatives.
- If a broken toolchain exists, explain the breakage and recommend repair or managed installation.

## Package Manager Scope
- `install` and `remove` are reserved for the GNUstep package manager component.
- The package-manager design is intentionally deferred.
- Do not overdesign package management before `setup`, `doctor`, `build`, `run`, and `new` are solid.

## Platform Direction
- Initial focus is non-macOS GNUstep environments.
- Future versions should support macOS.
- On macOS, the long-term direction is for the package manager to install applications against Apple APIs rather than GNUstep.
- Do not let future macOS support distort the initial GNUstep-focused architecture.

## Repository Working Rules
- Before building new mechanisms from scratch, inspect `../gnustep-cli` for useful prior art and lessons.
- Prefer architecture notes, specs, and shared schemas when behavior must be consistent across bootstrap and full implementations.
- Keep the early implementation narrow and correct rather than broad and speculative.
- Favor explicit compatibility checks and explicit user choices over hidden heuristics.

## Installation Layout Policy
- For managed installations performed by this CLI, support only the traditional GNUstep `gnustep` filesystem layout in the initial implementation.
- Do not support multiple managed installation layouts in v1 unless a concrete need appears.
- This is an intentional simplification to keep installation, repair, removal, and future package-management behavior predictable.
- The managed installation should preserve a GNUstep-style directory structure inside a user-chosen installation prefix.
- Do not use distro/system packaging layouts such as `fhs-system` or `debian` for managed installations by this CLI.
- Support for `fhs` as a managed installation layout can be considered later, but it is not part of the initial scope.

## Layout Detection Versus Layout Management
- Distinguish between layouts the CLI can manage and layouts the CLI can detect.
- Managed installation support may be narrow and opinionated.
- Detection support for pre-existing toolchains should be broader.
- The fact that the CLI manages only the `gnustep` layout initially must not prevent it from detecting and classifying existing toolchains installed in other layouts.
- At minimum, toolchain detection should aim to recognize common existing layouts such as:
- `gnustep`
- `fhs`
- `fhs-system`
- `debian`
- Additional historical or specialized layouts such as `apple`, `mac`, `next`, `gershwin`, and `standalone` are lower priority for early detection support unless they become relevant to actual users.

## Managed Install Roots
- Managed installations should default to per-user scope rather than system-wide scope.
- On Unix-like systems, the recommended default per-user managed install root is:
- `~/.local/share/gnustep-cli`
- On Unix-like systems, the recommended default system-wide managed install root is:
- `/opt/gnustep-cli`
- Do not default managed installs into `/usr` or `/usr/local`.
- On Windows, the recommended default per-user managed install root is:
- `%LOCALAPPDATA%\\gnustep-cli`
- On Windows, the recommended default system-wide managed install root is:
- `%ProgramFiles%\\gnustep-cli`
- The managed install root should contain the GNUstep-layout installation tree and project-owned runtime artifacts.
- Configuration, cache, and mutable state should be tracked separately from the managed toolchain tree when practical.
- Recommended supporting locations include:
- Unix-like config: `~/.config/gnustep-cli`
- Unix-like cache: `~/.cache/gnustep-cli`
- Unix-like state: `~/.local/state/gnustep-cli` when available
- Windows config: `%APPDATA%\\gnustep-cli`
- Windows cache: `%LOCALAPPDATA%\\gnustep-cli\\Cache`
- Windows state: `%LOCALAPPDATA%\\gnustep-cli\\State`

## Privilege Policy
- Use the simplest robust privilege model.
- Per-user installs are the default path.
- System-wide installs are supported only when the process is already running with sufficient privileges.
- Do not implement automatic privilege elevation flows in v1.
- If a user requests a system-wide install without sufficient privileges, fail early and cleanly before partial installation work is performed.
- In that situation, explain clearly that elevated privileges are required and tell the user exactly how to rerun the command appropriately for the host platform.
- Favor a clear restart instruction over trying to recover implicitly from a partially privileged execution context.
