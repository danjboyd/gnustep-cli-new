# GNUstep CLI Implementation Roadmap

## Purpose

This roadmap breaks the project into numbered phases with lettered subphases so implementation can proceed deliberately and test coverage can remain ahead of complexity. The intent is to build the smallest coherent slices first, validate them hard, and avoid drifting into a partially working tool with unclear support boundaries.

Testing is a first-class requirement in every phase. Each phase should leave behind stable automated tests before the next phase expands scope.

## Current Release Direction

- The current release should not assume that every host uses a managed GNUstep toolchain.
- The product should prefer a platform-native packaged GNUstep environment when `doctor` and validation evidence show that it satisfies the CLI's runtime and capability requirements.
- Managed toolchains remain required for environments where the packaged path is missing capabilities, incompatible with the published artifacts, or not yet validated.
- Managed artifact publication policy is now source/input-lock driven: official managed runtime artifacts must come from pinned upstream source or explicitly pinned curated binary-input channels, not from ambient distro-installed GNUstep trees.
- Current host-copied or distro-derived managed artifacts should be treated as transitional validation artifacts until replaced by source-built upstream component pipelines with recorded provenance.
- Current-release native-toolchain discovery and validation are in scope for:
  - OpenBSD
  - Fedora
  - Debian
  - Arch
- Deferred future distro targets are:
  - openSUSE
  - RHEL-family distributions and clones
  - Alpine
- Current-release validation infrastructure should therefore prioritize the highest-leverage current-release targets before expanding to the deferred distro set.

## Current Release Critical Path

The numbered phase history below remains the project record, but the current
release should be driven from this shorter critical path. The repository is
past the skeleton stage: the native Objective-C command surface, package flows,
setup lifecycle, update lifecycle, release metadata tooling, and smoke-harness
contracts exist and have local regression coverage. The remaining release risk
is evidence, production trust, and automation rather than basic command
existence.

Current priority order:

1. Keep Phase 26 live smoke evidence current for the active Tier 1 release
   targets. As of April 27, 2026, the release-candidate smoke gate passes with
   the OpenBSD native-packaged report and the Windows MSYS2 `clang64` report.
2. Complete Phase 12/13 production hardening: CI-held production signing keys
   or signing service, automated host-backed release qualification, controlled
   signed package artifact build jobs, and real old-to-new published update
   dogfood including one `gnustep update all --yes` run.
3. Finish native Objective-C `doctor` deep-detection parity with the shared
   Python model before claiming the full CLI is the authoritative diagnostic
   implementation.
4. Rebuild final Tier 1 full-CLI artifacts from production build lanes rather
   than relying on local, staged, or prerelease evidence.
5. Keep package, setup, update, and release trust gates green while converting
   remaining operator-run validation into repeatable automation.

Non-blocking for the immediate release unless this roadmap is revised:

- warm-builder live orchestration beyond the current planning surface
- native byte-delta application beyond the current manifest/delta contract
- Windows `amd64/msvc`
- OpenBSD `arm64`
- Debian/Linux `arm64` publication

April 27, 2026 execution update:

- Production-like `gnustep update all --yes` remains the main live-evidence
  blocker, but the gate now validates a concrete evidence contract instead of
  accepting a bare `{"ok": true}` payload. See
  `docs/validation/update-all-production-like-evidence.md`.
- Production signing/trust-root work is wired into the release workflow and
  still requires real CI secrets or an external signing service before Phase 12
  can pass in production mode.
- The release workflow now enforces the Phase 26 release-candidate smoke gate
  and Phase 12/13 hardening gates before GitHub publication.
- Package artifact publication readiness is green for the current repository
  package set; controlled build-job promotion remains an operations/CI
  implementation task rather than a policy-model gap.
- Native/shared doctor regression coverage is green; full parity remains a
  release-risk item to finish before claiming the native full CLI as the
  authoritative diagnostic implementation.
- CI now runs on `master`, matching the current repository branch used for
  pushes.
- The production-like update-all evidence path now has an executable operator
  runner at `scripts/dev/run-update-all-production-like-validation.sh`; it
  bootstraps an old managed release, runs `gnustep update all --yes` against a
  target manifest, captures before/after state, validates the evidence JSON,
  and emits the file expected by the Phase 13 gate.
- Release evidence bundling now accepts the modern Phase 26 reports,
  update-all evidence, and trust-root fingerprints. The release workflow uploads
  the resulting evidence bundle as a GitHub Actions artifact before publishing.
- CI has a dedicated package-artifact publication gate job so package release
  readiness is checked outside the release workflow as well.
- Support-matrix claims were refreshed for the April 27 OpenBSD and Windows
  Phase 26 evidence. The remaining final support-claims audit should be limited
  to production-signed artifacts and any target whose evidence changes after
  the next release-candidate run.
- new deferred Linux distro families such as openSUSE, RHEL-family targets, and
  Alpine

The Windows-only `gnustep shell` command is treated as a diagnostic escape hatch
for the private MSYS2 `CLANG64` environment, not as part of the portable v1 core
workflow. It may remain visible while Windows managed-toolchain validation needs
it, but product docs and release claims should continue to center the portable
core commands: `setup`, `doctor`, `build`, `clean`, `run`, `new`, `install`,
`remove`, and `update`.

## Phase 1. Foundation And Specifications

### A. Repository Foundation
- Create the initial repository structure for source, tests, schemas, docs, and release metadata.
- Establish coding conventions, formatting rules, linting rules, and a baseline development workflow.
- Add a minimal top-level README describing the project and its architectural split between bootstrap and full CLI.

### B. Specification Capture
- Convert the architectural decisions in `AGENTS.md` into durable project documents where appropriate.
- Draft the first formal specifications for:
- release manifest schema
- package manifest schema
- package index schema
- `doctor --json` schema
- command contracts for `setup`, `doctor`, `build`, `run`, `new`, `install`, and `remove`

### C. Shared Vocabulary And Normalization
- Define canonical names and enums for:
- OS values
- architecture values
- compiler families
- toolchain flavors
- Objective-C runtimes
- ABI values
- feature flags
- status/result values
- compatibility reason codes
- Define normalization rules so bootstrap and full CLI classify environments identically.

### D. Test Infrastructure
- Set up baseline unit test infrastructure for the chosen bootstrap and full CLI implementation languages.
- Establish schema validation tests.
- Establish fixture-driven tests for compatibility normalization and result serialization.
- Add test helpers for golden output comparisons for both human-readable and JSON output.

### E. Exit Criteria
- Core specifications exist in versioned draft form.
- Shared enums and normalization rules are defined.
- Baseline unit test harnesses are in place and running in CI.

## Phase 2. Core Data Models And Schema Implementations

### A. Release Manifest Schema
- Implement the versioned JSON schema for release manifests.
- Build fixture examples for supported and unsupported artifacts.
- Validate artifact selection edge cases.
- Add signed-metadata fields for signatures, metadata versioning, expiry, snapshot/timestamp freshness, and delegated signing roles.
- Carry provenance-oriented fields for source revision, build identity, and artifact integrity metadata so consumers do not need to trust filenames or release-page layout.

### B. Doctor JSON Schema
- Implement the `doctor --json` schema and canonical sample outputs for:
- no toolchain detected
- compatible toolchain detected
- incompatible toolchain detected
- broken toolchain detected

### C. Package Manifest Schema
- Implement the common package manifest schema with kind-specific validation.
- Add validation rules for `gui-app`, `cli-tool`, `library`, and `template`.

### D. Package Index Schema
- Implement the generated package index schema.
- Ensure package metadata can be transformed into the published index format without ambiguity.
- Include signed-metadata, version, expiry, and revocation/denylist hooks so the package index is a security-critical repository document rather than a convenience listing.

### E. Shared Compatibility Engine
- Implement the compatibility evaluation model independent of CLI command runners.
- Ensure the engine can evaluate:
- environment versus artifact
- environment versus package requirements
- package dependency compatibility

### F. Testing
- Exhaustive unit tests for schema validation success and failure paths.
- Exhaustive unit tests for normalization and compatibility evaluation.
- Golden tests for serialized JSON outputs.
- Negative tests for malformed data, unknown enum values, and incompatible feature combinations.
- Contract tests for signed-metadata shape, expiry/version handling, and rollback/freeze protection semantics.

### G. Exit Criteria
- All core schemas exist and are validated in automated tests.
- Compatibility evaluation logic is implemented and independently testable.

## Phase 3. Bootstrap CLI Skeleton

### A. Unix Bootstrap Skeleton
- Implement the POSIX `sh` bootstrap entry point.
- Implement argument parsing for:
- `--help`
- `--version`
- `--json`
- `--verbose`
- `--quiet`
- `--yes`
- `setup`
- `doctor`

### B. Windows Bootstrap Skeleton
- Implement the PowerShell bootstrap entry point with the same command contract and option behavior.
- Plan Windows execution testing around short-lived libvirt-backed leases provisioned through the sister repository `../OracleTestVMs` and its `otvm` CLI rather than assuming a permanent local Windows environment.

### C. Shared Output And Exit-Code Behavior
- Ensure bootstrap follows the common exit-code policy.
- Ensure bootstrap help shows the full command surface and clearly marks unavailable commands.
- Ensure unsupported commands fail clearly and consistently.

### D. Downloader Detection
- On Unix-like systems, implement downloader detection for `curl` and `wget`.
- Fail cleanly when neither is available.
- On Windows, implement the corresponding bootstrap networking assumptions using PowerShell-native capabilities.

### G. Testing
- Unit tests or fixture-driven command tests for bootstrap argument parsing and help output.
- Cross-platform behavioral tests for unsupported-command messaging.
- Exit-code tests for success, usage errors, prerequisite failures, and incompatibility conditions.
- For Windows PowerShell validation, use `otvm`-provisioned short-lived `windows-2022` leases when live testing is needed.
- Windows live tests should always use a short lease TTL, destroy the lease on completion or failure, and use `otvm reap` as a backstop cleanup mechanism.

### H. Exit Criteria
- Both bootstrap implementations expose the agreed command surface.
- Bootstrap behavior is consistent enough for shared documentation and test expectations.

## Phase 4. Doctor Engine

### A. Host Identity Detection
- Implement OS, architecture, shell-family, and install-scope detection.
- Implement install-root candidate resolution.

### B. Tool Discovery
- Detect compiler tools, GNUstep tools, download tools, and relevant helper utilities.
- Normalize discovery results into the shared environment model.

### C. Layout Detection
- Detect common preexisting GNUstep layouts:
- `gnustep`
- `fhs`
- `fhs-system`
- `debian`
- Classify lower-priority or unknown layouts where possible without overcommitting support.

### D. Toolchain Classification
- Detect compiler family and version.
- Detect Objective-C runtime and ABI.
- Detect GNUstep Make and related components.
- Detect feature flags such as `blocks`, `arc`, and nonfragile ABI support where practical.

### E. Functional Validation
- Implement minimal compile, link, and run probes where applicable.
- Ensure probes are narrowly scoped and safe.

### F. Compatibility Evaluation
- Compare detected environments against:
- managed CLI artifact requirements
- managed toolchain artifact requirements
- package requirements model
- Emit structured compatibility reasons and warnings.

### G. Remediation Generation
- Produce prioritized next actions based on environment state.
- Include special guidance for common cases such as Debian GCC-only toolchains lacking modern Objective-C features.
- Include explicit guidance for OpenBSD when the packaged GNUstep environment is already compatible so users can reuse platform-native packages instead of defaulting immediately to a managed install.

### H. Testing
- Exhaustive fixture-driven unit tests for every detection classification state.
- Probe tests for compile/link/run capability classification.
- Compatibility reasoning tests for supported, unsupported, and partially supported environments.
- JSON contract tests for all major `doctor` outcomes.
- Regression tests for common user mistake scenarios.

### I. Exit Criteria
- `doctor` can classify and explain the primary environment states accurately.
- Bootstrap and future full CLI can consume the same doctor result model.
- Bootstrap `doctor` is explicitly limited to the installer-oriented subset of checks.
- Full `doctor` owns deep validation such as richer feature detection and compile/link/run probing.

## Phase 5. Setup And Managed Installation

### A. Install Planning
- Implement `setup` planning logic driven by `doctor`.
- Select install scope, managed root, and artifact targets.
- Enforce privilege rules for system-wide installs.
- Allow `setup` to prefer a compatible existing toolchain when policy says that is the better path than a managed install.
- On OpenBSD, explicitly evaluate whether the packaged GNUstep environment should be the preferred supported installation method before selecting a managed toolchain plan.

### B. Manifest Fetch And Verification
- Fetch the release manifest.
- Validate schema version.
- Select the release/channel and target artifacts.
- Verify checksums and, later, signatures if enabled.
- Pin one trusted root public-key set into bootstrap and full CLI so release-manifest and package-index trust does not depend on transport alone.
- Verify signatures, metadata version, expiry, and snapshot/timestamp freshness before trusting manifests or indexes.
- Reject rollback, freeze, key-mismatch, and unsigned-metadata scenarios explicitly rather than silently falling back to checksum-only behavior.

### C. Managed Filesystem Layout
- Implement the internal managed install tree under the selected root.
- Preserve the GNUstep layout for managed installations.
- Separate config, cache, and state from the toolchain tree.

### D. Installation Transactions
- Stage installs before finalizing.
- Track installed files.
- Ensure interrupted installs are recoverable.

### E. PATH Integration
- Implement shell startup file updates where appropriate.
- Emit the exact command the user can run immediately in the current shell.
- On Windows, implement equivalent environment integration guidance.

### F. Repair, Update, And Re-Run Behavior
- Ensure re-running `setup` is safe.
- Support repair of incomplete or outdated managed installations.
- Treat update checks and upgrades as full-CLI lifecycle behavior, not as repeated bootstrap execution.
- Define `gnustep update` as the canonical day-2 update command.
- Define `gnustep update --check` as a read-only manifest and package-index comparison flow.
- Define `gnustep update cli` as a staged, verified, rollback-capable activation flow for CLI and managed toolchain artifacts.
- Define `gnustep update packages` as a signed-index, compatibility-aware package upgrade flow.
- Define `gnustep update all` as the default coordinated CLI/toolchain plus package update flow.
- Do not introduce or document `gnustep setup --update`; existing setup lifecycle hooks are compatibility/internal recovery paths while `gnustep update` owns the user-facing UX.

