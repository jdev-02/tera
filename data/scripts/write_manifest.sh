#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="${MANIFEST:-$ROOT_DIR/data/manifest.sha256}"

cd "$ROOT_DIR"
mkdir -p data

artifact_list="$(mktemp)"
find data/extracts data/dem -type f ! -name ".gitkeep" -print | LC_ALL=C sort > "$artifact_list"

if [[ ! -s "$artifact_list" ]]; then
  rm -f "$artifact_list"
  echo "error: no data artifacts found under data/extracts or data/dem" >&2
  exit 1
fi

xargs shasum -a 256 < "$artifact_list" > "$MANIFEST"
rm -f "$artifact_list"

echo "[data] wrote $MANIFEST"
