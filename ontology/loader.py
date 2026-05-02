"""Loads the route ontology + RouteQuery schema and builds the LLM system prompt.

Cached at module import. The system prompt is rendered once and reused for
every request — there's no per-request branching beyond user content.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ONTOLOGY_PATH = Path(__file__).resolve().parent / "route_ontology.yml"
ENTITIES_PATH = Path(__file__).resolve().parent / "entities.yml"
PROMPT_TEMPLATE_PATH = Path(__file__).resolve().parent / "system_prompt.md"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "docs" / "route_query.schema.json"


@lru_cache(maxsize=1)
def load_ontology() -> dict[str, Any]:
    """Parse route_ontology.yml. Cached for the process lifetime."""
    with ONTOLOGY_PATH.open("r", encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
    if not isinstance(data, dict) or "version" not in data:
        raise RuntimeError(f"Malformed ontology at {ONTOLOGY_PATH}: missing 'version'")
    return data


@lru_cache(maxsize=1)
def load_route_query_schema() -> dict[str, Any]:
    """Parse docs/route_query.schema.json. Cached for the process lifetime."""
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        schema: dict[str, Any] = json.load(f)
    return schema


@lru_cache(maxsize=1)
def load_entities() -> dict[str, Any]:
    """Parse entities.yml. Cached for the process lifetime.

    Returns the full document; callers typically iterate `data["entities"]`
    or look up by `data["entities_by_type"][type]` (built lazily here).
    """
    with ENTITIES_PATH.open("r", encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
    if not isinstance(data, dict) or "entities" not in data:
        raise RuntimeError(f"Malformed entities at {ENTITIES_PATH}: missing 'entities'")
    # Build a type→entry index for fast lookup at runtime.
    by_type: dict[str, dict[str, Any]] = {}
    for entry in data["entities"]:
        if "type" not in entry:
            raise RuntimeError(f"Entity entry missing 'type': {entry}")
        if entry["type"] in by_type:
            raise RuntimeError(f"Duplicate entity type: {entry['type']}")
        by_type[entry["type"]] = entry
    data["entities_by_type"] = by_type
    return data


def entity_types() -> list[str]:
    """Return the sorted list of all entity type ids. Used by tests + ATAK overlay."""
    return sorted(load_entities()["entities_by_type"].keys())


def _format_field_block(part: dict[str, Any]) -> str:
    """Render a WHERE/WHAT/HOW block as bullet lines for the system prompt."""
    lines = [f"- {part.get('description', '').strip()}"]
    for field in part.get("fields", []):
        line = f"  - **{field['name']}** ({field['type']})"
        if "schema_field" in field:
            line += f" -> schema: `{field['schema_field']}`"
        if "operator_question" in field:
            line += f'\n    operator asks: "{field["operator_question"]}"'
        if "default" in field:
            line += f"\n    default if unspecified: {field['default']!r}"
        lines.append(line)
    return "\n".join(lines)


def _format_examples_block(examples: list[dict[str, Any]]) -> str:
    out = []
    for ex in examples:
        out.append(f'Operator: "{ex["utterance"]}"')
        out.append(f"RouteQuery: {json.dumps(ex['route_query'], separators=(',', ':'))}")
        out.append("")
    return "\n".join(out).rstrip()


def _format_forbidden_block(forbidden: list[dict[str, Any]]) -> str:
    out = []
    for ex in forbidden:
        out.append(f'- "{ex["utterance"]}"')
        out.append(f"  why: {ex['why']}")
    return "\n".join(out)


@lru_cache(maxsize=1)
def build_system_prompt() -> str:
    """Render the system prompt by interpolating the ontology into the template.

    Returns a single string ready to use as the LLM's system message.
    """
    ontology = load_ontology()
    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")

    rendered = template.replace("{{where_block}}", _format_field_block(ontology["where"]))
    rendered = rendered.replace("{{what_block}}", _format_field_block(ontology["what"]))
    rendered = rendered.replace("{{how_block}}", _format_field_block(ontology["how"]))
    rendered = rendered.replace(
        "{{examples_block}}", _format_examples_block(ontology.get("examples", []))
    )
    rendered = rendered.replace(
        "{{forbidden_block}}",
        _format_forbidden_block(ontology.get("forbidden_examples", [])),
    )

    # Catch unfilled template placeholders (matches our `{{name}}` syntax) but
    # don't false-positive on JSON examples that legitimately end with `}}`.
    import re

    leftover = re.findall(r"\{\{[a-z_]+\}\}", rendered)
    if leftover:
        raise RuntimeError(f"system_prompt.md has unfilled placeholders: {leftover}")
    return rendered
