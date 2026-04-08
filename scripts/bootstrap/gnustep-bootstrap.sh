#!/usr/bin/env sh

set -eu

PROGRAM_NAME="${0##*/}"
CLI_VERSION="0.1.0-dev"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
INTERNAL_DOCTOR="$ROOT_DIR/scripts/internal/doctor.py"
INTERNAL_SETUP="$ROOT_DIR/scripts/internal/setup_plan.py"
SETUP_MANIFEST="${SETUP_MANIFEST:-}"

detect_os() {
  case "$(uname -s 2>/dev/null | tr '[:upper:]' '[:lower:]')" in
    linux*) printf '%s\n' "linux" ;;
    openbsd*) printf '%s\n' "openbsd" ;;
    *) printf '%s\n' "unknown" ;;
  esac
}

detect_arch() {
  case "$(uname -m 2>/dev/null)" in
    x86_64|amd64) printf '%s\n' "amd64" ;;
    aarch64|arm64) printf '%s\n' "aarch64" ;;
    *) printf '%s\n' "unknown" ;;
  esac
}

json_file_value() {
  path="$1"
  id="$2"
  field="$3"
  awk -v target="\"id\": \"$id\"" -v field="\"$field\"" '
    $0 ~ target {inblock=1}
    inblock && index($0, field) {
      line=$0
      sub(/^.*: "/, "", line)
      sub(/",?$/, "", line)
      print line
      exit
    }
    inblock && /^[[:space:]]*}[,]?[[:space:]]*$/ {inblock=0}
  ' "$path"
}

json_release_version() {
  path="$1"
  awk '
    /"version": "/ {
      line=$0
      sub(/^.*"version": "/, "", line)
      sub(/".*$/, "", line)
      print line
      exit
    }
  ' "$path"
}

sha256_file() {
  path="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$path" | awk '{print $1}'
    return 0
  fi
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$path" | awk '{print $1}'
    return 0
  fi
  if command -v openssl >/dev/null 2>&1; then
    openssl dgst -sha256 "$path" | awk '{print $2}'
    return 0
  fi
  return 1
}

download_to() {
  url="$1"
  destination="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$destination"
    return $?
  fi
  wget -qO "$destination" "$url"
}

extract_tarball() {
  archive="$1"
  destination="$2"
  mkdir -p "$destination"
  tar -xzf "$archive" -C "$destination"
}

first_child_dir() {
  parent="$1"
  find "$parent" -mindepth 1 -maxdepth 1 -type d | head -n 1
}

copy_tree_contents() {
  source_dir="$1"
  dest_dir="$2"
  mkdir -p "$dest_dir"
  (cd "$source_dir" && tar -cf - .) | (cd "$dest_dir" && tar -xf -)
}

install_cli_bundle() {
  source_dir="$1"
  dest_dir="$2"
  copy_tree_contents "$source_dir" "$dest_dir"
  if [ ! -x "$dest_dir/bin/gnustep" ]; then
    printf '%s\n' "setup: CLI bundle did not install a runnable gnustep binary" >&2
    return 1
  fi
  chmod 755 "$dest_dir/bin/gnustep"
  return 0
}

path_hint() {
  root="$1"
  printf 'export PATH="%s/bin:%s/System/Tools:$PATH"\n' "$root" "$root"
}

perform_setup() {
  selected_scope=${SETUP_SCOPE:-user}
  host_os=$(detect_os)
  host_arch=$(detect_arch)
  manifest_source=${SETUP_MANIFEST:-}
  selected_root=${SETUP_ROOT:-}

  if [ "$selected_scope" = "system" ] && [ "$(id -u)" -ne 0 ]; then
    if [ "${JSON_MODE:-0}" = "1" ]; then
      cat <<EOF
{"schema_version":1,"command":"setup","cli_version":"$CLI_VERSION","ok":false,"status":"error","summary":"System-wide installation requires elevated privileges.","doctor":{"status":"warning","environment_classification":"no_toolchain","summary":"No preexisting GNUstep toolchain was detected.","os":"$host_os"},"plan":{"scope":"$selected_scope","install_root":"/opt/gnustep-cli","channel":"stable","selected_release":null,"selected_artifacts":[],"system_privileges_ok":false},"actions":[{"kind":"rerun_with_elevated_privileges","priority":1,"message":"Re-run this command with sudo."}]}
EOF
    else
      printf '%s\n' "setup: system-wide installation requires elevated privileges"
      printf '%s\n' "next: Re-run this command with sudo."
    fi
    return 3
  fi

  if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    if [ "${JSON_MODE:-0}" = "1" ]; then
      cat <<EOF
{"schema_version":1,"command":"setup","cli_version":"$CLI_VERSION","ok":false,"status":"error","summary":"Bootstrap prerequisites are incomplete.","doctor":{"status":"error","environment_classification":"no_toolchain","summary":"A required downloader is missing.","os":"$host_os"},"plan":{"scope":"$selected_scope","install_root":"${selected_root:-~/.local/share/gnustep-cli}","channel":"stable","selected_release":null,"selected_artifacts":[],"system_privileges_ok":true},"actions":[{"kind":"install_downloader","priority":1,"message":"Install curl or wget, then rerun setup."}]}
EOF
    else
      printf '%s\n' "setup: neither curl nor wget is available"
      printf '%s\n' "next: Install curl or wget, then rerun setup."
    fi
    return 3
  fi

  if [ -z "$selected_root" ]; then
    if [ "$selected_scope" = "system" ]; then
      selected_root="/opt/gnustep-cli"
    else
      selected_root="$HOME/.local/share/gnustep-cli"
    fi
  fi

  temp_dir=$(mktemp -d "${TMPDIR:-/tmp}/gnustep-bootstrap-XXXXXX")
  cleanup() {
    rm -rf "$temp_dir"
  }
  trap cleanup EXIT INT TERM

  if [ -z "$manifest_source" ]; then
    if [ -f "$ROOT_DIR/dist/stable/${CLI_VERSION}/release-manifest.json" ]; then
      manifest_source="$ROOT_DIR/dist/stable/${CLI_VERSION}/release-manifest.json"
    else
      manifest_source="https://github.com/danjboyd/gnustep-cli-new/releases/download/v${CLI_VERSION}/release-manifest.json"
    fi
  fi
  case "$manifest_source" in
    http://*|https://*)
      manifest_path="$temp_dir/release-manifest.json"
      if ! download_to "$manifest_source" "$manifest_path"; then
        if [ "${JSON_MODE:-0}" = "1" ]; then
          cat <<EOF
{"schema_version":1,"command":"setup","cli_version":"$CLI_VERSION","ok":false,"status":"error","summary":"Failed to download the release manifest.","doctor":{"status":"warning","environment_classification":"no_toolchain","summary":"No preexisting GNUstep toolchain was detected.","os":"$host_os"},"plan":{"scope":"$selected_scope","install_root":"$selected_root","channel":"stable","selected_release":null,"selected_artifacts":[],"system_privileges_ok":true},"actions":[{"kind":"report_bug","priority":1,"message":"Check the manifest URL and network access, then rerun setup."}]}
EOF
        else
          printf '%s\n' "setup: failed to download the release manifest"
          printf '%s\n' "next: Check the manifest URL and network access, then rerun setup."
        fi
        return 1
      fi
      manifest_dir="$temp_dir"
      ;;
    *)
      manifest_path="$manifest_source"
      manifest_dir=$(CDPATH= cd -- "$(dirname "$manifest_path")" && pwd)
      ;;
  esac

  release_version=$(json_release_version "$manifest_path")
  target_id="cli-$host_os-$host_arch-clang"
  toolchain_id="toolchain-$host_os-$host_arch-clang"
  cli_url=$(json_file_value "$manifest_path" "$target_id" "url")
  cli_sha=$(json_file_value "$manifest_path" "$target_id" "sha256")
  toolchain_url=$(json_file_value "$manifest_path" "$toolchain_id" "url")
  toolchain_sha=$(json_file_value "$manifest_path" "$toolchain_id" "sha256")

  if [ -z "$cli_url" ] || [ -z "$toolchain_url" ]; then
    if [ "${JSON_MODE:-0}" = "1" ]; then
      cat <<EOF
{"schema_version":1,"command":"setup","cli_version":"$CLI_VERSION","ok":false,"status":"error","summary":"No matching release artifacts were found for this host.","doctor":{"status":"warning","environment_classification":"no_toolchain","summary":"No preexisting GNUstep toolchain was detected.","os":"$host_os"},"plan":{"scope":"$selected_scope","install_root":"$selected_root","channel":"stable","selected_release":"${release_version:-unknown}","selected_artifacts":[],"system_privileges_ok":true},"actions":[{"kind":"report_bug","priority":1,"message":"No supported managed artifact matches this host yet."}]}
EOF
    else
      printf '%s\n' "setup: no matching release artifacts were found for this host"
    fi
    return 4
  fi

  cli_file="$temp_dir/$(basename "$cli_url")"
  toolchain_file="$temp_dir/$(basename "$toolchain_url")"
  if [ -f "$manifest_dir/$(basename "$cli_url")" ]; then
    cp "$manifest_dir/$(basename "$cli_url")" "$cli_file"
  elif ! download_to "$cli_url" "$cli_file"; then
    printf '%s\n' "setup: failed to download CLI artifact" >&2
    return 1
  fi
  if [ -f "$manifest_dir/$(basename "$toolchain_url")" ]; then
    cp "$manifest_dir/$(basename "$toolchain_url")" "$toolchain_file"
  elif ! download_to "$toolchain_url" "$toolchain_file"; then
    printf '%s\n' "setup: failed to download toolchain artifact" >&2
    return 1
  fi

  if [ "$(sha256_file "$cli_file")" != "$cli_sha" ] || [ "$(sha256_file "$toolchain_file")" != "$toolchain_sha" ]; then
    printf '%s\n' "setup: artifact checksum verification failed" >&2
    return 1
  fi

  cli_extract="$temp_dir/cli"
  toolchain_extract="$temp_dir/toolchain"
  extract_tarball "$cli_file" "$cli_extract"
  extract_tarball "$toolchain_file" "$toolchain_extract"
  cli_root=$(first_child_dir "$cli_extract")
  toolchain_root=$(first_child_dir "$toolchain_extract")

  if ! install_cli_bundle "$cli_root" "$selected_root"; then
    return 1
  fi
  copy_tree_contents "$toolchain_root" "$selected_root"
  mkdir -p "$selected_root/state"
  cat >"$selected_root/state/cli-state.json" <<EOF
{
  "schema_version": 1,
  "cli_version": "$release_version",
  "toolchain_version": "$release_version",
  "packages_version": 1,
  "last_action": "setup",
  "status": "healthy"
}
EOF
  path_command=$(path_hint "$selected_root")
  path_command_json=$(json_escape "$path_command")

  if [ "${JSON_MODE:-0}" = "1" ]; then
    cat <<EOF
{"schema_version":1,"command":"setup","cli_version":"$CLI_VERSION","ok":true,"status":"ok","summary":"Managed installation completed.","doctor":{"status":"warning","environment_classification":"no_toolchain","summary":"No preexisting GNUstep toolchain was detected.","os":"$host_os"},"plan":{"scope":"$selected_scope","install_root":"$selected_root","channel":"stable","selected_release":"$release_version","selected_artifacts":["$target_id","$toolchain_id"],"system_privileges_ok":true},"actions":[{"kind":"add_path","priority":1,"message":"Add $selected_root/bin and $selected_root/System/Tools to PATH for future shells."},{"kind":"delete_bootstrap","priority":2,"message":"The bootstrap script is no longer required and may be deleted."}],"install":{"install_root":"$selected_root","path_hint":$path_command_json}}
EOF
  else
    printf '%s\n' "setup: managed installation completed"
    printf '%s\n' "setup: scope=$selected_scope root=$selected_root"
    printf '%s\n' "next: Run this in the current shell:"
    printf '%s\n' "  $path_command"
    printf '%s\n' "next: New shells should include $selected_root/bin and $selected_root/System/Tools on PATH."
    printf '%s\n' "next: The bootstrap script is no longer required and may be deleted."
  fi
  return 0
}

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
    --manifest)
      shift
      if [ "$#" -eq 0 ]; then
        printf '%s\n' "--manifest requires a value" >&2
        exit 2
      fi
      SETUP_MANIFEST="$1"
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

while [ "$#" -gt 0 ]; do
  case "$1" in
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
    --manifest)
      shift
      if [ "$#" -eq 0 ]; then
        printf '%s\n' "--manifest requires a value" >&2
        exit 2
      fi
      SETUP_MANIFEST="$1"
      shift
      ;;
    --verbose|--quiet|--yes)
      shift
      ;;
    *)
      break
      ;;
  esac
done

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
    perform_setup
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
