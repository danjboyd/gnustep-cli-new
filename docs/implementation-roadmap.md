# GNUstep CLI Implementation Roadmap

## Purpose

This roadmap breaks the project into numbered phases with lettered subphases so implementation can proceed deliberately and test coverage can remain ahead of complexity. The intent is to build the smallest coherent slices first, validate them hard, and avoid drifting into a partially working tool with unclear support boundaries.

Testing is a first-class requirement in every phase. Each phase should leave behind stable automated tests before the next phase expands scope.

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
- Plan Windows execution testing around short-lived Oracle OCI leases provisioned through the sister repository `../OracleTestVMs` and its `otvm` CLI rather than assuming a permanent local Windows environment.

### C. Shared Output And Exit-Code Behavior
- Ensure bootstrap follows the common exit-code policy.
- Ensure bootstrap help shows the full command surface and clearly marks unavailable commands.
- Ensure unsupported commands fail clearly and consistently.

### D. Downloader Detection
- On Unix-like systems, implement downloader detection for `curl` and `wget`.
- Fail cleanly when neither is available.
- On Windows, implement the corresponding bootstrap networking assumptions using PowerShell-native capabilities.

### E. Testing
- Unit tests or fixture-driven command tests for bootstrap argument parsing and help output.
- Cross-platform behavioral tests for unsupported-command messaging.
- Exit-code tests for success, usage errors, prerequisite failures, and incompatibility conditions.
- For Windows PowerShell validation, use `otvm`-provisioned short-lived `windows-2022` leases when live testing is needed.
- Windows live tests should always use a short lease TTL, destroy the lease on completion or failure, and use `otvm reap` as a backstop cleanup mechanism.

### F. Exit Criteria
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

### F. Repair And Re-Run Behavior
- Ensure re-running `setup` is safe.
- Support repair of incomplete or outdated managed installations.

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

### E. Testing
- Exhaustive unit tests for command dispatch, option parsing, JSON output, and exit-code behavior.
- Parity tests comparing bootstrap and full CLI behavior on overlapping functionality.
- Use `otvm` Windows leases for live PowerShell and Windows-specific full-CLI validation when local execution is not available.

### F. Exit Criteria
- The full CLI exists as the primary installed command surface with working `doctor` and `setup`.

## Phase 7. Build And Run Commands

### A. GNUstep Make Project Detection
- Implement conservative project discovery for GNUstep Make projects.
- Fail clearly for unsupported or ambiguous project layouts.

### B. Build Command
- Implement `build` as a thin wrapper around GNUstep Make.
- Capture backend invocation, status, and key outputs.

### C. Run Command
- Implement `run` as a thin wrapper around GNUstep execution conventions such as `openapp`.
- Resolve and execute the primary run target.

### D. JSON Output
- Implement structured output for `build --json` and `run --json`.

### E. Testing
- Unit tests for project detection and command planning.
- Integration tests using fixture GNUstep Make projects.
- Failure-path tests for ambiguous or unsupported project states.
- JSON output tests.

### F. Exit Criteria
- `build` and `run` work reliably for supported GNUstep Make projects.

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

### E. Testing
- Exhaustive schema and policy unit tests.
- Fixture tests for valid and invalid packages of every kind.
- Golden output tests for maintainer guidance and failure reports.

### F. Exit Criteria
- Maintainers can prepare and validate packages locally before submission.

## Phase 10. Package Repository And Publication Pipeline

### A. Official Package Repository
- Create the official package repository structure.
- Add schemas, docs, and CI scaffolding.

### B. Index Generation
- Implement generation of the published package index from per-package directories.

### C. Submission Workflow
- Document and automate the PR-based submission model.
- Ensure generated outputs are not hand-edited.

### D. Review Workflow
- Define review checklists and automation handoffs.

### E. Testing
- Tests for package repository generation.
- CI fixture tests simulating package additions and updates.
- Tests for generated index correctness and determinism.

### F. Exit Criteria
- The official package repository can accept reviewed package submissions and generate a valid package index.

