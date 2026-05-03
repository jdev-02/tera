#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AOIS_FILE="${AOIS_FILE:-$ROOT_DIR/data/aois.yml}"
SOURCE_DIR="${SOURCE_DIR:-$ROOT_DIR/data/runtime/osm-source}"
SF_SOURCE_URL="${SF_SOURCE_URL:-https://download.bbbike.org/osm/bbbike/SanFrancisco/SanFrancisco.osm.pbf}"
OVERPASS_URL="${OVERPASS_URL:-https://overpass-api.de/api/interpreter}"

if ! command -v curl >/dev/null 2>&1; then
  echo "error: curl is required" >&2
  exit 127
fi

if ! command -v osmium >/dev/null 2>&1; then
  echo "error: osmium is required. macOS: brew install osmium-tool" >&2
  exit 127
fi

mkdir -p "$SOURCE_DIR"

sf_source="$SOURCE_DIR/sf-source.osm.pbf"
if [[ ! -f "$sf_source" ]]; then
  echo "[data] downloading SF OSM source: $SF_SOURCE_URL"
  curl --fail --location --retry 3 --connect-timeout 10 --output "$sf_source" "$SF_SOURCE_URL"
else
  echo "[data] SF OSM source exists: $sf_source"
fi

"$ROOT_DIR/data/scripts/clip_osm.sh" "$sf_source"

mapfile -t overpass_jobs < <(
  "$ROOT_DIR/.venv/bin/python" - "$AOIS_FILE" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

import yaml

config = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8"))
for aoi in config["aois"]:
    if aoi["name"] == "sf":
        continue
    bbox = aoi["bbox"]
    print(
        "\t".join(
            [
                aoi["name"],
                str(aoi["osm_extract"]),
                str(bbox["south"]),
                str(bbox["west"]),
                str(bbox["north"]),
                str(bbox["east"]),
            ]
        )
    )
PY
)

for job in "${overpass_jobs[@]}"; do
  IFS=$'\t' read -r name output_rel south west north east <<<"$job"
  output="$ROOT_DIR/$output_rel"
  xml_source="$SOURCE_DIR/$name.osm"
  mkdir -p "$(dirname "$output")"

  if [[ ! -f "$xml_source" ]]; then
    query="[out:xml][timeout:180][maxsize:1073741824];(node($south,$west,$north,$east);way($south,$west,$north,$east);relation($south,$west,$north,$east););(._;>;);out meta;"
    echo "[data] querying OSM for $name via Overpass"
    curl \
      --fail \
      --location \
      --retry 3 \
      --connect-timeout 10 \
      --data-urlencode "data=$query" \
      --output "$xml_source" \
      "$OVERPASS_URL"
  else
    echo "[data] OSM XML source exists: $xml_source"
  fi

  echo "[data] converting $name OSM XML -> $output"
  osmium cat --overwrite --output "$output" "$xml_source"
done
