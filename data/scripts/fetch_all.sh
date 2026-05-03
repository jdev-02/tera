#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

"$ROOT_DIR/data/scripts/fetch_osm.sh"
"$ROOT_DIR/data/scripts/fetch_dem.sh"
"$ROOT_DIR/data/scripts/write_manifest.sh"
"$ROOT_DIR/data/scripts/verify_manifest.sh"
