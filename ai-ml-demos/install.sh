#!/bin/sh

# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

set -eu

ASSET_BASE_URL=${ASSET_BASE_URL:-}
BIN_DIR=${BIN_DIR:-/usr/bin}
INSTALL_ROOT=${INSTALL_ROOT:-/opt/var-demos/ai-ml}
IN_PLACE=0
PREFETCH_ONLY=0
VAR_DEMOS_REF=${VAR_DEMOS_REF:-edge-ai}
VAR_DEMOS_REPOSITORY=${VAR_DEMOS_REPOSITORY:-varigit/var-demos}

BOARD=
DRY_RUN=0
LIST_ONLY=0
REQUESTED_DEMOS=
REMOTE_SOURCE=0
SOURCE_ROOT=
UNINSTALL=0
NO_LAUNCHER=0
WORK_DIR=

progress() {
    [ "${VAR_DEMOS_PROGRESS:-0}" = 1 ] || return 0
    python3 -c 'import json,sys; print("VAR_INSTALL_EVENT " + json.dumps({
        "message":sys.argv[1], "done":sys.argv[2]=="1",
        "asset":sys.argv[3]=="1", "download":sys.argv[4] or None,
        "asset_path":sys.argv[5] or None}), flush=True)' \
        "$1" "${2:-0}" "${3:-0}" "${4:-}" "${5:-}"
}

usage() {
    cat <<'EOF'
Usage: install.sh [options] [demo ...]

Install every compatible demo, or only the demos named on the command line.

Options:
  --board BOARD       Override automatic board detection
  --bin-dir DIRECTORY Install the var-ai command in this directory
  --no-launcher       Install as a module without the var-ai command
  --dry-run           Show what would be installed
  --list              List demos compatible with the detected board
  --prefix DIRECTORY  Installation directory
  --source DIRECTORY  Use a local ai-ml-demos source tree
  --uninstall         Remove var-ai and every installed demo
  -h, --help          Show this help

Known board ids are defined in catalog.toml.
EOF
}

fail() {
    echo "Error: $*" >&2
    exit 1
}

