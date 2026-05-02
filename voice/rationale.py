"""Operator-cadence transformer.

Converts plain-English rationale strings (as produced by the orchestrator)
into the cadence operators expect when listening hands-free:

  - bearings (3-digit) -> "zero three zero"
  - counted numbers > 9 -> digit-by-digit ("three eight" not "thirty-eight")
  - decimals -> "two point one"
  - units -> spelled out ("kilometers" not "km")
  - MGRS grids -> phonetic letters + digit-by-digit
  - cardinal abbreviations -> full word ("northeast" not "NE")

Pure string transformation. No LLM in the loop. Deterministic, table-driven,
testable. The grammar is intentionally narrow: this code does NOT try to
turn arbitrary English into mil-cadence -- it only rewrites the patterns
the orchestrator's rationale templates actually emit.

Refining cadence rules is a paired task between Jon (impl) and Ben (operator
SME). When in doubt, prefer fewer transformations over more -- it's better
to leave a phrase plain-English than to mangle it.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Single-digit phonetics. Each digit gets its own word, no contractions
# (so "0" is "zero" not "oh").
# ---------------------------------------------------------------------------

_DIGIT_WORD = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}


def _digits_spoken(digits: str) -> str:
    """'1234' -> 'one two three four'."""
    return " ".join(_DIGIT_WORD[c] for c in digits if c in _DIGIT_WORD)


# ---------------------------------------------------------------------------
# Cardinal abbreviations -> full words.
# Order matters: longer matches first (NE before N) to avoid partial replace.
# ---------------------------------------------------------------------------

_CARDINAL_FULL = [
    ("NNW", "north-northwest"),
    ("NNE", "north-northeast"),
    ("ENE", "east-northeast"),
    ("ESE", "east-southeast"),
    ("SSE", "south-southeast"),
    ("SSW", "south-southwest"),
    ("WSW", "west-southwest"),
    ("WNW", "west-northwest"),
    ("NW", "northwest"),
    ("NE", "northeast"),
    ("SW", "southwest"),
    ("SE", "southeast"),
]


# ---------------------------------------------------------------------------
# MGRS phonetic alphabet (NATO). Used when reading grids letter-by-letter.
# Only the letters that actually appear in MGRS are required.
# ---------------------------------------------------------------------------

_MGRS_PHONETIC = {
    "A": "alpha",
    "B": "bravo",
    "C": "charlie",
    "D": "delta",
    "E": "echo",
    "F": "foxtrot",
    "G": "golf",
    "H": "hotel",
    "J": "juliet",
    "K": "kilo",
    "L": "lima",
    "M": "mike",
    "N": "november",
    "P": "papa",
    "Q": "quebec",
    "R": "romeo",
    "S": "sierra",
    "T": "tango",
    "U": "uniform",
    "V": "victor",
    "W": "whiskey",
    "X": "x-ray",
    "Y": "yankee",
    "Z": "zulu",
}


# ---------------------------------------------------------------------------
# Unit suffix expansion. Spoken-as is what Piper actually says; the synthesis
# is more natural when the unit is spelled out.
# ---------------------------------------------------------------------------

_UNIT_FULL = {
    "km": "kilometers",
    "kph": "kilometers per hour",
    "kmh": "kilometers per hour",
    "kts": "knots",
    "mph": "miles per hour",
    "mi": "miles",
    "nm": "nautical miles",
    "ft": "feet",
    "m": "meters",
}


# ---------------------------------------------------------------------------
# Transformation passes
# ---------------------------------------------------------------------------


def _expand_mgrs_grids(text: str) -> str:
    """Match MGRS grids like '11SMS1234 5678' or '11SMS12345678'.

    Pattern: 1-2 digits (zone), 1-3 letters (band+square), then digits in
    pairs of 2/4/6/8/10 (precision). Example: '11SMS1234 5678'.

    Speak as: 'one one Sierra Mike Sierra one two three four, five six seven eight'.
    """

    def repl(m: re.Match[str]) -> str:
        zone = m.group("zone")
        letters = m.group("letters")
        digits1 = m.group("digits1")
        digits2 = m.group("digits2") or ""

        zone_words = _digits_spoken(zone)
        letter_words = " ".join(_MGRS_PHONETIC.get(c, c) for c in letters.upper())
        d1_words = _digits_spoken(digits1)
        d2_words = _digits_spoken(digits2)

        parts = [zone_words, letter_words, d1_words]
        if d2_words:
            parts[-1] = d1_words + ","
            parts.append(d2_words)
        return " ".join(p for p in parts if p)

    pattern = re.compile(
        r"\b(?P<zone>\d{1,2})(?P<letters>[A-Z]{1,3})(?P<digits1>\d{2,5})(?:\s+(?P<digits2>\d{2,5}))?\b",
    )
    return pattern.sub(repl, text)


def _expand_cardinals(text: str) -> str:
    """NE -> northeast etc. Word-boundary anchored to avoid replacing inside identifiers."""
    for abbr, full in _CARDINAL_FULL:
        text = re.sub(rf"\b{abbr}\b", full, text)
    return text


def _expand_units(text: str) -> str:
    """Replace numeric+unit pairs ('2.1 km') with numeric + spelled-unit
    ('2.1 kilometers'). Handles numbers like 2, 2.1, 38, 0.5 with optional
    space before the unit."""
    for short, full in _UNIT_FULL.items():
        # Match number (int or decimal) followed by optional space + unit + word boundary.
        text = re.sub(rf"(\d+(?:\.\d+)?)\s*{short}\b", rf"\1 {full}", text)
    return text


def _expand_decimals(text: str) -> str:
    """'2.1' -> 'two point one' (always digit-by-digit on either side of '.')."""

    def repl(m: re.Match[str]) -> str:
        whole, frac = m.group(1), m.group(2)
        return f"{_digits_spoken(whole)} point {_digits_spoken(frac)}"

    return re.sub(r"\b(\d+)\.(\d+)\b", repl, text)


def _expand_counted_numbers(text: str) -> str:
    """Plain integers >= 10 spoken digit-by-digit ('38' -> 'three eight').
    Single-digit numbers (0-9) are usually fine as-is in Piper but spelled
    out anyway for consistency. Numbers in MGRS grids are already handled."""

    def repl(m: re.Match[str]) -> str:
        return _digits_spoken(m.group(0))

    # Match 1+ digits not preceded by a letter (avoids touching things mid-word).
    return re.sub(r"(?<![A-Za-z])\b\d+\b", repl, text)


def _expand_three_digit_bearings(text: str) -> str:
    """3-digit bearings (000-359) preceded by 'bearing' or 'heading' get
    digit-by-digit. We do this BEFORE _expand_counted_numbers so the cue word
    is still present when we match. The narrower pass is preserved through
    a placeholder substitution -- low risk since this matches only a couple
    of patterns in our rationale templates.

    NOTE: in practice _expand_counted_numbers will already speak '030' as
    'zero three zero' so this function is currently a no-op marker. Kept
    here for future cadence rules that need bearing-specific phrasing
    (e.g. future templates that emit just '030' without a cue word).
    """
    return text


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def to_operator_cadence(text: str) -> str:
    """Convert plain-English rationale into operator-cadence speech.

    The order of passes matters:
      1. MGRS grids first (their digits + letters need to win before generic
         passes touch them).
      2. Cardinal abbreviations (NE etc.) -> full words.
      3. Units (km, kph) -> spelled-out (so number+unit reads naturally).
      4. Decimals (2.1) -> 'two point one'.
      5. Plain integers (38) -> 'three eight' digit-by-digit.

    The result is fed straight to Piper. No further normalization required.
    """
    if not text:
        return text

    text = _expand_mgrs_grids(text)
    text = _expand_cardinals(text)
    text = _expand_units(text)
    text = _expand_decimals(text)
    text = _expand_three_digit_bearings(text)
    text = _expand_counted_numbers(text)

    # Collapse any double spaces that came from substitutions.
    return re.sub(r"\s{2,}", " ", text).strip()
