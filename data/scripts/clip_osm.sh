#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AOIS_FILE="${AOIS_FILE:-$ROOT_DIR/data/aois.yml}"
SOURCE_PBF="${1:-}"

if [[ -z "$SOURCE_PBF" ]]; then
  echo "usage: data/scripts/clip_osm.sh <source.osm.pbf>" >&2
  exit 2
fi

if ! command -v osmium >/dev/null 2>&1; then
  echo "error: osmium is required. macOS: brew install osmium-tool" >&2
  exit 127
fi

if [[ ! -f "$SOURCE_PBF" ]]; then
  echo "error: source PBF not found: $SOURCE_PBF" >&2
  exit 1
fi

"$ROOT_DIR/.venv/bin/python" - "$ROOT_DIR" "$AOIS_FILE" "$SOURCE_PBF" <<'PY'
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

root = Path(sys.argv[1])
aois_file = Path(sys.argv[2])
source_pbf = Path(sys.argv[3])
config = yaml.safe_load(aois_file.read_text(encoding="utf-8"))

for aoi in config["aois"]:
    bbox = aoi["bbox"]
    output = root / aoi["osm_extract"]
    output.parent.mkdir(parents=True, exist_ok=True)
    bbox_arg = f"{bbox['west']},{bbox['south']},{bbox['east']},{bbox['north']}"
    command = [
        "osmium",
        "extract",
        "--bbox",
        bbox_arg,
        "--strategy",
        "complete_ways",
        "--overwrite",
        "--output",
        str(output),
        str(source_pbf),
    ]
    print(f"[data] clipping {aoi['name']} -> {output}")
    subprocess.run(command, check=True)
PY
