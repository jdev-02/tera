#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

HOST="${TERA_ATAK_TEST_HOST:-0.0.0.0}"
PORT="${TERA_ATAK_TEST_PORT:-8080}"
MODEL="${OLLAMA_MODEL:-${TERA_GEMMA_MODEL:-gemma3:4b}}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
OLLAMA_LOG="${TERA_OLLAMA_LOG:-/tmp/tera-ollama.log}"

if ! command -v curl >/dev/null 2>&1; then
  echo "error: curl is required on the Jetson." >&2
  exit 1
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "error: ollama is required on the Jetson." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 is required on the Jetson." >&2
  exit 1
fi

start_ollama_if_needed() {
  if curl -fsS --max-time 2 "${OLLAMA_BASE_URL}/api/tags" >/dev/null 2>&1; then
    return
  fi

  case "${OLLAMA_BASE_URL}" in
    http://127.0.0.1:11434|http://localhost:11434)
      echo "Ollama is not responding at ${OLLAMA_BASE_URL}; starting ollama serve..."
      OLLAMA_HOST=127.0.0.1:11434 ollama serve >"${OLLAMA_LOG}" 2>&1 &
      ;;
    *)
      echo "error: Ollama is not responding at ${OLLAMA_BASE_URL}." >&2
      echo "Start Ollama manually or set OLLAMA_BASE_URL to the reachable local URL." >&2
      exit 1
      ;;
  esac

  for _ in $(seq 1 40); do
    if curl -fsS --max-time 2 "${OLLAMA_BASE_URL}/api/tags" >/dev/null 2>&1; then
      return
    fi
    sleep 0.25
  done

  echo "error: started ollama serve, but ${OLLAMA_BASE_URL} did not become ready." >&2
  echo "ollama log: ${OLLAMA_LOG}" >&2
  exit 1
}

start_ollama_if_needed

if ! ollama show "${MODEL}" >/dev/null 2>&1; then
  echo "error: Ollama model ${MODEL} is not installed." >&2
  echo "Before going offline, run: ollama pull ${MODEL}" >&2
  exit 1
fi

cd "${REPO_ROOT}"

if [ -x ".venv/bin/uvicorn" ]; then
  UVICORN_CMD=(".venv/bin/uvicorn")
elif command -v uvicorn >/dev/null 2>&1; then
  UVICORN_CMD=("uvicorn")
else
  UVICORN_CMD=("python3" "-m" "uvicorn")
fi

echo "TERA ATAK Jetson link server"
echo "repo: ${REPO_ROOT}"
echo "ollama: ${OLLAMA_BASE_URL}"
echo "model: ${MODEL}"
echo "bind: ${HOST}:${PORT}"
echo
echo "Use the Jetson WiFi IP from one of these commands on the ATAK device:"
echo "  hostname -I"
echo "  ip -4 addr show"
echo
echo "Health URL: http://<JETSON_WIFI_IP>:${PORT}/health"
echo "Prompt URL: http://<JETSON_WIFI_IP>:${PORT}/api/prompt"
echo

export OLLAMA_BASE_URL
export OLLAMA_MODEL="${MODEL}"

exec "${UVICORN_CMD[@]}" llm_dev_kmh.app:app --host "${HOST}" --port "${PORT}"
