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

exec "$REPO_DIR/.venv/bin/python" -m uvicorn llm_dev_kmh.app:app --host "$PLANNER_HOST" --port "$PLANNER_PORT"
