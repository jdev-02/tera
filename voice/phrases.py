"""Voice-out test phrase corpus.

Categorized phrases for listen-testing the rationale -> cadence -> Piper
chain. Each phrase exercises one or more failure modes that operators
care about. Keep these short and realistic -- they should sound like
something an operator would actually hear on net.

Categories
----------
clean        -- baseline, no traps. Should always sound natural.
bearings     -- 3-digit headings, bearing/range pairs.
mgrs         -- grid references at varying precision.
units        -- distances, speeds, altitudes.
homophones   -- numbers/words that confuse on radio (5/9, 3/free, 2/to).
compound     -- compound cardinals, multi-clause sentences.
mission      -- realistic mission narration (CASEVAC, contact, status).
ambiguous    -- intentionally tricky phrasing that could be misread.
prd          -- the canonical PRD scenario rationales.

Each entry is (id, category, text, what_to_listen_for).
"""

from __future__ import annotations

PHRASES: list[tuple[str, str, str, str]] = [
    # ---- baseline ------------------------------------------------------
    (
        "clean-01",
        "clean",
        "Operator, route plan ready. Standby for confirmation.",
        "natural pacing, clean stop at end",
    ),
    (
        "clean-02",
        "clean",
        "Acknowledge receipt and move on my mark.",
        "no numbers; pure prosody check",
    ),

    # ---- bearings & ranges --------------------------------------------
    (
        "bearing-01",
        "bearings",
        "Heading 030 for 2.5 kilometers.",
        "'zero three zero' digit-by-digit; decimal smooth",
    ),
    (
        "bearing-02",
        "bearings",
        "Bearing 270, range 800 meters.",
        "'two seven zero'; range read clean",
    ),
    (
        "bearing-03",
        "bearings",
        "Turn NE then maintain 045 for 1.2 kilometers.",
        "cardinal expansion + bearing + decimal",
    ),
    (
        "bearing-04",
        "bearings",
        "From here, bearing 359, range 50 meters.",
        "near-360 bearing -- still digit-by-digit",
    ),

    # ---- MGRS grids ---------------------------------------------------
    (
        "mgrs-01",
        "mgrs",
        "Grid 11SMS1234 5678.",
        "phonetic letters; comma pause between halves",
    ),
    (
        "mgrs-02",
        "mgrs",
        "Target at 18TWL8412 9023, friendlies at 18TWL8395 9011.",
        "two MGRS in one sentence; mid-sentence comma flow",
    ),
    (
        "mgrs-03",
        "mgrs",
        "Hill at 11SMS12345678.",
        "MGRS without space-separated halves",
    ),

    # ---- units --------------------------------------------------------
    (
        "units-01",
        "units",
        "Distance 4.2 km, ETA 38 minutes on foot.",
        "decimal, integer, units all in one line",
    ),
    (
        "units-02",
        "units",
        "Wind from 220 at 15 kph, gusting 25.",
        "kph -> 'kilometers per hour'; sequential numbers",
    ),
    (
        "units-03",
        "units",
        "Altitude 1250 meters, descent 200 meters per minute.",
        "longer numbers digit-by-digit; trailing unit",
    ),

    # ---- homophone hazards --------------------------------------------
    (
        "homo-01",
        "homophones",
        "5 friendlies at 9 o'clock.",
        "'five' vs 'nine' -- can you tell them apart cleanly?",
    ),
    (
        "homo-02",
        "homophones",
        "2 vehicles for 4 personnel.",
        "two/to and four/for collisions",
    ),
    (
        "homo-03",
        "homophones",
        "3 contacts at 300 meters bearing 030.",
        "'three' said three different ways (count, range, bearing)",
    ),

    # ---- compound directions -----------------------------------------
    (
        "compound-01",
        "compound",
        "Move NNE through draw, then SE around the ridge.",
        "compound cardinals -- 'north-northeast' smooth?",
    ),
    (
        "compound-02",
        "compound",
        "Primary route NW, alternate route SSW, contingency due south.",
        "three cardinals in one sentence",
    ),

    # ---- mission narration -------------------------------------------
    (
        "mission-01",
        "mission",
        "Routed to Lobos Creek. Distance 2.1 kilometers. ETA 38 minutes on foot covered.",
        "the PRD scenario A read; should sound briefing-grade",
    ),
    (
        "mission-02",
        "mission",
        "CASEVAC requested. Routing to open field at grid 11SMS1234 5678. Suitable HLZ.",
        "Kyle's situational-context prototype (issue #45)",
    ),
    (
        "mission-03",
        "mission",
        "Contact front, 200 meters, dismounts. Break.",
        "short urgent burst; 'break' should land hard",
    ),
    (
        "mission-04",
        "mission",
        "Be advised: route blocked at waypoint 3. Rerouting through alternate.",
        "'be advised' cadence; mid-sentence colon",
    ),
    (
        "mission-05",
        "mission",
        "Danger close, 50 meters, friendly mark north.",
        "'danger close' should NOT get glossed over",
    ),

    # ---- ambiguous / tricky -------------------------------------------
    (
        "amb-01",
        "ambiguous",
        "Move to 11SMS1234, then 11SMS5678, then halt.",
        "two grids back to back; do you confuse them?",
    ),
    (
        "amb-02",
        "ambiguous",
        "ETA 11, distance 11, bearing 110.",
        "'eleven' three ways; can you tell quantity from grid?",
    ),
    (
        "amb-03",
        "ambiguous",
        "0.9 kilometers to checkpoint, 9 minutes.",
        "leading-zero decimal next to plain integer",
    ),

    # ---- the canonical PRD scenarios ---------------------------------
    (
        "prd-A",
        "prd",
        "Routed to Lobos Creek, distance 2.1 kilometers, ETA 38 minutes on foot covered.",
        "PRD scenario A: urban freshwater route",
    ),
    (
        "prd-B",
        "prd",
        "Routed via covered ridge to objective. Avoiding open ground at 11SMS1234 5678.",
        "PRD scenario B: austere covered route with grid",
    ),
    (
        "prd-C",
        "prd",
        "Highest threat priority grid identified. Routing dismount team via NW draw.",
        "PRD scenario C: priority-grid dispatch",
    ),
]


def by_category(category: str) -> list[tuple[str, str, str, str]]:
    """Filter phrases by category. Returns empty list if category unknown."""
    return [p for p in PHRASES if p[1] == category]


def by_id(phrase_id: str) -> tuple[str, str, str, str] | None:
    """Find a single phrase by id. Returns None if not found."""
    for p in PHRASES:
        if p[0] == phrase_id:
            return p
    return None


def categories() -> list[str]:
    """Distinct category names, in PHRASES order."""
    seen: set[str] = set()
    out: list[str] = []
    for _, cat, _, _ in PHRASES:
        if cat not in seen:
            seen.add(cat)
            out.append(cat)
    return out
