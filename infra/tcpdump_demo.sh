#!/usr/bin/env bash
# Demo-day tcpdump capture — P2 owns this.
# PRD §8.4 proof point #1: "tcpdump window open on a second screen during P3 demo.
# Shows zero outbound packets while a plan is generated."
#
# Run BEFORE the demo on a second terminal / second monitor:
#   bash infra/tcpdump_demo.sh
#
# Output: live packet count + alert if ANY outbound non-loopback packet appears.

set -euo pipefail

INTERFACE="${1:-any}"           # network interface to monitor (default: all)
LOG_FILE="/tmp/wayfinder_demo_capture.pcap"
ALERT_COLOR="\033[31m"          # red
OK_COLOR="\033[32m"             # green
RESET="\033[0m"

echo "======================================================"
echo "  Wayfinder — Demo-Day Network Monitor"
echo "  Interface : $INTERFACE"
echo "  Log file  : $LOG_FILE"
echo "======================================================"
echo ""
echo "Monitoring for outbound non-loopback packets..."
echo "Expected during demo: ZERO outbound packets."
echo "Press Ctrl+C to stop."
echo ""

# Run tcpdump in background, capture to file
tcpdump -i "$INTERFACE" \
    -w "$LOG_FILE" \
    -l \
    not host 127.0.0.1 and not host ::1 &
TCPDUMP_PID=$!

trap "kill $TCPDUMP_PID 2>/dev/null; echo ''; echo 'Capture stopped. Log: $LOG_FILE'; exit 0" INT TERM

LAST_COUNT=0
OUTBOUND_DETECTED=0

while true; do
    sleep 2

    # Count captured packets
    CURRENT_COUNT=$(tcpdump -r "$LOG_FILE" 2>/dev/null | grep -c "^" || echo 0)

    DELTA=$((CURRENT_COUNT - LAST_COUNT))

    if [ "$DELTA" -gt 0 ]; then
        OUTBOUND_DETECTED=1
        echo -e "${ALERT_COLOR}[ALERT] $DELTA new outbound packet(s) detected! Total: $CURRENT_COUNT${RESET}"
    else
        echo -e "${OK_COLOR}[OK] No outbound packets. Total captured: $CURRENT_COUNT${RESET}"
    fi

    LAST_COUNT=$CURRENT_COUNT
done
