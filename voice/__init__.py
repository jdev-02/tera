"""TERA voice path: Whisper-tiny (in) + Piper TTS (out).

Converts the orchestrator's plain-English rationale into operator-cadence
speech, synthesizes audio via Piper TTS for hands-free output (PRD §6
hero scenario), and provides a deterministic glossary explain path for
on-demand acronym disambiguation.
"""

from voice.glossary import GLOSSARY, GlossaryEntry, explain, known_terms
from voice.piper_client import PiperClient, get_piper, reset_piper
from voice.rationale import to_operator_cadence
from voice.tts import synthesize_explanation_b64, synthesize_rationale_b64

__all__ = [
    "GLOSSARY",
    "GlossaryEntry",
    "PiperClient",
    "explain",
    "get_piper",
    "known_terms",
    "reset_piper",
    "synthesize_explanation_b64",
    "synthesize_rationale_b64",
    "to_operator_cadence",
]
