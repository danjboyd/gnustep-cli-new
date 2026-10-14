"""Put a toolchain's <root>/lib on the loader path when its GNUstep.sh is sourced.

Managed and custom toolchains install libobjc2, libdispatch, and BlocksRuntime
into <root>/lib. GNUstep Make's GNUstep.sh only adds the GNUstep library
domains to LD_LIBRARY_PATH, so a binary built by hand after sourcing it fails to
load libobjc. The snippet below closes that gap. It finds <root>/lib relative to
GNUSTEP_MAKEFILES (<root>/System/Library/Makefiles in the gnustep layout), so it
needs no install-root rewriting and survives relocation.
"""
from __future__ import annotations

from pathlib import Path

MARKER = "# gnustep-cli: runtime library path"

GNUSTEP_SH_SNIPPET = f"""{MARKER}
# libobjc2, libdispatch, and BlocksRuntime live in <root>/lib, which GNUstep
# Make does not put on the loader path.
if [ -n "$GNUSTEP_MAKEFILES" ] && [ -d "$GNUSTEP_MAKEFILES/../../../lib" ]; then
  GNUSTEP_CLI_RUNTIME_LIB=`CDPATH= cd -- "$GNUSTEP_MAKEFILES/../../../lib" && pwd`
  case ":${{LD_LIBRARY_PATH:-}}:" in
    *":$GNUSTEP_CLI_RUNTIME_LIB:"*) ;;
    *) LD_LIBRARY_PATH="$GNUSTEP_CLI_RUNTIME_LIB${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"; export LD_LIBRARY_PATH ;;
  esac
  unset GNUSTEP_CLI_RUNTIME_LIB
fi
"""

# GNUstep.sh ends by restoring zsh word splitting; insert before that so the
# snippet runs with the same shell options as the rest of the script.
_ZSH_RESTORE = 'if [ -n "$GS_ZSH_NEED_TO_RESTORE_SET" ]; then'


def add_runtime_library_path(makefiles_dir: str | Path) -> bool:
    """Patch <makefiles_dir>/GNUstep.sh once; return True if it was changed."""
    script = Path(makefiles_dir) / "GNUstep.sh"
    if not script.is_file():
        return False
    text = script.read_text(encoding="utf-8")
    if MARKER in text:
        return False
    index = text.rfind(_ZSH_RESTORE)
    if index == -1:
        patched = text.rstrip("\n") + "\n\n" + GNUSTEP_SH_SNIPPET
    else:
        patched = text[:index] + GNUSTEP_SH_SNIPPET + "\n" + text[index:]
    script.write_text(patched, encoding="utf-8")
    return True
