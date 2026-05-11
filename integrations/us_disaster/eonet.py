"""NASA EONET event adapter."""

from __future__ import annotations

from typing import Any

from agent.mission_schemas import NaturalEvent
from integrations.common import http

EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"


def get_open_events(limit: int = 20) -> dict[str, Any]:
    raw = http.get_json(EONET_URL, params={"status": "open", "limit": limit})
    if not isinstance(raw, dict):
        raise http.ApiError("EONET response was not an object")
    return raw


def normalize_events(raw: dict[str, Any]) -> list[NaturalEvent]:
    events: list[NaturalEvent] = []
    for index, item in enumerate(raw.get("events", [])):
        if not isinstance(item, dict):
            continue
        categories = item.get("categories", [])
        category = None
        if isinstance(categories, list) and categories and isinstance(categories[0], dict):
            category = categories[0].get("title")
        geometry = item.get("geometry", [])
        events.append(
            NaturalEvent(
                id=str(item.get("id") or f"eonet-{index}"),
                title=str(item.get("title") or "Natural event"),
                category=str(category) if category else None,
                geometry={"items": geometry} if isinstance(geometry, list) else None,
                properties=item,
            )
        )
    return events
