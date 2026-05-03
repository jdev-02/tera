#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/home/digitaltrident1/Documents/tera_folder/tera}"
REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-main}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
SERVICE_NAME="${SERVICE_NAME:-llm-dev-kmh}"
PLANNER_PORT="${PLANNER_PORT:-8080}"
PLANNER_URL="${PLANNER_URL:-http://127.0.0.1:${PLANNER_PORT}}"

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

detect_lan_ip() {
  if [[ -n "${TERA_JETSON_IP:-}" ]]; then
    printf '%s\n' "$TERA_JETSON_IP"
    return 0
  fi
  if [[ -n "${JETSON_IP:-}" ]]; then
    printf '%s\n' "$JETSON_IP"
    return 0
  fi
  local detected=""
  if command -v hostname >/dev/null 2>&1; then
    detected="$(hostname -I 2>/dev/null | awk '{print $1}')"
    if [[ -n "$detected" ]]; then
      printf '%s\n' "$detected"
      return 0
    fi
  fi
  if command -v ip >/dev/null 2>&1; then
    ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1; i<=NF; i++) if ($i=="src") {print $(i+1); exit}}'
  fi
}

wait_for_url() {
  local url="$1"
  local label="$2"
  local tries="${3:-30}"
  local body_path="${4:-/tmp/tera-health.json}"
  for _ in $(seq 1 "$tries"); do
    if curl -fsS --connect-timeout 2 --max-time 5 "$url" >"$body_path"; then
      echo "[jetson-refresh] OK: $label reachable at $url"
      return 0
    fi
    sleep 1
  done
  echo "[jetson-refresh] ERROR: $label is not reachable at $url" >&2
  return 1
}

print_network_diagnostics() {
  echo "[jetson-refresh] network diagnostics" >&2
  if command -v ip >/dev/null 2>&1; then
    ip -br addr >&2 || true
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp "( sport = :$PLANNER_PORT )" >&2 || true
  fi
  if command -v docker >/dev/null 2>&1; then
    compose ps >&2 || true
    compose logs --tail=80 "$SERVICE_NAME" >&2 || true
  fi
  if command -v ufw >/dev/null 2>&1; then
    sudo -n ufw status >&2 || ufw status >&2 || true
  fi
}

allow_planner_port_if_firewall_active() {
  if ! command -v ufw >/dev/null 2>&1; then
    return 0
  fi
  local status
  status="$(sudo -n ufw status 2>/dev/null || ufw status 2>/dev/null || true)"
  if grep -qi "Status: active" <<<"$status"; then
    echo "[jetson-refresh] ufw is active; allowing ${PLANNER_PORT}/tcp"
    sudo -n ufw allow "${PLANNER_PORT}/tcp" || echo "[jetson-refresh] warning: could not update ufw without sudo password" >&2
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
  local ready_message="${TERA_ATAK_READY_MESSAGE:-TERA Agent ready. Send your traffic.}"
  (
    ollama run "$model" "Readiness check. Reply exactly: \"$ready_message\"" &
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

LAN_IP="$(detect_lan_ip || true)"
if [[ -z "$LAN_IP" ]]; then
  echo "[jetson-refresh] warning: could not detect Jetson LAN IP; set TERA_JETSON_IP=10.1.63.96" >&2
else
  export TERA_JETSON_IP="$LAN_IP"
  export TERA_PUBLIC_BASE_URL="${TERA_PUBLIC_BASE_URL:-http://${LAN_IP}:${PLANNER_PORT}}"
  echo "[jetson-refresh] Jetson LAN endpoint: ${TERA_PUBLIC_BASE_URL}"
fi

if ! grep -q 'id="atakAgentBtn"' llm_dev_kmh/static/index.html; then
  echo "[jetson-refresh] warning: ATAK Local button marker not found in static HTML" >&2
fi

allow_planner_port_if_firewall_active

if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files tera-planner.service >/dev/null 2>&1; then
  echo "[jetson-refresh] stopping tera-planner.service to free port $PLANNER_PORT"
  sudo systemctl stop tera-planner.service || true
fi

start_ollama_for_atak

echo "[jetson-refresh] rebuilding and restarting Docker Compose service"
compose down --remove-orphans
compose up --build -d "$SERVICE_NAME"

echo "[jetson-refresh] compose status"
compose ps

if command -v curl >/dev/null 2>&1; then
  if ! wait_for_url "${PLANNER_URL}/health" "local health endpoint" 45 /tmp/tera-health-local.json; then
    print_network_diagnostics
    exit 1
  fi

  if ! wait_for_url "${PLANNER_URL}/" "local web app" 10 /tmp/tera-planner-index.html; then
    print_network_diagnostics
    exit 1
  fi

  if ! grep -q 'id="atakAgentBtn"' /tmp/tera-planner-index.html; then
    echo "[jetson-refresh] ERROR: planner responded, but ATAK Local button was not found" >&2
    print_network_diagnostics
    exit 1
  fi

  if [[ -n "$LAN_IP" ]]; then
    LAN_HEALTH_URL="http://${LAN_IP}:${PLANNER_PORT}/health"
    if ! wait_for_url "$LAN_HEALTH_URL" "LAN health endpoint for ATAK plugin" 10 /tmp/tera-health-lan.json; then
      echo "[jetson-refresh] ATAK plugin will fail until this LAN health URL works: $LAN_HEALTH_URL" >&2
      print_network_diagnostics
      exit 1
    fi
    echo "[jetson-refresh] ATAK plugin endpoint: http://${LAN_IP}:${PLANNER_PORT}/api/prompt"
  fi
fi
