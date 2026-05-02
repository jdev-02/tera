#!/usr/bin/env bash
# Jetson egress firewall — P2 owns this.
# Blocks all outbound traffic except loopback and local mesh subnet.
# PRD §8.3: "egress firewall on Jetson" mitigates data exfiltration via LLM.
#
# Run as root on Jetson Orin Nano BEFORE demo:
#   sudo bash infra/jetson_firewall.sh enable
#
# To restore full connectivity:
#   sudo bash infra/jetson_firewall.sh disable

set -euo pipefail

MESH_SUBNET="${MESH_SUBNET:-192.168.1.0/24}"   # adjust to actual mesh subnet
LOOPBACK="lo"

enable_firewall() {
    echo "[firewall] Enabling egress lockdown..."

    # Flush existing rules
    iptables -F OUTPUT 2>/dev/null || true
    iptables -F INPUT  2>/dev/null || true

    # Allow loopback (LLM ↔ agent ↔ routing ↔ ATAK bridge all use loopback)
    iptables -A OUTPUT -o "$LOOPBACK" -j ACCEPT
    iptables -A INPUT  -i "$LOOPBACK" -j ACCEPT

    # Allow established/related (responses to local-initiated connections)
    iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

    # Allow local mesh subnet (for ATAK CoT relay and mesh demo)
    iptables -A OUTPUT -d "$MESH_SUBNET" -j ACCEPT
    iptables -A INPUT  -s "$MESH_SUBNET" -j ACCEPT

    # DROP everything else outbound
    iptables -P OUTPUT DROP
    # Keep INPUT permissive (we block exfiltration, not inbound)
    iptables -P INPUT  ACCEPT

    echo "[firewall] Egress lockdown ACTIVE."
    echo "[firewall] Allowed outbound: loopback, $MESH_SUBNET"
    echo "[firewall] All other outbound: BLOCKED"
    echo ""
    echo "Verify with: iptables -L OUTPUT -v --line-numbers"
}

disable_firewall() {
    echo "[firewall] Disabling firewall (restoring connectivity)..."
    iptables -P OUTPUT ACCEPT
    iptables -P INPUT  ACCEPT
    iptables -F OUTPUT
    iptables -F INPUT
    echo "[firewall] Firewall disabled. Full connectivity restored."
}

status_firewall() {
    echo "[firewall] Current OUTPUT rules:"
    iptables -L OUTPUT -v --line-numbers
    echo ""
    echo "[firewall] Policy: $(iptables -L OUTPUT | head -1)"
}

case "${1:-status}" in
    enable)  enable_firewall ;;
    disable) disable_firewall ;;
    status)  status_firewall ;;
    *)
        echo "Usage: $0 {enable|disable|status}"
        exit 1
        ;;
esac
