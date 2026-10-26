#!/usr/bin/env bash
# Upload huggingface-space/ to a public Gradio Space.
# Requires HF_TOKEN (write). Default: <whoami>/route-optimizer-demo
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -z "${HF_TOKEN:-${HUGGING_FACE_HUB_TOKEN:-}}" ]]; then
  echo "error: set HF_TOKEN (or HUGGING_FACE_HUB_TOKEN) with write access" >&2
  exit 1
fi

PYTHON="python3"
if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PYTHON="${ROOT}/.venv/bin/python"
fi

mkdir -p huggingface-space/samples
cp -f samples/tiny_feasible.json samples/toy_mine.json huggingface-space/samples/

"$PYTHON" - <<'PY'
import os
from pathlib import Path

from huggingface_hub import HfApi, login

token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
login(token=token)
api = HfApi(token=token)
username = api.whoami()["name"]
repo_id = os.environ.get("HF_SPACE_REPO_ID") or ("%s/route-optimizer-demo" % username)
print("Publishing Space as %s → %s" % (username, repo_id))

api.create_repo(repo_id=repo_id, repo_type="space", exist_ok=True, private=False, space_sdk="gradio")
api.upload_folder(
    folder_path=str(Path("huggingface-space")),
    repo_id=repo_id,
    repo_type="space",
    commit_message="Add RouteOptimizer Gradio demo Space",
)
print("https://huggingface.co/spaces/" + repo_id)
PY
