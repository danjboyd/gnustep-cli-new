#!/usr/bin/env sh

set -eu

PROGRAM_NAME="${0##*/}"
CLI_VERSION="0.1.0-dev"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
SETUP_MANIFEST="${SETUP_MANIFEST:-}"
DOGFOOD_MANIFEST_URL="${DOGFOOD_MANIFEST_URL:-https://github.com/danjboyd/gnustep-cli-new/releases/download/dogfood/release-manifest.json}"
DOGFOOD_MODE=0

YES_MODE=0
HOST_PREREQUISITE_SOURCE="https://github.com/gnustep/tools-scripts"
HOST_PREREQUISITE_SOURCE_NOTE="Derived from GNUstep tools-scripts install-dependencies-* and normalized for this bootstrap."


detect_linux_distribution() {
  if [ -r /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    case "${ID:-}" in
      debian|ubuntu|fedora|arch) printf '%s\n' "$ID"; return 0 ;;
    esac
    case " ${ID_LIKE:-} " in
      *" debian "*) printf '%s\n' "debian"; return 0 ;;
      *" ubuntu "*) printf '%s\n' "ubuntu"; return 0 ;;
      *" fedora "*) printf '%s\n' "fedora"; return 0 ;;
      *" arch "*) printf '%s\n' "arch"; return 0 ;;
    esac
  fi
  printf '%s\n' "unknown"
}

detect_linux_os_version() {
  if [ -r /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    if [ -n "${VERSION_ID:-}" ]; then
      printf '%s\n' "${ID:-linux}-$VERSION_ID"
      return 0
    fi
    if [ -n "${VERSION_CODENAME:-}" ]; then
      printf '%s\n' "${ID:-linux}-$VERSION_CODENAME"
      return 0
    fi
    printf '%s\n' "${ID:-linux}"
    return 0
  fi
  printf '%s\n' "unknown"
}

host_platform_id() {
  os=$(detect_os)
  if [ "$os" = "linux" ]; then
    detect_linux_distribution
    return 0
  fi
  printf '%s\n' "$os"
}

managed_target_suffix() {
  os=$1
  arch=$2
  platform=$3
  os_version=${4:-}
  if [ "$os" = "linux" ] && [ "$platform" = "ubuntu" ] && [ "$arch" = "amd64" ]; then
    if [ "$os_version" = "ubuntu-24.04" ]; then
      printf '%s\n' "linux-ubuntu2404-amd64-clang"
    else
      printf '%s\n' "linux-ubuntu-unsupported-$arch-clang"
    fi
    return 0
  fi
  printf '%s\n' "$os-$arch-clang"
}

host_prerequisite_packages() {
  platform="$1"
  case "$platform" in
    debian|ubuntu)
      printf '%s\n' "ca-certificates curl tar gzip xz-utils zstd git make cmake ninja-build pkg-config clang lld libxml2-dev libxslt1-dev libicu-dev libavahi-client-dev libcurl4-gnutls-dev libgnutls28-dev libffi-dev libjpeg-dev libtiff-dev libpng-dev libcairo2-dev libxft-dev libxt-dev libx11-dev libxext-dev"
      ;;
    fedora)
      printf '%s\n' "ca-certificates curl tar gzip xz zstd git make cmake ninja-build pkgconf-pkg-config clang lld libxml2-devel libxslt-devel libicu-devel avahi-devel libcurl-devel gnutls-devel libffi-devel libjpeg-turbo-devel libtiff-devel libpng-devel cairo-devel libXft-devel libXt-devel libX11-devel libXext-devel"
      ;;
    arch)
      printf '%s\n' "ca-certificates curl tar gzip xz zstd git make cmake ninja pkgconf clang lld libxml2 libxslt icu avahi gnutls libffi libjpeg-turbo libtiff libpng cairo libxft libxt libx11 libxext"
      ;;
    openbsd)
      printf '%s\n' "curl gmake cmake ninja pkgconf clang libxml libxslt icu4c avahi gnutls libffi jpeg tiff png cairo libXft gnustep-make gnustep-base gnustep-libobjc2"
      ;;
    *)
      printf '%s\n' ""
      ;;
  esac
}