### G. Testing
- Exhaustive unit tests for install planning and artifact selection.
- Integration tests for user-scope installs.
- Integration tests for system-scope privilege failure paths.
- Transaction/rollback tests.
- Re-run/repair tests.
- PATH integration tests for supported shells and Windows behavior.
- When validating Windows install behavior live, prefer `otvm create windows-2022 --ttl-hours <small>` plus explicit `destroy` in cleanup logic over any long-lived shared VM.
- Add OpenBSD tests that prove `setup` can choose a compatible packaged GNUstep environment without forcing a managed toolchain path.

### H. Exit Criteria
- A user can run bootstrap `setup`, receive a managed install, and hand off cleanly to the full CLI.

## Phase 6. Full CLI Skeleton In Objective-C/GNUstep

### A. Project Scaffolding
- Create the Objective-C/GNUstep application structure for the full CLI.
- Establish command dispatch, shared option parsing, and output modes.

### B. Shared Data/Policy Consumption
- Ensure the full CLI can consume the same schemas, manifests, and compatibility logic concepts defined earlier.
- Keep the full CLI aligned with bootstrap behavior and terminology.

### C. Help, Version, And Error Behavior
- Implement full help output and command-level help.
- Match bootstrap exit codes and output semantics.

### D. Doctor And Setup Parity
- Implement `doctor` and `setup` in the full CLI with contract parity relative to bootstrap where applicable.
- Preserve the same command shape, terminology, JSON envelope, and status meanings across interfaces.
- Do not require bootstrap and full to execute the same diagnostic depth.

### G. Testing
- Exhaustive unit tests for command dispatch, option parsing, JSON output, and exit-code behavior.
- Parity tests comparing bootstrap and full CLI behavior on overlapping functionality.
- Use `otvm` Windows leases for live PowerShell and Windows-specific full-CLI validation when local execution is not available.

### H. Exit Criteria
- The full CLI exists as the primary installed command surface with working `doctor` and `setup`.

## Phase 7. Build, Clean, And Run Commands

### A. Build Backend Model
- Model `build`, `clean`, and `run` as GNUstep project commands with explicit build backend candidates.
- Treat GNUstep Make as the first implemented backend, not as the only product concept.
- Track CMake and libs-xcode/buildtool as core backend targets from the start.
- Use stable backend IDs:
- `gnustep-make`
- `cmake`
- `xcode-buildtool`
- A user-facing selector alias `xcode` may map to `xcode-buildtool`.
- Detection should return all supported backend candidates rather than collapsing to a single GNUstep-Make-only project model.

### B. Backend Detection And Selection
- Detect GNUstep Make projects through `GNUmakefile`.
- Detect CMake projects through `CMakeLists.txt`.
- Detect libs-xcode/buildtool projects through `*.xcodeproj`; defer `*.xcworkspace` until workspace behavior is validated.
- Add `--build-system <id>` to select a backend explicitly.
- Auto-select only when exactly one supported backend marker is present.
- If multiple supported markers are present, fail clearly and ask the user to choose a backend.
- Preserve unsupported, unavailable, and ambiguous states structurally in JSON.

### C. GNUstep Make Backend
- Implement `gnustep-make` build as `make` and clean as `make clean`.
- Do not parse GNUstep Make syntax as a validity gate for `gnustep build`.
- A directory containing `GNUmakefile` is buildable by the `gnustep-make` backend.
- Parse `TOOL_NAME`, `APP_NAME`, `LIBRARY_NAME`, `SUBPROJECTS`, and `aggregate.make` only as classification hints.
- Classify aggregate projects as `project_type=aggregate` when `SUBPROJECTS` or `aggregate.make` is present.
- Aggregate and unknown GNUstep Make projects should be accepted by `build` and delegated to `make`.

### D. CMake Backend Target
- Track `cmake` as a core planned backend.
- Planned configure invocation: `cmake -S <project-dir> -B <build-dir>`.
- Planned build invocation: `cmake --build <build-dir>`.
- Planned clean invocation: `cmake --build <build-dir> --target clean`.
- Implementation should wrap CMake as the source of truth rather than reimplementing CMake project parsing.

### E. libs-xcode/buildtool Backend Target
- Track libs-xcode/buildtool as a core planned Xcode-project backend.
- Stable backend ID: `xcode-buildtool`.
- Tool: `buildtool` from `gnustep/libs-xcode`.
- Marker: `*.xcodeproj`; later `*.xcworkspace` after validation.
- Planned build invocation: `buildtool build <project.xcodeproj>` when that form is validated, or the documented buildtool default invocation when operating in a project directory.
- Planned clean invocation: `buildtool clean <project.xcodeproj>` when validated.
- Track buildtool generation support separately from build execution.

### F. Clean Command
- Implement `gnustep clean` as the canonical clean-only UX.
- Do not make `gnustep build --clean` the primary documented clean command because it is ambiguous as clean-then-build.
- Route clean through the selected backend clean operation and report selected backend, invocation, and exit status in JSON.
- For GNUstep Make, delegate to GNUstep Make clean targets rather than deleting build outputs directly.

### G. Run Command
- Implement `run` as a thin wrapper over the selected backend's runnable artifact model and GNUstep execution conventions such as `openapp`.
- Resolve and execute the primary run target only when it can be identified unambiguously.
- For aggregate or unknown GNUstep Make projects, fail with a targeted run-specific message rather than claiming the project is unsupported for build.

### G. JSON Output
- Implement structured output for `build --json` and `run --json`.
- Include `build_systems`, `selected_build_system`, `backend`, `invocation`, `project_type`, detection reason, exit status, stdout, and stderr where applicable.
- Backend-specific failures must be preserved structurally so consumers never need to parse human-readable output.

### H. Testing
- Unit tests for backend detection, backend selection, ambiguity handling, and command planning.
- Integration tests using fixture GNUstep Make projects, including tool, app, library, aggregate, and unknown GNUmakefile forms.
- Regression test using a Gorm-style aggregate GNUmakefile with `SUBPROJECTS` and `aggregate.make`.
- Fixture tests for CMake and `.xcodeproj` marker detection even before execution support is enabled.
- Failure-path tests for ambiguous or unavailable backend states.
- JSON output tests.

### I. Exit Criteria
- Help text describes `build` and `run` as GNUstep project commands rather than GNUstep-Make-only commands.
- `gnustep build` accepts any directory containing `GNUmakefile` and delegates to `make`.
- Aggregate GNUstep Make projects are classified and buildable.
- `gnustep run` fails clearly for aggregate or unknown target projects unless a runnable target is specified or inferred safely.
- Backend selection and ambiguity are represented consistently in human output and JSON.
- CMake and libs-xcode/buildtool are documented and tracked as core backend targets, even if execution support is staged after GNUstep Make.

### Phase 7 Follow-up Status
- The aggregate GNUstep Make regression is fixed in the shared Python model and native Objective-C CLI detector.
- `GNUmakefile` is now sufficient for `gnustep build` support; direct target variables are classification hints only.
- Aggregate projects using `SUBPROJECTS` or `aggregate.make` are classified as `project_type=aggregate`.
- Unknown GNUmakefile shapes are classified as `project_type=unknown` and remain buildable.
- `gnustep run` still rejects aggregate and unknown projects with a run-specific no-runnable-target message.
- Regression coverage exists in `tests/test_build_run_engine.py` and `src/full-cli/Tests/GSCommandRunnerTests.m`.

## Phase 8. New Command And Project Templates

### A. Template Inventory
- Define the minimal curated template set:
- GUI app
- CLI tool
- optional library template if quality is high enough

### B. Template Generation
- Implement `new` to create projects with sane defaults and package-manager-friendly metadata placeholders.

### C. Packaging Readiness Hooks
- Ensure generated projects include enough structure to support later package validation and submission.

### D. Testing
- Golden tests for generated project trees.
- Smoke build/run tests for generated templates.
- Validation tests ensuring generated projects can progress cleanly into packaging workflows.
- Add Windows template smoke validation through `otvm` leases if template behavior diverges meaningfully on Windows.

### E. Exit Criteria
- `new` produces polished starter projects aligned with the rest of the toolchain.

## Phase 9. Package Validation Tooling

### A. Maintainer-Facing Commands
- Implement:
- `gnustep package init`
- `gnustep package validate`

### B. Manifest Validation
- Validate common required fields and kind-specific required sections.

### C. Integration Validation
- Validate launcher metadata, icon metadata, categories, and executable declarations.
- Validate install layout and installed-files manifest generation.

### D. Compatibility Validation
- Validate package requirements and artifact metadata against the shared compatibility model.

### G. Testing
- Exhaustive schema and policy unit tests.
- Fixture tests for valid and invalid packages of every kind.
- Golden output tests for maintainer guidance and failure reports.

### H. Exit Criteria
- Maintainers can prepare and validate packages locally before submission.

## Phase 10. Package Repository And Publication Pipeline

### A. Official Package Repository
- Create the official package repository structure.
- Add schemas, docs, and CI scaffolding.
- Treat package metadata as security-sensitive source input and keep install behavior declarative by default rather than package-script-driven.

### B. Index Generation
- Implement generation of the published package index from per-package directories.

### C. Submission Workflow
- Document and automate the PR-based submission model.
- Ensure generated outputs are not hand-edited.
- Prefer maintainer submission of source provenance and metadata over maintainer-uploaded canonical binaries for official publication.

### D. Review Workflow
- Define review checklists and automation handoffs.
- Enforce package-policy checks that reject unsafe package behaviors early, especially arbitrary install/remove scripts or undeclared binary payload expectations.

### G. Testing
- Tests for package repository generation.
- CI fixture tests simulating package additions and updates.
- Tests for generated index correctness and determinism.

### H. Exit Criteria
- The official package repository can accept reviewed package submissions and generate a valid package index.
- Official package publication is source/provenance-driven rather than trusting arbitrary maintainer-provided binaries as canonical release artifacts.

### Phase 10 Execution Status
- The repository now contains a real `packages/` tree with a generated
  `packages/package-index.json` artifact.
- CI verifies that the committed package index matches the current package
  manifests exactly.

## Phase 11. Package Installation And Removal

### A. Install Command
- Implement `install` against the official package index.
- Resolve compatible artifacts for the selected environment.
- Enforce dependency and compatibility rules.

### B. Transactional Package Installation
- Stage package extraction and integration changes.
- Finalize only when validation succeeds.
- Verify signed package-index metadata, selected-artifact identity, and artifact hash before any extraction or activation step.

### C. Remove Command
- Implement `remove` using installed-files manifests and dependency safeguards.
- Remove generated integration artifacts cleanly.

### D. Package State Tracking
- Track installed packages, selected artifacts, dependency relationships, and owned files.
- Record enough trusted metadata to support revocation, denylisting, and forensic traceability of installed official artifacts later.

### G. Testing
- Exhaustive install/remove transaction tests.
- Dependency satisfaction and rejection tests.
- File ownership and cleanup tests.
- Upgrade/reinstall tests for packages.

### H. Exit Criteria
- Users can install and remove reviewed packages safely inside the managed environment.

## Phase 12. Official Build Infrastructure

### A. CLI Artifact Builds
- Implement project-controlled builds for supported CLI targets.

### B. Toolchain Artifact Builds
- Implement project-controlled managed toolchain artifact builds for Tier 1 targets.
- For source-built targets, build managed GNUstep/runtime components from pinned upstream source into the managed prefix rather than packaging host-installed distro trees.
- For curated binary-input targets such as Windows `msys2-clang64`, lock the exact package identities, package checksums, source channel, and assembly inputs before publication.

### C. Package Artifact Builds
- Implement official package builds from source and package metadata.
- Apply package-scoped downstream patches from reviewed manifest declarations after source verification and before invoking the selected build backend.
- Emit provenance attestations, source revision linkage, applied patch identities/digests, and artifact identities that can be signed and published alongside the package artifacts.

### D. Publishing Pipeline
- Publish artifacts, regenerate manifests and indexes, and stage releases by channel.
- Separate build and signing roles so long-lived signing keys are not exposed to ordinary developer workstations or ad hoc build environments.
- Sign release manifests and package indexes as first-class repository metadata rather than relying on colocated checksums alone.
- Support key rotation, revocation, and emergency denylisting from the publication path from day one.
- Preserve transparency and audit history for published manifests, package indexes, and security-sensitive release-state transitions.

### Phase 12 Execution Status
- The repository already had lower-level release helpers for bundling, staging,
  verification, qualification, and GitHub publish planning.
- Those helpers are now also exposed through a single controlled
  `prepare-github-release` workflow in `scripts/internal/build_infra.py` so one
  command can stage assets, verify checksums, qualify extracted artifacts, run
  optional bootstrap-to-full handoff validation, and emit the GitHub release
  publish plan.
- Fresh native CLI artifact production is no longer blocked locally by a hard
  `-ldispatch` dependency; the GNUmake path now links `libdispatch` and
  `BlocksRuntime` conditionally when they are actually present.
- Release and package-index trust gates now exist in automation-facing tooling:
  release metadata can be verified against an explicit trusted public key, and
  package indexes can emit provenance, validate provenance digests, and enforce
  OpenSSL-backed signatures for release publication.
- Windows public bootstrap setup now has durable JSONL phase tracing via
  `--trace` or `GNUSTEP_BOOTSTRAP_TRACE`; `GNUSTEP_BOOTSTRAP_KEEP_TEMP=1` keeps
  downloaded and extracted artifacts available for post-failure inspection.
- CI now verifies generated package-index determinism and runs the package-index
  trust gate in unsigned development mode; the release workflow enforces signed
  release metadata, signed package-index metadata, externally pinned release and
  package-index trust roots, and package artifact publication readiness before
  publication.
- Package artifact build planning now surfaces source-provenance, patch provenance, artifact-digest, signing, publishability, and production-readiness blockers per package and per artifact instead of emitting a loose artifact list that publication tooling must reinterpret. A package artifact publication gate fails release publication while blockers remain; the current `tools-xctest` package now has real Linux and OpenBSD dogfood artifacts with source provenance and verified artifact digests, and regression coverage includes a synthetic production-ready package manifest.
- Phase 12 is complete for local release-tooling execution: release trust gates, package-index trust gates, package artifact publication gates, tools-xctest release gates, no-bundled-Python qualification, and key-rotation drill helpers are implemented and covered by regression tests. The remaining Phase 12 work is external production hardening:
  - provision CI secrets or a signing service with production release and package-index keys
  - move host-backed qualification from operator-manual lanes into release automation
  - turn package artifact build plans into real controlled build jobs that produce signed artifacts
  - run live production-channel expiry, rollback, revocation, and key-rotation drills around production-like trust roots
