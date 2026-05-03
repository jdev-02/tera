#!/usr/bin/env bash
# Open the three security proof monitors required by issue #15.
#
# Pane 1: tcpdump  — proves zero outbound packets (PRD §8.4 proof point 1)
# Pane 2: audit    — structured log of every pipeline step (proof point 4)
# Pane 3: CoT sign — live route_signed / route_unsigned events (proof point 3)

set -euo pipefail

INTERFACE="${1:-${WAYFINDER_TCPDUMP_INTERFACE:-any}}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TCPDUMP_CMD="cd '$ROOT_DIR' && sudo bash infra/tcpdump_demo.sh '$INTERFACE'"
AUDIT_CMD="cd '$ROOT_DIR' && bash infra/audit_log_scroll.sh"
COT_CMD="cd '$ROOT_DIR' && bash infra/cot_signed_scroll.sh"
SESSION_NAME="${WAYFINDER_DEMO_SESSION:-tera-security-demo}"

if command -v tmux >/dev/null 2>&1; then
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        tmux kill-session -t "$SESSION_NAME"
    fi
    tmux new-session -d -s "$SESSION_NAME" "$TCPDUMP_CMD"
    tmux split-window -v -t "$SESSION_NAME" "$AUDIT_CMD"
    tmux split-window -v -t "$SESSION_NAME" "$COT_CMD"
    tmux select-layout -t "$SESSION_NAME" even-vertical >/dev/null
    tmux attach-session -t "$SESSION_NAME"
    exit 0
fi

if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal -- bash -lc "$TCPDUMP_CMD; exec bash"
    gnome-terminal -- bash -lc "$AUDIT_CMD; exec bash"
    gnome-terminal -- bash -lc "$COT_CMD; exec bash"
    exit 0
fi

if command -v x-terminal-emulator >/dev/null 2>&1; then
    x-terminal-emulator -e bash -lc "$TCPDUMP_CMD; exec bash" &
    x-terminal-emulator -e bash -lc "$AUDIT_CMD; exec bash" &
    x-terminal-emulator -e bash -lc "$COT_CMD; exec bash" &
    exit 0
fi

cat <<EOF
No tmux or supported terminal emulator found.

Open three terminals manually:

  Terminal A (tcpdump — zero outbound proof):
    $TCPDUMP_CMD

  Terminal B (audit log — pipeline events):
    $AUDIT_CMD

  Terminal C (signed CoT events):
    $COT_CMD
EOF
exit 1
