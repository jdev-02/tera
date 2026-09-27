"""Infrastructure discovery tools for v2 emergency response."""

from __future__ import annotations

from typing import Any

from integrations.us_disaster import hifld


def find_nearby_hospitals(state: str = "CA") -> list[dict[str, Any]]:
    raw = hifld.get_hospitals_by_state(state)
    return [site.model_dump() for site in hifld.normalize_hospitals(raw)]


def list_critical_infrastructure_layers() -> list[dict[str, Any]]:
    return hifld.list_critical_infrastructure_layers()


def find_staging_candidates() -> list[dict[str, Any]]:
    layers = list_critical_infrastructure_layers()
    keywords = ("fire", "ems", "shelter", "school", "emergency", "eoc", "staging")
    return [
        layer
        for layer in layers
        if any(keyword in str(layer.get("name", "")).lower() for keyword in keywords)
    ]
