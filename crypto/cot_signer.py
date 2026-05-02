"""
CoT (Cursor on Target) field signer and verifier.

P4 calls sign_cot() before emitting to ATAK.
P4 calls verify_cot() on ingest from the mesh before forwarding to ATAK.

CoT XML structure — signature block appended to <detail>:
  <detail>
    <wayfinder>
      <signature>hex...</signature>
      <key_id>...</key_id>
      <algorithm>ML-DSA-65 | Ed25519-fallback</algorithm>
      <timestamp>unix_float</timestamp>
      <payload_hash>sha256hex</payload_hash>
      <payload_json>{ ... signed payload ... }</payload_json>
    </wayfinder>
  </detail>

P2 owns this file.
P4 integration: from crypto.cot_signer import sign_cot, verify_cot, CotRoute
"""

from __future__ import annotations

import json
import math
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, cast

from defusedxml.ElementTree import fromstring as safe_xml_fromstring

try:
    from .ml_dsa_signer import create_signer, _canonical_json, _sha256
except ImportError:  # Allows `python crypto/cot_signer.py` during demos.
    from ml_dsa_signer import create_signer, _canonical_json, _sha256  # type: ignore[no-redef]

# Device key ID — read from environment, default to hostname
_KEY_ID = os.environ.get("WAYFINDER_KEY_ID", "wayfinder-device-001")

# Singleton signer — initialized once on first use
_signer = None


def _get_signer():
    global _signer
    if _signer is None:
        _signer = create_signer(_KEY_ID)
    return _signer


# -------------------------------------------------------------------------------
# Data types (P4 imports CotRoute)
# -------------------------------------------------------------------------------


@dataclass
class CotRoute:
    """Route fields that get signed before emission to ATAK."""

    uid: str  # CoT uid attribute — unique per route
    lat: float  # destination lat
    lon: float  # destination lon
    route_geojson: dict  # full route geometry (LineString)
    rationale: str  # one-line operator-visible explanation
    mission_type: str  # matches schema enum


@dataclass
class VerificationResult:
    valid: bool
    key_id: str
    algorithm: str
    reason: str


def _reject(key_id: str, algorithm: str, reason: str) -> VerificationResult:
    return VerificationResult(
        valid=False, key_id=key_id, algorithm=algorithm, reason=reason
    )


# -------------------------------------------------------------------------------
# Sign
# -------------------------------------------------------------------------------


def sign_cot(route: CotRoute) -> dict:
    """
    Signs a CotRoute and returns a dict for embedding in CoT XML <detail>.

    The full payload JSON is included so verify_cot() can do full verification
    without needing the original CotRoute object.
    """
    payload = {
        "uid": route.uid,
        "lat": route.lat,
        "lon": route.lon,
        "route_hash": _sha256(json.dumps(route.route_geojson, sort_keys=True).encode()),
        "rationale": route.rationale,
        "mission_type": route.mission_type,
    }
    signed = _get_signer().sign(payload)
    return signed.to_dict()


def _float_matches(actual: str | None, expected: Any, tolerance: float = 1e-7) -> bool:
    if actual is None:
        return False
    try:
        return math.isclose(
            float(actual), float(expected), rel_tol=0.0, abs_tol=tolerance
        )
    except (TypeError, ValueError):
        return False


def _verify_payload_matches_cot_envelope(
    root: ET.Element,
    payload: dict,
    key_id: str,
    algorithm: str,
) -> VerificationResult | None:
    """
    The signature covers payload_json; this check binds that signed payload to
    the actual CoT fields ATAK will render.
    """
    event_uid = root.get("uid")
    payload_uid = payload.get("uid")
    if event_uid != payload_uid:
        return _reject(
            key_id,
            algorithm,
            f"CoT uid mismatch: event uid={event_uid!r}, signed uid={payload_uid!r}",
        )

    point = root.find("point")
    if point is None:
        return _reject(key_id, algorithm, "Missing <point> element - CoT REJECTED")

    if not _float_matches(point.get("lat"), payload.get("lat")):
        return _reject(
            key_id,
            algorithm,
            "CoT point latitude does not match signed payload - CoT REJECTED",
        )

    if not _float_matches(point.get("lon"), payload.get("lon")):
        return _reject(
            key_id,
            algorithm,
            "CoT point longitude does not match signed payload - CoT REJECTED",
        )

    return None


