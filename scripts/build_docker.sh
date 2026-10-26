#!/usr/bin/env bash
# Build the route-optimizer image tagged with the pyproject package version.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="$(
  python3 -c "
import re
from pathlib import Path
text = Path('pyproject.toml').read_text(encoding='utf-8')
match = re.search(r'(?m)^version\s*=\s*\"([^\"]+)\"', text)
if not match:
    raise SystemExit('version not found in pyproject.toml')
print(match.group(1))
"
)"

IMAGE_NAME="${IMAGE_NAME:-route-optimizer}"
TAG="${IMAGE_NAME}:${VERSION}"

echo "Building ${TAG} (PACKAGE_VERSION=${VERSION})"
docker build \
  --build-arg "PACKAGE_VERSION=${VERSION}" \
  -t "${TAG}" \
  -t "${IMAGE_NAME}:latest" \
  .

echo "Built ${TAG}"
echo "${TAG}"
