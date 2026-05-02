"""
ML-DSA (Dilithium, NIST FIPS 204) signer and verifier.

Uses liboqs-python for post-quantum signatures.
Install: pip install liboqs-python

If liboqs is not available (e.g. Windows dev without compiled bindings),
falls back to Ed25519 (classical) so development can continue.
P2 owns this file. Do not import without checking _PQC_AVAILABLE first.

Key storage: /etc/wayfinder/keys/ on Jetson (rootfs encrypted).
For dev/demo: keys stored in ./keys/ relative to this file.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import cast

# --- Attempt to import liboqs (post-quantum) -----------------------------------
try:
    import oqs  # pip install liboqs-python

    _PQC_AVAILABLE = True
    _ALGORITHM = "Dilithium3"  # ML-DSA-65 (NIST FIPS 204 level 3)
except ImportError:
    _PQC_AVAILABLE = False

# --- Classical fallback (Ed25519 via cryptography lib) -------------------------
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        PublicFormat,
        load_pem_private_key,
        load_pem_public_key,
    )

    _CLASSICAL_AVAILABLE = True
except ImportError:
    _CLASSICAL_AVAILABLE = False

# Key directory: prefer /etc/wayfinder/keys/ (Jetson), fall back to ./keys/
_KEY_DIR = Path(os.environ.get("WAYFINDER_KEY_DIR", Path(__file__).parent / "keys"))


@dataclass
class SignedPayload:
    """Signed wrapper around any serializable payload."""

    payload: dict
    signature: str  # hex-encoded signature bytes
    key_id: str  # identifies which key signed this
    algorithm: str  # "ML-DSA-65" or "Ed25519-fallback"
    timestamp: float  # Unix epoch at signing time
    payload_hash: str  # SHA-256 of canonical payload JSON

    def to_dict(self) -> dict:
        return {
            "payload": self.payload,
            "signature": self.signature,
            "key_id": self.key_id,
            "algorithm": self.algorithm,
            "timestamp": self.timestamp,
            "payload_hash": self.payload_hash,
        }

    def to_signature_dict(self, canonicalization: str = "payload-json-v1") -> dict:
        """
        Return the signature envelope shape expected by docs/contracts/cot_signed.md.

        The legacy `to_dict()` method remains intentionally unchanged because
        existing verification code consumes its internal field names.
        """
        return {
            "scheme": self.algorithm,
            "key_id": self.key_id,
            "signed_at": self.timestamp,
            "canonicalization": canonicalization,
            "value_b64": base64.b64encode(bytes.fromhex(self.signature)).decode("ascii"),
            "payload_hash": self.payload_hash,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SignedPayload:
        return cls(**d)


def _canonical_json(obj: dict) -> bytes:
    """Deterministic JSON serialization for signing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# -------------------------------------------------------------------------------
# PQC path (liboqs ML-DSA)
# -------------------------------------------------------------------------------


class MLDSASigner:
    """ML-DSA-65 (Dilithium3) signer — NIST FIPS 204."""

    def __init__(self, key_id: str = "device-001"):
        if not _PQC_AVAILABLE:
            raise RuntimeError(
                "liboqs-python not available. pip install liboqs-python, "
                "or use FallbackSigner for development."
            )
        self.key_id = key_id
        self._key_dir = _KEY_DIR
        self._key_dir.mkdir(parents=True, exist_ok=True)
        self._sk_path = self._key_dir / f"{key_id}.dilithium3.sk"
        self._pk_path = self._key_dir / f"{key_id}.dilithium3.pk"
        self._sk: bytes | None = None
        self._pk: bytes | None = None
        self._load_or_generate()

    def _load_or_generate(self):
        if self._sk_path.exists() and self._pk_path.exists():
            self._sk = self._sk_path.read_bytes()
            self._pk = self._pk_path.read_bytes()
        else:
            with oqs.Signature(_ALGORITHM) as sig:
                self._pk = sig.generate_keypair()
                self._sk = sig.export_secret_key()
            self._sk_path.write_bytes(self._sk)
            self._pk_path.write_bytes(self._pk)
            # Restrict permissions on Jetson (POSIX only)
            with suppress(Exception):
                os.chmod(self._sk_path, 0o600)

    @property
    def public_key_bytes(self) -> bytes:
        assert self._pk is not None
        return self._pk

    def sign(self, payload: dict) -> SignedPayload:
        canonical = _canonical_json(payload)
        with oqs.Signature(_ALGORITHM, secret_key=self._sk) as sig:
            signature_bytes = sig.sign(canonical)
        return SignedPayload(
            payload=payload,
            signature=signature_bytes.hex(),
            key_id=self.key_id,
            algorithm="ML-DSA-65",
            timestamp=time.time(),
            payload_hash=_sha256(canonical),
        )

    def verify(self, signed: SignedPayload, public_key_bytes: bytes | None = None) -> bool:
        pk = public_key_bytes or self._pk
        canonical = _canonical_json(signed.payload)
        # Verify payload hash first (fast check)
        if _sha256(canonical) != signed.payload_hash:
            return False
        try:
            with oqs.Signature(_ALGORITHM) as sig:
                return sig.verify(canonical, bytes.fromhex(signed.signature), pk)
        except Exception:
            return False


