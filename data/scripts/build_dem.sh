#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AOIS_FILE="${AOIS_FILE:-$ROOT_DIR/data/aois.yml}"
WORK_DIR="${WORK_DIR:-$ROOT_DIR/data/runtime/dem-build}"

if [[ "$#" -lt 1 ]]; then
  echo "usage: data/scripts/build_dem.sh <source-dem.tif> [source-dem-2.tif ...]" >&2
  exit 2
fi

if ! command -v gdalbuildvrt >/dev/null 2>&1; then
  echo "error: gdalbuildvrt is required. macOS: brew install gdal" >&2
  exit 127
fi

if ! command -v gdalwarp >/dev/null 2>&1; then
  echo "error: gdalwarp is required. macOS: brew install gdal" >&2
  exit 127
fi

mkdir -p "$WORK_DIR"
VRT="$WORK_DIR/source-dem.vrt"

gdalbuildvrt -overwrite "$VRT" "$@"

"$ROOT_DIR/.venv/bin/python" - "$ROOT_DIR" "$AOIS_FILE" "$VRT" <<'PY'
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

root = Path(sys.argv[1])
aois_file = Path(sys.argv[2])
vrt = Path(sys.argv[3])
config = yaml.safe_load(aois_file.read_text(encoding="utf-8"))

for aoi in config["aois"]:
    bbox = aoi["bbox"]
    output = root / aoi["dem"]
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "gdalwarp",
        "-overwrite",
        "-of",
        "GTiff",
        "-t_srs",
        "EPSG:4326",
        "-te",
        str(bbox["west"]),
        str(bbox["south"]),
        str(bbox["east"]),
        str(bbox["north"]),
        "-r",
        "bilinear",
        "-co",
        "COMPRESS=DEFLATE",
        "-co",
        "PREDICTOR=2",
        str(vrt),
        str(output),
    ]
    print(f"[data] building DEM {aoi['name']} -> {output}")
    subprocess.run(command, check=True)
PY