validate_removal_path() {
    path=$1
    [ ! -L "${path}" ] || fail "installation root must not be a symlink"
    case "${path}" in
        ''|/|/opt|/usr|/usr/bin|/home|/root|.|..)
            fail "refusing unsafe removal path: ${path}"
            ;;
        /*) ;;
        *) fail "removal path must be absolute: ${path}" ;;
    esac
    case "${path}/" in
        *'/../'*|*'/./'*|*'//'*) fail "unsafe removal path: ${path}" ;;
    esac
}

ensure_not_running() {
    require_command python3
    python3 - "${INSTALL_ROOT}" <<'PY' || fail "stop var-ai before continuing"
import os
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
for process in Path('/proc').glob('[0-9]*'):
    if process.name == str(os.getpid()):
        continue
    try:
        arguments = (process / 'cmdline').read_bytes().split(b'\0')
        if not Path(os.fsdecode(arguments[0])).name.startswith('python'):
            continue
        paths = [(process / 'cwd').resolve()]
        if len(arguments) > 1:
            script = Path(os.fsdecode(arguments[1]))
            if script.is_absolute():
                paths.append(script.resolve())
        if any(path == root or root in path.parents for path in paths):
            raise SystemExit(f'demo installation is in use by PID {process.name}')
    except (OSError, ValueError):
        continue
PY
}

uninstall_demos() {
    validate_removal_path "${INSTALL_ROOT}"
    launcher="${BIN_DIR}/var-ai"
    manager="${INSTALL_ROOT}/manager.py"

    if [ "${DRY_RUN}" -eq 1 ]; then
        echo "Would remove: ${INSTALL_ROOT}"
        if [ -L "${launcher}" ] && \
           [ "$(readlink "${launcher}")" = "${manager}" ]; then
            echo "Would remove: ${launcher}"
        fi
        return
    fi

    ensure_not_running

    if [ -e "${INSTALL_ROOT}" ]; then
        [ -f "${INSTALL_ROOT}/manager.py" ] && \
            [ -f "${INSTALL_ROOT}/catalog.toml" ] || \
            fail "refusing to remove an unrecognized installation"
    fi

    if [ -L "${launcher}" ]; then
        if [ "$(readlink "${launcher}")" = "${manager}" ]; then
            rm -f -- "${launcher}"
            echo "Removed ${launcher}"
        else
            echo "Keeping unrelated symlink: ${launcher}"
        fi
    elif [ -e "${launcher}" ]; then
        echo "Keeping unrelated file: ${launcher}"
    fi

    if [ -e "${INSTALL_ROOT}" ]; then
        rm -rf -- "${INSTALL_ROOT}"
        echo "Removed ${INSTALL_ROOT}"
    else
        echo "Nothing installed at ${INSTALL_ROOT}"
    fi

    echo "Uninstall complete"
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || \
        fail "required command not found: $1"
}

cleanup() {
    if [ -n "${WORK_DIR}" ] && [ -d "${WORK_DIR}" ]; then
        rm -rf "${WORK_DIR}"
    fi
}

detect_board() {
    [ -r /proc/device-tree/compatible ] || \
        fail "Device Tree compatible string is not available"
    BOARD=$(catalog detect) || \
        fail "unsupported board; use --board only for development"
}

download() {
    download_url=$1
    download_destination=$2

    curl \
        --fail \
        --silent --show-error \
        --location \
        --retry 5 \
        --retry-all-errors \
        --connect-timeout 15 \
        --speed-time 30 --speed-limit 1024 \
        --output "${download_destination}" \
        "${download_url}"
}

fetch_source() {
    if [ -n "${SOURCE_ROOT}" ]; then
        [ -d "${SOURCE_ROOT}" ] || fail "source directory does not exist"
        return
    fi

    script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd || true)
    if [ -n "${script_dir}" ] && \
       [ -f "${script_dir}/catalog.toml" ] && \
       [ ! -f "${script_dir}/.var-ai-installed" ]; then
        SOURCE_ROOT=${script_dir}
        return
    fi

    require_command curl
    require_command tar
    archive="${WORK_DIR}/source.tar.gz"
    source_dir="${WORK_DIR}/source"
    install -d "${source_dir}"
    ref_metadata="${WORK_DIR}/ref.json"
    download \
        "https://api.github.com/repos/${VAR_DEMOS_REPOSITORY}/commits/${VAR_DEMOS_REF}" \
        "${ref_metadata}"
    source_commit=$(python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1]))["sha"])' \
        "${ref_metadata}")
    [ "${#source_commit}" -eq 40 ] || fail "invalid source commit"
    url="https://github.com/${VAR_DEMOS_REPOSITORY}/archive/${source_commit}.tar.gz"
    echo "Downloading source from ${VAR_DEMOS_REPOSITORY}@${source_commit}"
    download "${url}" "${archive}"
    tar -xzf "${archive}" -C "${source_dir}"
    SOURCE_ROOT=$(find "${source_dir}" -type d \
        -path '*/ai-ml-demos' -print | head -n 1)
    [ -n "${SOURCE_ROOT}" ] || fail "ai-ml-demos not found"
    REMOTE_SOURCE=1
}

catalog() {
    python3 "${SOURCE_ROOT}/catalog.py" \
        --catalog "${SOURCE_ROOT}/catalog.toml" "$@"
}

check_platform() {
    status=$(catalog platform-field "${BOARD}" status) || \
        fail "unknown board: ${BOARD}"
    [ "${status}" = "validated" ] || \
        fail "${BOARD} support is ${status}; hardware validation is required"

    if [ -z "${ASSET_BASE_URL}" ]; then
        ASSET_BASE_URL=$(catalog \
            platform-field "${BOARD}" asset_base_url)
    fi
}

