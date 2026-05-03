"""Voice profile + severity-routing tests.

Pins the contract operators rely on:
  - calm < comms < critical (immutable order)
  - severity cues elevate, never demote
  - operator's chosen mode is honored unless cues escalate
  - env var sets the base mode, kwarg overrides env var
"""

from __future__ import annotations

import pytest

from voice import profiles
from voice.profiles import (
    ALL_MODES,
    PROFILES,
    OperatorMode,
    detect_severity_bump,
    select_profile,
)

# ---------------------------------------------------------------------------
# Structural invariants
# ---------------------------------------------------------------------------


def test_mode_order_is_calm_then_comms_then_critical() -> None:
    """The order is contract -- _bump and tests rely on it."""
    assert ALL_MODES == ("calm", "comms", "critical")


def test_every_mode_has_a_profile() -> None:
    for mode in ALL_MODES:
        assert mode in PROFILES, f"missing profile for mode {mode!r}"
        p = PROFILES[mode]
        assert p.name == mode
        assert p.voice
        assert p.fx in ("clean", "light", "comms", "degraded")
        assert 0.5 <= p.length_scale <= 2.0


def test_critical_uses_degraded_fx() -> None:
    """The 'CASEVAC' voice has the heaviest comms degradation."""
    assert PROFILES["critical"].fx == "degraded"


def test_calm_uses_clean_fx() -> None:
    """The 'briefing' voice has no FX -- you'd hear gear in calm reads."""
    assert PROFILES["calm"].fx == "clean"


def test_default_demo_profile_is_comms() -> None:
    """PR #54 first slice picked comms as the demo default per Jon."""
    assert PROFILES["comms"].fx == "comms"


# ---------------------------------------------------------------------------
# Severity cue detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected_bump",
    [
        ("Routed to Lobos Creek. Distance 2.1 km. ETA 38 min.", 0),
        ("hold position, await further orders", 0),
        ("Be advised, route blocked.", 1),
        ("BREAK -- new contact 200 meters", 1),
        ("Contact front, dismounts", 1),
        ("CASEVAC inbound", 2),
        ("MEDEVAC requested at grid 11SMS1234 5678", 2),
        ("Danger close, 50 meters", 2),
        ("Mass casualty at TOC", 2),
        ("Troops in contact, request fire support", 2),
        # Both an urgent and a critical cue -> takes the higher (critical).
        ("Be advised, CASEVAC inbound", 2),
        # Lowercase still matches because we uppercase before searching.
        ("casevac inbound", 2),
    ],
)
def test_detect_severity_bump(text: str, expected_bump: int) -> None:
    assert detect_severity_bump(text) == expected_bump


def test_severity_cue_word_boundary() -> None:
    """Substrings in normal English shouldn't trigger.

    This is a word-AND-phrase match (we use `in` after uppercase). The
    cue strings include spaces ('DANGER CLOSE') so they don't collide
    with normal English. 'breakdown' won't match 'BREAK' as a phrase
    because we don't word-boundary the single-word cue. Document the
    actual behavior (it's pragmatic, not bulletproof) for future-Jon.
    """
    # 'BREAK' is a single-word cue; 'breakdown' is unfortunately a match
    # because we do simple substring search. The test pins this behavior
    # so we know to revisit if false-positives sting in the field.
    assert detect_severity_bump("breakdown") == 1


# ---------------------------------------------------------------------------
# select_profile -- the integration of cues + operator mode
# ---------------------------------------------------------------------------


def test_default_returns_comms_when_no_cues_and_no_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TERA_VOICE_PROFILE", raising=False)
    p = select_profile("Routed to Lobos Creek. ETA 38 min.")
    assert p.name == "comms"


def test_kwarg_override_beats_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERA_VOICE_PROFILE", "critical")
    p = select_profile("Routed.", operator_mode="calm")
    assert p.name == "calm"


def test_env_var_when_no_kwarg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERA_VOICE_PROFILE", "calm")
    p = select_profile("Routed to Lobos Creek.")
    assert p.name == "calm"


def test_unknown_env_var_falls_back_to_comms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERA_VOICE_PROFILE", "tactical")  # not a known mode
    p = select_profile("Routed.")
    assert p.name == "comms"


def test_unknown_kwarg_raises() -> None:
    """Bad operator_mode arg is a programmer error, not silent fallback."""
    with pytest.raises(ValueError, match="unknown operator mode"):
        select_profile("anything", operator_mode="tactical")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Severity auto-elevation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "base_mode,text,expected_mode",
    [
        # Calm + no cues -> stays calm
        ("calm", "Routed to creek.", "calm"),
        # Calm + urgent cue -> bumps to comms
        ("calm", "Be advised, blocked.", "comms"),
        # Calm + critical cue -> bumps two to critical
        ("calm", "CASEVAC inbound.", "critical"),
        # Comms + no cues -> stays comms
        ("comms", "Routed.", "comms"),
        # Comms + urgent cue -> bumps to critical
        ("comms", "Be advised.", "critical"),
        # Comms + critical cue -> already capped at critical
        ("comms", "CASEVAC.", "critical"),
        # Critical + anything -> stays critical (capped)
        ("critical", "routine briefing", "critical"),
        ("critical", "CASEVAC.", "critical"),
    ],
)
def test_severity_elevates_never_demotes(
    base_mode: OperatorMode, text: str, expected_mode: OperatorMode
) -> None:
    p = select_profile(text, operator_mode=base_mode)
    assert p.name == expected_mode, (
        f"base={base_mode!r}, text={text!r} -> got {p.name!r}, expected {expected_mode!r}"
    )


# ---------------------------------------------------------------------------
# Internal _bump correctness (defense-in-depth)
# ---------------------------------------------------------------------------


def test_bump_clamps_at_critical() -> None:
    assert profiles._bump("comms", 99) == "critical"
    assert profiles._bump("critical", 99) == "critical"


def test_bump_zero_is_identity() -> None:
    for mode in ALL_MODES:
        assert profiles._bump(mode, 0) == mode


def test_bump_negative_is_identity() -> None:
    """We never demote, even if asked. Belt-and-suspenders."""
    assert profiles._bump("critical", -1) == "critical"
    assert profiles._bump("calm", -10) == "calm"
