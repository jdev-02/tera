"""Glue between the orchestrator's plain-English rationale and Piper TTS.

Two synthesis paths:

  synthesize_rationale_b64(text) -- the /plan default. Cadence-transforms
    a plain-English rationale, picks a voice profile (severity-aware), and
    synthesizes via the profile's Piper voice with optional radio FX.

  synthesize_explanation_b64(term) -- the on-demand explain path. Looks up
    `term` in voice.glossary (deterministic, no LLM) and synthesizes
    "<reading> stands for <full meaning>, <context>." Returns None for
    unknown terms so the operator never hears a fabricated definition.

Pure I/O wiring. Cadence transformation lives in voice.rationale; the
synth lives in voice.piper_client. This module composes them and routes
through voice.profiles for severity-aware voice selection.
"""

from __future__ import annotations

import base64
from pathlib import Path

import structlog

from voice.audio_fx import Intensity, apply_radio_fx
from voice.glossary import explain, render_explanation_text
from voice.piper_client import PiperClient, get_piper
from voice.profiles import OperatorMode, VoiceProfile, select_profile
from voice.rationale import to_operator_cadence

log = structlog.get_logger(__name__)


# Where to look for per-voice .onnx files. Same convention as piper_client.
_MODELS_DIR = Path(__file__).resolve().parent.parent / "models" / "piper"

# Per-voice client cache. Loading a Piper voice takes ~500ms, so we cache
# one client per `voice` id rather than reloading on every call.
_clients: dict[str, PiperClient] = {}


def _client_for_profile(profile: VoiceProfile) -> PiperClient:
    """Return a PiperClient configured for the profile's voice.

    Caches per-voice id. If the profile's voice .onnx isn't present on
    disk (e.g., the operator only ran `make install-voice` which downloads
    the libritts default), defers to the global singleton from get_piper()
    so we still produce audio with whatever voice IS available.
    """
    cached = _clients.get(profile.voice)
    if cached is not None:
        return cached
    candidate = PiperClient(
        model_path=_MODELS_DIR / f"{profile.voice}.onnx",
        length_scale=profile.length_scale,
    )
    if candidate.is_available():
        _clients[profile.voice] = candidate
        return candidate
    return get_piper()


def synthesize_rationale_b64(
    rationale: str,
    length_scale: float | None = None,
    radio_fx: Intensity | None = None,
    operator_mode: OperatorMode | None = None,
) -> str | None:
    """Take an English rationale, return base64-encoded WAV (or None).

    Steps:
      1. Pick a voice profile via severity-aware routing (voice.profiles).
      2. Convert the rationale to operator cadence.
      3. Synthesize via the profile's per-voice Piper client.
      4. Apply radio-comms FX (profile.fx unless overridden).
      5. Base64-encode for JSON transport.

    Args:
        rationale: plain English. Empty string returns None.
        length_scale: optional pacing override (None = profile default).
        radio_fx: explicit FX intensity override (None = profile.fx).
        operator_mode: explicit base profile (None = TERA_VOICE_PROFILE
            env var, falls back to 'comms'). Severity cue words in the
            rationale auto-elevate this base; never demote.

    Returns None if Piper isn't available (no model, package missing) so
    the caller can degrade gracefully. Never raises -- TTS is auxiliary
    to the route response.
    """
    if not rationale:
        return None

    profile = select_profile(rationale, operator_mode=operator_mode)
    client = _client_for_profile(profile)
    if not client.is_available():
        log.info("piper_unavailable", note="returning None; rationale will be text-only")
        return None

    final_length_scale = length_scale if length_scale is not None else profile.length_scale
    final_fx: Intensity = radio_fx if radio_fx is not None else profile.fx

    spoken = to_operator_cadence(rationale)
    try:
        wav_bytes = client.synthesize_wav(spoken, length_scale=final_length_scale)
    except Exception as e:  # noqa: BLE001 -- TTS failure must not fail /plan
        log.warning("piper_synth_failed", error=str(e))
        return None

    if final_fx != "clean":
        try:
            wav_bytes = apply_radio_fx(wav_bytes, intensity=final_fx)
        except Exception as e:  # noqa: BLE001 -- FX failure -> ship clean audio
            log.warning("radio_fx_failed", intensity=final_fx, error=str(e))

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
