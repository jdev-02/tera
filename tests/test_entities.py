"""Tests for the entities ontology (`ontology/entities.yml`).

The entities enum is the contract between Jon (classification) and Ben (ATAK
rendering + routing cost). These tests guard the contract so a stray YAML
edit doesn't silently break the bridge.
"""

from __future__ import annotations

import pytest

from ontology.loader import entity_types, load_entities


def test_entities_loads() -> None:
    data = load_entities()
    assert "entities" in data
    assert "entities_by_type" in data
    assert data["version"] >= 1


def test_at_least_20_entity_types() -> None:
    """We promised Ben ~20-30 typed entities. Guard against accidental deletions."""
    types = entity_types()
    assert len(types) >= 20, f"only {len(types)} entity types -- ontology shrunk?"


def test_no_duplicate_entity_types() -> None:
    """Duplicates are caught at load time but assert here for the test record."""
    types = entity_types()
    assert len(types) == len(set(types))


def test_required_demo_entities_exist() -> None:
    """The PRD §6 demo scenarios reference these specific entities. They MUST
    exist in the ontology or the demo breaks."""
    required = {
        "freshwater_stream",  # Scenario A: hero
        "freshwater_lake",  # Scenario A: alternate (too big to cross)
        "ridgeline",  # Scenario B: avoid
        "slope_steep",  # Scenario B: avoid
        "slope_extreme",  # Scenario B: blocking
        "bridge_passable",  # Scenario C: route across
        "bridge_restricted",  # Scenario C: avoid
        "trail",  # All foot scenarios
        "road_paved",  # Scenario C: vehicle-fast
    }
    types = set(entity_types())
    missing = required - types
    assert not missing, f"required demo entities missing: {missing}"


@pytest.mark.parametrize("entry", load_entities()["entities"])
def test_entity_has_minimum_fields(entry: dict) -> None:
    """Every entity has type, description, atak_icon_hint. Either osm_tags_match
    or derived_from is required (you have to know how to identify it)."""
    assert "type" in entry, entry
    assert "description" in entry, entry
    assert "atak_icon_hint" in entry, entry
    has_classifier = "osm_tags_match" in entry or "derived_from" in entry
    assert has_classifier, f"{entry['type']!r} has no osm_tags_match or derived_from"


@pytest.mark.parametrize("entry", load_entities()["entities"])
def test_routing_cost_shape(entry: dict) -> None:
    """If `routing_cost` is present, it has the three profile keys and numeric values.
    Costs of 999 indicate uncrossable -- valid but flagged."""
    if "routing_cost" not in entry:
        return  # not all entities have routing cost (e.g. landmark)
    cost = entry["routing_cost"]
    for profile in ("foot", "foot_covered", "vehicle"):
        assert profile in cost, f"{entry['type']!r}.routing_cost missing {profile}"
        assert isinstance(cost[profile], int | float), (
            f"{entry['type']!r}.routing_cost.{profile} not numeric: {cost[profile]!r}"
        )
        assert cost[profile] >= 0, (
            f"{entry['type']!r}.routing_cost.{profile} is negative: {cost[profile]}"
        )
