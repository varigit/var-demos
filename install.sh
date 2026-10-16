#!/bin/sh
# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause
set -eu

repo=${VAR_DEMOS_REPOSITORY:-varigit/var-demos}
ref=${VAR_DEMOS_REF:-edge-ai}
case "$repo" in
    *..*|/*|*' '*|*'?'*) echo 'Invalid repository' >&2; exit 1 ;;
esac
case "$ref" in
    *..*|/*|*' '*|*'?'*) echo 'Invalid revision' >&2; exit 1 ;;
esac

script_dir=
if [ -f "$0" ]; then
    script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
fi
if [ -n "$script_dir" ] && [ -f "$script_dir/installer.py" ]; then
    case " $* " in
        *' --uninstall '*|*' --source '*|*' --list '*|*' --dry-run '*)
            exec python3 "$script_dir/installer.py" "$@" ;;
    esac
    if [ ! -f "$script_dir/.var-demos-installed" ]; then
        exec python3 "$script_dir/installer.py" "$@"
    fi
fi

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
if [ -t 1 ] && [ "${TERM:-dumb}" != dumb ]; then
    printf 'Preparing var-demos installer...'
else
    printf 'var-demos: preparing installer\n'
fi
curl -fsSL --retry 2 \
    "https://api.github.com/repos/$repo/commits/$ref" -o "$work/revision.json"
revision=$(python3 -c 'import json,sys; s=json.load(open(sys.argv[1]))["sha"]; assert len(s)==40 and all(c in "0123456789abcdef" for c in s); print(s)' "$work/revision.json")
curl -fsSL --retry 2 \
    "https://github.com/$repo/archive/$revision.tar.gz" -o "$work/source.tgz"
mkdir "$work/source"
tar -tzf "$work/source.tgz" | awk '
    /^\// || /(^|\/)\.\.(\/|$)/ { bad=1 }
    END { exit bad }
'
tar -xzf "$work/source.tgz" --strip-components=1 -C "$work/source"
python3 "$work/source/installer.py" --source "$work/source" "$@"
