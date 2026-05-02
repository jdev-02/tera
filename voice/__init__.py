"""TERA voice path: Whisper-tiny (in) + Piper TTS (out).

This package converts the orchestrator's plain-English rationale into
operator-cadence speech, then synthesizes audio via Piper TTS for
hands-free output to the operator's headset (PRD §6 hero scenario).
"""

from voice.piper_client import PiperClient, get_piper, reset_piper
from voice.rationale import to_operator_cadence
from voice.tts import synthesize_rationale_b64

__all__ = [
    "PiperClient",
    "get_piper",
    "reset_piper",
    "synthesize_rationale_b64",
    "to_operator_cadence",
]