def embed_signature_in_cot_xml(cot_xml: str, signed_dict: dict) -> str:
    """
    Injects the full signature block (including payload_json) into CoT XML.
    P4 calls this before sending CoT to ATAK or the mesh.
    """
    root = safe_xml_fromstring(cot_xml)

    detail = root.find("detail")
    if detail is None:
        detail = ET.SubElement(root, "detail")

    # Remove any existing wayfinder block (prevents double-signing)
    for old in detail.findall("wayfinder"):
        detail.remove(old)

    wayfinder = ET.SubElement(detail, "wayfinder")
    ET.SubElement(wayfinder, "signature").text = signed_dict["signature"]
    ET.SubElement(wayfinder, "key_id").text = signed_dict["key_id"]
    ET.SubElement(wayfinder, "algorithm").text = signed_dict["algorithm"]
    ET.SubElement(wayfinder, "timestamp").text = str(signed_dict["timestamp"])
    ET.SubElement(wayfinder, "payload_hash").text = signed_dict["payload_hash"]
    # Full payload JSON — enables complete signature verification on receive
    ET.SubElement(wayfinder, "payload_json").text = json.dumps(
        signed_dict["payload"], sort_keys=True, separators=(",", ":")
    )

    return ET.tostring(root, encoding="unicode")


# -------------------------------------------------------------------------------
# Verify
# -------------------------------------------------------------------------------


def verify_cot(
    cot_xml: str, trust_list: dict[str, bytes] | None = None
) -> VerificationResult:
    """
    Extracts and fully verifies the ML-DSA (or Ed25519) signature from a CoT XML.

    Verification steps:
      1. <wayfinder> block must be present
      2. key_id must be in trust_list (if provided)
      3. payload_json must hash to payload_hash (tamper check)
      4. Signature must verify over canonical payload_json bytes

    P4: reject the CoT and do NOT forward to ATAK if valid=False.
    """
    try:
        root = safe_xml_fromstring(cot_xml)
        wayfinder = root.find(".//wayfinder")

        if wayfinder is None:
            return VerificationResult(
                valid=False,
                key_id="",
                algorithm="",
                reason="No <wayfinder> block — unsigned CoT REJECTED",
            )

        sig_hex = wayfinder.findtext("signature", "")
        key_id = wayfinder.findtext("key_id", "")
        algorithm = wayfinder.findtext("algorithm", "")
        _timestamp = float(wayfinder.findtext("timestamp", "0"))
        payload_hash = wayfinder.findtext("payload_hash", "")
        payload_json = wayfinder.findtext("payload_json", "")

        if not sig_hex or not key_id or not payload_hash or not payload_json:
            return VerificationResult(
                valid=False,
                key_id=key_id,
                algorithm=algorithm,
                reason="Incomplete signature block — CoT REJECTED",
            )

        # Step 1: Trust list check
        pub_key = None
        if trust_list is not None:
            pub_key = trust_list.get(key_id)
            if pub_key is None:
                return VerificationResult(
                    valid=False,
                    key_id=key_id,
                    algorithm=algorithm,
                    reason=f"key_id '{key_id}' not in trust list — CoT REJECTED",
                )

        # Step 2: Payload hash integrity check (fast, no crypto)
        payload_dict = json.loads(payload_json)
        canonical_bytes = _canonical_json(payload_dict)
        computed_hash = _sha256(canonical_bytes)
        if computed_hash != payload_hash:
            return VerificationResult(
                valid=False,
                key_id=key_id,
                algorithm=algorithm,
                reason="Payload hash mismatch — payload tampered — CoT REJECTED",
            )

        envelope_error = _verify_payload_matches_cot_envelope(
            root=root,
            payload=payload_dict,
            key_id=key_id,
            algorithm=algorithm,
        )
        if envelope_error is not None:
            return envelope_error

        # Step 4: Full signature verification over canonical payload bytes.
        signer = _get_signer()

        if algorithm == "Ed25519-fallback":
            # Ed25519 verification
            from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                Ed25519PublicKey,
            )
            from cryptography.hazmat.primitives.serialization import load_pem_public_key

            pk = (
                cast(Ed25519PublicKey, load_pem_public_key(pub_key))
                if pub_key
                else cast(Ed25519PublicKey, signer._pk)
            )
            try:
                pk.verify(bytes.fromhex(sig_hex), canonical_bytes)
                ok = True
            except Exception:
                ok = False
        else:
            # ML-DSA-65 verification
            try:
                import oqs

                pk_bytes = pub_key if pub_key else signer.public_key_bytes
                with oqs.Signature("Dilithium3") as s:
                    ok = s.verify(canonical_bytes, bytes.fromhex(sig_hex), pk_bytes)
            except Exception as e:
                return VerificationResult(
                    valid=False,
                    key_id=key_id,
                    algorithm=algorithm,
                    reason=f"ML-DSA verification error: {e}",
                )

        if ok:
            return VerificationResult(
                valid=True,
                key_id=key_id,
                algorithm=algorithm,
                reason="Signature valid — route is authentic",
            )
        return VerificationResult(
            valid=False,
            key_id=key_id,
            algorithm=algorithm,
            reason="Signature invalid — route REJECTED",
        )

    except ET.ParseError as e:
        return VerificationResult(
            valid=False, key_id="", algorithm="", reason=f"CoT XML parse error: {e}"
        )
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        return VerificationResult(
            valid=False,
            key_id="",
            algorithm="",
            reason=f"CoT signature parse error: {e}",
        )