- Phase 12 hardening status is now machine-checkable through `scripts/internal/build_infra.py --json phase12-production-hardening-status`. The gate composes explicit release trust roots, controlled-release validation, release key-rotation drills, and Phase 26 host-backed smoke evidence. A synthetic complete-evidence fixture can pass the gate in regression coverage; the April 27, 2026 run satisfies the host-backed Tier 1 smoke evidence input with the OpenBSD and Windows reports, and the refreshed dogfood release directory verifies in unsigned development mode. The real phase remains blocked on production trust roots/signatures and controlled package/release publication from production build lanes.

### G. Testing
- CI verification for every build target.
- Smoke install tests of published artifacts.
- Reproducibility or consistency checks where practical.
- Signature-verification, expiry, rollback, and compromised-key simulation tests for release-manifest and package-index consumption.
- Tier 1 Windows smoke validation should run against ephemeral `otvm` leases or an equivalent short-lived Windows execution environment rather than a permanently running VM.

### H. Exit Criteria
- Official artifacts are built and published through controlled automation.
- Official managed runtime artifacts have source locks or input locks, component inventories, provenance metadata, and qualification evidence matching the managed artifact source policy.

## Phase 13. Upgrade, Repair, And Lifecycle Operations

### A. Installed State And Channel Model
- Record installed CLI version, managed toolchain version, selected channel, release manifest identity, selected artifact IDs, active release path, previous release path, trust-root identity, and lifecycle status in managed state.
- Preserve compatibility with older state records where practical and classify unsupported old state clearly.

### B. Update Command Model
- Implement `gnustep update` as the canonical day-2 lifecycle command.
- `gnustep update` with no scope defaults to `gnustep update all` and shows a plan requiring confirmation unless `--yes` is supplied.
- Supported scopes are `cli`, `packages`, and `all`.
- `--check` makes any scope read-only and emits the same structured plan without mutation.
- Transitional `setup --check-updates` and `setup --upgrade` hooks delegate to the same lifecycle engine for compatibility and recovery coverage, but user help and docs point at `gnustep update`.
- Do not add or document `setup --update`.

### C. CLI/Toolchain Update
- Implement `gnustep update cli` for full CLI and managed toolchain updates.
- Fetch and verify the signed release manifest, evaluate metadata freshness and rollback/freeze protections, compare installed state against the latest compatible release, and emit a structured update plan.
- Stage the candidate CLI into a versioned release directory and activate it only after integrity checks and smoke validation pass.
- Update the managed toolchain when the selected release requires it.
- Keep CLI and managed toolchain artifacts independently versioned even when one update transaction installs both.

### D. Package Update
- Implement `gnustep update packages` for installed package upgrades.
- Refresh and verify the package index, select compatible newer artifacts for installed packages, verify artifact integrity/signatures, respect dependency/conflict policy, and upgrade packages transactionally.
- If package updates require a newer CLI/toolchain, fail with a structured next action for `gnustep update cli`; `gnustep update all` may apply the CLI/toolchain update first.

### E. Coordinated Update And Activation
- Implement `gnustep update all` as the dependency-safe coordinator for CLI/toolchain and package updates.
- Plan package updates against the post-update toolchain environment before applying them.
- Re-exec or instruct the user clearly if the running CLI cannot safely continue after self-update.
- Prefer a managed layout with `releases/<version>` plus a stable active pointer such as `current` rather than mutating the active runtime in place.
- Preserve the previous active release until the new release is confirmed healthy.

### F. Repair Operations
- Support recovery from partial installs, missing files, stale staging, failed activation, or interrupted upgrades.
- Require `setup --repair` to normalize lifecycle state before retrying an update when the managed root is marked `needs_repair`.

### G. Lifecycle State Handling
- Ensure state tracking remains consistent across installs, update checks, CLI/toolchain updates, package updates, removals, repairs, rollbacks, and interrupted operations.
- Keep package update state separate from CLI/toolchain update state while exposing both through the common `gnustep update` UX and metadata trust vocabulary.

### H. Testing
- Upgrade path tests from older manifests and artifacts.
- Native `tools-xctest` coverage for every `gnustep update` scope and mode: default `update`/`update all` plan mode, `update --check`, `update cli --check`, `update cli --yes`, `update packages --check`, `update packages --yes`, `update all --check`, and `update all --yes`.
- Read-only `gnustep update --check` tests for no-update, update-available, package-update-available, incompatible-update, stale-manifest, expired-metadata, revoked-release, rollback, freeze, and key-mismatch scenarios.
- JSON contract tests for update payloads, including `scope`, `mode`, `plan`, selected artifacts, package actions, compatibility blockers, transaction state, and next actions.
- Usage/argument tests for unknown update scopes, missing option values, unsupported options, confirmation-required plan mode, and bootstrap-unavailable `update` behavior.
- Repair tests for interrupted operations and corrupted state.
- Activation/rollback tests for failed downloads, checksum mismatch, failed extraction, failed smoke validation, failed active-pointer switch, and package transaction recovery.
- Package-update tests for version comparison, missing package index, package not found in index, incompatible artifact, unmet requirements, dependency/conflict preservation, idempotent no-update behavior, successful upgrade, and failed upgrade rollback that restores the previous package root and state record.
- Backward-compatibility tests for manifests and state records where supported.
- Built-executable smoke tests for `gnustep update --help`, `gnustep update --check --json`, and representative error paths, in addition to direct Objective-C method tests.
- OTVM dogfood from an older staged Debian install to a newer staged release using the canonical `gnustep update` command rather than setup lifecycle hooks.

### I. Exit Criteria
- Managed environments can be updated and repaired without fragile manual recovery.
- A user can install an older release, run `gnustep update --check`, run `gnustep update cli` or `gnustep update all`, and end with a verified newer active CLI while preserving rollback state. Package updates can be checked and applied through `gnustep update packages`.


### Phase 13 Execution Status
- Initial native lifecycle state is implemented for managed setup: the full CLI records installed CLI/toolchain version, channel, selected manifest, selected artifact IDs, active release path, previous release path, last lifecycle action, and health status in `state/cli-state.json`.
- Native `gnustep update` now owns the user-facing update engine: `update --check` is non-mutating and `update cli --yes` delegates to the transactional setup lifecycle machinery. Transitional setup hooks remain compatibility/internal coverage paths, not product UX.
- Native `gnustep update` is now wired as the canonical user-facing lifecycle command: `update --check`, `update cli`, `update packages`, and default `update all` produce structured JSON plans, and package updates can be checked and applied against the native installed-package state. Transitional setup hooks remain available for repair/rollback internals and compatibility tests, but dogfood validation now exercises `gnustep update`.
- The existing update engine reads installed state, evaluates the release manifest with the full `doctor` environment model, rejects downgrade manifests, expired metadata, revoked selected artifacts, frozen metadata, and manifest metadata older than the last accepted metadata, stages verified artifacts, smoke-validates the candidate release, records upgrade lifecycle state, and preserves the previous release path for rollback/recovery.
- Successful managed setup/upgrade now materializes `releases/<version>`, smoke-validates the candidate `bin/gnustep --version`, switches the stable `current` pointer, and writes the root `bin/gnustep` launcher as a pointer launcher into `current/bin/gnustep`.
- `gnustep setup --rollback` is implemented for managed roots with preserved previous-release state and records rollback completion in `state/cli-state.json`; rollback remains explicit recovery UX while `gnustep update` becomes the normal update UX. The Debian upgrade dogfood lane now exercises upgrade followed by rollback on a live lease.
- Regression coverage now includes update-available planning, downgrade rejection, expired metadata rejection, frozen older-manifest rejection, revoked selected-artifact rejection, needs-repair upgrade rejection, checksum rollback, stale transaction recovery, local artifact path staging, archive layout preservation, runtime-bundle double-wrap prevention, conflict rejection, smoke-validated pointer activation, explicit rollback, versioned-release snapshot creation, previous-release preservation, default `update all` planning, combined `update all --check`, `update cli --yes`, package-update rollback, update usage-error JSON, package-update human output, and built-executable `gnustep update` smoke tests.
- Phase 13 is complete for native dogfood: `gnustep update` owns check/apply UX for CLI, package, and default all-scope updates; rollback, stale transaction recovery, downgrade rejection, expired metadata rejection, revoked artifact rejection, and package-update rollback are covered. Remaining Phase 13 hardening is live old-to-new dogfood against two real published update-capable releases, one production-like `update all --yes` run covering both CLI/toolchain and package updates, and final signed metadata/key-mismatch cases that require production-like trust roots.
- Debian old-to-new VM dogfood automation is available at `scripts/dev/debian-upgrade-dogfood-validation.sh` and now stages old/new managed-built synthetic release pairs when release-candidate artifacts are not yet published in two update-capable versions. The current-pointer/rollback refresh passed this lane on April 20, 2026.
- Phase 13 hardening status is now machine-checkable through `scripts/internal/build_infra.py --json phase13-update-hardening-status`. The gate requires live old-to-new smoke reports containing `self-update-cli-only`, production-like `update all --yes` evidence, and a release-key mismatch/rotation drill. The April 27, 2026 run satisfies the old-to-new/self-update smoke evidence and signed metadata key-mismatch drill inputs using the refreshed dogfood release directory. The real phase remains blocked on one production-like `gnustep update all --yes` run that covers both CLI/toolchain and package update behavior.

## Phase 14. Cross-Platform Integration Polish

### A. Linux/OpenBSD Integration
- Finalize shell integration, desktop integration, and user messaging for Unix-like environments.
- Add platform hardening where practical:
  - use OpenBSD `pledge`/`unveil` around untrusted metadata parsing, archive extraction, and install/remove flows
  - use Linux equivalents such as `seccomp`, namespaces, or similar constrained-process models where available
- Structure the CLI so network access, filesystem mutation, and general process execution can be reduced after startup rather than remaining broadly available for the whole process lifetime.

### B. Windows Integration
- Finalize PowerShell bootstrap behavior, Start Menu integration, and Windows-specific messaging.
- Ensure MSYS2 and MSVC paths remain clearly separated.
- Use `otvm` for live Windows integration validation and ensure test procedures always destroy leases promptly after use.
- Investigate reduced-token or constrained child-process models for Windows-side archive handling and other high-risk operations where that hardening is practical.

### C. GUI Package Polish
- Standardize launcher generation, icon handling, and package integration rules across supported platforms.

### D. Testing
- Platform-specific integration tests.
- Launcher/shortcut generation tests.
- Regression tests for package polish expectations.

### E. Exit Criteria
- The user-facing integration details feel deliberate and polished across Tier 1 platforms.

## Phase 15. Hardening, QA, And Release Readiness

### A. Comprehensive Regression Suite
- Consolidate unit, integration, transaction, and schema tests into a release-gating suite.

### B. Stress And Failure Testing
- Add tests for interrupted downloads, partial extractions, corrupted manifests, missing dependencies, and conflicting state.
- Add adversarial tests for spoofed metadata, stale but validly signed metadata, malformed signatures, revoked artifacts, and intentionally unsafe package definitions.

### C. Documentation Polish
- Finalize user docs, maintainer docs, contribution docs, and operational docs.

### D. Beta Validation
- Run structured beta validation across supported targets and representative environments.

### E. Release Readiness Review
- Review supported-target claims, known limitations, package quality bar, and upgrade expectations.
- Review trust-root management, signing-role separation, key rotation drills, provenance coverage, and package-policy exceptions before any v1 security claims are made.

### H. Exit Criteria
- The project has a defensible v1 release candidate with broad automated test coverage and documented operational behavior.

## Phase 16. Managed Toolchain Component Locks And Linux Reference Build

### A. Source Lock And Input Manifests
- Define the source-lock format for source-built managed toolchains.
- Define the input-manifest format for curated binary-input targets such as Windows `msys2-clang64`.
- Record the exact v1 Unix-like core managed component set:
- `libobjc2`
- `libdispatch`
- `tools-make`
- `libs-base`
- `libs-corebase`
- `libs-gui`
- `libs-back`
- Record any platform-specific downstream patches explicitly rather than as undocumented operator knowledge.
- Record authoritative upstream repository URLs, exact tags/commits/archive digests, checksums, configure/build flags, and build identity for every source-built component.
- Treat distro packages as bootstrap prerequisites or native packaged validation inputs, not as canonical managed runtime contents.

### B. Linux `amd64/clang` Managed Toolchain Build
- Implement the first real managed toolchain build pipeline for Linux `amd64/clang`.
- Build the pinned component set into a staging prefix.
- Build GNUstep Make from `gnustep/tools-make` into the managed prefix instead of copying distro-generated Makefiles or `gnustep-config` output.
- Produce a toolchain manifest, source lock, component inventory, checksums, and archive artifact.

### B2. Linux `arm64/clang` Debian Managed Toolchain Build
- Add Debian/aarch64 as a managed build target for the full CLI, managed toolchain, and official packages.
- Use canonical target id `linux-arm64-clang` and canonical architecture value `arm64`, while documenting Debian/aarch64 as the initial host profile.
- Prefer `../OracleTestVMs` local libvirt/mac capacity for build and validation leases, falling back to OCI only when local capacity is unavailable.
- Keep publication disabled until source-built toolchain, full CLI, package artifacts, and host-backed install/remove validation pass on the target.

### C. Linux Validation
- Run `doctor` against the staged Linux managed toolchain.
- Build and run minimal GNUstep Make fixtures against the staged toolchain.
- Verify required capabilities such as compile, link, run, `blocks`, and the expected Objective-C runtime/ABI.

### D. Testing
- Exhaustive unit tests for source-lock parsing, normalization, and validation.
- Exhaustive unit tests for Linux build-plan generation and component inventory serialization.
- Integration tests that stage, archive, unpack, and validate a Linux managed toolchain artifact.
- Regression tests for missing component, wrong revision, patch drift, and runtime-capability mismatches.

### E. Exit Criteria
- Linux `amd64/clang` has a repeatable, project-controlled managed toolchain build that produces a validated release-style artifact.