# -------------------------------------------------------------------------------
# Classical fallback (Ed25519) — for dev machines without liboqs
# -------------------------------------------------------------------------------


class FallbackSigner:
    """Ed25519 fallback signer — use only in development. NOT post-quantum."""

    ALGORITHM = "Ed25519-fallback"

    def __init__(self, key_id: str = "device-001-dev"):
        if not _CLASSICAL_AVAILABLE:
            raise RuntimeError("pip install cryptography")
        self.key_id = key_id
        self._key_dir = _KEY_DIR
        self._key_dir.mkdir(parents=True, exist_ok=True)
        self._sk_path = self._key_dir / f"{key_id}.ed25519.pem"
        self._pk_path = self._key_dir / f"{key_id}.ed25519.pub.pem"
        self._sk: Ed25519PrivateKey | None = None
        self._pk: Ed25519PublicKey | None = None
        self._load_or_generate()

    def _load_or_generate(self):
        if self._sk_path.exists():
            pem = self._sk_path.read_bytes()
            self._sk = cast(Ed25519PrivateKey, load_pem_private_key(pem, password=None))
            self._pk = self._sk.public_key()
        else:
            self._sk = Ed25519PrivateKey.generate()
            self._pk = self._sk.public_key()
            self._sk_path.write_bytes(
                self._sk.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
            )
            self._pk_path.write_bytes(
                self._pk.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
            )
            with suppress(Exception):
                os.chmod(self._sk_path, 0o600)

    @property
    def public_key_pem(self) -> bytes:
        assert self._pk is not None
        return self._pk.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)

    def sign(self, payload: dict) -> SignedPayload:
        canonical = _canonical_json(payload)
        assert self._sk is not None
        sig_bytes = self._sk.sign(canonical)
        return SignedPayload(
            payload=payload,
            signature=sig_bytes.hex(),
            key_id=self.key_id,
            algorithm=self.ALGORITHM,
            timestamp=time.time(),
            payload_hash=_sha256(canonical),
        )

    def verify(self, signed: SignedPayload, public_key_pem: bytes | None = None) -> bool:
        canonical = _canonical_json(signed.payload)
        if _sha256(canonical) != signed.payload_hash:
            return False
        try:
            pk_bytes = public_key_pem or self.public_key_pem
            pk = cast(Ed25519PublicKey, load_pem_public_key(pk_bytes))
            pk.verify(bytes.fromhex(signed.signature), canonical)
            return True
        except Exception:
            return False


# -------------------------------------------------------------------------------
# Unified factory — callers use this, not the classes directly
# -------------------------------------------------------------------------------


def create_signer(key_id: str | None = None) -> MLDSASigner | FallbackSigner:
    if key_id is None:
        key_id = os.environ.get("WAYFINDER_KEY_ID", "wayfinder-device-001")
    """
    Returns ML-DSA signer if liboqs is available, Ed25519 fallback otherwise.
    Always log which mode is active.
    """
    if _PQC_AVAILABLE:
        print(f"[crypto] ML-DSA-65 signer active (liboqs) — key_id={key_id}")
        return MLDSASigner(key_id=key_id)
    print(f"[crypto] WARNING: liboqs not available — using Ed25519 fallback — key_id={key_id}")
    return FallbackSigner(key_id=key_id)


# -------------------------------------------------------------------------------
# Demo
# -------------------------------------------------------------------------------

if __name__ == "__main__":
    signer = create_signer("jetson-demo-001")

    payload = {
        "type": "route",
        "origin": {"lat": 37.7955, "lon": -122.3937},
        "destination": {"lat": 37.803, "lon": -122.415},
        "rationale": "Covered route via draw, avoiding ridgeline at GR 12345 67890.",
        "mission_type": "search_and_rescue",
    }

    print("\n--- Signing route payload ---")
    signed = signer.sign(payload)
    print(f"Algorithm : {signed.algorithm}")
    print(f"Key ID    : {signed.key_id}")
    print(f"Hash      : {signed.payload_hash}")
    print(f"Sig (hex) : {signed.signature[:32]}...")

    print("\n--- Verifying ---")
    valid = signer.verify(signed)
    print(f"Valid: {valid}")

    print("\n--- Tamper test (should fail) ---")
    tampered = SignedPayload.from_dict(signed.to_dict())
    tampered.payload["destination"]["lat"] = 99.999
    print(f"Valid after tamper: {signer.verify(tampered)}")