host_prerequisite_install_command() {
  platform="$1"
  packages=$(host_prerequisite_packages "$platform")
  if [ -z "$packages" ]; then
    return 1
  fi
  case "$platform" in
    debian|ubuntu)
      printf '%s\n' "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y $packages"
      ;;
    fedora)
      printf '%s\n' "dnf install -y $packages"
      ;;
    arch)
      printf '%s\n' "pacman -Sy --needed --noconfirm $packages"
      ;;
    openbsd)
      printf '%s\n' "pkg_add $packages"
      ;;
    *)
      return 1
      ;;
  esac
}

can_install_host_prerequisites() {
  platform="$1"
  case "$platform" in
    debian|ubuntu) command -v apt-get >/dev/null 2>&1 ;;
    fedora) command -v dnf >/dev/null 2>&1 ;;
    arch) command -v pacman >/dev/null 2>&1 ;;
    openbsd) command -v pkg_add >/dev/null 2>&1 ;;
    *) return 1 ;;
  esac
}

run_as_root_command() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
    return $?
  fi
  if command -v sudo >/dev/null 2>&1; then
    sudo "$@"
    return $?
  fi
  return 127
}

install_host_prerequisites() {
  platform="$1"
  packages=$(host_prerequisite_packages "$platform")
  if [ -z "$packages" ]; then
    return 0
  fi
  if ! can_install_host_prerequisites "$platform"; then
    printf '%s\n' "setup: package manager for host prerequisites is not available for $platform" >&2
    return 0
  fi
  if [ "$YES_MODE" != "1" ]; then
    command_text=$(host_prerequisite_install_command "$platform" || true)
    if [ -n "$command_text" ]; then
      printf '%s\n' "setup: host prerequisites are derived from $HOST_PREREQUISITE_SOURCE" >&2
      printf '%s\n' "setup: to install GNUstep host prerequisites, run: $command_text" >&2
      printf '%s\n' "setup: rerun bootstrap with --yes to let setup install these prerequisites automatically" >&2
    fi
    return 0
  fi
  printf '%s\n' "setup: installing GNUstep host prerequisites for $platform" >&2
  case "$platform" in
    debian|ubuntu)
      run_as_root_command apt-get update >&2
      # shellcheck disable=SC2086
      run_as_root_command env DEBIAN_FRONTEND=noninteractive apt-get install -y $packages >&2
      ;;
    fedora)
      # shellcheck disable=SC2086
      run_as_root_command dnf install -y $packages >&2
      ;;
    arch)
      # shellcheck disable=SC2086
      run_as_root_command pacman -Sy --needed --noconfirm $packages >&2
      ;;
    openbsd)
      # shellcheck disable=SC2086
      run_as_root_command pkg_add $packages >&2
      ;;
  esac
}

