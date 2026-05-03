#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AOIS_FILE="${AOIS_FILE:-$ROOT_DIR/data/aois.yml}"
SOURCE_DIR="${SOURCE_DIR:-$ROOT_DIR/data/runtime/dem-source}"
COPERNICUS_BASE_URL="${COPERNICUS_BASE_URL:-https://copernicus-dem-30m.s3.amazonaws.com}"

if ! command -v curl >/dev/null 2>&1; then
  echo "error: curl is required" >&2
  exit 127
fi

if ! command -v gdalbuildvrt >/dev/null 2>&1; then
  echo "error: gdalbuildvrt is required. macOS: brew install gdal" >&2
  exit 127
fi

if ! command -v gdalwarp >/dev/null 2>&1; then
  echo "error: gdalwarp is required. macOS: brew install gdal" >&2
  exit 127
fi

mkdir -p "$SOURCE_DIR"

mapfile -t tile_urls < <(
  "$ROOT_DIR/.venv/bin/python" - "$AOIS_FILE" "$COPERNICUS_BASE_URL" <<'PY'
from __future__ import annotations

import math
import sys
from pathlib import Path

import yaml

aois_file = Path(sys.argv[1])
base_url = sys.argv[2].rstrip("/")
config = yaml.safe_load(aois_file.read_text(encoding="utf-8"))

tiles: set[tuple[int, int]] = set()
for aoi in config["aois"]:
    bbox = aoi["bbox"]
    west = math.floor(float(bbox["west"]))
    east = math.floor(float(bbox["east"]))
    south = math.floor(float(bbox["south"]))
    north = math.floor(float(bbox["north"]))
    for lat in range(south, north + 1):
        for lon in range(west, east + 1):
            tiles.add((lat, lon))

for lat, lon in sorted(tiles):
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    dirname = f"Copernicus_DSM_COG_10_{ns}{abs(lat):02d}_00_{ew}{abs(lon):03d}_00_DEM"
    print(f"{base_url}/{dirname}/{dirname}.tif")
PY
)

source_files=()
for url in "${tile_urls[@]}"; do
  output="$SOURCE_DIR/$(basename "$url")"
  source_files+=("$output")
  if [[ -f "$output" ]]; then
    echo "[data] DEM source exists: $output"
    continue
  fi
  echo "[data] downloading DEM source: $url"
  curl --fail --location --retry 3 --connect-timeout 10 --output "$output" "$url"
done

"$ROOT_DIR/data/scripts/build_dem.sh" "${source_files[@]}"
