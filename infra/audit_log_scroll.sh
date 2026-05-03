#!/usr/bin/env bash
# Follow the local security audit log during the demo.

set -euo pipefail

AUDIT_LOG="${WAYFINDER_AUDIT_LOG:-logs/security_audit.jsonl}"
TAIL_LINES="${TAIL_LINES:-30}"

mkdir -p "$(diname "$AUDIT_LOG")"
touch "$AUDIT_LOG"

echo "======================================================"
echo "  TERA Security Audit Log"
echo "  File: $AUDIT_LOG"
echo "======================================================"
echo ""
echo "Waiting for structured /plan and /plan/approve events..."
echo ""

if command -v jq >/dev/null 2>&1; then
    tail -n "$TAIL_LINES" -F "$AUDIT_LOG" | jq -c .
else
    tail -n "$TAIL_LINES" -F "$AUDIT_LOG"
fi