json_string_array_from_words() {
  words="$1"
  printf '['
  first=1
  for word in $words; do
    if [ "$first" = "1" ]; then
      first=0
    else
      printf ','
    fi
    json_escape "$word"
  done
  printf ']'
}

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
    index($0, "\"id\":") && $0 !~ target && inblock {exit}
    $0 ~ target {inblock=1}
    inblock && index($0, field) {
      line=$0
      sub(/^.*: "/, "", line)
      sub(/",?$/, "", line)
      print line
      exit
    }
  ' "$path"
}

json_file_bool() {
  path="$1"
  id="$2"
  field="$3"
  awk -v target="\"id\": \"$id\"" -v field="\"$field\"" '
    index($0, "\"id\":") && $0 !~ target && inblock {exit}
    $0 ~ target {inblock=1}
    inblock && index($0, field) {
      line=$0
      sub(/^.*: /, "", line)
      sub(/,?$/, "", line)
      gsub(/[[:space:]]/, "", line)
      print line
      exit
    }
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

sed_replacement_escape() {
  printf '%s' "$1" | sed 's/[\&|]/\\&/g'
}

relocate_managed_toolchain() {
  root="$1"
  placeholder="__GNUSTEP_CLI_INSTALL_ROOT__"
  escaped_root=$(sed_replacement_escape "$root")
  find "$root" -type f 2>/dev/null | while IFS= read -r file; do
    if LC_ALL=C grep -Iq "$placeholder" "$file" 2>/dev/null; then
      temp_file="$file.relocating.$$"
      sed "s|$placeholder|$escaped_root|g" "$file" >"$temp_file"
      cat "$temp_file" >"$file"
      rm -f "$temp_file"
    fi
  done
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
  printf 'export PATH="%s/bin:%s/Tools:%s/System/Tools:$PATH"\n' "$root" "$root" "$root"
}

install_root_writable() {
  root="$1"
  candidate="$root"
  while [ ! -e "$candidate" ]; do
    parent=$(dirname "$candidate")
    if [ "$parent" = "$candidate" ]; then
      break
    fi
    candidate="$parent"
  done
  [ -w "$candidate" ]
}

perform_setup() {
  selected_scope=${SETUP_SCOPE:-user}
  host_os=$(detect_os)
  host_arch=$(detect_arch)
  host_platform=$(host_platform_id)
  host_os_version=""
  if [ "$host_os" = "linux" ]; then
    host_os_version=$(detect_linux_os_version)
  fi
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

  if [ "$YES_MODE" = "1" ]; then
    if ! install_host_prerequisites "$host_platform"; then
      if [ "${JSON_MODE:-0}" = "1" ]; then
        cat <<EOF
{"schema_version":1,"command":"setup","cli_version":"$CLI_VERSION","ok":false,"status":"error","summary":"Failed to install host prerequisites.","doctor":{"status":"error","environment_classification":"no_toolchain","summary":"Host prerequisite installation failed.","os":"$host_os"},"plan":{"scope":"$selected_scope","install_root":"${selected_root:-~/.local/share/gnustep-cli}","channel":"stable","selected_release":null,"selected_artifacts":[],"system_privileges_ok":true},"actions":[{"kind":"install_host_prerequisites","priority":1,"message":"Install the GNUstep host prerequisites manually, then rerun setup."}]}
EOF
      else
        printf '%s\n' "setup: failed to install host prerequisites"
        printf '%s\n' "next: Install the GNUstep host prerequisites manually, then rerun setup."
      fi
      return 3
    fi
  fi

  if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    if [ "${JSON_MODE:-0}" = "1" ]; then
      cat <<EOF
{"schema_version":1,"command":"setup","cli_version":"$CLI_VERSION","ok":false,"status":"error","summary":"Bootstrap prerequisites are incomplete.","doctor":{"status":"error","environment_classification":"no_toolchain","summary":"A required downloader is missing.","os":"$host_os"},"plan":{"scope":"$selected_scope","install_root":"${selected_root:-~/.local/share/gnustep-cli}","channel":"stable","selected_release":null,"selected_artifacts":[],"system_privileges_ok":true,"host_prerequisites":{"source":"$HOST_PREREQUISITE_SOURCE","platform":"$host_platform","install_command":$(json_escape "$(host_prerequisite_install_command "$host_platform" || true)")}},"actions":[{"kind":"install_downloader","priority":1,"message":"Install curl or wget, or rerun setup with --yes to let bootstrap install host prerequisites."}]}
EOF
    else
      printf '%s\n' "setup: neither curl nor wget is available"
      printf '%s\n' "next: Install curl or wget, then rerun setup."
    fi
    return 3
  fi

  if [ "$YES_MODE" != "1" ]; then
    install_host_prerequisites "$host_platform"
  fi

  if [ -z "$selected_root" ]; then
    if [ "$selected_scope" = "system" ]; then
      selected_root="/opt/gnustep-cli"
    else
      selected_root="$HOME/.local/share/gnustep-cli"
    fi
  fi

  if ! install_root_writable "$selected_root"; then
    if [ "${JSON_MODE:-0}" = "1" ]; then
      cat <<EOF
{"schema_version":1,"command":"setup","cli_version":"$CLI_VERSION","ok":false,"status":"error","summary":"The selected install root is not writable.","doctor":{"status":"warning","environment_classification":"no_toolchain","summary":"No preexisting GNUstep toolchain was detected.","os":"$host_os"},"plan":{"scope":"$selected_scope","install_root":"$selected_root","channel":"stable","selected_release":null,"selected_artifacts":[],"system_privileges_ok":true},"actions":[{"kind":"rerun_with_elevated_privileges","priority":1,"message":"Choose a writable install root or rerun with sufficient privileges."}]}
EOF
    else
      printf '%s\n' "setup: the selected install root is not writable"
      printf '%s\n' "next: Choose a writable install root or rerun with sufficient privileges."
    fi
    return 3
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
  target_suffix=$(managed_target_suffix "$host_os" "$host_arch" "$host_platform" "$host_os_version")
  target_id="cli-$target_suffix"
  toolchain_id="toolchain-$target_suffix"
  cli_published=$(json_file_bool "$manifest_path" "$target_id" "published")
  toolchain_published=$(json_file_bool "$manifest_path" "$toolchain_id" "published")
  cli_url=$(json_file_value "$manifest_path" "$target_id" "url")
  cli_sha=$(json_file_value "$manifest_path" "$target_id" "sha256")
  toolchain_url=$(json_file_value "$manifest_path" "$toolchain_id" "url")
  toolchain_sha=$(json_file_value "$manifest_path" "$toolchain_id" "sha256")

  if [ "$cli_published" != "true" ] || [ "$toolchain_published" != "true" ]; then
    cli_url=""
    toolchain_url=""
  fi

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
  relocate_managed_toolchain "$selected_root"
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
  manifest_source_json=$(json_escape "$manifest_source")
  host_packages=$(host_prerequisite_packages "$host_platform")
  host_packages_json=$(json_string_array_from_words "$host_packages")
  host_install_command=$(host_prerequisite_install_command "$host_platform" || true)
  host_install_command_json=$(json_escape "$host_install_command")

  if [ "${JSON_MODE:-0}" = "1" ]; then
    cat <<EOF
{"schema_version":1,"command":"setup","cli_version":"$CLI_VERSION","ok":true,"status":"ok","summary":"Managed installation completed.","doctor":{"status":"warning","environment_classification":"no_toolchain","summary":"No preexisting GNUstep toolchain was detected.","os":"$host_os"},"plan":{"scope":"$selected_scope","install_root":"$selected_root","channel":"stable","manifest_path":$manifest_source_json,"selected_release":"$release_version","selected_artifacts":["$target_id","$toolchain_id"],"system_privileges_ok":true,"host_prerequisites":{"source":"$HOST_PREREQUISITE_SOURCE","source_note":"$HOST_PREREQUISITE_SOURCE_NOTE","platform":"$host_platform","packages":$host_packages_json,"install_command":$host_install_command_json,"auto_install_requested":$([ "$YES_MODE" = "1" ] && printf true || printf false)}},"actions":[{"kind":"add_path","priority":1,"message":"Add $selected_root/bin, $selected_root/Tools, and $selected_root/System/Tools to PATH for future shells."},{"kind":"delete_bootstrap","priority":2,"message":"The bootstrap script is no longer required and may be deleted."}],"install":{"install_root":"$selected_root","path_hint":$path_command_json}}
EOF
  else
    printf '%s\n' "setup: managed installation completed"
    printf '%s\n' "setup: scope=$selected_scope root=$selected_root"
    printf '%s\n' "next: Run this in the current shell:"
    printf '%s\n' "  $path_command"
    printf '%s\n' "next: New shells should include $selected_root/bin, $selected_root/Tools, and $selected_root/System/Tools on PATH."
    printf '%s\n' "note: Host prerequisite guidance is derived from $HOST_PREREQUISITE_SOURCE."
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
  clean      Unavailable in bootstrap. Install the full interface first.
  run        Unavailable in bootstrap. Install the full interface first.
  shell      Unavailable in bootstrap. Install the full interface first.
  new        Unavailable in bootstrap. Install the full interface first.
  install    Unavailable in bootstrap. Install the full interface first.
  remove     Unavailable in bootstrap. Install the full interface first.
  update     Unavailable in bootstrap. Install the full interface first.

Global options:
  --help
  --version
  --json
  --verbose
  --quiet
  --yes
  --dogfood
EOF
}

json_escape() {
  printf '"'
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
  printf '"'
}

emit_doctor_json() {
  host_platform=$(host_platform_id)
  host_packages=$(host_prerequisite_packages "$host_platform")
  host_packages_json=$(json_string_array_from_words "$host_packages")
  host_install_command=$(host_prerequisite_install_command "$host_platform" || true)
  host_install_command_json=$(json_escape "$host_install_command")
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
{"schema_version":1,"command":"doctor","cli_version":"$CLI_VERSION","ok":true,"status":"warning","environment_classification":"no_toolchain","summary":"No preexisting GNUstep toolchain was detected.","environment":{"os":"$(detect_os)","arch":"$(detect_arch)","platform":"$host_platform","bootstrap_prerequisites":{"curl":$has_curl,"wget":$has_wget},"host_prerequisites":{"source":"$HOST_PREREQUISITE_SOURCE","source_note":"$HOST_PREREQUISITE_SOURCE_NOTE","packages":$host_packages_json,"install_command":$host_install_command_json}},"compatibility":{"compatible":true,"target_kind":null,"target_id":null,"reasons":[],"warnings":[{"code":"toolchain_not_present","message":"No preexisting GNUstep toolchain was detected; a managed install will be required."}]},"checks":[{"id":"bootstrap.downloader","title":"Check for downloader","status":"ok","severity":"error","message":"Found curl or wget."}],"actions":[{"kind":"install_managed_toolchain","priority":1,"message":"Install the supported managed GNUstep toolchain."}]}
EOF
    return 0
  fi
  cat <<EOF
{"schema_version":1,"command":"doctor","cli_version":"$CLI_VERSION","ok":false,"status":"error","environment_classification":"no_toolchain","summary":"A required downloader is missing.","environment":{"os":"$(detect_os)","arch":"$(detect_arch)","platform":"$host_platform","bootstrap_prerequisites":{"curl":false,"wget":false},"host_prerequisites":{"source":"$HOST_PREREQUISITE_SOURCE","source_note":"$HOST_PREREQUISITE_SOURCE_NOTE","packages":$host_packages_json,"install_command":$host_install_command_json}},"compatibility":{"compatible":false,"target_kind":null,"target_id":null,"reasons":[{"code":"bootstrap_downloader_missing","message":"Neither curl nor wget is available."}],"warnings":[]},"checks":[{"id":"bootstrap.downloader","title":"Check for downloader","status":"error","severity":"error","message":"Neither curl nor wget is available."}],"actions":[{"kind":"install_downloader","priority":1,"message":"Install curl or wget, then rerun setup."}]}
EOF
  return 3
}

emit_doctor_human() {
  if command -v curl >/dev/null 2>&1; then
    printf '%s\n' "doctor: found curl"
    printf '%s\n' "doctor: no preexisting GNUstep toolchain was detected"
    printf '%s\n' "next: Install the supported managed GNUstep toolchain."
    command_text=$(host_prerequisite_install_command "$(host_platform_id)" || true)
    if [ -n "$command_text" ]; then
      printf '%s\n' "note: Host prerequisite guidance is derived from $HOST_PREREQUISITE_SOURCE."
      printf '%s\n' "note: Prerequisite install command: $command_text"
    fi
    return 0
  fi
  if command -v wget >/dev/null 2>&1; then
    printf '%s\n' "doctor: found wget"
    printf '%s\n' "doctor: no preexisting GNUstep toolchain was detected"
    printf '%s\n' "next: Install the supported managed GNUstep toolchain."
    command_text=$(host_prerequisite_install_command "$(host_platform_id)" || true)
    if [ -n "$command_text" ]; then
      printf '%s\n' "note: Host prerequisite guidance is derived from $HOST_PREREQUISITE_SOURCE."
      printf '%s\n' "note: Prerequisite install command: $command_text"
    fi
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
    --verbose|--quiet)
      shift
      ;;
    --yes)
      YES_MODE=1
      shift
      ;;
    --dogfood)
      DOGFOOD_MODE=1
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
      DOGFOOD_MODE=0
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
      DOGFOOD_MODE=0
      shift
      ;;
    --verbose|--quiet)
      shift
      ;;
    --yes)
      YES_MODE=1
      shift
      ;;
    --dogfood)
      DOGFOOD_MODE=1
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
    if [ "$DOGFOOD_MODE" = "1" ] && [ -z "$SETUP_MANIFEST" ]; then
      SETUP_MANIFEST="$DOGFOOD_MANIFEST_URL"
    fi
    perform_setup
    exit $?
    ;;
  build|clean|run|shell|new|install|remove|update)
    unsupported_command "$COMMAND"
    exit $?
    ;;
  *)
    printf '%s\n' "Unknown command: $COMMAND" >&2
    exit 2
    ;;
esac
