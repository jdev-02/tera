#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/home/digitaltrident1/Documents/tera_folder/tera}"
PLANNER_HOST="${PLANNER_HOST:-0.0.0.0}"
PLANNER_PORT="${PLANNER_PORT:-8080}"

cd "$REPO_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export DTED_SOURCE_DIR="${DTED_SOURCE_DIR:-/DTED}"
export TERA_WINTAK_IMAGERY_DIR="${TERA_WINTAK_IMAGERY_DIR:-/WINTAK Imagery}"
export TERA_OSM_ROOT_DIRS="${TERA_OSM_ROOT_DIRS:-$TERA_WINTAK_IMAGERY_DIR}"
export NAIP_EARTHEXPLORER_DIR="${NAIP_EARTHEXPLORER_DIR:-$TERA_WINTAK_IMAGERY_DIR}"
export TERA_JETSON_LOCAL_SOURCES_ONLY="${TERA_JETSON_LOCAL_SOURCES_ONLY:-1}"

exec "$REPO_DIR/.venv/bin/python" -m uvicorn llm_dev_kmh.app:app --host "$PLANNER_HOST" --port "$PLANNER_PORT"
