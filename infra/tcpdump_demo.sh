#!/usr/bin/env bash
# Demo-day tcpdump capture. P2 owns this proof.
#
# Run before the /plan demo:
#   sudo bash infra/tcpdump_demo.sh any
#
# The monitor captures real outbound, non-loopback traffic and stores both a
# pcap and a text log under logs/security_demo/ for the judges or after-action
# review.

set -euo pipefail

INTERFACE="${1:-${WAYFINDER_TCPDUMP_INTERFACE:-any}}"
CAPTURE_DIR="${WAYFINDER_CAPTURE_DIR:-logs/security_demo}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
PCAP_FILE="${CAPTURE_DIR}/no_outbound_${STAMP}.pcap"
TEXT_LOG="${CAPTURE_DIR}/no_outbound_${STAMP}.log"
SUMMARY_LOG="${CAPTURE_DIR}/no_outbound_summary.jsonl"
ALERT_COLOR="\033[31m"
OK_COLOR="\033[32m"
WARN_COLOR="\033[33m"
RESET="\033[0m"

if ! command -v tcpdump >/dev/null 2>&1; then
    echo "ERROR: tcpdump is not installed. Install tcpdump on the demo host." >&2
    exit 127
fi

mkdir -p "$CAPTURE_DIR"
touch "$TEXT_LOG" "$SUMMARY_LOG"

# The firewall already blocks egress in the hero demo. The capture filter is a
# second proof surface: it ignores loopback and TAK multicast so local runtime
# traffic does not obscure external outbound attempts.
BPF_FILTER="${WAYFINDER_TCPDUMP_FILTER:-not (host 127.0.0.1 or host ::1 or dst net 224.0.0.0/4 or dst host 239.2.3.1)}"
DIRECTION_ARGS=()
if tcpdump -h 2>&1 | grep -q -- "-Q "; then
    DIRECTION_ARGS=(-Q out)
else
    echo -e "${WARN_COLOR}[WARN] tcpdump does not advertise -Q; capture may include inbound packets.${RESET}"
fi

echo "======================================================"
echo "  TERA Demo Network Monitor"
echo "  Interface : $INTERFACE"
echo "  Filter    : $BPF_FILTER"
echo "  Pcap      : $PCAP_FILE"
echo "  Text log  : $TEXT_LOG"
echo "======================================================"
echo ""
echo "Monitoring for outbound non-loopback/non-TAK-multicast packets."
echo "Expected during Phase 3 /plan demo: ZERO packets."
echo "Press Ctrl+C to stop."
echo ""

tcpdump -i "$INTERFACE" "${DIRECTION_ARGS[@]}" -nn -U -w "$PCAP_FILE" "$BPF_FILTER" >/dev/null 2>>"$TEXT_LOG" &
TCPDUMP_PID=$!
sleep 1
if ! kill -0 "$TCPDUMP_PID" 2>/dev/null; then
    echo "ERROR: tcpdump failed to start. Details:" >&2
    tail -n 20 "$TEXT_LOG" >&2 || true
    exit 1
fi

cleanup() {
    kill "$TCPDUMP_PID" 2>/dev/null || true
    wait "$TCPDUMP_PID" 2>/dev/null || true
    echo ""
    echo "Capture stopped."
    echo "Pcap: $PCAP_FILE"
    echo "Text: $TEXT_LOG"
    exit 0
}
trap cleanup INT TERM

LAST_COUNT=0

while true; do
    sleep 2

    CURRENT_COUNT="$(tcpdump -nn -r "$PCAP_FILE" 2>/dev/null | tee "$TEXT_LOG.tmp" | grep -c "^" || true)"
    mv "$TEXT_LOG.tmp" "$TEXT_LOG"

    DELTA=$((CURRENT_COUNT - LAST_COUNT))
    TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    if [ "$DELTA" -gt 0 ]; then
        echo -e "${ALERT_COLOR}[ALERT] $DELTA outbound packet(s) detected. Total: $CURRENT_COUNT${RESET}"
        printf '{"ts":"%s","event":"tcpdump_outbound_detected","delta":%s,"total":%s,"pcap":"%s"}\n' \
            "$TS" "$DELTA" "$CURRENT_COUNT" "$PCAP_FILE" >> "$SUMMARY_LOG"
    else
        echo -e "${OK_COLOR}[OK] No outbound packets. Total captured: $CURRENT_COUNT${RESET}"
        printf '{"ts":"%s","event":"tcpdump_no_outbound","delta":0,"total":%s,"pcap":"%s"}\n' \
            "$TS" "$CURRENT_COUNT" "$PCAP_FILE" >> "$SUMMARY_LOG"
    fi

    LAST_COUNT=$CURRENT_COUNT
done
