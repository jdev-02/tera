"""Operator-cadence transformer tests. Table-driven so adding a rule = adding a row."""

from __future__ import annotations

import pytest

from voice.rationale import to_operator_cadence

# Each entry: (input rationale, expected operator-cadence output, comment).
_CASES: list[tuple[str, str, str]] = [
    # Empty / no-op cases
    ("", "", "empty stays empty"),
    ("Hello operator.", "Hello operator.", "no numbers, no transform"),

    # Cardinal abbreviations
    ("Heading NE.", "Heading northeast.", "NE -> northeast"),
    ("Bearing SW from origin.", "Bearing southwest from origin.", "SW -> southwest"),
    ("Move NNE through draw.", "Move north-northeast through draw.", "3-letter cardinal"),

    # Decimal expansion
    ("2.1 kilometers", "two point one kilometers", "decimal expanded"),
    ("0.5", "zero point five", "leading zero"),
    ("12.345", "one two point three four five", "multi-digit decimal"),

    # Plain integer expansion (digit-by-digit)
    ("ETA 38 minutes", "ETA three eight minutes", "two-digit count"),
    ("over 4 kilometers per hour", "over four kilometers per hour", "single digit"),

    # Unit expansion
    ("2 km", "two kilometers", "km -> kilometers"),
    ("4 kph", "four kilometers per hour", "kph -> kilometers per hour"),
    ("500 m", "five zero zero meters", "m -> meters"),

    # MGRS grid -- single 8-digit precision pair (phonetics are lowercase
    # because Piper synthesizes the same regardless of case).
    (
        "Grid 11SMS1234 5678",
        "Grid one one sierra mike sierra one two three four, five six seven eight",
        "MGRS with two 4-digit halves",
    ),

    # MGRS grid -- inline 4-digit precision (no space)
    (
        "Hill at 11SMS1234",
        "Hill at one one sierra mike sierra one two three four",
        "MGRS without the second half",
    ),

    # The flagship rationale from PRD §6 (hero scenario A)
    (
        "Routed to Lobos Creek, distance 2.1 kilometers, ETA 38 minutes on foot covered.",
        (
            "Routed to Lobos Creek, distance two point one kilometers, "
            "ETA three eight minutes on foot covered."
        ),
        "PRD scenario A canonical rationale",
    ),

    # Combined: cardinal + decimal + integer
    (
        "Selected creek 2.1 km NE; ETA 38 min.",
        "Selected creek two point one kilometers northeast; ETA three eight min.",
        "multiple transforms in one string",
    ),
]


@pytest.mark.parametrize("text,expected,comment", _CASES, ids=[c[2] for c in _CASES])
def test_operator_cadence_cases(text: str, expected: str, comment: str) -> None:
    actual = to_operator_cadence(text)
    assert actual == expected, f"{comment}: {actual!r} != {expected!r}"


def test_idempotent_on_already_spoken_form() -> None:
    """Running the transformer twice should not change the output further.
    (Defensive: catches accidental double-substitution bugs.)"""
    text = "Routed to Lobos Creek, distance 2.1 kilometers, ETA 38 minutes."
    once = to_operator_cadence(text)
    twice = to_operator_cadence(once)
    assert twice == once, "transformer is not idempotent"


def test_preserves_no_number_text() -> None:
    """Strings without numbers / cardinals / units should pass through cleanly."""
    text = "Operator approved. Standby for confirmation."
    assert to_operator_cadence(text) == text
