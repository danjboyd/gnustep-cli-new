#!/bin/sh
# Qualify a distro-scoped managed Linux target inside a clean container of that
# distro release. Run as root in the container with the repository at $REPO.
#
# Usage: linux-container-qualification.sh <target-id> <artifacts-dir> <version> <icu-major> <output-dir>
#
# Steps: install minimal tools, check bundled SONAMEs, write a local release
# manifest for the target from build_infra's TIER1 metadata, then as an
# unprivileged user with sudo run the bootstrap (--yes installs host
# prerequisites), --version, --help, doctor --json, new/build/run, and a
# Foundation/blocks/ARC/libdispatch compile-link-run probe. Results go to
# <output-dir>/container-qualification.json.
set -eu

TARGET=$1
ARTIFACTS=$(CDPATH= cd -- "$2" && pwd)
VERSION=$3
ICU_MAJOR=$4
OUT=$5
REPO=${REPO:-/src}
USER_NAME=gsqualify

mkdir -p "$OUT"
OUT=$(CDPATH= cd -- "$OUT" && pwd)
export DEBIAN_FRONTEND=noninteractive
apt-get update >/dev/null
apt-get install -y --no-install-recommends sudo ca-certificates curl python3 binutils >/dev/null

toolchain="$ARTIFACTS/gnustep-toolchain-$TARGET-$VERSION.tar.gz"
cli="$ARTIFACTS/gnustep-cli-$TARGET-$VERSION.tar.gz"
test -f "$toolchain"
test -f "$cli"

set +e
ICU_MAJOR="$ICU_MAJOR" sh "$REPO/scripts/dev/check-bundled-sonames.sh" "$toolchain" "$cli" > "$OUT/soname-check.txt" 2>&1
soname_rc=$?
set -e
cat "$OUT/soname-check.txt"

PYTHONPATH="$REPO/src" python3 - "$TARGET" "$VERSION" "$toolchain" "$cli" "$OUT/release-manifest.json" <<'PY'
import hashlib, json, sys
from gnustep_cli_shared.build_infra import release_manifest_from_matrix
target, version, toolchain, cli, output = sys.argv[1:]
manifest = release_manifest_from_matrix(version, "file:///unused")
paths = {f"cli-{target}": cli, f"toolchain-{target}": toolchain}
release = manifest["releases"][0]
release["artifacts"] = [a for a in release["artifacts"] if a["id"] in paths]
if len(release["artifacts"]) != 2:
    raise SystemExit(f"target {target} is not defined in build_infra TIER1_TARGETS")
for artifact in release["artifacts"]:
    path = paths[artifact["id"]]
    digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
    artifact["url"] = "file://" + path
    artifact["sha256"] = digest
    artifact["integrity"] = {"sha256": digest}
    # Qualification evaluates the artifact as it would be published.
    artifact["published"] = True
json.dump(manifest, open(output, "w"), indent=2)
PY

