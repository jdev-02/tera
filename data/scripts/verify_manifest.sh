#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="${MANIFEST:-$ROOT_DIR/data/manifest.sha256}"

cd "$ROOT_DIR"

if [[ ! -f "$MANIFEST" ]]; then
  echo "error: manifest not found: $MANIFEST" >&2
  exit 1
fi

if ! grep -Eq "^[0-9a-f]{64}  data/" "$MANIFEST"; then
  echo "error: manifest has no data artifact checksums: $MANIFEST" >&2
  exit 1
fi

shasum -a 256 -c "$MANIFEST"