## Phase 11. Package Installation And Removal

### A. Install Command
- Implement `install` against the official package index.
- Resolve compatible artifacts for the selected environment.
- Enforce dependency and compatibility rules.

### B. Transactional Package Installation
- Stage package extraction and integration changes.
- Finalize only when validation succeeds.

### C. Remove Command
- Implement `remove` using installed-files manifests and dependency safeguards.
- Remove generated integration artifacts cleanly.

### D. Package State Tracking
- Track installed packages, selected artifacts, dependency relationships, and owned files.

### E. Testing
- Exhaustive install/remove transaction tests.
- Dependency satisfaction and rejection tests.
- File ownership and cleanup tests.
- Upgrade/reinstall tests for packages.

### F. Exit Criteria
- Users can install and remove reviewed packages safely inside the managed environment.

## Phase 12. Official Build Infrastructure

### A. CLI Artifact Builds
- Implement project-controlled builds for supported CLI targets.

### B. Toolchain Artifact Builds
- Implement project-controlled managed toolchain artifact builds for Tier 1 targets.

### C. Package Artifact Builds
- Implement official package builds from source and package metadata.

### D. Publishing Pipeline
- Publish artifacts, regenerate manifests and indexes, and stage releases by channel.

### E. Testing
- CI verification for every build target.
- Smoke install tests of published artifacts.
- Reproducibility or consistency checks where practical.
- Tier 1 Windows smoke validation should run against ephemeral `otvm` leases or an equivalent short-lived Windows execution environment rather than a permanently running VM.

### F. Exit Criteria
- Official artifacts are built and published through controlled automation.

## Phase 13. Upgrade, Repair, And Lifecycle Operations

### A. CLI Upgrade Flow
- Implement upgrade detection and installation for the full CLI.

### B. Toolchain Upgrade Flow
- Implement managed toolchain upgrades with safety checks.

### C. Repair Operations
- Support recovery from partial installs, missing files, or stale state.

### D. Lifecycle State Handling
- Ensure state tracking remains consistent across installs, upgrades, removals, and interrupted operations.

### E. Testing
- Upgrade path tests from older manifests and artifacts.
- Repair tests for interrupted operations and corrupted state.
- Backward-compatibility tests for manifests and state records where supported.

### F. Exit Criteria
- Managed environments can be updated and repaired without fragile manual recovery.

## Phase 14. Cross-Platform Integration Polish

### A. Linux/OpenBSD Integration
- Finalize shell integration, desktop integration, and user messaging for Unix-like environments.

### B. Windows Integration
- Finalize PowerShell bootstrap behavior, Start Menu integration, and Windows-specific messaging.
- Ensure MSYS2 and MSVC paths remain clearly separated.
- Use `otvm` for live Windows integration validation and ensure test procedures always destroy leases promptly after use.

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

### C. Documentation Polish
- Finalize user docs, maintainer docs, contribution docs, and operational docs.

### D. Beta Validation
- Run structured beta validation across supported targets and representative environments.

### E. Release Readiness Review
- Review supported-target claims, known limitations, package quality bar, and upgrade expectations.

### F. Exit Criteria
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

### B. Linux `amd64/clang` Managed Toolchain Build
- Implement the first real managed toolchain build pipeline for Linux `amd64/clang`.
- Build the pinned component set into a staging prefix.
- Produce a toolchain manifest, source lock, component inventory, checksums, and archive artifact.

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

## Phase 17. Remaining Tier 1 Toolchain Builds

### A. OpenBSD `amd64/clang` Managed Toolchain Build
- Implement the OpenBSD managed toolchain pipeline using the same pinned GNUstep component set.
- Record and apply OpenBSD-specific patches explicitly.
- Validate the resulting artifact with compile, link, run, and `doctor` coverage.
- Keep the managed OpenBSD toolchain path optional in product policy if the packaged OpenBSD GNUstep environment proves sufficient for the CLI's supported workflows.

