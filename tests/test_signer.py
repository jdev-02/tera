from __future__ import annotations

import base64
import json
import os

import pytest

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


# ---------------------------------------------------------------------------
# ADR-003 two-signature approval flow — integration tests (FallbackSigner)
# These run without liboqs. If liboqs lands on CI these tests still pass
# because FallbackSigner path is gated by _PQC_AVAILABLE.
# ---------------------------------------------------------------------------


@pytest.fixture()
def _operator_key_dir(tmp_path, monkeypatch):
    """Redirect key storage to a temp dir so tests don't pollute crypto/keys/."""
    monkeypatch.setenv("WAYFINDER_KEY_DIR", str(tmp_path))
    return tmp_path


def _make_approval_wrapper(
    *,
    route_id: str = "TERA-test-001",
    route_hash: str,
    device_sig_b64: str = "ZGV2aWNlLXNpZw==",
    operator_key_id: str = "OPERATOR-VEGA-TEST",
    approved_by: str | None = "Sgt. Vega",
    key_dir: str,
) -> tuple[dict, bytes]:
    """Build a real approval wrapper. Returns (wrapper_dict, operator_public_key_bytes).

    The caller passes operator_public_key_bytes in the trust_list when calling
    verify_approval_wrapper — same as the ATAK bridge does in production.
    """
    os.environ["WAYFINDER_KEY_DIR"] = key_dir

    # Reset the module-level singleton so it picks up the new key dir.
    import crypto.cot_signer as _cs

    _cs._signer = None

    from agent.orchestrator import _sign_operator_commit
    from agent.schemas import Signature
    from crypto.ml_dsa_signer import FallbackSigner, create_signer

    device_signature = Signature(
        scheme="ML-DSA-65",
        key_id="wayfinder-device-test",
        value_b64=device_sig_b64,
        signed_at="2026-05-02T22:30:00Z",
    )
    op_sig = _sign_operator_commit(
        route_id=route_id,
        route_hash=route_hash,
        device_signature=device_signature,
        operator_key_id=operator_key_id,
        approved_by=approved_by,
    )

    # Extract the operator's public key so the caller can build a trust_list.
    op_signer = create_signer(operator_key_id)
    op_pub_key = (
        op_signer.public_key_pem
        if isinstance(op_signer, FallbackSigner)
        else op_signer.public_key_bytes
    )

    wrapper = {
        "route_id": route_id,
        "approval_state": "operator_committed",
        "route_hash": route_hash,
        "device_signature": device_signature.model_dump(),
        "operator_signature": op_sig.model_dump(),
    }
    return wrapper, op_pub_key


def test_sign_operator_commit_real_fallback_signer(
    _operator_key_dir, monkeypatch, tmp_path
) -> None:
    """_sign_operator_commit produces a valid OperatorSignature without mocking."""
    import crypto.cot_signer as _cs

    _cs._signer = None

    from agent.orchestrator import _sign_operator_commit
    from agent.schemas import Signature

    device_sig = Signature(
        scheme="ML-DSA-65",
        key_id="wayfinder-device-001",
        value_b64="ZGV2aWNlLXNpZw==",
        signed_at="2026-05-02T22:30:00Z",
    )
    route_hash = "a" * 64  # fake sha256 hex

    op_sig = _sign_operator_commit(
        route_id="TERA-real-test",
        route_hash=route_hash,
        device_signature=device_sig,
        operator_key_id="OPERATOR-VEGA-001",
        approved_by="Sgt. Vega",
    )

    assert op_sig.key_id == "OPERATOR-VEGA-001"
    assert op_sig.approves_route_hash == route_hash
    assert op_sig.value_b64  # non-empty signature
    assert op_sig.payload_json is not None
    # payload_json must contain the approves_route_hash
    payload = json.loads(op_sig.payload_json)
    assert payload["approves_route_hash"] == route_hash
    assert payload["route_id"] == "TERA-real-test"
    assert payload["approved_by"] == "Sgt. Vega"
    # payload_hash must match sha256 of canonical payload_json bytes
    import hashlib

    computed = hashlib.sha256(op_sig.payload_json.encode("utf-8")).hexdigest()
    assert op_sig.payload_hash == computed


