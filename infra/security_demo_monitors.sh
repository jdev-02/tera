#!/usr/bin/env bash
# Open the two security proof monitors required by issue #15.

set -euo pipefail

INTERFACE="${1:-${WAYFINDER_TCPDUMP_INTERFACE:-any}}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TCPDUMP_CMD="cd '$ROOT_DIR' && sudo bash infra/tcpdump_demo.sh '$INTERFACE'"
AUDIT_CMD="cd '$ROOT_DIR' && bash infra/audit_log_scroll.sh"
SESSION_NAME="${WAYFINDER_DEMO_SESSION:-tera-security-demo}"

if command -v tmux >/dev/null 2>&1; then
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        tmux kill-session -t "$SESSION_NAME"
    fi
    tmux new-session -d -s "$SESSION_NAME" "$TCPDUMP_CMD"
    tmux split-window -v -t "$SESSION_NAME" "$AUDIT_CMD"
    tmux select-layout -t "$SESSION_NAME" even-vertical >/dev/null
    tmux attach-session -t "$SESSION_NAME"
    exit 0
fi

if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal -- bash -lc "$TCPDUMP_CMD; exec bash"
    gnome-terminal -- bash -lc "$AUDIT_CMD; exec bash"
    exit 0
fi

if command -v x-terminal-emulator >/dev/null 2>&1; then
    x-terminal-emulator -e bash -lc "$TCPDUMP_CMD; exec bash" &
    x-terminal-emulator -e bash -lc "$AUDIT_CMD; exec bash" &
    exit 0
fi

cat <<EOF
No tmux or supported terminal emulator found.

Open two terminals manually:

  Terminal A:
    $TCPDUMP_CMD

  Terminal B:
    $AUDIT_CMD
EOF
exit 1