### B. Windows `amd64/msys2-clang64` Managed Toolchain Assembly
- Define the pinned MSYS2 package input set for the Windows `clang64` target.
- Include `libdispatch` when the curated MSYS2-based assembly supports it cleanly.
- Include CoreBase only when it is available in a validated form for this target.
- Normalize the curated package inputs into the managed install layout.
- Produce a release-style managed toolchain artifact with checksums and component inventory.

### C. Windows `amd64/msvc` Go/No-Go Workstream
- Implement the dedicated MSVC managed toolchain pipeline if feasible.
- Keep MSVC-specific source locks, patches, and inventories separate from the MSYS2 target.
- If the MSVC stack is not production-ready, mark it explicitly as not yet published rather than silently degrading support claims.

### D. Tier 1 Live Validation
- Validate Windows artifacts on short-lived `otvm` leases.
- Validate OpenBSD artifacts on the corresponding dedicated validation host or VM path.
- Ensure every live validation flow destroys external leases or instances promptly after use.

### E. Testing
- Exhaustive per-target build and assembly plan tests.
- Artifact unpack/install/validate smoke tests for every Tier 1 managed toolchain artifact.
- Windows lease-backed regression tests for PowerShell bootstrap plus managed toolchain installation.
- Cross-target consistency tests for toolchain manifests, component inventories, and release metadata.

### F. Exit Criteria
- Every published Tier 1 managed toolchain artifact has a repeatable build or assembly path and explicit validation evidence.

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

### D. Build The Full CLI For Tier 1 Targets
- Build the Objective-C full CLI against each supported managed toolchain target.
- Produce release-style CLI artifacts, checksums, and manifest entries.
- Verify that the full CLI can bootstrap normal user workflows on each supported target.

### E. Testing
- Exhaustive unit tests for Objective-C command parsing, dispatch, JSON output, and failure behavior.
- Integration tests that exercise the built full CLI against staged managed toolchains.
- Regression tests for bootstrap-to-full handoff, command parity, and manifest-driven setup behavior.
- Windows live smoke tests of the built full CLI on `otvm` leases where native runners are unavailable.
- Add a Debian live-validation path that provisions an `otvm` Linux lease or equivalent disposable Debian VM with stock distro GNUstep packages installed and verifies that the full Objective-C CLI can still be built in the GCC-based environment.
- Treat that Debian GCC build as an interoperability test, not as evidence that Debian's stock toolchain is a managed Tier 1 artifact target.
- Add an OpenBSD live-validation path that uses the packaged OpenBSD Clang/GNUstep environment and determines whether it is sufficient to support the CLI as a preferred packaged-toolchain path.

### F. Exit Criteria
- The full GNUstep-based CLI is built, tested, and usable as the primary installed command on the supported published targets.

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
- A structured Debian GCC interoperability validation plan now exists in the
  build infrastructure so the remaining GCC live-validation work is executable
  once disposable Debian host capacity is available.
- A generated CLI-tool project was created, built, and run successfully through
  the Objective-C front end.
- Package installation and removal were validated against a local manifest and
  archive fixture using the built native CLI.
- On April 10, 2026, the libvirt-backed `OracleTestVMs` farm was exercised
  directly for the remaining OpenBSD and Debian live-validation paths using a
  corrected host inventory (`iep-vm2` and `iep-ocr01`, `default` storage pool,
  `br0` network, and the current `debian13-wayland.qcow2` /
  `openbsd78-fvwm.qcow2` image references).
- Phase 18E preflight is now proven on the real farm for both
  `openbsd-7.8-fvwm` and `debian-13-gnome-wayland`. The libvirt dependency,
  host connectivity, storage pool visibility, bridge visibility, and pinned
  image presence checks all passed against the corrected farm subset.
- The corresponding live acceptance paths currently regress in the guest
  readiness stage rather than in provisioning:
  - OpenBSD lease `lease-20260410212940-vu2p3e` launched on `iep-vm2`,
    obtained `172.17.2.115`, and passed TCP port 22 readiness before stalling
    in the `oracleadmin` SSH readiness probe.
  - Debian lease `lease-20260410213335-0zitc1` launched on `iep-vm2`,
    obtained `172.17.2.171`, and passed TCP port 22 plus port 3389 readiness
    before stalling in the `debian` SSH readiness probe.
