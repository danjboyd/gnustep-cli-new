"""Put a toolchain's <root>/lib on the loader path when its GNUstep.sh or GNUstep.csh is sourced.

Managed and custom toolchains install libobjc2, libdispatch, and BlocksRuntime
into <root>/lib. GNUstep Make's GNUstep.sh and GNUstep.csh only add the GNUstep library
domains to LD_LIBRARY_PATH, so a binary built by hand after sourcing it fails to
load libobjc. The snippets below close that gap. It finds <root>/lib relative to
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


GNUSTEP_CSH_SNIPPET = f"""{MARKER}
# libobjc2, libdispatch, and BlocksRuntime live in <root>/lib, which GNUstep
# Make does not put on the loader path. Works in csh and tcsh.
if ( $?GNUSTEP_MAKEFILES ) then
  if ( -d "$GNUSTEP_MAKEFILES/../../../lib" ) then
    set gnustep_cli_runtime_lib=`cd "$GNUSTEP_MAKEFILES/../../../lib" && pwd`
    if ( ! $?LD_LIBRARY_PATH ) then
      setenv LD_LIBRARY_PATH "$gnustep_cli_runtime_lib"
    else if ( ":${{LD_LIBRARY_PATH}}:" !~ *":${{gnustep_cli_runtime_lib}}:"* ) then
      setenv LD_LIBRARY_PATH "${{gnustep_cli_runtime_lib}}:${{LD_LIBRARY_PATH}}"
    endif
    unset gnustep_cli_runtime_lib
  endif
endif
"""


def _patch_gnustep_sh(script: Path) -> bool:
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


def _patch_gnustep_csh(script: Path) -> bool:
    text = script.read_text(encoding="utf-8")
    if MARKER in text:
        return False
    # GNUstep.csh ends by unsetting its unexported helpers; GNUSTEP_MAKEFILES stays set.
    script.write_text(text.rstrip("\n") + "\n\n" + GNUSTEP_CSH_SNIPPET, encoding="utf-8")
    return True


def add_runtime_library_path(makefiles_dir: str | Path) -> bool:
    """Patch <makefiles_dir>/GNUstep.sh and GNUstep.csh once each; return True if either changed."""
    changed = False
    sh_script = Path(makefiles_dir) / "GNUstep.sh"
    csh_script = Path(makefiles_dir) / "GNUstep.csh"
    if sh_script.is_file():
        changed = _patch_gnustep_sh(sh_script) or changed
    if csh_script.is_file():
        changed = _patch_gnustep_csh(csh_script) or changed
    return changed
