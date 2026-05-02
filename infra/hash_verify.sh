#!/usr/bin/env bash
# Model + map data hash verification — PRD §8.4 proof point #3.
# Run before demo to print sha256 of model and map files.
# Matches value on the printed card the judge can verify.
#
# Usage: bash infra/hash_verify.sh

set -euo pipefail

echo "======================================================"
echo "  Wayfinder — Pre-flight Hash Verification"
echo "======================================================"

PASS=0
FAIL=0

check_file() {
    local label="$1"
    local path="$2"
    if [ -f "$path" ]; then
        HASH=$(sha256sum "$path" | awk '{print $1}')
        echo "  [OK] $label"
        echo "       $HASH"
        echo "       $path"
        PASS=$((PASS + 1))
    else
        echo "  [MISSING] $label — $path"
        FAIL=$((FAIL + 1))
    fi
    echo ""
}

echo ""
echo "--- LLM Model ---"
check_file "Gemma model weights" "${GEMMA_MODEL_PATH:-models/gemma-2b-q4_k_m.gguf}"

echo "--- Map Data ---"
check_file "SF OSM extract"     "${SF_OSM_PATH:-data/sf_extract.osm.pbf}"
check_file "Austere AO extract" "${AO_OSM_PATH:-data/ao_extract.osm.pbf}"
check_file "DEM tiles (SF)"     "${SF_DEM_PATH:-data/sf_dem.tif}"
check_file "DEM tiles (AO)"     "${AO_DEM_PATH:-data/ao_dem.tif}"

echo "--- Crypto Keys ---"
check_file "Device public key"  "crypto/keys/jetson-demo-001.dilithium3.pk"
check_file "Trust list"         "crypto/keys/trust_list.json"

echo "======================================================"
echo "  Results: $PASS OK, $FAIL MISSING"
echo "======================================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