### Phase 16 Execution Status
- Phase 16A is implemented in build infrastructure: source locks and curated input manifests have validators, generated metadata carries upstream URLs/revisions, and checked-in toolchain metadata is regenerated from those templates.
- Phase 16B is implemented for Linux `amd64/clang`: the pinned upstream source-build script builds `libobjc2`, `libdispatch`, `tools-make`, `libs-base`, `libs-corebase`, `libs-gui`, and `libs-back` into a managed staging prefix, then packages the result with `source-lock.json`, `component-inventory.json`, `toolchain-manifest.json`, and assembly metadata.
- Phase 16C is validated locally and on a fresh Debian 13 OTVM lease: the source-built artifact packages as `production_eligible = true`, passes host-origin path leakage audit after placeholder normalization, relocates into a release-style install root, and successfully drives installed CLI smoke, `doctor`, managed Foundation compile/run, `gnustep new`, `gnustep build`, `gnustep run`, and package install/remove through the installed native CLI.
- Phase 16D regression coverage includes source-lock validation, MSYS2 input-manifest validation, source-built Linux artifact packaging, release metadata propagation, archive metadata auditing, setup-time managed-prefix relocation, and host-origin GNUstep path leakage detection.
- The older host-derived Linux assembler remains available only as a transitional non-production path and marks its artifacts `production_eligible = false`.
- Phase 16 follow-up resolves the immediate Linux portability blocker by making the current `linux-amd64-clang` managed artifact explicitly Debian-scoped in generated release metadata, toolchain manifests, component inventories, and artifact selection. Ubuntu `amd64/clang` is now a separate distro-scoped target (`linux-ubuntu2404-amd64-clang`) with Docker-built managed CLI/toolchain artifacts published to the `v0.1.0-dev` prerelease and April 20, 2026 setup/doctor/package dogfood evidence. Fedora and Arch remain validated GCC/libobjc interoperability targets, and future managed Clang support there requires dependency closure or per-distro artifacts rather than reusing the Debian-scoped artifact.
- Phase 16.B2 is implemented at metadata/planning level: the build matrix, source lock, toolchain manifest, component inventory, generated build script, package target metadata, and regression coverage now exist for `linux-arm64-clang`. Publication remains disabled until a Debian/aarch64 host-backed build and install/remove validation pass. Interim validation can use the new `../OracleTestVMs` `ubuntu-24.04-aarch64` profile because Ubuntu is close enough to exercise the Debian-family apt/prerequisite and Linux arm64 managed-build path. Blocker for final 16.B2 closeout: `../OracleTestVMs` must provide the in-progress Debian/aarch64 image/profile or we must explicitly revise 16.B2 from Debian/aarch64 to Ubuntu/aarch64.

## Phase 17. Remaining Tier 1 Toolchain Builds

### A. OpenBSD `amd64/clang` Managed Toolchain Build
- Implement the OpenBSD managed toolchain pipeline using the same pinned GNUstep component set.
- Build from pinned upstream GNUstep/runtime sources when publishing a managed OpenBSD artifact; use `pkg_add` validation as the preferred native packaged path, not as the canonical managed artifact source.
- Record and apply OpenBSD-specific patches explicitly.
- Validate the resulting artifact with compile, link, run, and `doctor` coverage.
- Keep the managed OpenBSD toolchain path optional in product policy if the packaged OpenBSD GNUstep environment proves sufficient for the CLI's supported workflows.

### A2. OpenBSD `arm64/clang` Managed Toolchain Build
- Add OpenBSD/arm64 as a first-class planned target for the full CLI, managed toolchain metadata, and official packages.
- Use canonical target id `openbsd-arm64-clang` and canonical architecture value `arm64`.
- Validate initially on the available OpenBSD arm64 server before enabling artifact publication.
- Keep publication disabled until source-built toolchain, full CLI, package artifacts, and host-backed install/remove validation pass on the target.

### Phase 17 Execution Status
- Phase 17.A2 is implemented at metadata/planning level: the build matrix, source lock, toolchain manifest, component inventory, generated build script, package target metadata, and regression coverage now exist for `openbsd-arm64-clang`. Publication remains disabled until a live OpenBSD/arm64 build, full-CLI smoke, package artifact rebuild, and install/remove validation pass. Blocker: `../OracleTestVMs` must provide the in-progress OpenBSD/arm64 image/profile or equivalent managed access to the available OpenBSD arm64 host for finishing 17.A2.

### B. Windows `amd64/msys2-clang64` Managed Toolchain Assembly
- Define the pinned MSYS2 package input set for the Windows `clang64` target.
- Include `libdispatch` when the curated MSYS2-based assembly supports it cleanly.
- Include CoreBase only when it is available in a validated form for this target.
- Normalize the curated package inputs into the managed install layout.
- Produce a release-style managed toolchain artifact with checksums and component inventory.
- Current status: the checked-in assembly script now stages the MSYS2 `clang64` GNUstep stack, preserves a `clang64` prefix for GNUstep Make shell builds, and copies the MSYS `usr/bin` executable/DLL runtime closure needed by developer tools such as `bash.exe`, `make.exe`, and `sha256sum.exe`. Generated metadata records `input-manifest.json`, `component-inventory.json`, and the checksum-tool entrypoint. Refreshed local staged Windows CLI/toolchain artifacts were rebuilt, release-artifact-qualified, and published to the `v0.1.0-dev` GitHub prerelease on April 17, 2026. Runtime/package flows pass from the staged artifact, and a fresh `windows-2022` libvirt lease confirmed the extracted toolchain can rebuild the Objective-C CLI and run `doctor --json` successfully against an explicit local Windows manifest.

### C. Windows `amd64/msvc` Go/No-Go Workstream
- Implement the dedicated MSVC managed toolchain pipeline if feasible.
- Keep MSVC-specific source locks, patches, and inventories separate from the MSYS2 target.
- If the MSVC stack is not production-ready, mark it explicitly as not yet published rather than silently degrading support claims.

### D. Tier 1 Live Validation
- Validate Windows artifacts on short-lived `otvm` leases.
- Validate OpenBSD artifacts on the corresponding dedicated validation host or VM path.
- Validate that published managed artifacts carry complete source/input locks and do not depend on host-origin GNUstep Makefiles, `gnustep-config`, or unmanaged runtime library paths.
- Ensure every live validation flow destroys external leases or instances promptly after use.

### G. Testing
- Exhaustive per-target build and assembly plan tests.
- Artifact unpack/install/validate smoke tests for every Tier 1 managed toolchain artifact.
- Windows lease-backed regression tests for PowerShell bootstrap plus managed toolchain installation.
- Cross-target consistency tests for toolchain manifests, component inventories, and release metadata.

### H. Exit Criteria
- Every published Tier 1 managed toolchain artifact has a repeatable build or assembly path and explicit validation evidence.
- Source-built Tier 1 managed artifacts are built from pinned upstream source; curated binary-input artifacts have locked package inputs and documented provenance.
- Native packaged paths remain clearly labeled as native/interoperability paths and are not counted as managed artifact publication evidence.

## Phase 18. Full GNUstep CLI Implementation And Build

### A. Command Runtime Architecture
- Replace the current full-CLI skeleton with a real Objective-C/GNUstep command runtime.
- Implement shared option parsing, structured output generation, command dispatch, and error handling in the full CLI.
- Keep behavior aligned with the bootstrap interface on overlapping commands.

### B. Full `doctor` And `setup`
- Implement production-grade `doctor` and `setup` behavior in the Objective-C CLI.
- Consume the shared schemas, release manifests, compatibility policy, and managed-install state directly from the full CLI.
- Move deep validation responsibilities into the full Objective-C `doctor` implementation rather than trying to force them into bootstrap.

### C. Full `build`, `run`, `new`, `install`, And `remove`
- Replace current planning helpers and scaffolds with real full-CLI implementations built on the managed GNUstep stack.
- Ensure the full CLI is the primary installed command surface after bootstrap handoff.

### C2. Remove Python From The Installed Full Runtime
- Treat the installed full CLI as pure Objective-C/GNUstep runtime code rather than as a native front end bundled with Python product logic.
- Move remaining full-interface runtime behavior out of `src/gnustep_cli_shared` and `scripts/internal` where those modules still define shipped command behavior.
- Keep Python only for repository tooling, release/build helpers, and tests unless a later explicit exception is adopted.
- Remove the bundled Python runtime tree from the installed full CLI bundle once native parity is complete.
- Add a release gate proving that the installed full CLI works for its shipped command set without any bundled Python command runtime.

### D. Build The Full CLI For Tier 1 Targets
- Build the Objective-C full CLI against each supported managed toolchain target.
- Produce release-style CLI artifacts, checksums, and manifest entries.
- Verify that the full CLI can bootstrap normal user workflows on each supported target.

### G. Testing
- Exhaustive unit tests for Objective-C command parsing, dispatch, JSON output, and failure behavior.
- Integration tests that exercise the built full CLI against staged managed toolchains.
- Regression tests for bootstrap-to-full handoff, command parity, and manifest-driven setup behavior.
- Add a built-artifact validation path that removes bundled Python runtime code from the installed full CLI bundle and proves the native CLI still runs its shipped command set.
- Windows live smoke tests of the built full CLI on `otvm` leases where native runners are unavailable.
- Add a Debian live-validation path that provisions an `otvm` Linux lease or equivalent disposable Debian VM with stock distro GNUstep packages installed and verifies that the full Objective-C CLI can still be built in the GCC-based environment.
- Treat that Debian GCC build as an interoperability test, not as evidence that Debian's stock toolchain is a managed Tier 1 artifact target.
- Add an OpenBSD live-validation path that uses the packaged OpenBSD Clang/GNUstep environment and determines whether it is sufficient to support the CLI as a preferred packaged-toolchain path.

### H. Exit Criteria
- The full GNUstep-based CLI is built, tested, and usable as the primary installed command on the supported published targets.
- The installed full CLI no longer depends on bundled Python product runtime code for its shipped command behavior.

### Phase 18 Execution Status
- Linux `amd64/clang`: completed through real execution.
- The full Objective-C GNUstep CLI now builds against the managed Linux
  toolchain and has been smoke-tested for `--help`, `--version`,
  `doctor --json`, `setup --json`, `new`, `build`, `run`, `install --json`,
  and `remove --json`.
- The CLI release bundling path now installs a runtime-aware launcher so the
  installed `gnustep` command can resolve the managed GNUstep runtime after
  bootstrap handoff rather than depending on an ambient host library path.
- Local bootstrap-to-full handoff qualification is now automated against staged
  release artifacts and verifies that `setup` installs a runnable native
  Objective-C CLI with working `--help` and `--version` behavior.
- A generated CLI-tool project was created, built, and run successfully through
  the Objective-C front end.
- Native full-CLI package installation and removal are now validated through
  both local fixture coverage and generated-index/package-state regression
  coverage in Python and native test lanes.
- OpenBSD packaged-path validation is now completed through live libvirt
  evidence: a fresh lease used `pkg_add` to install `gnustep-make`,
  `gnustep-base`, `gnustep-libobjc2`, and `gmake`, then compiled, linked, and
  ran a Foundation probe successfully in the packaged GNUstep environment.
- Debian validation is now completed at three levels:
  - the GCC-oriented packaged environment remains recorded as an
    interoperability path
  - the managed Linux artifact passed clean-host `clang` compile-link-run
    validation plus package-flow smoke on a Debian libvirt lease
  - the April 16, 2026 dogfood gate in
    `scripts/dev/debian-dogfood-validation.sh` passed against freshly staged
    `linux/amd64/clang` artifacts, covering bootstrap setup, installed CLI
    smoke, `doctor --json`, managed Foundation compile-link-run, and package
    install/remove on a clean Debian libvirt lease
- Managed Linux artifact assembly now carries transitive runtime libraries,
  sysroot C headers, GNUstep/libobjc linker names, and setup-time text-only
  relocation needed by the Debian dogfood path. The April 16, 2026 Debian
  OTVM gate now passes installed CLI smoke, `doctor`, managed Foundation
  compile-link-run, `gnustep new`, `gnustep build`, `gnustep run`, and package
  install/remove after explicit host prerequisite installation of `clang` and
  `make`.
- The installed full CLI bundle now keeps only native runtime content plus the
  shipped example manifests under `libexec/gnustep-cli`; the bundled Python
  runtime trees are no longer copied into release bundles.
- Built-artifact qualification now fails if bundled Python runtime trees
  reappear in the installed full CLI bundle, so the no-bundled-Python gate is
  active rather than aspirational.
- Native full-CLI `setup` now evaluates the richer full-interface `doctor`
  payload, makes the native-versus-managed decision explicitly in Objective-C,
  and records a setup transaction with rollback restoration semantics around
  managed installs.
- Native full-CLI package installation now supports package-index lookup,
  environment/requirements-aware artifact selection, dependency preflight, and
  dependency-safe removal behavior using tracked installed-package state.
- The Windows host path now has live package-flow evidence: on April 17, 2026 a
  `windows-2022` libvirt lease rebuilt the full Objective-C CLI under the
  checked-in MSYS2 assembly path, passed `--version` / `--help`, installed a
  staged Windows package artifact with native SHA-256 verification, and removed
  it successfully. Phase 14/18 are complete for the current command surface and
  staged cross-platform artifacts; remaining work is production-lane artifact
  builds for every Tier 1 target, automated live smoke lanes, continued native
  Objective-C migration for future shipped behavior, and native `doctor` deep
  detection parity.

## Phase 19. GitHub Release Publication And End-To-End Consumption

### A. Release Asset Naming And Layout
- Finalize release asset naming for full CLI artifacts, managed toolchain artifacts, checksums, manifests, and validation evidence.
- Ensure asset naming stays subordinate to the release manifest rather than becoming the discovery protocol.
- Include source-lock/input-lock, component-inventory, and provenance artifacts in the release asset layout for every official managed runtime artifact.
- Treat signed manifest and index metadata as the security boundary; HTTPS asset hosting and checksum sidecars are necessary but not sufficient on their own.

### B. GitHub Release Publication Pipeline
- Implement project-controlled publication of full CLI artifacts, managed toolchain artifacts, checksums, and release manifests to GitHub Releases.
- Ensure publication uses the configured GitHub operator account and produces deterministic release metadata.
- Sign release manifests and package indexes with project-controlled keys and publish provenance attestations for the referenced artifacts.

### C. Manifest Wiring
- Publish release manifests whose artifact URLs point at the canonical GitHub Release assets.
- Ensure bootstrap and full `setup` can consume those manifests without any GitHub-page scraping behavior.
- Ensure consumers verify signatures, trust roots, metadata freshness, and selected-artifact identity before trusting any release-manifest or package-index document.

### D. End-To-End Install Qualification
- Verify fresh-machine flows from bootstrap script to installed managed toolchain to installed full CLI using the actual published GitHub Release assets.
- Exercise supported Unix flows plus Windows lease-backed flows through `otvm`.