load_demo() {
    demo=$1
    DEMO_TITLE=$(catalog demo-field "${demo}" title)
    DEMO_PATH=$(catalog demo-field "${demo}" path)
    DEMO_ENTRYPOINT=$(catalog demo-field "${demo}" entrypoint)
    DEMO_MANIFEST=$(catalog demo-field "${demo}" manifest)
}

demo_is_compatible() {
    catalog supports "$1" "${BOARD}" >/dev/null
}

selected_demos() {
    if [ -n "${REQUESTED_DEMOS}" ]; then
        printf '%s\n' ${REQUESTED_DEMOS}
    else
        catalog demos --platform "${BOARD}"
    fi
}

list_demos() {
    echo "Compatible demos for ${BOARD}:"
    catalog demos --platform "${BOARD}" --titles | \
        while IFS="$(printf '\t')" read -r demo title; do
            printf '  %-32s %s\n' "${demo}" "${title}"
        done
}

check_runtime() {
    require_command cp
    require_command curl
    require_command install
    require_command ln
    require_command python3
    require_command sha256sum

    delegate=$(catalog platform-field "${BOARD}" delegate_path)
    [ -r "${delegate}" ] || fail "missing NPU delegate: ${delegate}"

    python3 - <<'PY' || fail "required Python modules are missing"
import cv2
import numpy
import tflite_runtime.interpreter
import gi
gi.require_version('GstPbutils', '1.0')
gi.require_version('GstVideo', '1.0')
gi.require_version('Gtk', '3.0')
from gi.repository import GstPbutils, GstVideo, Gtk
PY

    require_command gst-inspect-1.0
    plugins=$(catalog platform-field "${BOARD}" runtime_plugins)
    for plugin in ${plugins}; do
        gst-inspect-1.0 "${plugin}" >/dev/null 2>&1 || \
            fail "missing GStreamer plugin: ${plugin}"
    done
}

