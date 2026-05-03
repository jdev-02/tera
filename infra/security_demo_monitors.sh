#!/usr/bin/env bash
# Open the three security proof monitors required by issue #15.
#
# Pane 1: tcpdump  - proves zero outbound packets (PRD 8.4 proof point 1)
# Pane 2: audit    - structured log of every pipeline step (proof point 4)
# Pane 3: CoT sign - live route_signed / route_unsigned events (proof point 3)

set -euo pipefail

INTERFACE="${1:-${WAYFINDER_TCPDUMP_INTERFACE:-any}}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_OS="$(uname -s 2>/dev/null || echo unknown)"
if [[ "$HOST_OS" == MINGW* || "$HOST_OS" == MSYS* || "$HOST_OS" == CYGWIN* ]]; then
    TCPDUMP_CMD="cd '$ROOT_DIR' && bash infra/tcpdump_demo.sh '$INTERFACE'"
elif command -v sudo >/dev/null 2>&1; then
    TCPDUMP_CMD="cd '$ROOT_DIR' && sudo bash infra/tcpdump_demo.sh '$INTERFACE'"
else
    TCPDUMP_CMD="cd '$ROOT_DIR' && bash infra/tcpdump_demo.sh '$INTERFACE'"
fi
AUDIT_CMD="cd '$ROOT_DIR' && bash infra/audit_log_scroll.sh"
COT_CMD="cd '$ROOT_DIR' && bash infra/cot_signed_scroll.sh"
SESSION_NAME="${WAYFINDER_DEMO_SESSION:-tera-security-demo}"
HOLD_CMD='echo; echo "[demo-proofs] Window finished. Press Enter to close."; read -r _'

print_manual_commands() {
    cat <<EOF
Open three terminals manually:

  Terminal A (tcpdump - zero outbound proof):
    $TCPDUMP_CMD

  Terminal B (audit log - pipeline events):
    $AUDIT_CMD

  Terminal C (signed CoT events):
    $COT_CMD
EOF
}

if [ "${WAYFINDER_DEMO_DRY_RUN:-0}" = "1" ]; then
    echo "[demo-proofs] Dry run only; no terminal windows opened."
    echo ""
    print_manual_commands
    exit 0
fi

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

if command -v mintty >/dev/null 2>&1; then
    mintty --title "TERA tcpdump - zero outbound proof" bash -lc "$TCPDUMP_CMD; $HOLD_CMD" &
    mintty --title "TERA audit log - pipeline events" bash -lc "$AUDIT_CMD; $HOLD_CMD" &
    mintty --title "TERA signed CoT events" bash -lc "$COT_CMD; $HOLD_CMD" &
    echo "[demo-proofs] Opened three Git Bash windows via mintty."
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

echo "No tmux or supported terminal emulator found."
echo ""
print_manual_commands
exit 0