# -------------------------------------------------------------------------------
# Trust list management
# -------------------------------------------------------------------------------


def load_trust_list(path: str = "crypto/keys/trust_list.json") -> dict[str, bytes]:
    """
    Loads {key_id: public_key_hex} from a flat JSON file.
    Replace with CRL-backed distribution post-hackathon (PRD §8.5).
    """
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    return {k: bytes.fromhex(v) for k, v in data.items()}


def export_public_key_to_trust_list(
    signer_instance=None, path: str = "crypto/keys/trust_list.json"
):
    """Exports this device's public key to the trust list JSON file."""
    from pathlib import Path

    try:
        from .ml_dsa_signer import FallbackSigner, MLDSASigner
    except ImportError:
        from ml_dsa_signer import FallbackSigner, MLDSASigner  # type: ignore[no-redef]

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    s = signer_instance or _get_signer()
    existing = json.loads(p.read_text()) if p.exists() else {}

    if isinstance(s, MLDSASigner):
        pk_hex = s.public_key_bytes.hex()
    elif isinstance(s, FallbackSigner):
        pk_hex = s.public_key_pem.hex()
    else:
        raise TypeError("Unknown signer type")

    existing[s.key_id] = pk_hex
    p.write_text(json.dumps(existing, indent=2))
    print(f"[trust_list] Exported public key: {s.key_id} -> {path}")


# -------------------------------------------------------------------------------
# Smoke test (python crypto/cot_signer.py)
# -------------------------------------------------------------------------------

if __name__ == "__main__":
    sample_cot = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<event version="2.0" uid="WAYFINDER-001" type="b-m-r-w"'
        ' time="2026-05-02T12:00:00Z" start="2026-05-02T12:00:00Z"'
        ' stale="2026-05-02T13:00:00Z" how="m-g">'
        '<point lat="37.7955" lon="-122.3937" hae="0" ce="9999999" le="9999999"/>'
        "<detail/></event>"
    )

    route = CotRoute(
        uid="WAYFINDER-001",
        lat=37.7955,
        lon=-122.3937,
        route_geojson={
            "type": "LineString",
            "coordinates": [[-122.3937, 37.7955], [-122.415, 37.803]],
        },
        rationale="Fastest covered route to freshwater via draw.",
        mission_type="search_and_rescue",
    )

    print("--- Signing ---")
    signed_dict = sign_cot(route)
    print(f"Algorithm : {signed_dict['algorithm']}")
    print(f"Key ID    : {signed_dict['key_id']}")

    print("\n--- Embed + Verify (should be VALID) ---")
    signed_xml = embed_signature_in_cot_xml(sample_cot, signed_dict)
    r = verify_cot(signed_xml)
    print(f"valid={r.valid}  reason={r.reason}")

    print("\n--- Unsigned CoT (should be REJECTED) ---")
    r2 = verify_cot(sample_cot)
    print(f"valid={r2.valid}  reason={r2.reason}")

    print("\n--- Tampered CoT envelope (should be REJECTED) ---")
    tampered_root = safe_xml_fromstring(signed_xml)
    tampered_point = tampered_root.find("point")
    if tampered_point is not None:
        tampered_point.set("lat", "99.999")
    tampered = ET.tostring(tampered_root, encoding="unicode")
    r3 = verify_cot(tampered)
    print(f"valid={r3.valid}  reason={r3.reason}")