### G. Testing
- Release-pipeline tests for asset completeness, checksum coverage, and manifest correctness.
- End-to-end fresh-host install tests using published release artifacts rather than local staging paths.
- Regression tests for broken asset URLs, missing checksums, mismatched manifests, interrupted downloads, expired metadata, and rollback/freeze scenarios.

### H. Exit Criteria
- Supported v1 platforms have live GitHub-hosted CLI and managed-toolchain binaries, and bootstrap plus full `setup` can install them end-to-end from the published release manifest.
- Published managed-toolchain binaries are accompanied by source/input locks, component inventories, checksums, signatures, and release qualification evidence proving they satisfy the managed artifact source policy.
- Any release containing transitional host-copied or distro-derived managed artifacts is clearly marked non-production or prerelease-only.

### Phase 19 Execution Status
- Release staging, checksum generation, manifest emission, GitHub release
  command planning, and local release qualification are implemented.
- Real staged Linux and Windows release payloads exist under `dist/stable/0.1.0-dev`
  and verify successfully.
- Local qualification against the staged release directory succeeds and extracts
  the CLI and managed toolchain artifacts into a disposable install root.
- A GitHub Actions workflow skeleton exists for release publication.
- The repository remote and GitHub access are configured for
  `danjboyd/gnustep-cli-new`; `v0.1.0-dev` prerelease assets have been
  published with digest-verified replacement uploads.
- The repository is public, the `v0.1.0-dev` prerelease assets are published,
  and Debian published-URL fresh-host qualification now passes end-to-end from
  the public release manifest. Release provenance plus OpenSSL-backed
  manifest/provenance signatures are published and locally gate-verified for the
  prerelease; the local trust gate now supports verification against an external
  pinned public key rather than only a colocated release key. A fresh Windows
  libvirt lease on April 17, 2026 reproduced the remaining public-consumption
  blocker during bootstrap setup itself: after invoking PowerShell setup against
  the public manifest, SSH on the guest stopped responding before installed CLI
  version/help/package smoke could run; a traced retry on lease
  `lease-20260417193352-g9lrky` also hung before trace retrieval. Bootstrap now
  has JSONL trace instrumentation and a scheduled-task diagnostic wrapper so the
  next live run can preserve phase evidence even if SSH stdout is lost.
  Production signing policy is documented, and the release workflow now uses a
  controlled release gate that verifies release metadata and package indexes
  against externally pinned trust roots. CI-held production key material,
  real package artifact outputs, rotation/revocation procedures, and Windows
  bootstrap/session stability remain required before production security claims.

## Phase 20. Tiered `doctor` Convergence And Shared Execution Policy

### A. Shared Check Catalog And Execution Tiers
- Refine the shared `doctor` specification so each check declares:
- stable check identifier
- platform applicability
- interface applicability
- execution tier such as `bootstrap_required`, `bootstrap_optional`, or `full_only`
- Represent bootstrap limitations intentionally rather than as missing behavior.

### B. Bootstrap `doctor` Reduction And Hardening
- Narrow bootstrap `doctor` to the installer-oriented subset of checks.
- Ensure bootstrap focuses on:
- host identity
- downloader/bootstrap prerequisites
- install-target suitability
- privilege and PATH/shell-context issues relevant to setup
- coarse toolchain detection and coarse compatibility classification
- Remove or avoid deep validation behavior that is not necessary to make setup decisions safely.

### C. Full `doctor` Deep Validation
- Move deep diagnostics into the full CLI `doctor` implementation.
- Implement richer runtime, ABI, feature-flag, and GNUstep-component detection.
- Implement compile/link/run probes and other narrowly scoped active validation in the full CLI where appropriate.
- Add managed-install integrity checks and repair-oriented diagnostics for the installed environment.
- Make full `doctor` authoritative for deciding when a packaged OpenBSD GNUstep environment is supported and should be preferred over managed installation.

### D. Shared Output Semantics
- Keep one JSON envelope, one vocabulary, and one set of check identifiers across bootstrap and full interfaces.
- Define how bootstrap reports checks that are shared by spec but unavailable in bootstrap, such as structured `not_run` or `unavailable_in_bootstrap` states.
- Ensure `setup` can consume the shared `doctor` result model without depending on deep-only checks.
- Keep one normalization policy for host facts and compatibility vocabulary across interfaces, including `os`, `arch`, compiler/runtime identifiers, and canonical `arm64` normalization.

### G. Testing
- Add contract tests proving bootstrap and full share the same envelope and status vocabulary.
- Add regression tests for unavailable-check reporting semantics.
- Add fixture and live tests for full-CLI deep validation paths.

### H. Exit Criteria
- Bootstrap and full `doctor` share one policy model while differing intentionally in diagnostic depth.
- Bootstrap `doctor` is clearly installer-oriented, and full `doctor` is the authoritative deep diagnostic interface.

### Phase 20 Execution Status
- The shared Python `doctor` layer now exposes one stable envelope across
  bootstrap and full interfaces, including stable check identifiers, interface
  markers, and execution tiers.
- Bootstrap now reports full-only checks structurally as `not_run` with
  `unavailable_in_bootstrap` details instead of silently omitting them.
- The shared `doctor` payload now includes a separate
  `native_toolchain_assessment` and structured `environment.native_toolchain`
  section so packaged/native toolchain policy can be expressed without changing
  the stable top-level environment classification vocabulary.
- The current shared native-toolchain assessment model distinguishes among:
  - `unavailable`
  - `broken`
  - `preferred`
  - `supported`
  - `interoperability_only`
  - `incompatible`
- Initial policy heuristics now exist for:
  - OpenBSD packaged GNUstep as a preferred native-path candidate when a modern
    Clang plus `libobjc2` stack is detected
  - Fedora as a supported native-path discovery target when the same modern
    runtime model is detected
  - Debian and Arch as interoperability-oriented discovery targets when a
    working GCC-based packaged GNUstep stack is detected
- Full `doctor` now includes a managed-install integrity check in the shared
  vocabulary, while bootstrap reports that check as unavailable in bootstrap.
- Automated coverage now includes:
  - bootstrap/full shared check-vocabulary tests
  - unavailable-check semantics tests
  - native Objective-C regression coverage that the full CLI preserves the core bootstrap/full check identifiers
  - fixture-style native-toolchain classification tests for Debian GCC and
    OpenBSD packaged Clang scenarios
- Full `doctor` in the shared Python layer now performs a deeper fact pass than
  bootstrap, including:
  - runtime/library-symbol-based Objective-C runtime detection where practical
  - compile-flag feature probes for `blocks`, ARC, and nonfragile ABI
  - GNUstep Base/GUI component detection through `gnustep-config`
  - explicit detection-depth reporting in the toolchain facts
- The main remaining work for this phase is extending the native Objective-C
  CLI's `doctor` implementation from vocabulary parity into the same deep
  compile/link/runtime/toolchain detection depth as the shared Python model,
  then validating that parity in built native CLI tests.

## Phase 21. Setup, Repair, And Managed Lifecycle Hardening

### A. Manifest And Artifact Validation
- Validate manifest schema versions explicitly during setup.
- Harden artifact selection against malformed manifests, unsupported hosts, and ambiguous matches.
- Reject official managed artifacts whose manifests omit required source/input lock, provenance, component inventory, or signing metadata once those fields are release-gated.
- Separate manifest parsing failures from compatibility failures in user-visible results.
- Require release artifact selection to match on compiler family, `toolchain_flavor`, Objective-C runtime, ABI, and required feature flags rather than selecting on `os` and `arch` alone.
- Reject ambiguous same-host matches explicitly instead of silently taking the first artifact of a given kind.
- When a compatible external toolchain is already available, make the managed-install decision explicit and policy-driven rather than assuming a managed artifact should win by default.

### B. Transaction And Rollback Semantics
- Strengthen staged-install behavior so interrupted setup is recoverable.
- Record enough state to support rollback, repair, and clean reruns.
- Ensure partial downloads, partial extractions, and failed handoffs do not leave the managed root in an ambiguous state.

### C. PATH And Configuration Integration
- Implement durable shell startup integration where appropriate.
- Emit exact current-shell activation commands and persist future-shell guidance consistently.
- Finalize config, cache, and state placement separately from the managed toolchain tree.

### D. Upgrade And Repair Flows
- Implement managed CLI upgrade detection and application.
- Implement managed toolchain repair and upgrade behavior.
- Ensure repeated `setup` behaves as repair-or-upgrade rather than as a fragile reinstall.
- Add `gnustep update --check` for read-only update planning from the signed release manifest and package index.
- Add `gnustep update cli` for transactional CLI/toolchain updates with staged extraction, smoke validation, active-pointer activation, previous-release retention, and rollback on failure.
- Add `gnustep update packages` for signed-index package upgrades using the package transaction model.
- Add `gnustep update all` as the default coordinated update path.
- Keep bootstrap out of the normal update path except as a documented recovery mechanism.

### G. Testing
- Add failure-injection tests for interrupted setup, interrupted upgrade, corrupted state, and broken manifests.
- Add negative tests for managed artifacts with missing provenance, missing source/input locks, stale component inventories, or host-origin path leakage.
- Add rollback, repair, update-check, update-activation, package-update, downgrade-rejection, stale-metadata, and freeze/rollback-attack tests.
- Add shell-integration tests for supported Unix shells and Windows PowerShell behavior.

### H. Exit Criteria
- `setup` is a recoverable lifecycle operation for install, repair, and rollback/recovery; `gnustep update` owns normal update check and upgrade UX.

### Phase 21 Execution Status
- Native full-CLI `setup` now validates setup plans from the richer full
  `doctor` environment model instead of the bootstrap-only assessment.
- When a preferred or supported native GNUstep toolchain is already present,
  the native CLI now records that policy decision explicitly as
  `plan.install_mode = native` instead of implicitly forcing a managed install.
- Managed setup execution now snapshots the previous install root, records an
  in-progress transaction under `.staging/setup/transaction.json`, restores the
  prior installation on failure, and cleans up rollback state on success. Native
  regression coverage now includes both checksum-failure rollback and stale
  transaction recovery that restores a backup root while removing partial
  install state.
- Native full-CLI `setup --repair` now clears stale staging and transaction
  state and marks interrupted lifecycle state as `needs_repair`, with
  `tools-xctest` regression coverage.
- Native full-CLI transitional setup update checks now emit a structured read-only update
  plan from installed lifecycle state plus manifest artifact selection, rejects
  downgrade manifests, rejects expired metadata when `expires_at` is present,
  and rejects selected artifacts listed in signed revocation metadata.
- Native full-CLI transitional setup upgrade now reuses managed setup transactions,
  rejects `needs_repair` state, refuses downgrade targets, records lifecycle
  state as an upgrade, preserves the previous install root for rollback/recovery,
  and forces managed artifact application for an existing managed root even when
  host prerequisites make a native toolchain look supported.
- Managed setup artifact staging now supports plain local artifact paths as well
  as URL/download flows, archive extraction preserves standard install layout
  directories such as `bin` and `System` instead of flattening them, and setup
  avoids double-wrapping complete full-CLI runtime bundles.
- Successful managed setup/upgrade now materializes an initial versioned layout
  under `releases/<version>` with a `current` pointer while preserving the
  existing flat-root compatibility path.
- `gnustep update cli --yes` now preserves the canonical setup PATH activation
  guidance in its payload, with native regression coverage, so update does not
  regress shell/path configuration semantics.

## Phase 22. Package Manager Delivery And Safety Completion

### A. Package Index Consumption
- Replace direct-manifest package installation assumptions with official package-index consumption.
- Resolve package selection through compatibility-aware artifact matching rather than the first listed artifact.
- Retire the current direct end-user package-manifest install path as the primary package workflow once package-index consumption is in place.

### B. Dependency And Compatibility Enforcement
- Implement dependency resolution and dependency rejection behavior.
- Enforce environment, artifact, and package requirement compatibility before installation.
- Keep package compatibility evaluation separate from CLI and toolchain compatibility conclusions.
- Remove the current `first artifact wins` package-install behavior so package selection is always compatibility-driven and policy-checked.

### C. Ownership And Removal Safety
- Track owned files, selected artifacts, and dependency relationships in installed state.
- Make `remove` consult installed-files manifests and dependency safeguards before deleting anything.
- Clean up generated integration artifacts such as launchers and shortcuts reliably.

### D. End-User Package UX
- Improve install/remove messaging, structured output, and failure explanations.
- Ensure package flows feel integrated with the managed environment rather than like standalone archive extraction helpers.

### G. Testing
- Add end-to-end install/remove tests using a generated package index.
- Add package publication/installation tests that reject opaque official binaries without reviewed source provenance unless a documented exception policy applies.
- Reject package publication when declared downstream patches are missing, use placeholder digests, or do not match their reviewed patch files.
- Add dependency, conflict, compatibility, and ownership regression tests.
- Add upgrade and reinstall tests for reviewed packages.

### H. Exit Criteria
- Users can install and remove reviewed packages safely through the official package workflow.
- Official package artifacts are selected from package-index metadata that records source provenance, build identity, target compatibility, checksums, and signing state.

### Phase 22 Execution Status
- Native full-CLI `install` now accepts either a direct package manifest or a
  package ID resolved through a package index supplied with `--index`.
- Package artifact selection is now host- and toolchain-aware in native code
  instead of taking the first listed artifact blindly.
- Native package installation now enforces package requirements and rejects
  installs when declared dependencies are not already installed.
- Native `remove` now blocks removal when other installed packages declare a
  dependency on the target package.
- Native install/remove payloads and human-readable output now expose package
  IDs, selected artifacts, managed roots, install roots, file counts, and
  dependency blockers more explicitly.
- Native package installation now rejects declared package conflicts against
  already installed packages and records installed package conflict metadata for
  future checks.
- Lifecycle repair now clears stale staging/transaction state, removes stale
  setup transaction records, and marks interrupted install/upgrade state as
  `needs_repair`; full doctor reports these managed-install integrity warnings.
- Package repository tooling now emits package-index trust metadata, writes
  package-index provenance, signs package-index/provenance metadata, and runs a
  package-index trust gate; Python package installation now rejects missing or
  mismatched artifact digests before extraction, supports signed-index package upgrades, audits/recovers stale package transactions, and supports ZIP package
  artifacts for Windows-aligned smoke flows.
- Package-index and release trust gates both support externally pinned public
  keys, allowing production CI to verify against configured trust roots rather
  than implicitly trusting colocated metadata. Package-index consumer installs
  now enforce the package-index trust gate by default, with explicit development
  overrides for unsigned indexes.
