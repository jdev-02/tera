"""Glue between the orchestrator's plain-English rationale and Piper TTS.

Two synthesis paths:

  synthesize_rationale_b64(text) -- the /plan default. Cadence-transforms
    a plain-English rationale and synthesizes it. Used in every plan
    response when ?tts=true.

  synthesize_explanation_b64(term) -- the on-demand explain path. Looks up
    `term` in voice.glossary (deterministic, no LLM) and synthesizes
    "<reading> stands for <full meaning>, <context>." Returns None for
    unknown terms so the operator never hears a fabricated definition.

Pure I/O wiring. Cadence transformation lives in voice.rationale; the
synth lives in voice.piper_client. This module just composes them.
"""

from __future__ import annotations

import base64

import structlog

from voice.glossary import explain, render_explanation_text
from voice.piper_client import get_piper
from voice.rationale import to_operator_cadence

log = structlog.get_logger(__name__)


def synthesize_rationale_b64(rationale: str, length_scale: float | None = None) -> str | None:
    """Take an English rationale, return base64-encoded WAV (or None).

    Steps:
      1. Convert to operator cadence.
      2. Synthesize via Piper.
      3. Base64-encode for JSON transport.

    Args:
        rationale: plain English. Empty string returns None.
        length_scale: optional pacing override (1.0 = default, 1.15 = ops
                      cadence, 1.3 = slow). None uses the client default.

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
        wav_bytes = client.synthesize_wav(spoken, length_scale=length_scale)
    except Exception as e:  # noqa: BLE001 -- TTS failure must not fail /plan
        log.warning("piper_synth_failed", error=str(e))
        return None

    return base64.b64encode(wav_bytes).decode("ascii")


def synthesize_explanation_b64(
    term: str, length_scale: float | None = None
) -> dict[str, str] | None:
    """Synthesize a deterministic spoken explanation of an acronym.

    Looks up `term` in voice.glossary (case-insensitive). If known, returns
    `{"term": <canonical key>, "text": <spoken text>, "audio_b64": <wav>}`.
    If unknown, returns None and logs `glossary_term_unknown` -- caller can
    play a 'term not recognized' clip or surface that to the operator.

    Why this is safer than asking the LLM to define the acronym:
      - Deterministic: same input always yields same output.
      - Auditable: the definition lives in a versioned source file.
      - No fabrication risk: unknown terms don't get plausibly-wrong defs.

    Args:
        term: the acronym the operator wants explained (e.g. "HLZ").
        length_scale: optional pacing override (None = client default).
    """
    entry = explain(term)
    if entry is None:
        log.info("glossary_term_unknown", term=term)
        return None

    spoken_text = render_explanation_text(entry)

    client = get_piper()
    if not client.is_available():
        log.info("piper_unavailable", note="explain returns text without audio")
        return {
            "term": term.strip().upper(),
            "text": spoken_text,
            "audio_b64": "",
        }

    try:
        wav_bytes = client.synthesize_wav(spoken_text, length_scale=length_scale)
    except Exception as e:  # noqa: BLE001 -- never fail the explain path
        log.warning("piper_explain_synth_failed", error=str(e))
        return {
            "term": term.strip().upper(),
            "text": spoken_text,
            "audio_b64": "",
        }

    return {
        "term": term.strip().upper(),
        "text": spoken_text,
        "audio_b64": base64.b64encode(wav_bytes).decode("ascii"),
    }
