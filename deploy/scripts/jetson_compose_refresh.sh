#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/home/digitaltrident1/Documents/tera_folder/tera}"
REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-main}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
SERVICE_NAME="${SERVICE_NAME:-llm-dev-kmh}"
PLANNER_URL="${PLANNER_URL:-http://127.0.0.1:8080}"

cd "$REPO_DIR"

if [[ ! -d .git ]]; then
  echo "[jetson-refresh] not a git repo: $REPO_DIR" >&2
  exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "[jetson-refresh] missing compose file: $REPO_DIR/$COMPOSE_FILE" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "[jetson-refresh] repo has uncommitted changes; refusing to overwrite them" >&2
  git status --short >&2
  exit 1
fi

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose -f "$COMPOSE_FILE" "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose -f "$COMPOSE_FILE" "$@"
  else
    echo "[jetson-refresh] docker compose was not found" >&2
    exit 1
  fi
}

echo "[jetson-refresh] repo: $REPO_DIR"
echo "[jetson-refresh] branch: $BRANCH"

if [[ "$(git branch --show-current)" != "$BRANCH" ]]; then
  git fetch --quiet "$REMOTE" "$BRANCH"
  git switch "$BRANCH" 2>/dev/null || git switch --track "$REMOTE/$BRANCH"
fi

if command -v make >/dev/null 2>&1; then
  make catchup
else
  git fetch --all --prune --quiet
  git pull --ff-only "$REMOTE" "$BRANCH"
fi

head_short="$(git rev-parse --short HEAD)"
echo "[jetson-refresh] now at $head_short"

if ! grep -q 'id="atakAgentBtn"' llm_dev_kmh/static/index.html; then
  echo "[jetson-refresh] warning: ATAK Local button marker not found in static HTML" >&2
fi

if systemctl list-unit-files tera-planner.service >/dev/null 2>&1; then
  echo "[jetson-refresh] stopping tera-planner.service to free port 8080"
  sudo systemctl stop tera-planner.service || true
fi

echo "[jetson-refresh] rebuilding and restarting Docker Compose service"
compose down --remove-orphans
compose up --build -d "$SERVICE_NAME"

echo "[jetson-refresh] compose status"
compose ps

if command -v curl >/dev/null 2>&1; then
  for _ in $(seq 1 30); do
    if curl -fsS "$PLANNER_URL/" >/tmp/tera-planner-index.html; then
      break
    fi
    sleep 1
  done

  if grep -q 'id="atakAgentBtn"' /tmp/tera-planner-index.html; then
    echo "[jetson-refresh] OK: new planner is serving ATAK Local button at $PLANNER_URL"
  else
    echo "[jetson-refresh] warning: planner responded, but ATAK Local button was not found" >&2
    echo "[jetson-refresh] inspect logs with: docker compose -f $COMPOSE_FILE logs -f $SERVICE_NAME" >&2
  fi
fi