- End-to-end package regression coverage now includes generated-index installs,
  dependency rejection, reinstall/idempotent install behavior, ownership and
  cleanup checks, package-update planning/apply/rollback, package-update human
  output, and removal-state updates in both Python and native test lanes.

## Phase 23. Release Candidate Consolidation

### A. Repository Health And Release Gates
- Restore a fully green automated test suite and keep it green as a release gate.
- Promote the regression suite into a required release-readiness signal rather than a best-effort helper.
- Add a release gate that fails production release qualification if managed artifacts are host-copied/distro-derived without an explicit prerelease exception and documented provenance status.

### Phase 23 Execution Status
- GitHub Actions now runs the Python/shared suite and the native Objective-C
  `tools-xctest` suite on pushes and pull requests.
- The release workflow now runs the full regression suite before publication.
- The current support position is recorded explicitly in
  `docs/support-matrix.md`.
- Release-candidate qualification status is recorded explicitly in
  `docs/release-candidate-qualification.md`.
- The OpenBSD and Debian libvirt refresh path is now documented with a checked-in
  `otvm` libvirt config template that matches the currently validated farm
  model (`danboyd@...`, `qemu+ssh`, `direct-lan`, current published images).
- OpenBSD and Debian now have fresh release-candidate evidence. Debian also has
  an April 16, 2026 repeatable dogfood gate for managed setup/doctor/package
  flows through `scripts/dev/debian-dogfood-validation.sh`. Fedora and Arch
  also have April 16, 2026 libvirt preflight, acceptance-run, native build,
  CLI smoke, and package install/remove evidence; follow-up validation confirms
  their distro GNUstep packages are GCC/libobjc interoperability paths rather
  than preferred Clang/libobjc2 native stacks.
- Windows libvirt readiness is also now working on the current farm, and the
  April 17, 2026 live smoke proves the checked-in MSYS2 assembly path can build
  the full CLI and complete native package install/remove on a `windows-2022`
  lease.
- Phase 23.B and 23.C are substantially executed through the current support
  matrix and qualification docs, but the top-level repository docs still need a
  final freshness pass so every status surface matches the newer evidence.
- Phase 23.D and 23.E now have broader live evidence, and the release validation
  runner can execute short-lived `otvm` lease checks with destroy-on-exit cleanup.
  Remaining work is focused on production key material, final published-URL
  qualification gates, and turning the successful Windows public-bootstrap and
  extracted-toolchain evidence into repeatable CI/farm jobs:
  - OpenBSD and Debian have fresh live evidence; on April 20, 2026 the OpenBSD packaged GNUstep smoke passed and a real OpenBSD `tools-xctest` package artifact was produced on a live OpenBSD lease
  - Windows native package-flow validation passed again on April 17, 2026 after
    refreshing the checked-in MSYS2 assembly script to include `sha256sum.exe`;
    lease `lease-20260417160327-z8fnih` built the full CLI, passed `--version`
    / `--help`, installed the staged package, removed it successfully, and was
    destroyed after validation
  - refreshed local Windows MSYS2 toolchain and CLI artifacts now pass
    package-flow qualification against the staged release ZIPs; public-bootstrap
    setup passed from the GitHub prerelease endpoint with trace evidence, and
    extracted-toolchain rebuild plus explicit-manifest `doctor --json` passed on
    a fresh Windows libvirt lease
  - Fedora and Arch are live-validated GCC interoperability targets; preferred
    modern-runtime validation must use managed Clang/libobjc2 artifacts
  - Debian managed setup/doctor/package and `gnustep new`/`build`/`run`
    dogfood passed on clean libvirt leases; Debian public published-URL
    bootstrap/full-CLI qualification also passed on April 17, 2026 after
    rebuilding the Linux CLI against the managed source-built toolchain and
    adding runtime SONAME aliases plus native HTTPS-manifest downloader fallback
  - April 20, 2026 follow-up: a locally rebuilt Linux full-CLI artifact
    produced from the host GNUstep Make environment failed live Debian upgrade
    dogfood with `undefined symbol: __objc_class_name_NSAutoreleasePool` when
    executed inside the managed libobjc2 runtime. The dev workflow now builds
    Linux CLI artifacts against the managed source-built GNUstep/libobjc2 prefix
    with `build-linux-cli-against-managed-toolchain` and the wrapper
    `scripts/dev/build-linux-cli-against-managed-toolchain.sh`; the build now
    includes a `linux-cli-abi-audit` gate that rejects legacy GCC Objective-C
    class symbols. After refreshing staged old/new manifests, the live Debian
    `gnustep update --check` / `gnustep update cli --yes` / rollback dogfood
    lane passed on April 20, 2026. Production release builders must use the
    managed-prefix build path, not ad hoc host GNUstep Make artifacts.

### B. Documentation Freshness
- Bring the README and status docs into alignment with the actual implementation state.
- Distinguish clearly among shipped behavior, validated behavior, prototype behavior, and externally blocked targets.
- Reconcile status-report claims with the live repository state, including release publication configuration, remote/repository availability, and which validations are still pending versus completed.

### C. Support Matrix Review
- Reconcile claimed support with validated release artifacts and qualification evidence.
- Record known limitations explicitly for GCC interoperability, OpenBSD, Windows MSYS2, and deferred MSVC work.
- Distinguish native packaged support, interoperability validation, transitional managed artifacts, and production managed artifacts in the support matrix.
- Treat current-release native-toolchain discovery/classification as in-scope for:
  - OpenBSD
  - Fedora
  - Debian
  - Arch
- Treat the following distro families as explicitly deferred future investigation targets unless the roadmap is revised later:
  - openSUSE
  - RHEL-family distributions and clones
  - Alpine

### D. Structured Beta And Qualification Runs
- Run fresh-host qualification on every supported published target.
- Run explicit bootstrap-to-full handoff validation and package-flow smoke tests on release-candidate artifacts.
- Capture release evidence in a form that is auditable by maintainers later.
- Run explicit OpenBSD qualification against the packaged GNUstep path and record whether that path is supported and preferred versus managed installation.
- Fedora qualification against the packaged GNUstep path has live evidence from April 16, 2026 and is classified as GCC interoperability-only; do not mark it preferred for modern-runtime workflows without a validated Clang/libobjc2 stack.
- Debian and Arch qualification have live evidence and are classified as GCC interoperability-oriented unless a validated packaged Clang/libobjc2 path is later proven.
- Ubuntu `amd64/clang` managed support is now represented by the distro-scoped `linux-ubuntu2404-amd64-clang` target, built in a base Ubuntu Docker image, published to the `v0.1.0-dev` prerelease, and dogfooded for setup/doctor plus `tools-xctest` install/help/minimal-bundle/remove on April 20, 2026. Fedora and Arch managed Clang/libobjc2 support remains blocked pending dependency closure or per-distro artifact work. The current `linux-amd64-clang` managed artifact is explicitly Debian-scoped in metadata and artifact selection so setup does not claim Ubuntu/Fedora/Arch portability from the Debian-built artifact.

### E. Exit Criteria
- The project has a defensible v1 release candidate with accurate docs, passing release gates, and validated support claims.
- No managed artifact is treated as production-supported unless its source/input provenance, component inventory, signing metadata, and host-backed qualification evidence satisfy the managed artifact source policy.

## Phase 24. Official Package Initiative And `tools-xctest` Installability

### A. Package Source-Of-Truth And Update Policy
- Extend package manifests so every official package declares its upstream source of truth, tracking strategy, update cadence, and channel policy.
- Default stable packages to tagged upstream releases; allow commit or branch snapshots only on dogfood/snapshot channels or through an explicit package exception.
- Record upstream PRs, downstream patches, source revisions, source digests, and package-version mapping in package metadata and generated provenance.

### B. Patch-Aware Package Build Pipeline
- Apply declared package patches after verified source fetch and before invoking the selected build backend.
- Verify patch file digests, safe relative paths, target applicability, and upstream status before a package artifact can be published.
- Add regression coverage for successful patch application, failed patch application, patch digest mismatch, and target-specific patch selection.
- Current `tools-xctest` package state: PR `https://github.com/gnustep/tools-xctest/pull/5` is recorded as downstream patch `add-apple-style-xctest-cli-filters`; Debian amd64, Ubuntu amd64, and OpenBSD amd64 artifacts have now been rebuilt from that patch and validated with package lifecycle dogfood evidence.

### C. `tools-xctest` Build-With-Our-CLI Flow
- Teach package build tooling to build `tools-xctest` through our own CLI/package workflow rather than only through ad hoc shell commands.
- Build patched `tools-xctest` artifacts for Debian Linux `amd64/clang`, Ubuntu Linux `amd64/clang`, Debian Linux `arm64/clang`, OpenBSD `amd64/clang`, OpenBSD `arm64/clang`, and Windows `amd64/msys2-clang64`; use Docker for the Ubuntu amd64 build, local libvirt/mac VM capacity through `../OracleTestVMs` first for VM-backed targets, and fall back to OCI only when local capacity is unavailable.
- Preserve the OpenBSD linker-name workaround either as an upstreamable patch, a package build step, or a target-specific post-build fix with provenance.
- Regenerate package artifact checksums and package-index metadata from the rebuilt artifacts.

### D. Package Index Publication And Trust
- Publish package artifacts and package index metadata through the same signed/trusted artifact model used for release metadata.
- Ensure the generated package index only exposes artifacts that correspond exactly to the declared source revision plus declared patches.
- Add package provenance evidence including upstream source, applied patches, builder identity, target profile, artifact digest, and install/remove validation result.

### Phase 24 Execution Status
- Phase 24.A-D are implemented at repository-tooling level: the `tools-xctest` package manifest records upstream source policy, update cadence, channel policy, submitted PR #5 as a verified downstream patch, and a `gnustep build`-oriented build workflow. Package tooling can now validate and apply declared patches to a source checkout, package build planning exposes build backend/invocation metadata, and generated package indexes/provenance carry package and per-artifact source/patch identity.
- Phase 24.E-G now have a repository release gate through `scripts/internal/build_infra.py --json tools-xctest-release-gate --packages-dir packages --evidence-dir <evidence-dir>`. The gate now passes with OpenBSD arm64 explicitly deferred as a documented non-release blocker; validated targets have rebuilt `tools-xctest` artifacts from the declared upstream revision plus PR #5 patch with native install/smoke/minimal-bundle/remove evidence.
- Current blockers: OpenBSD arm64 remains a documented non-release blocker pending an OTVM profile or equivalent scripted access to the OpenBSD arm64 host. Debian Linux amd64, Ubuntu Linux amd64, Linux arm64 on the OTVM Ubuntu/aarch64 managed Clang/libobjc2 path, OpenBSD amd64, and Windows/MSYS2 are rebuilt from the declared upstream revision plus PR #5 patch, published in package metadata, and validated with install/help/minimal-bundle/remove evidence.

### E. Native CLI Install/Remove Dogfood
- Use the native full CLI to install `org.gnustep.tools-xctest` from the generated package index on a clean managed root.
- Verify `xctest` is on the expected installed path, can execute `--help` or equivalent smoke behavior, and can run at least one minimal XCTest bundle.
- Remove the package through the CLI and verify owned-file cleanup, state updates, and dependency behavior.
- Run this flow on Debian Linux amd64, Ubuntu Linux amd64, Linux arm64/Debian, OpenBSD, and Windows/MSYS2 as target artifacts become available.
- Status: gate defined and enforced at repository level; Debian Linux amd64, Ubuntu Linux amd64, Linux arm64 on OTVM Ubuntu/aarch64 with a managed Clang/libobjc2 toolchain, OpenBSD amd64, and Windows/MSYS2 now pass the gate with accepted dogfood evidence. OpenBSD arm64 remains host-access blocked and is recorded as a documented non-release blocker. The `tools-xctest-release-gate` now passes with that explicit deferral.

### F. Release Gate Integration
- Add `tools-xctest` package install/remove smoke to release qualification so Objective-C unit-test infrastructure is validated as a real package, not only as a developer prerequisite.
- Fail release qualification if the package index references stale artifacts, unsigned/untrusted metadata, unapplied declared patches, or package artifacts that do not pass install/remove smoke.
- Treat `tools-xctest` as the canonical first official package proving the package lifecycle: upstream source, downstream patch, package build, artifact publication, index trust, install, smoke, remove, and update.
- Status: `tools-xctest-release-gate` now reports stale-artifact, missing-artifact, missing-digest, and dogfood-evidence blockers in structured JSON for CI/release integration.

### G. Exit Criteria
- `gnustep install org.gnustep.tools-xctest --package-index <signed-index>` works on the validated Linux target.
- `gnustep remove org.gnustep.tools-xctest` restores package state cleanly.
- Ubuntu Linux amd64, Linux arm64/Debian, OpenBSD, and Windows/MSYS2 have either the same install/remove proof or explicitly documented non-release blockers.
- Published `tools-xctest` artifacts are rebuilt from the declared upstream source plus PR #5 patch, with recorded source/patch/artifact digests and host-backed validation evidence; targets without host access must be represented as explicit documented non-release blockers rather than implicit release failures.

## Phase 25. Layered Artifacts And Delta Update Delivery

### A. Product Goal And Update Policy
- Treat small CLI changes as small updates: a CLI-only code change must not require rebuilding, re-uploading, or redownloading the managed MSYS2 toolchain.
- Make managed installation and update behavior layer-aware across three independently versioned product layers:
  - full CLI
  - managed toolchain
  - installable packages
- Prefer manifest-level artifact reuse and component-level replacement before introducing byte-level binary patching.
- Keep full artifacts available as recovery checkpoints; deltas are an optimization path, not the only path to a working update.
- Preserve the existing transactional lifecycle model: stage, verify, smoke-test, activate by pointer switch, and retain rollback state.

### B. Release Manifest And Schema Extensions
- Extend release manifests so a release can reference immutable artifacts published by an earlier release when those artifacts remain compatible.
- Add explicit relationships between artifacts, including CLI-to-toolchain requirements, compatible toolchain version ranges, selected base artifact IDs, and selected base artifact digests.
- Add first-class delta artifact records for future use, with fields for source artifact, target artifact, source digest, target digest, format, URL, size, integrity metadata, and applicability rules.
- Require every reusable artifact reference to include immutable URL, SHA-256, size, signing/provenance metadata, artifact kind, target ID, and compatibility requirements.
- Ensure manifest validation rejects mutable or ambiguous artifact references, missing base digests, stale metadata, revoked base artifacts, and downgrade paths except through explicit rollback UX.