install_asset() {
    demo=$1
    expected=$2
    remote_path=$3
    relative_path=$4

    case "${remote_path}:${relative_path}" in
        /*:*|*:/|*..*) fail "unsafe asset path in ${demo}" ;;
    esac

    destination="${INSTALL_ROOT}/${demo}/${relative_path}"
    cache_file="${WORK_DIR}/assets/${expected}"
    if [ "${PREFETCH_ONLY}" -eq 1 ]; then
        progress "Verifying ${relative_path}" 0 0 "${cache_file}.part" "${remote_path}"
    else
        progress "Installing ${relative_path}" 0 0 "" "${remote_path}"
    fi
    if [ ! -f "${cache_file}" ]; then
        if [ -f "${destination}" ] && \
           printf '%s  %s\n' "${expected}" "${destination}" | \
               sha256sum -c - >/dev/null 2>&1; then
            [ "${VAR_DEMOS_PROGRESS:-0}" = 1 ] || echo "Using verified ${relative_path}"
            cp "${destination}" "${cache_file}"
        else
            progress "Downloading ${relative_path}" 0 0 "${cache_file}.part" "${remote_path}"
            [ "${VAR_DEMOS_PROGRESS:-0}" = 1 ] || echo "Downloading ${remote_path}"
            case "${remote_path}" in
                https://*) asset_url=${remote_path} ;;
                *://*) fail "unsupported asset URL: ${remote_path}" ;;
                *) asset_url="${ASSET_BASE_URL}/${remote_path}" ;;
            esac
            download \
                "${asset_url}" \
                "${cache_file}.part"
            printf '%s  %s\n' "${expected}" "${cache_file}.part" | \
                sha256sum -c - >/dev/null
            mv -f "${cache_file}.part" "${cache_file}"
        fi
    fi

    if [ "${PREFETCH_ONLY:-0}" -eq 1 ]; then
        progress "Verified ${relative_path}" 1 1 "" "${remote_path}"
        return 0
    fi
    install -d "$(dirname -- "${destination}")"
    install -m 0644 "${cache_file}" "${destination}"
    progress "Installed ${relative_path}" 1 0 "" "${remote_path}"
}

prepare_demo_assets() {
    manifest="${SOURCE_ROOT}/${DEMO_PATH}/${DEMO_MANIFEST}"
    while read -r expected remote_path relative_path; do
        case "${expected}" in
            ''|'#'*) continue ;;
        esac
        install_asset "${DEMO_PATH}" "${expected}" \
            "${remote_path}" "${relative_path}"
    done < "${manifest}"
}

install_demo() {
    demo=$1
    load_demo "${demo}"
    demo_is_compatible "${demo}" || \
        fail "${demo} is not compatible with ${BOARD}"

    progress "Installing ${DEMO_TITLE}"
    [ "${VAR_DEMOS_PROGRESS:-0}" = 1 ] || echo "Installing ${DEMO_TITLE}"
    install -d "${INSTALL_ROOT}/${DEMO_PATH}"
    if [ "${IN_PLACE}" -eq 0 ]; then
        cp -R "${SOURCE_ROOT}/${DEMO_PATH}/." \
            "${INSTALL_ROOT}/${DEMO_PATH}/"
    fi

    prepare_demo_assets

    progress "${DEMO_TITLE} installed" 1
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --board)
            [ "$#" -ge 2 ] || fail "--board requires a value"
            BOARD=$2
            shift 2
            ;;
        --bin-dir)
            [ "$#" -ge 2 ] || fail "--bin-dir requires a value"
            BIN_DIR=$2
            shift 2
            ;;
        --no-launcher)
            NO_LAUNCHER=1
            shift
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --list)
            LIST_ONLY=1
            shift
            ;;
        --prefix)
            [ "$#" -ge 2 ] || fail "--prefix requires a value"
            INSTALL_ROOT=$2
            shift 2
            ;;
        --source)
            [ "$#" -ge 2 ] || fail "--source requires a value"
            SOURCE_ROOT=$2
            shift 2
            ;;
        --uninstall)
            UNINSTALL=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --*) fail "unknown option: $1" ;;
        *)
            REQUESTED_DEMOS="${REQUESTED_DEMOS} $1"
            shift
            ;;
    esac
done

if [ "${UNINSTALL}" -eq 1 ]; then
    [ "${LIST_ONLY}" -eq 0 ] || \
        fail "--uninstall cannot be combined with --list"
    [ -z "${REQUESTED_DEMOS}" ] || \
        fail "--uninstall does not accept demo names"
    require_command readlink
    require_command rm
    uninstall_demos
    exit 0
fi

require_command install
require_command python3
WORK_DIR=$(mktemp -d)
trap cleanup EXIT HUP INT TERM
install -d "${WORK_DIR}/assets"
fetch_source
if [ "${REMOTE_SOURCE}" -eq 1 ]; then
    # Run the installer from the same revision as the downloaded demo code.
    set -- --source "${SOURCE_ROOT}" --prefix "${INSTALL_ROOT}" \
        --bin-dir "${BIN_DIR}"
    [ -z "${BOARD}" ] || set -- "$@" --board "${BOARD}"
    [ "${DRY_RUN}" -eq 0 ] || set -- "$@" --dry-run
    [ "${LIST_ONLY}" -eq 0 ] || set -- "$@" --list
    [ "${NO_LAUNCHER}" -eq 0 ] || set -- "$@" --no-launcher
    for requested_demo in ${REQUESTED_DEMOS}; do
        set -- "$@" "${requested_demo}"
    done
    export ASSET_BASE_URL
    sh "${SOURCE_ROOT}/install.sh" "$@"
    exit 0
fi
catalog validate --root "${SOURCE_ROOT}"

if [ -z "${BOARD}" ]; then
    detect_board
fi
check_platform

if [ "${LIST_ONLY}" -eq 1 ]; then
    list_demos
    exit 0
fi

if [ "${DRY_RUN}" -eq 1 ]; then
    echo "Board: ${BOARD}"
    echo "Install root: ${INSTALL_ROOT}"
    echo "Command: ${BIN_DIR}/var-ai"
    echo "Demos:"
    selected_demos | while read -r demo; do
        load_demo "${demo}"
        demo_is_compatible "${demo}" || \
            fail "${demo} is not compatible with ${BOARD}"
        echo "  ${demo}"
    done
    exit 0
fi

check_runtime
ensure_not_running
PREFETCH_ONLY=1
selected_demos | while read -r demo; do
    load_demo "${demo}"
    demo_is_compatible "${demo}" || \
        fail "${demo} is not compatible with ${BOARD}"
    echo "Preparing assets for ${DEMO_TITLE}"
    prepare_demo_assets
done
PREFETCH_ONLY=0
install -d "${INSTALL_ROOT}"
source_path=$(CDPATH= cd -- "${SOURCE_ROOT}" && pwd)
install_path=$(CDPATH= cd -- "${INSTALL_ROOT}" && pwd)
if [ "${source_path}" = "${install_path}" ]; then
    IN_PLACE=1
else
    install -m 0755 "${SOURCE_ROOT}/install.sh" \
        "${INSTALL_ROOT}/install.sh"
    install -m 0644 "${SOURCE_ROOT}/catalog.toml" \
        "${INSTALL_ROOT}/catalog.toml"
    install -m 0755 "${SOURCE_ROOT}/catalog.py" \
        "${INSTALL_ROOT}/catalog.py"
    install -m 0755 "${SOURCE_ROOT}/manager.py" \
        "${INSTALL_ROOT}/manager.py"
    install -m 0644 "${SOURCE_ROOT}/telemetry.py" \
        "${INSTALL_ROOT}/telemetry.py"
    install -m 0644 "${SOURCE_ROOT}/runtime.py" \
        "${INSTALL_ROOT}/runtime.py"
    install -m 0644 "${SOURCE_ROOT}/vision_overlay.py" \
        "${INSTALL_ROOT}/vision_overlay.py"
    install -m 0644 "${SOURCE_ROOT}/vision_window.py" \
        "${INSTALL_ROOT}/vision_window.py"
    install -m 0644 "${SOURCE_ROOT}/terminal_ui.py" \
        "${INSTALL_ROOT}/terminal_ui.py"
    install -m 0644 "${SOURCE_ROOT}/demo_menu.py" \
        "${INSTALL_ROOT}/demo_menu.py"
    install -m 0644 "${SOURCE_ROOT}/retired_assets.py" \
        "${INSTALL_ROOT}/retired_assets.py"
    install -m 0644 "${SOURCE_ROOT}/retired-assets.manifest" \
        "${INSTALL_ROOT}/retired-assets.manifest"
fi
selected_demos | while read -r demo; do
    install_demo "${demo}"
done

if [ "${NO_LAUNCHER}" -eq 0 ]; then
    install -d "${BIN_DIR}"
    if [ -e "${BIN_DIR}/var-ai" ] && [ ! -L "${BIN_DIR}/var-ai" ]; then
        fail "refusing to replace non-symlink: ${BIN_DIR}/var-ai"
    fi
    ln -sfn "${INSTALL_ROOT}/manager.py" "${BIN_DIR}/var-ai"
fi
touch "${INSTALL_ROOT}/.var-ai-installed"
progress "Removing retired sample videos"
python3 "${SOURCE_ROOT}/retired_assets.py" "${INSTALL_ROOT}" \
    "${SOURCE_ROOT}/retired-assets.manifest"

echo
echo "Installation complete: ${INSTALL_ROOT}"
[ "${NO_LAUNCHER}" -eq 1 ] || echo "Run the demo manager: var-ai"
