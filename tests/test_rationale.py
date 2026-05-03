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
    ("ETA 38 minutes", "E T A three eight minutes", "two-digit count + acronym"),
    ("over 4 kilometers per hour", "over four kilometers per hour", "single digit"),

    # Unit expansion
    ("2 km", "two kilometers", "km -> kilometers"),
    ("4 kph", "four kilometers per hour", "kph -> kilometers per hour"),
    ("500 m", "five zero zero meters", "m -> meters"),

    # MGRS grid -- single 8-digit precision pair. Phonetic letters comma-
    # separated so 'sierra mike sierra' doesn't slur (op note 17:03 #4).
    (
        "Grid 11SMS1234 5678",
        "Grid one one sierra, mike, sierra one two three four, five six seven eight",
        "MGRS with two 4-digit halves",
    ),

    # MGRS grid -- 4-digit no-space form (1km precision, 2+2 split).
    # The standard read inserts a beat between easting and northing.
    (
        "Hill at 11SMS1234",
        "Hill at one one sierra, mike, sierra one two, three four",
        "MGRS no-space 4-digit precision (split 2+2)",
    ),

    # MGRS grid -- 8-digit no-space form (10m precision, 4+4 split).
    (
        "Hill at 11SMS12345678.",
        "Hill at one one sierra, mike, sierra one two three four, five six seven eight.",
        "MGRS no-space 8-digit precision",
    ),

    # Acronym expansion -- spelled letter-by-letter.
    (
        "ETA 5 minutes.",
        "E T A five minutes.",
        "ETA -> 'E T A'",
    ),
    (
        "HLZ at grid 11SMS1234.",
        "H L Z at grid one one sierra, mike, sierra one two, three four.",
        "HLZ -> 'H L Z'",
    ),
    (
        "Identify CP and TOC.",
        "Identify C P and T O C.",
        "multiple acronyms in one line",
    ),

    # Acronym expansion -- read as a word with hyphen hint.
    (
        "CASEVAC inbound.",
        "case-vac inbound.",
        "CASEVAC -> 'case-vac'",
    ),
    (
        "MEDEVAC requested.",
        "med-evac requested.",
        "MEDEVAC -> 'med-evac'",
    ),

    # Clause-comma promotion -- ', ETA' -> '. ETA' for radio cadence.
    (
        "Distance 2.1 km, ETA 38 minutes.",
        "Distance two point one kilometers. E T A three eight minutes.",
        "comma before ETA promoted to period",
    ),
    (
        "Hold position, bearing 270, range 800 meters.",
        "Hold position. bearing two seven zero. range eight zero zero meters.",
        "commas before bearing/range promoted",
    ),

    # The flagship rationale from PRD §6 (hero scenario A). Note: ', distance'
    # is also promoted to '. distance' (clause-comma rule), and ', ETA' to
    # '. ETA'. Result: three full-sentence beats between the elements.
    (
        "Routed to Lobos Creek, distance 2.1 kilometers, ETA 38 minutes on foot covered.",
        (
            "Routed to Lobos Creek. distance two point one kilometers. "
            "E T A three eight minutes on foot covered."
        ),
        "PRD scenario A canonical rationale",
    ),

    # Combined: cardinal + decimal + integer + acronym. Note '; ETA' is
    # not promoted -- the rule only promotes ', ' (comma+space) before cues.
    (
        "Selected creek 2.1 km NE; ETA 38 min.",
        "Selected creek two point one kilometers northeast; E T A three eight min.",
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