### C. Build And Publication Pipeline
- Change release preparation so CLI-only releases publish only new CLI artifacts and reuse the previous compatible managed toolchain artifact by manifest reference.
- Make Windows MSYS2 toolchain assembly conditional on the MSYS2 input manifest digest, not on every CLI release.
- Record a stable toolchain input identity derived from MSYS2 installer metadata, package names, package versions, package digests, repository snapshot identity, assembly rules, and post-assembly normalization.
- Teach release gates that a reused toolchain artifact is valid when its manifest reference, digest, provenance, source/input lock, component inventory, and qualification evidence satisfy policy.
- Keep GitHub Releases as the initial storage layer, but do not require every referenced artifact to be physically uploaded to the newest release when the manifest points to an older immutable asset.

### D. Session-Scoped Build Boxes And Fast Iteration
- Add a development workflow that can provision one warm build box per supported target through `../OracleTestVMs` / `otvm` and keep those boxes online for the duration of an active coding session.
- Allow dogfood sessions to declare an explicit active target subset, such as `windows-amd64-msys2-clang64` and `openbsd-amd64-clang`, so rapid iteration only builds, publishes, and validates the platforms currently under test.
- Keep scoped dogfood publication separate from release qualification: a partial dogfood manifest may intentionally omit untouched or untested targets, but stable and RC release claims must still be expanded back to the full supported platform/architecture matrix before publication.
- Treat warm build boxes as session-scoped infrastructure: quick to create, reusable for repeated full-CLI rebuilds during the session, and explicitly destroyable at the end of the session.
- Sync only the changed source and required build metadata to warm builders rather than re-provisioning toolchains or rebuilding large managed roots for every CLI edit.
- Build small target-specific full-CLI artifacts on the warm builders and publish or stage them into a dogfood channel without rebuilding unchanged managed toolchain artifacts.
- Add commands or scripts to list warm builders, refresh source, build selected or all supported CLI artifacts, collect artifacts, publish/update the dogfood manifest, and tear down the session cleanly.
- Preserve cost-control rules: default to short TTLs, show active lease state, support explicit cleanup, and avoid leaving long-lived idle Windows VMs running unintentionally.

### E. Dogfood Versioning And Update Visibility
- Add a dogfood/snapshot versioning scheme granular enough to publish multiple update-visible CLI builds per day.
- Record the dogfood target scope in every snapshot manifest so bootstrap, `setup`, and `update --check` can distinguish "no update for this platform in this scoped dogfood run" from "the project forgot to publish a required release artifact."
- Use monotonically ordered build identifiers that include enough information for humans and automation, such as base semantic version, UTC timestamp, source revision, and build sequence when needed.
- Ensure `gnustep update --check` sees newer dogfood builds from the selected channel even when several have been published on the same day.
- Keep stable release versioning separate from dogfood snapshot versioning so rapid iteration does not weaken production rollback, freshness, or compatibility policy.
- Record dogfood manifest identity, source revision, builder identity, build timestamp, artifact digests, and reused toolchain layer identity for every published snapshot.
- Add cleanup or retention policy for dogfood artifacts and manifests so rapid iteration does not leave an unbounded artifact history in GitHub Releases or any later artifact store.

### F. Installed State And Content Store
- Extend managed state to record active CLI artifact ID/digest, active toolchain artifact ID/digest, active package-index digest, active component inventory digest, selected release manifest digest, and previous activation metadata.
- Add a content-addressed local store for downloaded or extracted artifacts keyed by digest so repeated updates can reuse already verified payloads.
- Keep version strings as human-facing metadata, but drive update correctness from artifact IDs, digests, manifest identities, and compatibility records.
- Record pending transaction metadata with enough detail to resume, rollback, or repair interrupted delta and layered-artifact updates.
- Ensure repair can distinguish missing active pointer, missing store payload, stale staging root, interrupted activation, and incompatible installed base.

### G. Update Planning And User Experience
- Teach `gnustep update --check` to report whether an update is CLI-only, toolchain-required, package-only, or coordinated across layers.
- Include planned download size, reused installed layers, selected new artifacts, selected base artifacts, fallback choices, and next actions in both human output and JSON.
- Make `gnustep update cli --yes` choose the smallest valid plan in this order:
  - no-op when installed artifact digests already match
  - CLI-only artifact update when the installed toolchain remains compatible
  - component or toolchain delta when available and the installed base digest matches
  - full toolchain artifact fallback when no valid delta exists
  - clear failure when neither delta nor full artifact can be verified
- Never patch the active toolchain in place; all delta or component updates must materialize a verified candidate root before activation.
- Preserve clear messaging when a user has a stale binary but the manifest contains a newer CLI-only update that reuses the same toolchain layer.

### H. Windows MSYS2 Toolchain Layering
- Model the Windows `msys2-clang64` managed toolchain as a stable base layer plus explicit component/package records.
- Preserve the private MSYS2 root layout required by the Windows integration contract while making the published artifact inventory granular enough to identify changed MSYS2 packages.
- Add a Windows component inventory that records each curated MSYS2 package, installed version, package digest, installed file set digest, and owning layer.
- Add tooling to compare two Windows toolchain inventories and identify whether a new full toolchain artifact is required, whether package/component replacement is sufficient, or whether the existing toolchain can be reused unchanged.
- Keep `pacman -Qkk`, archive audit, extracted-toolchain rebuild, package-flow smoke, GUI smoke, and Gorm qualification gates mandatory for any newly published Windows toolchain base or component update.

### I. Delta Format And Fallback Strategy
- Introduce a project-owned `gnustep-delta-v1` metadata envelope before choosing a concrete binary patch algorithm.
- Require every delta application to verify the installed source digest before applying, verify the materialized target digest after applying, and fall back to a full artifact when verification fails or the source base does not match.
- Limit published delta chains to a small supported window such as the last N toolchain versions or the last stable checkpoint.
- Publish full artifacts for every CLI release and every changed toolchain checkpoint even when deltas are also available.
- Treat binary diff algorithms as replaceable implementation details behind the manifest delta contract; do not expose algorithm-specific assumptions in user-facing compatibility policy.

### J. Security, Freshness, And Failure Handling
- Keep signed release manifests and trusted metadata as the only source of update truth; do not infer update relationships from filenames or GitHub release page layout.
- Reject rollback, freeze, expired metadata, revoked artifact, revoked base artifact, digest mismatch, and signature mismatch cases before staging mutable filesystem changes.
- If delta application, extraction, smoke validation, or activation fails, leave the previous active release untouched and mark transaction state for repair.
- Ensure `setup --repair` and lifecycle repair can recover from interrupted layered updates without requiring manual deletion of the managed root.
- Add structured JSON failure reasons for invalid base artifact, missing reusable artifact, missing delta, corrupt delta, target digest mismatch, stale metadata, and full-artifact fallback failure.

### K. Testing And Validation
- Add unit and contract tests for layered manifest validation, reusable artifact references, delta artifact records, compatibility selection, download-size planning, and artifact fallback ordering.
- Add lifecycle tests for CLI-only update, toolchain-required update, no-op digest match, invalid base digest, missing reused artifact, revoked reused artifact, failed delta with full fallback, failed full fallback, interrupted staging, activation rollback, and repair.
- Add scoped-dogfood tests proving a manifest can intentionally publish only the active validation targets while preserving clear unsupported/unavailable diagnostics for platforms outside the current dogfood scope.
- Add Windows-specific tests or host-backed validation for installing an old release, publishing a new CLI-only release against the same MSYS2 toolchain, running `gnustep update`, and proving only the CLI artifact is downloaded.
- Add dogfood-channel tests proving multiple same-day CLI snapshots are ordered correctly and visible to `gnustep update --check`.
- Add warm-builder workflow tests or scripted dry runs for provision, source refresh, rebuild, artifact collection, dogfood manifest publication, and cleanup.
- Add release-gate tests that prevent stale Windows CLI artifacts from being published while still allowing unchanged MSYS2 toolchain artifacts to be reused.
- Extend dogfood validation to report transferred bytes and selected update layers so regressions in update size are visible.

### L. Exit Criteria
- A CLI-only change on Windows produces and publishes only a small CLI artifact while reusing the existing compatible MSYS2 toolchain artifact by signed manifest reference.
- A clean Windows VM can install an older release, run `gnustep update --check`, see a CLI-only update plan, apply it, and end with the new CLI plus the unchanged verified toolchain layer.
- During active development, one command can provision or reuse warm build boxes for supported targets, rebuild changed full-CLI artifacts, publish a new dogfood manifest, and make the new build visible to `gnustep update --check` without rebuilding unchanged toolchain layers.
- During a scoped dogfood session, the same workflow can limit warm builders, artifact collection, publication, manifest contents, and validation to the declared active target subset, then later expand back to all Tier 1 release targets without changing the update model.
- Multiple dogfood CLI builds published on the same day are versioned, ordered, and update-visible without confusing stable release ordering or rollback policy.
- A changed Windows MSYS2 input manifest produces a new toolchain identity and either a full toolchain checkpoint or a verified component/delta update with automatic full-artifact fallback.
- Update, rollback, and repair behavior remains transactional across CLI-only, toolchain, package, and coordinated update plans.
- Release qualification proves that stale binaries cannot be silently served as current and that unchanged large toolchain layers are not rebuilt, re-uploaded, or redownloaded for routine CLI iteration.

### Phase 25 Execution Status
- Phase 25.A-C now have repository-tooling support for immutable reused artifact references: release staging can publish a small CLI artifact while carrying a manifest reference to an older compatible toolchain artifact, verification/provenance/trust checks understand reused references, and manifest validation rejects reused artifacts without concrete digest/size metadata.
- Phase 25.B schema work has begun: release-manifest schema v1 now documents reused artifact references, CLI-to-toolchain relationships, and future delta artifact fields.
- Phase 25.D has an executable planning surface through `scripts/internal/build_infra.py --json session-build-box-plan`, which emits the session-scoped warm-builder plan, target/profile mapping, source-sync policy, artifact intent, dogfood channel, TTL, and cleanup controls. Live provisioning/sync/build orchestration remains the next implementation step.
- Phase 25.D now explicitly supports scoped dogfood target sets: active validation sessions may build and publish only the platforms currently under test, while stable/RC release qualification remains responsible for expanding back to the full supported matrix.
- Phase 25.E now has dogfood snapshot version helpers that generate monotonically ordered same-day versions from base version, UTC timestamp, source revision, and sequence; dogfood snapshot manifests can carry new CLI artifacts plus reused toolchain layer references and retention policy metadata.
- Phase 25.F now has shared lifecycle primitives for recording active CLI/toolchain artifact IDs and digests, manifest/component-inventory digests, and content-addressed artifact storage under `store/sha256`. Setup state records active artifact identities where the selected artifacts are available.
- Phase 25.G has initial update-plan layer metadata: shared lifecycle planning reports `cli_only`, `toolchain_required`, or `none`, planned download size, layer actions, and reuse/download decisions; the native full CLI update-check path now emits layer metadata in `update_plan`.
- Phase 25.H has a Windows `msys2-clang64` component inventory model and comparison helper that distinguishes unchanged toolchains, component/package replacement candidates, and destructive changes that require a full toolchain checkpoint.
- Phase 25.I now has a project-owned `gnustep-delta-v1` metadata envelope and helper for generating delta artifact records. Lifecycle planning can select a matching delta when the installed base digest and target digest match, or fall back to the full artifact when the delta is unavailable or not applicable. Concrete byte-patch application remains behind this metadata contract and is intentionally not exposed as policy.
- Phase 25.J now has structured layered-update preflight checks for revoked artifacts, invalid base artifacts, corrupt or unsupported deltas, target digest mismatches, and missing full-artifact fallback. These checks fail before mutable filesystem work and return machine-readable failure reasons.
- Phase 25.K has focused regression coverage for layered manifest reuse, dogfood snapshot ordering, content-addressed storage, active artifact state recording, layered update planning, delta selection, full-artifact fallback, revoked-artifact preflight, Windows MSYS2 inventory comparison, and warm-builder planning.
- Phase 25.L is complete at the repository-tooling contract level: the project can model small CLI-only releases, dogfood snapshots, reused toolchain layers, content-addressed state, delta/fallback update strategy, and Windows toolchain component comparison. April 24, 2026 host-backed Windows dogfood evidence on a fresh `windows-2022` `otvm` lease proved a local-assets-only `.63` bootstrap install and `.63 -> .64` CLI update using a reused unchanged MSYS2 toolchain layer; the update trace reached `windows.upgrade.cli.stage.smoke.ok`, skipped toolchain relocation, and activated the new release. Remaining implementation depth is live warm-builder orchestration and native byte-delta application.

## Phase 26. Cross-Platform Smoke Harness And Release-Proving Scenarios

### A. Smoke Harness Architecture
- Introduce a first-class smoke-test harness distinct from unit tests, contract tests, and narrow integration tests.
- Build the harness around three explicit records:
  - `scenario`: the workflow being proven
  - `target`: the platform/architecture/toolchain combination under test
  - `runner`: the execution transport, such as local process, SSH host, or `otvm` lease
- Prefer a Python-based harness so the project can reuse existing Python build/test infrastructure, structured JSON assertions, and remote execution helpers without scattering more shell-only test logic.
- Treat smoke tests as extensible infrastructure rather than a one-off set of scripts; adding a new smoke scenario later should require declaring target applicability, fixture inputs, steps, and assertions rather than cloning a whole validation script.
- Keep smoke orchestration logic separate from per-platform command fragments so one scenario definition can run across multiple targets with target-specific adapters only where necessary.

### B. Scenario Model And Extensibility
- Define every smoke scenario with stable metadata including:
  - scenario ID
  - summary
  - supported targets
  - estimated duration
  - network requirement
  - GUI requirement
  - destructive or isolated-prefix requirement
  - artifact/channel prerequisites
- Make scenarios composable so target suites can select a subset such as `core`, `update`, `gui`, or `release`.
- Require scenario steps to emit structured results and named assertions rather than only shell exit codes or free-form log text.
- Preserve a low-friction path for future scenarios such as package install/remove smoke, GUI app qualification, GCC interoperability smoke, upgrade-from-two-versions-back, or damaged-state repair smoke.
- Ensure scenarios can consume pinned fixtures from the repository or pinned upstream revisions rather than drifting against moving external `HEAD` state.

