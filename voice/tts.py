"""Glue between the orchestrator's plain-English rationale and Piper TTS.

The orchestrator calls `synthesize_rationale_b64(rationale)` to get a
base64-encoded WAV ready to embed in PlanResponse. Returns None if Piper
is unavailable -- caller treats that as a degraded but valid response.

Pure I/O wiring. Cadence transformation lives in voice.rationale; the
synth lives in voice.piper_client. This module just composes them.
"""

from __future__ import annotations

import base64

import structlog

from voice.piper_client import get_piper
from voice.rationale import to_operator_cadence

log = structlog.get_logger(__name__)


def synthesize_rationale_b64(rationale: str) -> str | None:
    """Take an English rationale, return base64-encoded WAV (or None).

    Steps:
      1. Convert to operator cadence.
      2. Synthesize via Piper.
      3. Base64-encode for JSON transport.

    Returns None if Piper isn't available (no model, package missing) so
    the caller can degrade gracefully. Never raises -- TTS is auxiliary
    to the route response.
    """
    if not rationale:
        return None

    client = get_piper()
    if not client.is_available():
        log.info("piper_unavailable", note="returning None; rationale will be text-only")
        return None

    spoken = to_operator_cadence(rationale)
    try:
        wav_bytes = client.synthesize_wav(spoken)
    except Exception as e:  # noqa: BLE001 -- TTS failure must not fail /plan
        log.warning("piper_synth_failed", error=str(e))
        return None

    return base64.b64encode(wav_bytes).decode("ascii")
