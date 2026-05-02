"""Tests for the route ontology + system prompt builder."""

from __future__ import annotations

from ontology.loader import (
    build_system_prompt,
    load_ontology,
    load_route_query_schema,
)


def test_load_ontology_has_three_parts() -> None:
    onto = load_ontology()
    assert "where" in onto
    assert "what" in onto
    assert "how" in onto
    assert onto["version"] >= 1


def test_load_route_query_schema_is_object_schema() -> None:
    schema = load_route_query_schema()
    assert schema["type"] == "object"
    assert "mission_type" in schema["required"]
    assert "objective" in schema["required"]


def test_system_prompt_builds_without_placeholders() -> None:
    import re

    prompt = build_system_prompt()
    # Catch unfilled `{{name}}` template placeholders specifically.
    # Don't false-positive on JSON examples that legitimately end with `}}`.
    assert not re.search(r"\{\{[a-z_]+\}\}", prompt), (
        "system_prompt.md still has unfilled placeholders"
    )
    assert "WHERE" in prompt
    assert "WHAT" in prompt
    assert "HOW" in prompt


def test_system_prompt_includes_examples() -> None:
    prompt = build_system_prompt()
    # At least one canonical operator utterance from ontology examples.
    assert "freshwater" in prompt.lower()
    assert "RouteQuery" in prompt


def test_system_prompt_caches() -> None:
    """Repeated calls return the same string (cached -- avoids re-parsing YAML)."""
    a = build_system_prompt()
    b = build_system_prompt()
    assert a is b