id "$USER_NAME" >/dev/null 2>&1 || useradd -m -s /bin/sh "$USER_NAME"
printf '%s ALL=(ALL) NOPASSWD:ALL\n' "$USER_NAME" > /etc/sudoers.d/gsqualify
chmod 0440 /etc/sudoers.d/gsqualify
chmod a+rx "$OUT" "$ARTIFACTS"
chmod a+r "$OUT"/* "$ARTIFACTS"/*
work=$(su - "$USER_NAME" -c 'mktemp -d')

cat > "$work/probe.m" <<'OBJC'
#import <Foundation/Foundation.h>
#include <dispatch/dispatch.h>
int main(void) {
  @autoreleasepool {
    NSArray *a = @[@1, @2, @39];
    __block NSInteger sum = 0;
    [a enumerateObjectsUsingBlock:^(NSNumber *n, NSUInteger i, BOOL *stop) { sum += [n integerValue]; }];
    dispatch_queue_t q = dispatch_queue_create("probe", DISPATCH_QUEUE_SERIAL);
    dispatch_sync(q, ^{ sum += 0; });
    printf("%s\n", [[[NSString stringWithFormat:@"sum=%ld", (long)sum] uppercaseString] UTF8String]);
  }
  return 0;
}
OBJC

cat > "$work/probe.sh" <<'PROBE'
set -eu
# GNUstep.sh references unset shell variables (for example ZSH_VERSION).
set +u
. "$R/System/Library/Makefiles/GNUstep.sh"
set -u
clang -fobjc-arc -fblocks $(gnustep-config --objc-flags) probe.m -o probe $(gnustep-config --base-libs) -L"$R/lib" -ldispatch
LD_LIBRARY_PATH="$R/lib:${LD_LIBRARY_PATH:-}" ./probe
LD_LIBRARY_PATH="$R/lib:${LD_LIBRARY_PATH:-}" ldd ./probe
PROBE
cat > "$work/steps.sh" <<'STEPS'
set -u
cd "$WORK"
R="$HOME/.local/share/gnustep-cli"
export R
step() { name=$1; shift; "$@" > "$OUT/$name.out" 2> "$OUT/$name.err"; printf '%s %s\n' "$name" "$?" >> "$OUT/steps.txt"; }
: > "$OUT/steps.txt"
step setup env GNUSTEP_BOOTSTRAP_ALLOW_UNSIGNED=1 sh "$REPO/scripts/bootstrap/gnustep-bootstrap.sh" --yes --json setup --user --manifest "$OUT/release-manifest.json"
export PATH="$R/bin:$PATH"
step version gnustep --version
step help gnustep --help
step doctor gnustep doctor --json --manifest "$OUT/release-manifest.json"
step doctor_default gnustep doctor --json
step new gnustep new --json cli-tool "$WORK/proj" --name HelloTool
cd "$WORK/proj"
step build gnustep build --json
step run gnustep run --json
cd "$WORK"
step probe sh "$WORK/probe.sh"
STEPS
chown -R "$USER_NAME" "$work"
chmod a+rwx "$OUT"
su - "$USER_NAME" -c "OUT='$OUT' REPO='$REPO' WORK='$work' sh '$work/steps.sh'"

PYTHONPATH="$REPO/src" python3 - "$OUT" "$TARGET" "$VERSION" "$ICU_MAJOR" "$soname_rc" "$toolchain" "$cli" <<'PY'
import hashlib, json, os, platform, subprocess, sys
out, target, version, icu_major, soname_rc, toolchain, cli = sys.argv[1:]
def read(name):
    try:
        return open(os.path.join(out, name)).read()
    except OSError:
        return ""
def last_json(text):
    for line in reversed(text.strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return {}
steps = dict(line.split() for line in read("steps.txt").splitlines() if line.strip())
os_release = dict(line.split("=", 1) for line in open("/etc/os-release").read().splitlines() if "=" in line)
setup, doctor, run = last_json(read("setup.out")), last_json(read("doctor.out")), last_json(read("run.out"))
probe = read("probe.out")
results = {
    "soname_check": "passed" if soname_rc == "0" else "failed",
    "bootstrap_setup": "passed" if steps.get("setup") == "0" and setup.get("ok") else "failed",
    "cli_version": "passed" if steps.get("version") == "0" else "failed",
    "cli_help": "passed" if steps.get("help") == "0" else "failed",
    "doctor": "passed" if steps.get("doctor") == "0" and doctor.get("status") in ("ok", "warning") else "failed",
    "new_build_run": "passed" if all(steps.get(s) == "0" for s in ("new", "build", "run")) and "Hello from CLI tool" in run.get("stdout", "") else "failed",
    "foundation_probe": "passed" if steps.get("probe") == "0" and "SUM=42" in probe else "failed",
}
probe_icu = [line.strip() for line in probe.splitlines() if "libicu" in line or "libc.so.6" in line]
report = {
    "schema_version": 1,
    "kind": "linux-container-qualification",
    "target_id": target,
    "version": version,
    "ok": all(value == "passed" for value in results.values()),
    "host": {
        "distribution": os_release.get("PRETTY_NAME", "").strip('"'),
        "os_version": f'{os_release.get("ID", "")}-{os_release.get("VERSION_ID", "").strip(chr(34))}',
        "kernel": platform.release(),
        "glibc": platform.libc_ver()[1],
        "expected_icu_major": int(icu_major),
        "container": True,
    },
    "artifacts": {
        os.path.basename(path): hashlib.sha256(open(path, "rb").read()).hexdigest() for path in (toolchain, cli)
    },
    "results": results,
    "step_exit_codes": steps,
    "evidence": {
        "soname_check": read("soname-check.txt").splitlines(),
        "cli_version_stdout": read("version.out").strip(),
        "setup_selected_artifacts": setup.get("plan", {}).get("selected_artifacts"),
        "doctor_status": doctor.get("status"),
        "doctor_environment_classification": doctor.get("environment_classification"),
        "doctor_default_manifest_status": last_json(read("doctor_default.out")).get("status"),
        "doctor_default_manifest_classification": last_json(read("doctor_default.out")).get("environment_classification"),
        "run_stdout": run.get("stdout", "").strip(),
        "probe_runtime_resolution": probe_icu,
    },
}
json.dump(report, open(os.path.join(out, "container-qualification.json"), "w"), indent=2)
print(json.dumps(report["results"], indent=2))
raise SystemExit(0 if report["ok"] else 1)
PY
