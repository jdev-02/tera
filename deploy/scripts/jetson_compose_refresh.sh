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

start_ollama_for_atak() {
  local model="${TERA_ATAK_MODEL:-gemma3:4b}"
  local ollama_url="${TERA_HOST_OLLAMA_URL:-http://127.0.0.1:11434}"
  local runtime_dir="${TERA_RUNTIME_DIR:-$REPO_DIR/llm_dev_kmh/offline_packages/runtime}"
  local warm_timeout="${TERA_ATAK_WARMUP_TIMEOUT_S:-45}"
  mkdir -p "$runtime_dir"

  echo "[jetson-refresh] preparing Ollama model for TERA ATAK mode: $model"
  if ! command -v ollama >/dev/null 2>&1; then
    echo "[jetson-refresh] warning: ollama CLI not found on Jetson host; web button can only use an already-running Ollama endpoint" >&2
    return 0
  fi

  if ! curl -fsS "$ollama_url/api/tags" >/dev/null 2>&1; then
    if command -v systemctl >/dev/null 2>&1; then
      sudo -n systemctl start ollama >/dev/null 2>&1 || systemctl --user start ollama >/dev/null 2>&1 || true
    fi
  fi

  if ! curl -fsS "$ollama_url/api/tags" >/dev/null 2>&1; then
    nohup ollama serve >"$runtime_dir/ollama-serve.log" 2>&1 &
  fi

  for _ in $(seq 1 30); do
    if curl -fsS "$ollama_url/api/tags" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done

  if ! curl -fsS "$ollama_url/api/tags" >/dev/null 2>&1; then
    echo "[jetson-refresh] warning: Ollama did not become reachable at $ollama_url" >&2
    return 0
  fi

  if ! ollama list | awk '{print $1}' | grep -Fx "$model" >/dev/null 2>&1; then
    echo "[jetson-refresh] pulling $model for local ATAK mode"
    ollama pull "$model"
  fi

  echo "[jetson-refresh] warming $model with TERA ATAK prompt in background"
  (
    ollama run "$model" "TERA ATAK readiness check. Reply READY in one short sentence." &
    warm_pid="$!"
    (
      sleep "$warm_timeout"
      if kill -0 "$warm_pid" >/dev/null 2>&1; then
        echo "[jetson-refresh] warning: Ollama warmup exceeded ${warm_timeout}s; stopping warmup"
        kill "$warm_pid" >/dev/null 2>&1 || true
      fi
    ) &
    watchdog_pid="$!"
    wait "$warm_pid" >/dev/null 2>&1 || true
    kill "$watchdog_pid" >/dev/null 2>&1 || true
  ) >"$runtime_dir/ollama-warmup.log" 2>&1 &
  echo "[jetson-refresh] Ollama warmup background pid $!; continuing with web app restart"
}

echo "[jetson-refresh] repo: $REPO_DIR"
echo "[jetson-refresh] branch: $BRANCH"

if [[ "$(git branch --show-current)" != "$BRANCH" ]]; then
  git fetch --quiet "$REMOTE" "$BRANCH"
  git switch "$BRANCH" 2>/dev/null || git switch --track "$REMOTE/$BRANCH"
fi

if command -v make >/dev/null 2>&1; then
  make catchup
fi

git fetch --quiet "$REMOTE" "$BRANCH"
git pull --ff-only "$REMOTE" "$BRANCH"

head_short="$(git rev-parse --short HEAD)"
echo "[jetson-refresh] now at $head_short"

if ! grep -q 'id="atakAgentBtn"' llm_dev_kmh/static/index.html; then
  echo "[jetson-refresh] warning: ATAK Local button marker not found in static HTML" >&2
fi

if systemctl list-unit-files tera-planner.service >/dev/null 2>&1; then
  echo "[jetson-refresh] stopping tera-planner.service to free port 8080"
  sudo systemctl stop tera-planner.service || true
fi

start_ollama_for_atak

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
