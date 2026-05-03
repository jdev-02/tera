"""Glossary lookup + explain-text rendering tests.

The glossary is the single source of truth for both:
  - cadence reading of acronyms in /plan rationales
  - on-demand explanation when the operator asks "what does X mean"

Anything the orchestrator or voice path renders must be deterministic and
auditable. These tests pin that contract.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from voice import glossary
from voice.tts import synthesize_explanation_b64

# ---------------------------------------------------------------------------
# Glossary structural invariants
# ---------------------------------------------------------------------------


def test_every_term_has_required_fields() -> None:
    """Every entry must declare a reading, kind, and full expansion."""
    for term, entry in glossary.GLOSSARY.items():
        assert entry.reading, f"{term} missing reading"
        assert entry.reading_kind in ("spell", "word"), f"{term} bad reading_kind"
        assert entry.full, f"{term} missing full expansion"
        # Capitalization sanity: full should start uppercase, term should be uppercase.
        assert term == term.upper(), f"{term} key must be uppercase"


def test_reading_kind_alignment() -> None:
    """spell-kind readings should be multi-word; word-kind should be single."""
    for term, entry in glossary.GLOSSARY.items():
        n_words = len(entry.reading.split())
        if entry.reading_kind == "spell":
            assert n_words >= 2, f"{term} spell-kind reading must be multi-word"
        elif entry.reading_kind == "word":
            assert n_words == 1, f"{term} word-kind reading must be a single word"


def test_known_terms_sorted_alphabetical() -> None:
    """known_terms() must return alphabetical order for stable UI/help output."""
    terms = glossary.known_terms()
    assert terms == sorted(terms)


# ---------------------------------------------------------------------------
# Lookup behaviour
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "term,expected_full",
    [
        ("HLZ", "Helicopter Landing Zone"),
        ("hlz", "Helicopter Landing Zone"),  # case-insensitive
        ("  HLZ  ", "Helicopter Landing Zone"),  # whitespace-tolerant
        ("CASEVAC", "Casualty Evacuation"),
        ("ETA", "Estimated Time of Arrival"),
        ("MEDEVAC", "Medical Evacuation"),
    ],
)
def test_explain_known_terms(term: str, expected_full: str) -> None:
    entry = glossary.explain(term)
    assert entry is not None, f"{term} should be in glossary"
    assert entry.full == expected_full


@pytest.mark.parametrize("term", ["", "   ", "XYZZY", "asdf", "PLATYPUS"])
def test_explain_unknown_terms_returns_none(term: str) -> None:
    """Unknown terms must return None -- never fabricate a definition."""
    assert glossary.explain(term) is None


# ---------------------------------------------------------------------------
# Render explanation text
# ---------------------------------------------------------------------------


def test_render_includes_reading_first() -> None:
    """The reading (what the operator HEARD) leads, then 'stands for'."""
    entry = glossary.explain("HLZ")
    assert entry is not None
    text = glossary.render_explanation_text(entry)
    assert text.startswith("hotel lima zulu stands for ")
    assert "Helicopter Landing Zone" in text
    assert "rotary-wing landing" in text  # context appended
    assert text.endswith(".")


def test_render_no_context_no_trailing_clause() -> None:
    """When `context` is None, the explanation is just '<reading> stands for <full>.'."""
    entry = glossary.GLOSSARY["ETA"]  # ETA has no context field
    text = glossary.render_explanation_text(entry)
    assert text == "echo tango alpha stands for Estimated Time of Arrival."


# ---------------------------------------------------------------------------
# synthesize_explanation_b64 -- glue path
# ---------------------------------------------------------------------------


def test_synthesize_explanation_unknown_returns_none() -> None:
    """Unknown terms must return None; never call Piper, never invent text."""
    with patch("voice.tts.get_piper") as mock_get_piper:
        result = synthesize_explanation_b64("ZZZTOP")
    assert result is None
    mock_get_piper.assert_not_called()


def test_synthesize_explanation_known_returns_text_when_piper_unavailable() -> None:
    """Even without Piper, the deterministic explanation TEXT must be returned.

    This is intentional: the operator might be on a degraded device where
    audio synth fails, but the text-only explanation is still useful (e.g.
    show in the ATAK panel).
    """
    fake = MagicMock()
    fake.is_available.return_value = False
    with patch("voice.tts.get_piper", return_value=fake):
        result = synthesize_explanation_b64("HLZ")
    assert result is not None
    assert result["term"] == "HLZ"
    assert "Helicopter Landing Zone" in result["text"]
    assert result["audio_b64"] == ""
    fake.synthesize_wav.assert_not_called()


def test_synthesize_explanation_known_returns_audio_when_piper_available() -> None:
    fake = MagicMock()
    fake.is_available.return_value = True
    fake.synthesize_wav.return_value = b"RIFF\x00\x00\x00\x00WAVE_fake"
    with patch("voice.tts.get_piper", return_value=fake):
        result = synthesize_explanation_b64("CASEVAC")
    assert result is not None
    assert result["term"] == "CASEVAC"
    assert "Casualty Evacuation" in result["text"]
    assert result["audio_b64"]  # non-empty
    # Verify the spoken text begins with the reading (operator-anchored).
    sent = fake.synthesize_wav.call_args.args[0]
    assert sent.startswith("case-vac stands for")


def test_synthesize_explanation_swallows_piper_errors() -> None:
    """If Piper raises, we still return the text-only explanation."""
    fake = MagicMock()
    fake.is_available.return_value = True
    fake.synthesize_wav.side_effect = RuntimeError("synth boom")
    with patch("voice.tts.get_piper", return_value=fake):
        result = synthesize_explanation_b64("HLZ")
    assert result is not None
    assert result["audio_b64"] == ""
    assert "Helicopter Landing Zone" in result["text"]