def test_verify_approval_wrapper_valid(_operator_key_dir, monkeypatch, tmp_path) -> None:
    """Round-trip: sign then verify the approval wrapper — should be valid."""
    import crypto.cot_signer as _cs

    _cs._signer = None

    route_hash = "b" * 64
    wrapper, op_pub_key = _make_approval_wrapper(
        route_hash=route_hash,
        key_dir=str(tmp_path),
    )
    _cs._signer = None  # force re-init with same key dir
    trust_list = {"OPERATOR-VEGA-TEST": op_pub_key}

    result = _cs.verify_approval_wrapper(wrapper, trust_list=trust_list)
    assert result.valid, f"Expected valid but got: {result.reason}"
    assert "operator-committed" in result.reason or "valid" in result.reason.lower()


def test_verify_approval_wrapper_tampered_route_hash(
    _operator_key_dir, monkeypatch, tmp_path
) -> None:
    """Replay attack: changing route_hash after signing must be rejected."""
    import crypto.cot_signer as _cs

    _cs._signer = None

    route_hash = "c" * 64
    wrapper, op_pub_key = _make_approval_wrapper(route_hash=route_hash, key_dir=str(tmp_path))

    # Attacker swaps in a different route_hash (e.g. a different route).
    wrapper["route_hash"] = "d" * 64

    _cs._signer = None
    trust_list = {"OPERATOR-VEGA-TEST": op_pub_key}
    result = _cs.verify_approval_wrapper(wrapper, trust_list=trust_list)
    assert not result.valid
    assert (
        "replay" in result.reason.lower()
        or "tamper" in result.reason.lower()
        or "REJECTED" in result.reason
    )


def test_verify_approval_wrapper_tampered_device_signature(
    _operator_key_dir, monkeypatch, tmp_path
) -> None:
    """Changing the outer device signature after approval must be rejected."""
    import crypto.cot_signer as _cs

    _cs._signer = None

    route_hash = "d" * 64
    wrapper, op_pub_key = _make_approval_wrapper(route_hash=route_hash, key_dir=str(tmp_path))

    wrapper["device_signature"]["value_b64"] = "dGFtcGVyZWQ="

    _cs._signer = None
    trust_list = {"OPERATOR-VEGA-TEST": op_pub_key}
    result = _cs.verify_approval_wrapper(wrapper, trust_list=trust_list)
    assert not result.valid
    assert "device_signature" in result.reason or "REJECTED" in result.reason


def test_verify_approval_wrapper_unknown_key(_operator_key_dir, monkeypatch, tmp_path) -> None:
    """If the operator key_id is not in the trust list, wrapper must be rejected."""
    import crypto.cot_signer as _cs

    _cs._signer = None

    route_hash = "f" * 64
    wrapper, _ = _make_approval_wrapper(route_hash=route_hash, key_dir=str(tmp_path))

    _cs._signer = None
    # Pass a trust_list that doesn't include the operator key.
    result = _cs.verify_approval_wrapper(wrapper, trust_list={"SOME-OTHER-KEY": b"pubkey"})
    assert not result.valid
    assert "trust list" in result.reason.lower() or "REJECTED" in result.reason


def test_verify_approval_wrapper_missing_operator_sig(tmp_path) -> None:
    """Wrapper without operator_signature must be rejected immediately."""
    from crypto.cot_signer import verify_approval_wrapper

    wrapper = {
        "route_id": "TERA-001",
        "route_hash": "g" * 64,
        "device_signature": {"scheme": "ML-DSA-65", "key_id": "dev"},
        # operator_signature intentionally absent
    }
    result = verify_approval_wrapper(wrapper)
    assert not result.valid
    assert "REJECTED" in result.reason
