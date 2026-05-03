"""Demo: unsigned CoT REJECTED, signed CoT ACCEPTED.

Pitch beat: PRD section 12, 3:00-3:30. P2 runs this during the security segment.

What judges see:
  1. Attacker injects unsigned CoT -> bridge rejects it immediately.
  2. Attacker injects tampered CoT (good sig, wrong lat/lon) -> also rejected.
  3. Jetson generates properly signed CoT -> accepted.

Runs standalone -- no ATAK device or network required.
When Ben wires atak/bridge.py, call verify_cot() from there instead.

Usage:
    python security/cot_inject_demo.py
    make inject-demo
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Allow running from repo root or from security/ directory.
sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto.cot_signer import CotRoute, VerificationResult, sign_cot, verify_cot
from crypto.cot_signer import embed_signature_in_cot_xml as _embed

# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------

SAMPLE_COT = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<event version="2.0" uid="TERA-DEMO-001" type="b-m-r-w"'
    ' time="2026-05-03T09:00:00Z" start="2026-05-03T09:00:00Z"'
    ' stale="2026-05-03T10:00:00Z" how="m-g">'
    '<point lat="37.7955" lon="-122.3937" hae="0" ce="9999999" le="9999999"/>'
    "<detail/></event>"
)

SAMPLE_ROUTE = CotRoute(
    uid="TERA-DEMO-001",
    lat=37.7955,
    lon=-122.3937,
    route_geojson={
        "type": "LineString",
        "coordinates": [[-122.3937, 37.7955], [-122.415, 37.803]],
    },
    rationale="Fastest covered route to Lobos Creek freshwater.",
    mission_type="search_and_rescue",
)


# ---------------------------------------------------------------------------
# Output helpers (ASCII-safe for Windows cp1252 + Linux UTF-8)
# ---------------------------------------------------------------------------

def _line(char: str = "-", width: int = 60) -> str:
    return char * width


def _print_result(label: str, r: VerificationResult, expect_valid: bool) -> bool:
    tag = "[ACCEPT]" if r.valid else "[REJECT]"
    outcome = "PASS" if r.valid == expect_valid else "*** FAIL ***"
    print(f"  {tag}  {label}")
    print(f"         reason  : {r.reason}")
    print(f"         key_id  : {r.key_id or '(none)'}")
    print(f"         outcome : {outcome}")
    print()
    return r.valid == expect_valid


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo() -> None:
    print()
    print(_line("="))
    print("  TERA -- CoT Track Injection Demo")
    print("  PRD section 12 security beat (3:00 - 3:30)")
    print(_line("="))
    print()
    print("Simulates what happens on the TAK mesh when:")
    print("  * An adversary injects an unsigned track   -> REJECT")
    print("  * An adversary tampers a signed CoT        -> REJECT")
    print("  * The Jetson emits a properly signed route -> ACCEPT")

    all_passed = True

    # ------------------------------------------------------------------
    # Scenario 1: No signature block at all
    # ------------------------------------------------------------------
    print()
    print(_line())
    print("  Scenario 1 -- Adversary injects UNSIGNED CoT")
    print(_line())
    print()
    print("Attacker sends a raw CoT message with no <wayfinder> block.")
    print("This is what every legacy device on the mesh already sends.")
    print()
    r = verify_cot(SAMPLE_COT)
    all_passed &= _print_result("unsigned CoT from legacy device / adversary", r, expect_valid=False)

    # ------------------------------------------------------------------
    # Scenario 2: Tampered CoT -- valid signature, wrong lat/lon
    # ------------------------------------------------------------------
    print(_line())
    print("  Scenario 2 -- Adversary TAMPERS a captured signed CoT")
    print(_line())
    print()
    print("Attacker intercepts a valid signed CoT and moves the destination.")
    print("(Signed payload intact -- but point coordinates changed after signing.)")
    print()
    signed_dict = sign_cot(SAMPLE_ROUTE)
    signed_xml = _embed(SAMPLE_COT, signed_dict)
    # Tamper: change point lat in the outer CoT envelope after signing
    root = ET.fromstring(signed_xml)  # safe -- we just built it
    point = root.find("point")
    assert point is not None
    point.set("lat", "99.999")  # attacker moves the destination
    tampered_xml = ET.tostring(root, encoding="unicode")
    r = verify_cot(tampered_xml)
    all_passed &= _print_result("tampered CoT (destination moved by attacker)", r, expect_valid=False)

    # ------------------------------------------------------------------
    # Scenario 3: Properly signed route from Jetson
    # ------------------------------------------------------------------
    print(_line())
    print("  Scenario 3 -- Jetson emits a properly signed route")
    print(_line())
    print()
    print("Operator runs /plan. Jetson signs with ML-DSA-65 (or Ed25519 dev fallback).")
    print("ATAK bridge verifies -> ACCEPTS -> draws blue line on operator screen.")
    print()
    signed_dict2 = sign_cot(SAMPLE_ROUTE)
    valid_xml = _embed(SAMPLE_COT, signed_dict2)
    r = verify_cot(valid_xml)
    print(f"  Algorithm : {signed_dict2['algorithm']}")
    print(f"  Key ID    : {signed_dict2['key_id']}")
    short_sig = signed_dict2['signature'][:32] + "..."
    print(f"  Sig (hex) : {short_sig}")
    print()
    all_passed &= _print_result("signed CoT from Jetson", r, expect_valid=True)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(_line("="))
    if all_passed:
        print("  RESULT: All 3 scenarios PASSED.")
        print("  Track injection is blocked. Authentic routes are accepted.")
        print("  This is the PS4 security proof for the TERA pitch.")
    else:
        print("  RESULT: One or more scenarios FAILED -- fix before demo.")
    print(_line("="))
    print()

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    demo()
