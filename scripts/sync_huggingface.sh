#!/usr/bin/env bash
# Refresh huggingface/ from the canonical samples, docs, and LICENSE.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
DEST="${ROOT}/huggingface"

mkdir -p "${DEST}/samples" "${DEST}/docs"
cp "${ROOT}/LICENSE" "${DEST}/LICENSE"
cp "${ROOT}/samples/tiny_feasible.json" "${DEST}/samples/tiny_feasible.json"
cp "${ROOT}/samples/toy_mine.json" "${DEST}/samples/toy_mine.json"
cp "${ROOT}/samples/README.md" "${DEST}/samples/README.md"
cp "${ROOT}/docs/scenario-format.md" "${DEST}/docs/scenario-format.md"

# Point sample links at the Hub-local copies
python3 - <<'PY'
from pathlib import Path
path = Path("huggingface/docs/scenario-format.md")
text = path.read_text(encoding="utf-8")
old = """## Sample files

| File | Status |
|------|--------|
| [`samples/toy_mine.json`](../samples/toy_mine.json) | Published synthetic fixture |
| Haul-history anonymized sample | **Not published** until the data owner approves release |
"""
new = """## Sample files

| File | Status |
|------|--------|
| [`samples/tiny_feasible.json`](../samples/tiny_feasible.json) | Small feasible mine (dispatch + shift plan) |
| [`samples/toy_mine.json`](../samples/toy_mine.json) | Published synthetic fixture (dispatch) |
| Haul-history anonymized sample | **Not published** until the data owner approves release |
"""
if old in text:
    path.write_text(text.replace(old, new), encoding="utf-8")
print("synced", path)
PY

echo "Synced Hub snapshot under huggingface/"
