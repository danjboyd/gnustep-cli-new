# Bug Report: `gnustep build` Rejected Aggregate GNUstep Make Projects

Date: 2026-04-19
Status: fixed in working tree

## Summary

`gnustep build` rejected valid aggregate GNUstep Make projects whose top-level
`GNUmakefile` did not declare `TOOL_NAME`, `APP_NAME`, or `LIBRARY_NAME`
directly.

This broke projects such as Gorm, where the top-level makefile uses
`SUBPROJECTS` and includes `$(GNUSTEP_MAKEFILES)/aggregate.make`.

## Expected Behavior

A directory containing `GNUmakefile` is a buildable GNUstep Make project for
`gnustep build`. The CLI should invoke `make` and let GNUstep Make decide
whether the project is valid and buildable.

Aggregate projects should be classified as `project_type=aggregate` when
`SUBPROJECTS` or `aggregate.make` is present. Unknown GNUmakefile shapes should
be classified as `project_type=unknown`, but still buildable.

## Actual Behavior Before Fix

The detector treated a GNUmakefile as supported only when it directly contained
one of:

- `TOOL_NAME`
- `APP_NAME`
- `LIBRARY_NAME`

When none were present, `gnustep build` failed before invoking `make` with a
message saying the directory was not a supported GNUstep Make project.

## Root Cause

The CLI was using a small parser as a validity gate for GNUstep Make projects.
That duplicated GNUstep Make responsibility and rejected valid aggregate or
non-trivial makefile structures.

## Fix

- `GNUmakefile` is now sufficient for `gnustep build` support.
- `TOOL_NAME`, `APP_NAME`, `LIBRARY_NAME`, `SUBPROJECTS`, and `aggregate.make`
  are classification hints only.
- Aggregate GNUstep Make projects are classified as `project_type=aggregate`.
- Unknown GNUmakefile shapes are classified as `project_type=unknown`.
- `gnustep run` still requires a runnable target and fails with a run-specific
  message for aggregate or unknown projects.
- Human-facing build messages now refer to a GNUstep project unless the text is
  specifically backend-specific.

## Regression Coverage

- Shared Python build/run detector tests cover aggregate and unknown GNUmakefile
  projects.
- Native Objective-C `tools-xctest` tests cover aggregate and unknown
  GNUmakefile detection.
