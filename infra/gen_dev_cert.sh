#!/usr/bin/env bash
# Generate a self-signed TLS cert for local HTTPS development.
# Run once before `make run-https`. Cert is gitignored (certs/).
#
# Usage:
#   bash infra/gen_dev_cert.sh
#   make gen-cert

set -euo pipefail

CERT_DIR="$(git rev-parse --show-toplevel)/certs"
KEY="$CERT_DIR/key.pem"
CERT="$CERT_DIR/cert.pem"

mkdir -p "$CERT_DIR"

if [[ -f "$KEY" && -f "$CERT" ]]; then
    echo "[cert] Already exists: $CERT"
    echo "[cert] Delete certs/ and re-run to regenerate."
    exit 0
fi

openssl req -x509 -newkey rsa:2048 \
    -keyout "$KEY" -out "$CERT" \
    -days 365 -nodes \
    -subj "/CN=localhost" \
    -addext "subjectAltName=IP:127.0.0.1,DNS:localhost" 2>/dev/null

echo ""
echo "[cert] Generated: $CERT"
echo "[cert] Key:       $KEY"
echo "[cert] Valid for: 365 days (localhost + 127.0.0.1)"
echo ""
echo "[cert] Run server: make run-https"
echo "[cert] NOTE: Browser will show 'Not secure' warning -- click Advanced -> Proceed."
echo "[cert]       This is expected for self-signed certs on localhost."
echo ""
