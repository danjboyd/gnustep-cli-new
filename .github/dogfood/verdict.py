#!/usr/bin/env python3
"""Pass/fail for one dogfood run's output directory; writes verdict.json."""
import json, re, sys
from pathlib import Path

out = Path(sys.argv[1])
text = "".join((out / name).read_text(encoding="utf-8-sig", errors="replace") for name in ("dogfood.txt", "checks.txt") if (out / name).exists())
def code(name):
    match = re.search(rf"^{re.escape(name)} exit (\S+)", text, re.M)
    return match.group(1) if match else None
checks = {
    "setup": code("setup") == "0",
    "install": code("install") == "0",
    "include written into $(GNUSTEP_MAKEFILES)/Auxiliary": "include present:" in text,
    "make check passes": code("make-check") == "0",
    "make check with XCTEST set explicitly passes": code("make-check-explicit") == "0",
    "a failing test makes make check exit nonzero": code("make-check-failing") not in (None, "0"),
    "xctest-bundle bundle runs": code("xctest-bundle-run") == "0",
    "remove": code("remove") == "0",
    "remove leaves nothing behind": "left after remove: none" in text,
}
ok = all(checks.values())
(out / "verdict.json").write_text(json.dumps({"ok": ok, "checks": checks}, indent=2) + "\n")
for name, passed in checks.items():
    print(("PASS " if passed else "FAIL ") + name)
sys.exit(0 if ok else 1)
