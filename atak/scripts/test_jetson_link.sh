#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  atak/scripts/test_jetson_link.sh <JETSON_IP> [PORT]

Environment overrides:
  OLLAMA_MODEL              Model name sent to the Jetson. Default: gemma3:4b
  TERA_ATAK_TEST_PROMPT     Prompt sent to /api/prompt.
  TERA_ATAK_CONNECT_S       TCP connect timeout. Default: 5
  TERA_ATAK_TIMEOUT_S       Full prompt timeout. Default: 180

Example:
  atak/scripts/test_jetson_link.sh 192.168.1.42 8080
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

if [ "$#" -lt 1 ]; then
  usage >&2
  exit 2
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "error: curl is required. On Android, install Termux and run: pkg install curl" >&2
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "error: python is required for JSON escaping." >&2
  echo "On Android Termux, run: pkg install python" >&2
  exit 1
fi

JETSON_IP="$1"
PORT="${2:-8080}"
MODEL="${OLLAMA_MODEL:-gemma3:4b}"
CONNECT_TIMEOUT="${TERA_ATAK_CONNECT_S:-5}"
REQUEST_TIMEOUT="${TERA_ATAK_TIMEOUT_S:-180}"
PROMPT="${TERA_ATAK_TEST_PROMPT:-TERA ATAK link test. Reply with JSON containing status, model, and one short readiness sentence.}"

BASE_URL="http://${JETSON_IP}:${PORT}"
HEALTH_URL="${BASE_URL}/health"
PROMPT_URL="${BASE_URL}/api/prompt"

if ! curl -fsS --connect-timeout "${CONNECT_TIMEOUT}" --max-time 10 "${HEALTH_URL}" >/dev/null; then
  echo "FAIL: could not reach Jetson health endpoint: ${HEALTH_URL}" >&2
  echo "Check same WiFi, Jetson IP, firewall, and that uvicorn is bound to 0.0.0.0." >&2
  exit 1
fi

BODY="$(printf '{"prompt":%s,"model":%s,"llm_provider":"ollama","agent_profile":"tera-atak-link-test"}' \
  "$(printf '%s' "${PROMPT}" | "${PYTHON_BIN}" -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" \
  "$(printf '%s' "${MODEL}" | "${PYTHON_BIN}" -c 'import json,sys; print(json.dumps(sys.stdin.read()))')")"

TMP_RESPONSE="$(mktemp)"
trap 'rm -f "${TMP_RESPONSE}"' EXIT

HTTP_CODE="$(
  curl -sS \
    --connect-timeout "${CONNECT_TIMEOUT}" \
    --max-time "${REQUEST_TIMEOUT}" \
    -o "${TMP_RESPONSE}" \
    -w "%{http_code}" \
    -X POST "${PROMPT_URL}" \
    -H "Content-Type: application/json" \
    -d "${BODY}"
)"

if [ "${HTTP_CODE}" != "200" ]; then
  echo "FAIL: Jetson prompt endpoint returned HTTP ${HTTP_CODE}: ${PROMPT_URL}" >&2
  cat "${TMP_RESPONSE}" >&2
  echo >&2
  exit 1
fi

if ! grep -q '"response"' "${TMP_RESPONSE}"; then
  echo "FAIL: Jetson returned HTTP 200 but no response field." >&2
  cat "${TMP_RESPONSE}" >&2
  echo >&2
  exit 1
fi

echo "SUCCESS: TERA ATAK link reached Jetson Gemma endpoint."
echo "health: ${HEALTH_URL}"
echo "prompt: ${PROMPT_URL}"
echo "model: ${MODEL}"
echo
cat "${TMP_RESPONSE}"
echo
