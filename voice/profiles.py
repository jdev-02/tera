"""Voice profiles + severity-aware routing.

Three principles:

1. **Operator picks the base mode.** Default = `comms` (operator on net,
   the demo voice). They can switch to `calm` for slower briefing-grade
   speech or pin `critical` for everything-is-urgent contexts. Set via
   the TERA_VOICE_PROFILE env var or per-request override.

2. **Severity auto-elevates, never demotes.** If the rationale contains
   critical cue words (CASEVAC, MEDEVAC, DANGER CLOSE, MASS CASUALTY,
   TROOPS IN CONTACT), the request elevates one level toward critical
   regardless of the base mode. A calm request with a CASEVAC bumps to
   comms; a comms request with a CASEVAC bumps to critical. Demotion
   is never automatic -- operator agency is one-way.

3. **Profiles are data, not code.** Adding a new profile = one entry in
   the dict. Severity-routed work that previously sprawled across
   rationale.py / tts.py / piper_client.py now lives in one file.

Profile = (voice model, FX intensity, length_scale). Each is independently
tunable. New profiles can mix-and-match.

Usage::

    from voice.profiles import select_profile, VoiceProfile

    profile = select_profile(
        rationale="CASEVAC inbound to grid 11SMS1234 5678.",
        operator_mode="calm",   # base mode
    )
    # profile.voice == 'en_US-ryan-high'
    # profile.fx == 'comms'  (auto-elevated from calm due to CASEVAC)

Env var override: TERA_VOICE_PROFILE=critical pins to critical regardless.
"""

from __future__ import annotations

import os
from typing import Literal, NamedTuple

from voice.audio_fx import Intensity

OperatorMode = Literal["calm", "comms", "critical"]
ALL_MODES: tuple[OperatorMode, ...] = ("calm", "comms", "critical")


class VoiceProfile(NamedTuple):
    """Bundle of synthesis parameters for one voice mode."""

    name: OperatorMode
    voice: str  # Piper voice id, must exist at models/piper/<voice>.onnx
    fx: Intensity  # radio post-processing intensity
    length_scale: float  # speech rate (higher = slower)


# ---------------------------------------------------------------------------
# Profile catalog -- demo defaults baked in based on Jon's listen-test
# (Sat 19:32). Voices kept consistent (ryan-high) across modes so the
# operator hears the same speaker, just with changing 'gear' and pace.
# ---------------------------------------------------------------------------

PROFILES: dict[OperatorMode, VoiceProfile] = {
    "calm": VoiceProfile(
        name="calm",
        voice="en_US-ryan-high",
        fx="clean",
        length_scale=1.20,  # briefing-grade pacing
    ),
    "comms": VoiceProfile(
        name="comms",
        voice="en_US-ryan-high",
        fx="comms",
        length_scale=1.15,  # default: ops cadence
    ),
    "critical": VoiceProfile(
        name="critical",
        voice="en_US-ryan-high",
        fx="degraded",
        length_scale=1.05,  # tighter, slightly faster -- conveys urgency
    ),
}

# The fallback if everything else is missing. PR #49 voice that always
# exists if 'make install-voice' has been run.
FALLBACK_PROFILE = VoiceProfile(
    name="comms",
    voice="en_US-libritts_r-medium",
    fx="comms",
    length_scale=1.15,
)


# ---------------------------------------------------------------------------
# Cue words that auto-elevate severity. Word-boundary anchored so we don't
# match substrings (e.g. 'contact' inside 'contracted' won't fire).
# ---------------------------------------------------------------------------

# Critical cues -> always elevate to critical regardless of base mode.
_CRITICAL_CUES: tuple[str, ...] = (
    "CASEVAC",
    "MEDEVAC",
    "DANGER CLOSE",
    "MASS CASUALTY",
    "TROOPS IN CONTACT",
)

# Urgent cues -> elevate by one step (calm -> comms, comms -> critical).
_URGENT_CUES: tuple[str, ...] = (
    "BREAK",
    "BE ADVISED",
    "CONTACT FRONT",
    "CONTACT REAR",
    "CONTACT LEFT",
    "CONTACT RIGHT",
)


def detect_severity_bump(text: str) -> int:
    """Return how many levels to bump the operator's chosen mode upward.

    0 = no cues; 1 = urgent cue (BREAK, BE ADVISED, CONTACT *);
    2 = critical cue (CASEVAC, MEDEVAC, DANGER CLOSE, ...).

    If both an urgent and a critical cue are present, returns 2.
    """
    upper = text.upper()
    if any(cue in upper for cue in _CRITICAL_CUES):
        return 2
    if any(cue in upper for cue in _URGENT_CUES):
        return 1
    return 0


def _bump(mode: OperatorMode, levels: int) -> OperatorMode:
    """Move `mode` upward by N levels in the calm < comms < critical order.
    Capped at critical; never demotes."""
    if levels <= 0:
        return mode
    idx = ALL_MODES.index(mode)
    return ALL_MODES[min(idx + levels, len(ALL_MODES) - 1)]


# ---------------------------------------------------------------------------
# Public selection
# ---------------------------------------------------------------------------


def _resolve_operator_mode(override: OperatorMode | None) -> OperatorMode:
    """Operator's base mode. Argument > env var > default 'comms'."""
    if override is not None:
        if override not in ALL_MODES:
            raise ValueError(f"unknown operator mode: {override!r}; allowed: {ALL_MODES}")
        return override
    raw = os.environ.get("TERA_VOICE_PROFILE", "").strip().lower()
    if raw in ALL_MODES:
        return raw
    return "comms"


def select_profile(
    rationale: str,
    operator_mode: OperatorMode | None = None,
) -> VoiceProfile:
    """Pick a voice profile.

    Args:
        rationale: the cadence-ready text about to be synthesized. Scanned
            for severity cues that may auto-elevate the chosen mode.
        operator_mode: optional explicit base mode override. None = use
            TERA_VOICE_PROFILE env var, or fall back to 'comms'.

    Returns:
        The chosen VoiceProfile. Severity auto-elevation may push the
        result above the base mode but never below.
    """
    base = _resolve_operator_mode(operator_mode)
    bump = detect_severity_bump(rationale)
    final = _bump(base, bump)
    return PROFILES.get(final, FALLBACK_PROFILE)
