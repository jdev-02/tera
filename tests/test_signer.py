from __future__ import annotations

import base64

from crypto.ml_dsa_signer import SignedPayload


def test_signed_payload_signature_dict_matches_cot_contract() -> None:
    signed = SignedPayload(
        payload={"uid": "TERA-001"},
        signature="deadbeef",
        key_id="WF-DEV-0001",
        algorithm="ML-DSA-65",
        timestamp=1_779_000_000.0,
        payload_hash="abc123",
    )

    envelope = signed.to_signature_dict(canonicalization="c14n11")

    assert envelope == {
        "scheme": "ML-DSA-65",
        "key_id": "WF-DEV-0001",
        "signed_at": 1_779_000_000.0,
        "canonicalization": "c14n11",
        "value_b64": base64.b64encode(bytes.fromhex("deadbeef")).decode("ascii"),
        "payload_hash": "abc123",
    }


def test_signed_payload_legacy_dict_is_unchanged() -> None:
    signed = SignedPayload(
        payload={"uid": "TERA-001"},
        signature="deadbeef",
        key_id="WF-DEV-0001",
        algorithm="ML-DSA-65",
        timestamp=1_779_000_000.0,
        payload_hash="abc123",
    )

    assert signed.to_dict() == {
        "payload": {"uid": "TERA-001"},
        "signature": "deadbeef",
        "key_id": "WF-DEV-0001",
        "algorithm": "ML-DSA-65",
        "timestamp": 1_779_000_000.0,
        "payload_hash": "abc123",
    }