- Direct SSH validation against both guests confirmed that the current images
  reject both available operator keys (`~/.ssh/id_rsa` and
  `~/.ssh/oracletestvms_ed25519`). That makes the remaining blocker guest-image
  SSH key alignment or guest bootstrap hygiene, not libvirt farm reachability.
- The stalled OpenBSD and Debian leases were destroyed cleanly after evidence
  capture, so destroy-path hygiene on the libvirt backend was exercised even
  though ready-state acceptance did not complete.
- Phase 18E is therefore partially executed but not complete: the farm route is
  validated, while the OpenBSD packaged-path decision and the Debian GCC
  interoperability acceptance remain blocked on image repair and rerun.
- Phase 18F remains open because the supported non-Linux live-validation set
  still lacks a clean ready/destroy evidence pass on the current farm-backed
  OpenBSD and Debian images.
- Windows full-CLI live build validation should continue as follow-up work, but
  Windows managed toolchain assembly and bootstrap validation were already
  proven earlier in the roadmap.

## Phase 19. GitHub Release Publication And End-To-End Consumption

### A. Release Asset Naming And Layout
- Finalize release asset naming for full CLI artifacts, managed toolchain artifacts, checksums, manifests, and validation evidence.
- Ensure asset naming stays subordinate to the release manifest rather than becoming the discovery protocol.

### B. GitHub Release Publication Pipeline
- Implement project-controlled publication of full CLI artifacts, managed toolchain artifacts, checksums, and release manifests to GitHub Releases.
- Ensure publication uses the configured GitHub operator account and produces deterministic release metadata.

### C. Manifest Wiring
- Publish release manifests whose artifact URLs point at the canonical GitHub Release assets.
- Ensure bootstrap and full `setup` can consume those manifests without any GitHub-page scraping behavior.

### D. End-To-End Install Qualification
- Verify fresh-machine flows from bootstrap script to installed managed toolchain to installed full CLI using the actual published GitHub Release assets.
- Exercise supported Unix flows plus Windows lease-backed flows through `otvm`.

### E. Testing
- Release-pipeline tests for asset completeness, checksum coverage, and manifest correctness.
- End-to-end fresh-host install tests using published release artifacts rather than local staging paths.
- Regression tests for broken asset URLs, missing checksums, mismatched manifests, and interrupted downloads.

### F. Exit Criteria
- Supported v1 platforms have live GitHub-hosted CLI and managed-toolchain binaries, and bootstrap plus full `setup` can install them end-to-end from the published release manifest.

### Phase 19 Execution Status
- Release staging, checksum generation, manifest emission, GitHub release
  command planning, and local release qualification are implemented.
- A real staged Linux release payload exists under `dist/stable/0.1.0-dev`
  and has been verified successfully.
- Local qualification against the staged release directory succeeds and extracts
  the CLI and managed toolchain into a disposable install root.
- A GitHub Actions workflow skeleton exists for release publication.
- Live GitHub publication is still blocked because this repository has no Git
  remote configured and no GitHub repository currently exists at
  `danjboyd/gnustep-cli-new`.

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

### E. Testing
- Add contract tests proving bootstrap and full share the same envelope and status vocabulary.
- Add regression tests for unavailable-check reporting semantics.
- Add fixture and live tests for full-CLI deep validation paths.

### F. Exit Criteria
- Bootstrap and full `doctor` share one policy model while differing intentionally in diagnostic depth.
- Bootstrap `doctor` is clearly installer-oriented, and full `doctor` is the authoritative deep diagnostic interface.

## Phase 21. Setup, Repair, And Managed Lifecycle Hardening

### A. Manifest And Artifact Validation
- Validate manifest schema versions explicitly during setup.
- Harden artifact selection against malformed manifests, unsupported hosts, and ambiguous matches.
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