### C. Core Tier 1 Smoke Scenarios
- Formalize the current manual validation set as canonical smoke scenarios for Tier 1 release-validation targets:
  - `bootstrap-install-usable-cli`
  - `new-cli-project-build-run`
  - `gorm-build-run`
  - `self-update-cli-only`
- `bootstrap-install-usable-cli` should prove that the bootstrap script installs into a user-scoped root, produces a usable `gnustep` entry point, and can execute `--help`, `--version`, and `doctor --json`.
- `new-cli-project-build-run` should prove that `gnustep new` creates a usable fresh project, `gnustep build` completes successfully, and `gnustep run` executes the expected sample output.
- `gorm-build-run` should use a pinned Gorm revision or tag and prove that the installed CLI can build and launch a known real GNUstep GUI application on supported GUI targets.
- `self-update-cli-only` should install an older dogfood or staged release, verify `gnustep update --check`, apply a CLI-only update, verify the selected layer plan, and rerun at least one post-update build/run workflow.
- Treat these four scenarios as the minimum release-proving smoke bar for the currently active Tier 1 targets unless a roadmap revision explicitly changes that bar.

### D. Target Matrix And Target Profiles
- Define target profiles for at least:
  - `windows-amd64-msys2-clang64`
  - `openbsd-amd64-clang`
- Target profiles should record remote OS family, shell or PowerShell invocation mode, path conventions, bootstrap entry point, expected managed layout, GUI capability, and required host provisioning method.
- Support a future matrix expansion path for Linux amd64/clang, Windows amd64/MSVC, Linux arm64, and GCC/native-toolchain smoke without redesigning the harness.
- Allow each target profile to opt scenarios in or out explicitly; for example, GUI scenarios may be unavailable on a headless lease while still allowing bootstrap/new/update smoke to run.
- Record target-specific expected assertions such as toolchain flavor, Objective-C runtime, bootstrap script variant, and managed install root style so smoke failures can distinguish harness mismatch from product regression.

### E. Runner Layer And OTVM Integration
- Add runner implementations for:
  - local process execution
  - generic SSH execution
  - `otvm` lease-backed execution
- Keep `otvm` lease lifecycle in the runner layer rather than embedding lease creation and teardown inside each scenario.
- Require the `otvm` runner to support create/reuse, TTL selection, artifact staging, result retrieval, explicit cleanup, and failure-safe destroy behavior.
- Prefer short-lived lease-backed smoke for Windows and OpenBSD when no equivalent local runner exists, while still allowing reuse of existing active leases during rapid debugging.
- Preserve the existing ad hoc validation scripts as transitional evidence only until equivalent scenario coverage exists in the shared harness, then retire or reduce those scripts to thin wrappers around the harness.

### F. Assertions, Logs, And Report Format
- Emit one machine-readable smoke report per run with stable fields such as:
  - schema version
  - smoke suite ID
  - target ID
  - scenario results
  - command transcript references
  - manifest/release identity
  - artifact IDs and digests under test
  - overall status
- Record stdout, stderr, exit code, timing, and structured assertion results for every step.
- Preserve failure artifacts automatically, including remote command logs, staged manifests, installed state files, and any scenario-specific evidence such as Gorm launch logs or update-plan JSON.
- Prefer assertions over English matching wherever a stable machine-readable surface exists, but keep a limited set of human-output smoke checks where output clarity is itself part of the product contract.
- Make the report format suitable for both local debugging and release-gate consumption.

### G. Fixture And Provenance Policy
- Pin external smoke inputs explicitly, including Gorm source revision, demo project expectations, and any package smoke fixtures.
- Keep repository-owned smoke fixtures small, reproducible, and human-reviewable.
- Do not allow smoke scenarios to silently consume mutable upstream default branches or mutable package indexes unless the scenario is explicitly testing that live channel behavior.
- Record the manifest URL/path, artifact digests, fixture revisions, and source revision of the CLI in every smoke report so a pass is reproducible and auditable later.
- For update smoke, record both the installed base release identity and the target release identity so regressions in update planning and activation can be reasoned about after the fact.

### H. Execution Modes And Developer Workflow
- Add explicit smoke modes such as:
  - `quick`: core scenarios on one target
  - `tier1-core`: canonical scenarios on all active Tier 1 targets
  - `release`: full release-proving smoke matrix
- Provide one command that can run a selected smoke suite against one or more declared targets without forcing developers to remember the per-target shell/PowerShell details.
- Allow smoke runs to consume either a local staged release directory, a published manifest URL, or a dogfood channel manifest.
- Keep local unit tests fast and separate; smoke should be an intentional command with heavier prerequisites and clearer evidence output.
- Add thin convenience wrappers under `scripts/dev/` as needed, but keep the authoritative execution model in the shared harness rather than duplicating target logic in multiple wrapper scripts.

### I. Release Gates And Policy Integration
- Make smoke suite results consumable by release qualification tooling so dogfood, release-candidate, and stable-publication gates can require the appropriate smoke suites by target.
- Require Tier 1 targets to pass the canonical smoke scenarios before the project claims that a new release, dogfood snapshot, or reused layered artifact is validated for that target.
- Integrate update smoke with the layered-artifact policy from Phase 25 so release gates can prove that CLI-only iterations do not unnecessarily rebuild or redownload unchanged toolchain layers.
- Allow scoped dogfood sessions to run a reduced target set while still marking full release qualification as incomplete until the broader smoke matrix has passed.
- Ensure release gates can distinguish:
  - smoke not run
  - smoke failed
  - smoke passed with explicit documented non-release blockers for deferred targets

### J. Exit Criteria
- The repository contains a reusable smoke harness with explicit scenario, target, and runner models rather than only one-off validation scripts.
- The four canonical smoke scenarios are implemented and executable through the harness for the current active Tier 1 targets.
- Windows `amd64/msys2-clang64` and OpenBSD `amd64/clang` can each produce a machine-readable smoke report that proves bootstrap install, new project build/run, Gorm build/run where GUI support is available, and CLI self-update behavior.
- Developers can add a new smoke scenario without redesigning the harness or copying whole platform-specific validation scripts.
- Dogfood and release qualification flows can consume smoke results directly and use them as evidence for target readiness.
- Existing ad hoc host-backed validation scripts are either reduced to wrappers around the smoke harness or explicitly marked as temporary until the equivalent shared smoke scenario exists.

### Phase 26 Execution Status
- Phase 26.A is implemented through `src/gnustep_cli_shared/smoke_harness.py`, which introduces explicit smoke runner, target, and scenario records plus catalog validation and suite planning primitives. This establishes a reusable Python-based harness layer distinct from the existing unit and narrow integration tests.
- Phase 26.B is implemented at the catalog-definition level: smoke scenarios now carry stable metadata for supported targets, estimated duration, network/gui requirements, isolation/destructive behavior, fixture policy, artifact/channel prerequisites, tags, and named assertions so additional scenarios can be added without cloning full validation scripts.
- Phase 26.C is implemented as the first canonical Tier 1 smoke catalog with four shared scenarios: `bootstrap-install-usable-cli`, `new-cli-project-build-run`, `gorm-build-run`, and `self-update-cli-only`.
- Phase 26.D is implemented for the currently active Tier 1 targets `windows-amd64-msys2-clang64` and `openbsd-amd64-clang`, including explicit bootstrap style, shell/path conventions, GUI availability, managed-root style, expected Objective-C runtime, and default runner profile metadata. Windows remains modeled as a managed MSYS2 `clang64` artifact target; OpenBSD is now explicitly modeled as the preferred native-packaged GNUstep path for v1 smoke qualification rather than as requiring a managed OpenBSD toolchain artifact.
- Phase 26.E is implemented at the runner-contract level: the shared harness now models local-process, SSH-host, and `otvm` lease runners, and can emit structured execution plans covering transport requirements, lease profile selection, stage actions, TTL/reuse policy, result retrieval, and cleanup behavior.
- Phase 26.F is implemented through structured smoke report records for command transcripts, assertion results, step results, scenario reports, and top-level run reports. `scripts/dev/run-smoke-tests.py --report-template ...` now emits a machine-readable report template that includes target metadata, runner plan, fixture references, and scenario placeholders before live execution exists.
- Phase 26.G is implemented through a pinned fixture catalog with explicit provenance records. The harness now records immutable Gorm source identity (`gorm-1_5_0` / `a8cd1792e08a50dd9900474373e6ca8daad4a4a9`), repository-owned generated CLI output expectations, and update-channel policy fixtures for CLI-only dogfood update smoke.
- Phase 26.H is implemented through explicit suite modes and developer workflow surfaces: the harness now defines `quick`, `tier1-core`, and `release` suites, and `scripts/dev/run-smoke-tests.py --workflow-plan ...` can emit the intended developer command sequence for catalog validation, runner planning, and report-template generation against selected targets and release sources.
- Phase 26.I is implemented through report-based smoke release gates. The harness now models `dogfood`, `release-candidate`, and `stable` gate policies, can evaluate one or more smoke report JSON files against the required suite/target set, and exposes that policy through `scripts/dev/run-smoke-tests.py --release-gate ...`.
- Phase 26.J is implemented and currently satisfied by live evidence: `scripts/dev/run-smoke-tests.py --phase26-exit-status [--report ...]` evaluates whether the framework is present and whether supplied Tier 1 smoke reports satisfy the release-candidate gate. On April 27, 2026, the phase exit check passed with the OpenBSD native-packaged Tier 1 report and the Windows MSYS2 `clang64` patched-Gorm Tier 1 report.
- Phase 26.J now also supports importing externally collected live evidence as structured smoke reports through `scripts/dev/run-smoke-tests.py --evidence-report`. Release gates reject partial reports that omit required scenarios or contain failed scenario entries. The accepted April 24 evidence covers both active Tier 1 targets: `windows-amd64-msys2-clang64` and `openbsd-amd64-clang`, each including `bootstrap-install-usable-cli`, `new-cli-project-build-run`, `gorm-build-run`, and `self-update-cli-only`.
- `scripts/dev/run-smoke-tests.py` now exposes the smoke catalog as a lightweight planning/listing/report/gating command, and `tests/test_smoke_harness.py` provides focused regression coverage for framework definitions, runner plans, report templates, fixture provenance, workflow modes, release gates, and Phase 26 exit-status evaluation.

### Current Phase 26 Focus

- Treat Phase 26 as a release-maintenance gate rather than the primary blocker.
  The April 27, 2026 release-candidate gate passed with both active Tier 1
  targets represented.
- Preserve the accepted evidence bundle paths in release qualification notes:
  `.artifacts/phase26-openbsd-tier1-20260424/openbsd-tier1-report.json` and
  `.artifacts/phase26-windows-gorm-patched-20260424/windows-tier1-report-patched-gorm.json`.
- Re-run the gate whenever refreshed artifacts are published or any Tier 1
  target metadata changes.
- The next release-critical work should stay on Phase 12/13 production trust,
  production build automation, and production-like `gnustep update all --yes`
  evidence before returning to warm-builder live orchestration or native
  byte-delta application.

## Testing Principles For All Phases

### A. Unit Testing Standard
- Every shared parser, selector, classifier, normalizer, serializer, planner, transaction primitive, and state transition should have unit tests.
- Objective-C/full-CLI unit tests must be executable `tools-xctest` tests under `src/full-cli/Tests` whenever the behavior lives in the native CLI.
- Prefer table-driven or fixture-driven tests for compatibility, classification, manifest selection, package selection, and update-planning logic.
- New feature work should land tests with the implementation, not as a later cleanup phase.

### B. Contract Testing Standard
- Every versioned JSON schema should have positive and negative contract tests.
- Every stable command `--json` payload should have tests that assert machine-readable fields, not only English summaries.
- Contract tests should cover success, usage error, environment failure, compatibility failure, and internal/recovery failure envelopes where the command can produce them.
- Human-readable output that is intentionally unstable should still have focused smoke tests for clarity and completeness.

### C. Integration Testing Standard
- Every command with side effects should have staging/integration tests.
- Install, remove, setup, repair, rollback, and update operations should always be tested in isolated prefixes.
- Transactional operations should have both success-path and failure-injection tests that verify rollback and final state consistency.
- Built-artifact smoke tests should exercise the installed executable path, not only direct method calls, before release claims are made.

### D. Regression Testing Standard
- Every bug that reaches implementation, dogfood, external validation, or beta validation should add a regression test.
- If a regression cannot be automated immediately, the roadmap entry must name the blocker and the manual validation evidence required until automation is available.
- Bug reports logged in the repository should link to or name the covering test once fixed.

### E. Cross-Platform Testing Standard
- Tier 1 targets must have explicit automated coverage in CI or dedicated release validation infrastructure.
- Windows Tier 1 validation should preferentially use `../OracleTestVMs` and `otvm` for short-lived leased execution when a native Windows runner is not otherwise available.
- GCC interoperability should have explicit live validation on a disposable Debian host with stock distro GNUstep packages installed so the project can confirm the full CLI still builds in that common real-world environment.
- Platform-specific behavior should have unit coverage where it is modeled in code and host-backed smoke coverage where the behavior depends on the target OS.

### F. Release Gate Standard
- No phase should be considered complete until its corresponding automated tests are in place and passing.
- A release candidate requires the Python/shared suite, the native Objective-C `tools-xctest` suite, package-index/repository contract tests, built-artifact smoke tests, and required Tier 1 host-backed validation to pass or have explicitly documented non-release blockers.

## External Validation Infrastructure

### A. OracleTestVMs Integration
- Use the sister repository `../OracleTestVMs` and its `otvm` CLI as the planned external Windows lease provider for live PowerShell and Windows integration testing.
- Treat `otvm` as part of the project's validation tooling strategy rather than an ad hoc manual testing path.
- For the current release, `otvm` now has profile coverage for native-toolchain discovery and validation on:
  - OpenBSD
  - Fedora
  - Debian
  - Arch
- Keep these profiles in the release qualification rotation and run Fedora/Arch managed-toolchain validation for preferred modern-runtime coverage.
- Treat openSUSE, RHEL-family distributions/clones, and Alpine as future `otvm` profile targets rather than current-release requirements.

### B. Cost-Control And Cleanup Rules
- Do not rely on long-lived idle Oracle Windows VMs for routine validation.
- Prefer short-lived leases with explicit low TTL values.
- Every live Windows validation workflow must include explicit destroy-on-success and destroy-on-failure cleanup behavior.
- Run `otvm reap` as a scheduled or end-of-run safety backstop to catch expired or orphaned leases.
- Avoid `--keep-on-failure` except when deliberate debugging requires preserving a failed lease temporarily.
