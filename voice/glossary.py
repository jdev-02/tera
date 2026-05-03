"""Operator acronym glossary -- single source of truth for both the
default cadence reading AND the on-demand explain path.

Two readers consume this:
  - voice.rationale uses the `reading` field to render acronyms inside
    a normal /plan rationale (default cadence, fast).
  - voice.tts.synthesize_explanation_b64 uses `full` + `context` to
    speak a deterministic explanation when the operator asks
    "what does HLZ mean".

Why deterministic (no LLM):
  - Adding/changing an acronym updates both reading and explain
    simultaneously -- no drift.
  - No hallucination risk on the explain path. If a term isn't in this
    file, the system says so honestly instead of guessing.
  - The full file is auditable in source control. JAG / event organizer
    can read it and confirm no classified content.

Editorial guardrail:
  - Use only **publicly doctrinal definitions**. No classified TTPs.
  - Cite the doctrine source in `source` when one exists -- belt-and-
    suspenders for the SUBMISSION_NOTES.md OPSEC posture.
  - Keep `context` to one declarative sentence; this is what an
    operator hears when they ask for an explanation, not a tutorial.

Adding a term:
  1. Pick `reading_kind`:
       'spell' -> NATO phonetic ("hotel lima zulu"). Use for any
                  acronym that operators read as separate letters on
                  net. Required for any acronym ending in a single
                  vowel (Piper drops trailing solo letters).
       'word'  -> single pronounceable word ("case-vac", "tock").
                  Use ONLY when operators universally pronounce it as
                  a word, not as letters.
  2. Set `reading` to what Piper should literally say.
  3. Set `full` to the canonical capitalized expansion.
  4. Optional `context`: one short sentence ("an area suitable for
     rotary-wing landing"). Spoken after `full` in explain mode.
  5. Optional `source`: doctrinal reference (e.g. "ATP 4-02.2").
"""

from __future__ import annotations

from typing import Literal, NamedTuple

ReadingKind = Literal["spell", "word"]


class GlossaryEntry(NamedTuple):
    reading: str  # what Piper actually pronounces
    reading_kind: ReadingKind
    full: str  # canonical expansion
    context: str | None = None
    source: str | None = None  # doctrinal cite if applicable


# ---------------------------------------------------------------------------
# The glossary. Keep alphabetical for diff-readability.
# ---------------------------------------------------------------------------

GLOSSARY: dict[str, GlossaryEntry] = {
    "AO": GlossaryEntry(
        reading="alpha oscar",
        reading_kind="spell",
        full="Area of Operations",
        context="the geographic area assigned to a unit for the conduct of "
        "operations",
        source="JP 3-0",
    ),
    "CASEVAC": GlossaryEntry(
        reading="case-vac",
        reading_kind="word",
        full="Casualty Evacuation",
        context="non-medical evacuation of a casualty by available transport",
        source="ATP 4-02.2",
    ),
    "CP": GlossaryEntry(
        reading="charlie papa",
        reading_kind="spell",
        full="Checkpoint",
        context="a predetermined point used as a reference for control of "
        "movement",
    ),
    "EOD": GlossaryEntry(
        reading="echo oscar delta",
        reading_kind="spell",
        full="Explosive Ordnance Disposal",
        context="the detection, identification, evaluation, render-safe, and "
        "disposal of explosive ordnance",
        source="JP 3-42",
    ),
    "ETA": GlossaryEntry(
        reading="echo tango alpha",
        reading_kind="spell",
        full="Estimated Time of Arrival",
    ),
    "HLZ": GlossaryEntry(
        # 'lima' alone gets the trailing-vowel swallow; 'lee-mah' forces both
        # syllables (op note 17:41). Same trick as case-vac / med-evac.
        reading="hotel lee-mah zulu",
        reading_kind="spell",
        full="Helicopter Landing Zone",
        context="an area suitable for rotary-wing landing",
        source="ATP 3-04.1",
    ),
    "IED": GlossaryEntry(
        reading="india echo delta",
        reading_kind="spell",
        full="Improvised Explosive Device",
        source="JP 3-15.1",
    ),
    "LZ": GlossaryEntry(
        reading="lee-mah zulu",
        reading_kind="spell",
        full="Landing Zone",
        context="a specified ground area for landing aircraft",
    ),
    "MEDEVAC": GlossaryEntry(
        reading="med-evac",
        reading_kind="word",
        full="Medical Evacuation",
        context="evacuation by a dedicated medical platform with "
        "en-route care",
        source="ATP 4-02.2",
    ),
    "MGRS": GlossaryEntry(
        reading="mike golf romeo sierra",
        reading_kind="spell",
        full="Military Grid Reference System",
        context="the geocoordinate standard used by NATO militaries",
    ),
    "OP": GlossaryEntry(
        reading="oscar papa",
        reading_kind="spell",
        full="Observation Post",
        context="a position from which observation is conducted",
    ),
    "POI": GlossaryEntry(
        reading="papa oscar india",
        reading_kind="spell",
        full="Point of Interest",
    ),
    "PZ": GlossaryEntry(
        reading="papa zulu",
        reading_kind="spell",
        full="Pickup Zone",
        context="a designated location for the pickup of personnel or "
        "equipment by aircraft",
    ),
    "QRF": GlossaryEntry(
        reading="quebec romeo foxtrot",
        reading_kind="spell",
        full="Quick Reaction Force",
        context="a designated unit on standby for rapid response",
    ),
    "RECON": GlossaryEntry(
        reading="ree-kon",
        reading_kind="word",
        full="Reconnaissance",
    ),
    "TOC": GlossaryEntry(
        reading="tock",
        reading_kind="word",
        full="Tactical Operations Center",
        context="the principal command and control node for a unit",
    ),
    "TRP": GlossaryEntry(
        reading="tango romeo papa",
        reading_kind="spell",
        full="Target Reference Point",
    ),
}


# ---------------------------------------------------------------------------
# Public lookup helpers
# ---------------------------------------------------------------------------


def explain(term: str) -> GlossaryEntry | None:
    """Look up a glossary entry by term, case-insensitive.

    Returns None if the term isn't known. Callers should treat that as
    "not in glossary" and respond honestly to the operator instead of
    fabricating a definition.
    """
    if not term:
        return None
    return GLOSSARY.get(term.strip().upper())


def known_terms() -> list[str]:
    """Sorted list of every glossary key. For UI/help/debug."""
    return sorted(GLOSSARY.keys())


def acronym_readings_spell() -> dict[str, str]:
    """Mapping of {term -> NATO-phonetic reading} for cadence transforms."""
    return {k: v.reading for k, v in GLOSSARY.items() if v.reading_kind == "spell"}


def acronym_readings_word() -> dict[str, str]:
    """Mapping of {term -> word-form reading} for cadence transforms."""
    return {k: v.reading for k, v in GLOSSARY.items() if v.reading_kind == "word"}


def render_explanation_text(entry: GlossaryEntry) -> str:
    """Build the spoken-explanation string from a glossary entry.

    Format: '<reading> stands for <full>[, <context>].'

    The leading `reading` is what the operator HEARD that they're asking
    about; placing it first acknowledges their query before defining it.
    """
    text = f"{entry.reading} stands for {entry.full}"
    if entry.context:
        text = f"{text}, {entry.context}"
    return text + "."
