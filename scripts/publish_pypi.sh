#!/usr/bin/env bash
# Build and upload route-optimizer to PyPI.
# Requires: TWINE_USERNAME=__token__ and TWINE_PASSWORD=<pypi-api-token>
# Create a token at https://pypi.org/manage/account/token/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${ROOT}/.venv/bin/python"
PIP="${ROOT}/.venv/bin/pip"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
  PIP=pip3
fi

"$PIP" install -q build twine
rm -rf dist build
"$PYTHON" -m build

if [[ -z "${TWINE_PASSWORD:-}" && -z "${PYPI_API_TOKEN:-}" ]]; then
  echo "error: set TWINE_PASSWORD or PYPI_API_TOKEN to a PyPI API token" >&2
  echo "  export TWINE_USERNAME=__token__" >&2
  echo "  export TWINE_PASSWORD=pypi-..." >&2
  exit 1
fi

export TWINE_USERNAME="${TWINE_USERNAME:-__token__}"
if [[ -n "${PYPI_API_TOKEN:-}" && -z "${TWINE_PASSWORD:-}" ]]; then
  export TWINE_PASSWORD="$PYPI_API_TOKEN"
fi

"$PYTHON" -m twine upload dist/*
echo "https://pypi.org/project/route-optimizer/"
