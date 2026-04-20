# Production Signing And Trust Roots

This document records the production signing policy for release metadata and package-index consumption.

## Policy

- Production releases must verify release metadata against an externally pinned release trust root. The release trust root must come from CI configuration, a signing service, or another maintainer-controlled trusted channel, not from the same release assets being verified.
- Production package-index consumption must verify package-index metadata against an externally pinned package-index trust root. The package-index signing key is distinct from the release metadata signing key.
- Colocated public keys in release or package-index assets are useful for diagnostics and prerelease bring-up, but they are not sufficient by themselves for production trust decisions.
- Development and prerelease flows may allow unsigned package indexes only when the command or workflow passes an explicit development override such as `--allow-unsigned-package-index` or `--allow-unsigned-index`.
- Official package artifacts must remain tied to reviewed package metadata, provenance, checksums, and compatibility declarations. Signature verification supplements that policy; it does not replace package review or source provenance.

## Current Enforcement Points

- `scripts/internal/build_infra.py --json controlled-release-gate` verifies release metadata and, when supplied, the package index in one production release gate. For production mode, package-index verification now requires an externally supplied package-index trust root rather than accepting a colocated public key.
- `scripts/internal/build_infra.py --json package-artifact-publication-gate --packages-dir packages` fails publication when reviewed package manifests still contain placeholder source or artifact digests.
- `.github/workflows/release.yml` now requires release signing material, package-index signing material, `GNUSTEP_CLI_RELEASE_TRUST_ROOT`, and `GNUSTEP_CLI_PACKAGE_INDEX_TRUST_ROOT` before publication. The release workflow no longer falls back to unsigned package-index verification.
- `scripts/internal/install_package.py --index <index>` enforces package-index trust by default when installing through an index.
- Native and shared package flows must continue to prefer signed package-index consumption over direct package-manifest installation for end-user package installs.

## Key Management Requirements Before v1 Production

- Generate and store the release metadata signing private key outside the repository.
- Generate and store the package-index signing private key outside the repository, separately from the release key.
- Store public trust roots in CI secrets, a signing-service configuration, or another explicit trusted channel.
- Document key rotation, revocation, and emergency denylist procedures before claiming production release security.
- Run a release drill that proves verification fails with the wrong trust root and passes only with the pinned production trust root.

## Required Security Drills

Before production security claims, CI or the signing service must run these drills against release metadata and package-index metadata:

- wrong trust root: verification must fail when a different public key is pinned
- expired metadata: verification must fail when `expires_at` is in the past
- rollback/freeze: verification must fail when stale metadata is presented after a fresher trusted version has been accepted by the release process
- revoked artifact or package: verification must fail when the selected artifact/package appears in the signed revocation list
- tampered provenance: verification must fail when manifest/index content no longer matches provenance digests
- compromised-key response: maintainers must be able to rotate the trust root and publish an emergency denylist without requiring users to trust the compromised key again

The current tooling enforces signature validity, externally pinned trust roots, provenance digest matching, metadata expiry when present, revocation-list checks, package artifact publication readiness, and nonzero CLI exits for failed package-index trust gates. Rollback/freeze prevention still needs persistent client-side or release-service state before production claims.

## Non-Goals

- Do not trust GitHub asset names or release-page scraping as an integrity mechanism.
- Do not treat checksums fetched from the same unauthenticated channel as sufficient for production integrity.
- Do not silently fall back from signature verification to unsigned installation in production paths.
