#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
venv_python="$project_dir/.venv/bin/python"

if [ ! -x "$venv_python" ]; then
    printf '找不到虚拟环境中的 Python：%s\n' "$venv_python" >&2
    exit 1
fi

cd -- "$project_dir"
exec "$venv_python" -m app.main