### E. Testing
- Add failure-injection tests for interrupted setup, corrupted state, and broken manifests.
- Add rollback and repair tests.
- Add shell-integration tests for supported Unix shells and Windows PowerShell behavior.

### F. Exit Criteria
- `setup` is not just an installer prototype; it is a recoverable lifecycle operation for install, repair, and upgrade.

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

### E. Testing
- Add end-to-end install/remove tests using a generated package index.
- Add dependency, conflict, compatibility, and ownership regression tests.
- Add upgrade and reinstall tests for reviewed packages.

### F. Exit Criteria
- Users can install and remove reviewed packages safely through the official package workflow.

## Phase 23. Release Candidate Consolidation

### A. Repository Health And Release Gates
- Restore a fully green automated test suite and keep it green as a release gate.
- Promote the regression suite into a required release-readiness signal rather than a best-effort helper.

### B. Documentation Freshness
- Bring the README and status docs into alignment with the actual implementation state.
- Distinguish clearly among shipped behavior, validated behavior, prototype behavior, and externally blocked targets.
- Reconcile status-report claims with the live repository state, including release publication configuration, remote/repository availability, and which validations are still pending versus completed.

### C. Support Matrix Review
- Reconcile claimed support with validated release artifacts and qualification evidence.
- Record known limitations explicitly for GCC interoperability, OpenBSD, Windows MSYS2, and deferred MSVC work.

### D. Structured Beta And Qualification Runs
- Run fresh-host qualification on every supported published target.
- Run explicit bootstrap-to-full handoff validation and package-flow smoke tests on release-candidate artifacts.
- Capture release evidence in a form that is auditable by maintainers later.
- Run explicit OpenBSD qualification against the packaged GNUstep path and record whether that path is supported and preferred versus managed installation.

### E. Exit Criteria
- The project has a defensible v1 release candidate with accurate docs, passing release gates, and validated support claims.

## Testing Principles For All Phases

### A. Unit Testing Standard
- Every shared parser, selector, classifier, normalizer, and serializer should have exhaustive unit tests.
- Prefer table-driven or fixture-driven tests for compatibility and classification logic.

### B. Contract Testing Standard
- Every versioned JSON schema should have positive and negative contract tests.
- Human-readable output that is intentionally unstable should still have focused smoke tests for clarity and completeness.

### C. Integration Testing Standard
- Every command with side effects should have staging/integration tests.
- Install, remove, and upgrade operations should always be tested in isolated prefixes.

### D. Regression Testing Standard
- Every bug that reaches implementation or beta validation should add a regression test.

### E. Cross-Platform Testing Standard
- Tier 1 targets must have explicit automated coverage in CI or dedicated release validation infrastructure.
- Windows Tier 1 validation should preferentially use `../OracleTestVMs` and `otvm` for short-lived leased execution when a native Windows runner is not otherwise available.
- GCC interoperability should have explicit live validation on a disposable Debian host with stock distro GNUstep packages installed so the project can confirm the full CLI still builds in that common real-world environment.

### F. Release Gate Standard
- No phase should be considered complete until its corresponding automated tests are in place and passing.

## External Validation Infrastructure

### A. OracleTestVMs Integration
- Use the sister repository `../OracleTestVMs` and its `otvm` CLI as the planned external Windows lease provider for live PowerShell and Windows integration testing.
- Treat `otvm` as part of the project's validation tooling strategy rather than an ad hoc manual testing path.

### B. Cost-Control And Cleanup Rules
- Do not rely on long-lived idle Oracle Windows VMs for routine validation.
- Prefer short-lived leases with explicit low TTL values.
- Every live Windows validation workflow must include explicit destroy-on-success and destroy-on-failure cleanup behavior.
- Run `otvm reap` as a scheduled or end-of-run safety backstop to catch expired or orphaned leases.
- Avoid `--keep-on-failure` except when deliberate debugging requires preserving a failed lease temporarily.
