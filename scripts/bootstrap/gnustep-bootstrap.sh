#!/usr/bin/env sh

set -eu

PROGRAM_NAME="${0##*/}"
CLI_VERSION="0.1.0-dev"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
INTERNAL_DOCTOR="$ROOT_DIR/scripts/internal/doctor.py"
INTERNAL_SETUP="$ROOT_DIR/scripts/internal/setup_plan.py"

print_help() {
  cat <<EOF
GNUstep CLI bootstrap interface

Usage:
  $PROGRAM_NAME [global-options] <command> [command-options]

Commands:
  setup      Install the full GNUstep CLI and its dependencies.
  doctor     Inspect this machine and report GNUstep/toolchain readiness.
  build      Unavailable in bootstrap. Install the full interface first.
  run        Unavailable in bootstrap. Install the full interface first.
  new        Unavailable in bootstrap. Install the full interface first.
  install    Unavailable in bootstrap. Install the full interface first.
  remove     Unavailable in bootstrap. Install the full interface first.

Global options:
  --help
  --version
  --json
  --verbose
  --quiet
  --yes
EOF
}

json_escape() {
  printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

emit_doctor_json() {
  has_curl=false
  has_wget=false
  if command -v curl >/dev/null 2>&1; then
    has_curl=true
  fi
  if command -v wget >/dev/null 2>&1; then
    has_wget=true
  fi
  if [ "$has_curl" = true ] || [ "$has_wget" = true ]; then
    cat <<EOF
{"schema_version":1,"command":"doctor","cli_version":"$CLI_VERSION","ok":true,"status":"warning","environment_classification":"no_toolchain","summary":"No preexisting GNUstep toolchain was detected.","environment":{"os":"unknown","arch":"unknown","bootstrap_prerequisites":{"curl":$has_curl,"wget":$has_wget}},"compatibility":{"compatible":true,"target_kind":null,"target_id":null,"reasons":[],"warnings":[{"code":"toolchain_not_present","message":"No preexisting GNUstep toolchain was detected; a managed install will be required."}]},"checks":[{"id":"bootstrap.downloader","title":"Check for downloader","status":"ok","severity":"error","message":"Found curl or wget."}],"actions":[{"kind":"install_managed_toolchain","priority":1,"message":"Install the supported managed GNUstep toolchain."}]}
EOF
    return 0
  fi
  cat <<EOF
{"schema_version":1,"command":"doctor","cli_version":"$CLI_VERSION","ok":false,"status":"error","environment_classification":"no_toolchain","summary":"A required downloader is missing.","environment":{"os":"unknown","arch":"unknown","bootstrap_prerequisites":{"curl":false,"wget":false}},"compatibility":{"compatible":false,"target_kind":null,"target_id":null,"reasons":[{"code":"bootstrap_downloader_missing","message":"Neither curl nor wget is available."}],"warnings":[]},"checks":[{"id":"bootstrap.downloader","title":"Check for downloader","status":"error","severity":"error","message":"Neither curl nor wget is available."}],"actions":[{"kind":"install_downloader","priority":1,"message":"Install curl or wget, then rerun setup."}]}
EOF
  return 3
}

emit_doctor_human() {
  if command -v curl >/dev/null 2>&1; then
    printf '%s\n' "doctor: found curl"
    printf '%s\n' "doctor: no preexisting GNUstep toolchain was detected"
    printf '%s\n' "next: Install the supported managed GNUstep toolchain."
    return 0
  fi
  if command -v wget >/dev/null 2>&1; then
    printf '%s\n' "doctor: found wget"
    printf '%s\n' "doctor: no preexisting GNUstep toolchain was detected"
    printf '%s\n' "next: Install the supported managed GNUstep toolchain."
    return 0
  fi
  printf '%s\n' "doctor: neither curl nor wget is available"
  printf '%s\n' "next: Install curl or wget, then rerun setup."
  return 3
}

handle_setup_human() {
  selected_scope=${SETUP_SCOPE:-user}
  if [ "$selected_scope" = "system" ] && [ "$(id -u)" -ne 0 ]; then
    printf '%s\n' "setup: system-wide installation requires elevated privileges"
    printf '%s\n' "next: Re-run this command with sudo."
    return 3
  fi
  if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    printf '%s\n' "setup: neither curl nor wget is available"
    printf '%s\n' "next: Install curl or wget, then rerun setup."
    return 3
  fi
  selected_root=${SETUP_ROOT:-}
  if [ -z "$selected_root" ]; then
    if [ "$selected_scope" = "system" ]; then
      selected_root="/opt/gnustep-cli"
    else
      selected_root="~/.local/share/gnustep-cli"
    fi
  fi
  printf '%s\n' "setup: managed installation plan created"
  printf '%s\n' "setup: scope=$selected_scope root=$selected_root"
  printf '%s\n' "next: Artifact download and managed installation are not implemented yet."
  return 3
}

emit_setup_json() {
  selected_scope=${SETUP_SCOPE:-user}
  selected_root=${SETUP_ROOT:-}
  if [ -z "$selected_root" ]; then
    if [ "$selected_scope" = "system" ]; then
      selected_root="/opt/gnustep-cli"
    else
      selected_root="~/.local/share/gnustep-cli"
    fi
  fi
  if [ "$selected_scope" = "system" ] && [ "$(id -u)" -ne 0 ]; then
    cat <<EOF
{"schema_version":1,"command":"setup","cli_version":"$CLI_VERSION","ok":false,"status":"error","summary":"System-wide installation requires elevated privileges.","doctor":{"status":"warning","environment_classification":"no_toolchain","summary":"No preexisting GNUstep toolchain was detected."},"plan":{"scope":"$selected_scope","install_root":"$selected_root","channel":"stable","selected_release":null,"selected_artifacts":[],"system_privileges_ok":false},"actions":[{"kind":"rerun_with_elevated_privileges","priority":1,"message":"Re-run this command with sudo."}]}
EOF
    return 3
  fi
  if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    cat <<EOF
{"schema_version":1,"command":"setup","cli_version":"$CLI_VERSION","ok":false,"status":"error","summary":"Bootstrap prerequisites are incomplete.","doctor":{"status":"error","environment_classification":"no_toolchain","summary":"A required downloader is missing."},"plan":{"scope":"$selected_scope","install_root":"$selected_root","channel":"stable","selected_release":null,"selected_artifacts":[],"system_privileges_ok":true},"actions":[{"kind":"install_downloader","priority":1,"message":"Install curl or wget, then rerun setup."}]}
EOF
    return 3
  fi
  cat <<EOF
{"schema_version":1,"command":"setup","cli_version":"$CLI_VERSION","ok":true,"status":"ok","summary":"Managed installation plan created.","doctor":{"status":"warning","environment_classification":"no_toolchain","summary":"No preexisting GNUstep toolchain was detected."},"plan":{"scope":"$selected_scope","install_root":"$selected_root","channel":"stable","selected_release":null,"selected_artifacts":[],"system_privileges_ok":true},"actions":[{"kind":"apply_install_plan","priority":1,"message":"Proceed with artifact download and managed installation once implementation is complete."}]}
EOF
  return 0
}

unsupported_command() {
  cmd="$1"
  if [ "${JSON_MODE:-0}" = "1" ]; then
    cat <<EOF
{"schema_version":1,"command":$(json_escape "$cmd"),"ok":false,"status":"error","summary":"This command is unavailable in bootstrap.","actions":[{"kind":"install_full_cli","priority":1,"message":"Install the full GNUstep CLI to use '$cmd'."}]}
EOF
  else
    printf '%s\n' "$cmd: unavailable in bootstrap"
    printf '%s\n' "Install the full GNUstep CLI to use '$cmd'."
  fi
  return 3
}

JSON_MODE=0
SETUP_SCOPE=""
SETUP_ROOT=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --help)
      print_help
      exit 0
      ;;
    --version)
      printf '%s\n' "$CLI_VERSION"
      exit 0
      ;;
    --json)
      JSON_MODE=1
      shift
      ;;
    --verbose|--quiet|--yes)
      shift
      ;;
    --system)
      SETUP_SCOPE="system"
      shift
      ;;
    --user)
      SETUP_SCOPE="user"
      shift
      ;;
    --root)
      shift
      if [ "$#" -eq 0 ]; then
        printf '%s\n' "--root requires a value" >&2
        exit 2
      fi
      SETUP_ROOT="$1"
      shift
      ;;
    --*)
      printf '%s\n' "Unknown option: $1" >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

if [ "$#" -eq 0 ]; then
  print_help
  exit 2
fi

COMMAND="$1"
shift

case "$COMMAND" in
  doctor)
    if [ "$JSON_MODE" = "1" ]; then
      emit_doctor_json
      exit $?
    fi
    emit_doctor_human
    exit $?
    ;;
  setup)
    if [ "$JSON_MODE" = "1" ]; then
      emit_setup_json
      exit $?
    fi
    handle_setup_human
    exit $?
    ;;
  build|run|new|install|remove)
    unsupported_command "$COMMAND"
    exit $?
    ;;
  *)
    printf '%s\n' "Unknown command: $COMMAND" >&2
    exit 2
    ;;
esac
