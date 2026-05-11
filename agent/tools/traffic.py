"""Traffic-event tools for route risk scoring."""

from __future__ import annotations

from typing import Any

from integrations.us_disaster import sf511


def get_road_events() -> list[dict[str, Any]]:
    raw = sf511.get_traffic_events()
    return [event.model_dump() for event in sf511.normalize_traffic_events(raw)]


def score_traffic_risk(route: dict[str, Any], events: list[dict[str, Any]]) -> str:
    route_text = str(route).lower()
    relevant = [
        event
        for event in events
        if any(token in route_text for token in str(event.get("description", "")).lower().split())
    ]
    if len(relevant) >= 3:
        return "high"
    if relevant:
        return "moderate"
    return "low"
