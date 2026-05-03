#!/usr/bin/env bash
# Third proof pane for the demo: live CoT signing events from the audit log.
#
# Filters: route_signed, route_unsigned, tool_dispatch_completed
# so the judge can see each route as it is signed in real time.
#
# Used by infra/security_demo_monitors.sh (pane 3 of 3).

set -euo pipefail

AUDIT_LOG="${WAYFINDER_AUDIT_LOG:-logs/security_audit.jsonl}"
TAIL_LINES="${TAIL_LINES:-30}"
OK_COLOR="\033[32m"
WARN_COLOR="\033[33m"
RESET="\033[0m"

mkdir -p "$(dirname "$AUDIT_LOG")"
touch "$AUDIT_LOG"

echo "======================================================"
echo "  TERA — Signed CoT Events"
echo "  Watching: route_signed | route_unsigned | tool_dispatch_completed"
echo "  Log: $AUDIT_LOG"
echo "======================================================"
echo ""

colorize() {
    while IFS= read -r line; do
        if echo "$line" | grep -q '"event":"route_signed"'; then
            echo -e "${OK_COLOR}${line}${RESET}"
        elif echo "$line" | grep -q '"event":"route_unsigned"'; then
            echo -e "${WARN_COLOR}${line}${RESET}"
        else
            echo "$line"
        fi
    done
}

FILTER='select(
  .event == "route_signed" or
  .event == "route_unsigned" or
  .event == "tool_dispatch_completed" or
  .event == "security_pipeline_allowed" or
  .event == "security_pipeline_blocked"
)'

if command -v jq >/dev/null 2>&1; then
    tail -n "$TAIL_LINES" -F "$AUDIT_LOG" | jq -c "$FILTER" | colorize
else
    # fallback: grep for the key events without jq
    tail -n "$TAIL_LINES" -F "$AUDIT_LOG" \
      | grep --line-buffered -E '"event":"(route_signed|route_unsigned|tool_dispatch_completed|security_pipeline_allowed|security_pipeline_blocked)"' \
      | colorize
fi
