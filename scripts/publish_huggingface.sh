#!/usr/bin/env bash
# Upload the local huggingface/ snapshot to the Hugging Face Hub.
# Requires: pip install huggingface_hub, and HF_TOKEN (write access).
#
# Defaults to <your-hf-username>/route-optimizer (from the token's whoami).
# Override with: HF_REPO_ID=my-org/route-optimizer ./scripts/publish_huggingface.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -z "${HF_TOKEN:-${HUGGING_FACE_HUB_TOKEN:-}}" ]]; then
  echo "error: set HF_TOKEN (or HUGGING_FACE_HUB_TOKEN) with write access" >&2
  exit 1
fi

./scripts/sync_huggingface.sh

# Prefer the venv interpreter when present (has huggingface_hub / Pillow).
PYTHON="python3"
if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PYTHON="${ROOT}/.venv/bin/python"
fi

"$PYTHON" "${ROOT}/scripts/build_hub_assets.py"

"$PYTHON" - <<'PY'
import os
from pathlib import Path

from huggingface_hub import HfApi, login

token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
login(token=token)
api = HfApi(token=token)
me = api.whoami()
username = me["name"]
repo_id = os.environ.get("HF_REPO_ID") or ("%s/route-optimizer" % username)
print("Publishing as %s → %s" % (username, repo_id))

api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True, private=False)
api.upload_folder(
    folder_path=str(Path("huggingface")),
    repo_id=repo_id,
    repo_type="model",
    commit_message="Sync RouteOptimizer Hub snapshot (samples, format, license)",
)
print("https://huggingface.co/" + repo_id)
PY
