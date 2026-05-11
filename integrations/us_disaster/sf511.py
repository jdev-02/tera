"""SF Bay 511 traffic events adapter."""

from __future__ import annotations

import os
from typing import Any

from agent.mission_schemas import Coord, TrafficEvent
from integrations.common import http

SF511_URL = "https://api.511.org/traffic/events"


def get_traffic_events() -> dict[str, Any] | list[dict[str, Any]]:
    api_key = http.require_env("SF511_API_KEY", os.getenv("SF511_API_KEY"))
    raw = http.get_json(SF511_URL, params={"api_key": api_key})
    if not isinstance(raw, dict | list):
        raise http.ApiError("SF511 response was not an object or list")
    return raw


def normalize_traffic_events(raw: dict[str, Any] | list[dict[str, Any]]) -> list[TrafficEvent]:
    items: list[Any]
    if isinstance(raw, dict):
        items = raw.get("events") or raw.get("Events") or raw.get("data") or []
    else:
        items = raw
    events: list[TrafficEvent] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        events.append(
            TrafficEvent(
                id=str(item.get("id") or item.get("ID") or f"sf511-{index}"),
                event_type=_optional_str(item.get("event_type") or item.get("EventType")),
                description=_optional_str(item.get("description") or item.get("Description")),
                severity=_optional_str(item.get("severity") or item.get("Severity")),
                coord=_coord_from_item(item),
                properties=item,
            )
        )
    return events


def _coord_from_item(item: dict[str, Any]) -> Coord | None:
    lat = item.get("lat") or item.get("Latitude")
    lon = item.get("lon") or item.get("Longitude")
    if not isinstance(lat, int | float) or not isinstance(lon, int | float):
        return None
    return Coord(lat=float(lat), lon=float(lon))


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None
