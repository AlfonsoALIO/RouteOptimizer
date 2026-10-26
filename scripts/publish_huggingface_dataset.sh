#!/usr/bin/env bash
# Generate synthetic scenarios and upload huggingface-dataset/ to the Hub.
# Requires HF_TOKEN with write access.
#
# Default repo: <your-hf-username>/route-optimizer-scenarios
# Override: HF_DATASET_ID=my-org/route-optimizer-scenarios ./scripts/publish_huggingface_dataset.sh
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

"$PYTHON" "${ROOT}/scripts/generate_synthetic_scenarios.py"

"$PYTHON" - <<'PY'
import os
from pathlib import Path

from huggingface_hub import HfApi, login

token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
login(token=token)
api = HfApi(token=token)
username = api.whoami()["name"]
repo_id = os.environ.get("HF_DATASET_ID") or ("%s/route-optimizer-scenarios" % username)
print("Publishing dataset as %s → %s" % (username, repo_id))

api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True, private=False)
api.upload_folder(
    folder_path=str(Path("huggingface-dataset")),
    repo_id=repo_id,
    repo_type="dataset",
    commit_message="Sync synthetic mine scenarios (format v1)",
)
print("https://huggingface.co/datasets/" + repo_id)
PY
