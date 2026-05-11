"""USGS earthquake feed adapter."""

from __future__ import annotations

from typing import Any

from agent.mission_schemas import Coord, EarthquakeEvent
from integrations.common import http

SIGNIFICANT_WEEK_URL = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson"
)


def get_significant_earthquakes_week() -> dict[str, Any]:
    raw = http.get_json(SIGNIFICANT_WEEK_URL)
    if not isinstance(raw, dict):
        raise http.ApiError("USGS earthquake response was not an object")
    return raw


def normalize_earthquakes(raw: dict[str, Any]) -> list[EarthquakeEvent]:
    events: list[EarthquakeEvent] = []
    for index, feature in enumerate(raw.get("features", [])):
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties", {})
        if not isinstance(props, dict):
            props = {}
        coord, depth_km = _coord_from_feature(feature)
        events.append(
            EarthquakeEvent(
                id=str(feature.get("id") or f"usgs-quake-{index}"),
                magnitude=_optional_float(props.get("mag")),
                place=_optional_str(props.get("place")),
                time=_optional_int(props.get("time")),
                coord=coord,
                depth_km=depth_km,
                url=_optional_str(props.get("url")),
            )
        )
    return events


def _coord_from_feature(feature: dict[str, Any]) -> tuple[Coord | None, float | None]:
    geometry = feature.get("geometry")
    if not isinstance(geometry, dict):
        return None, None
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return None, None
    lon = _optional_float(coordinates[0])
    lat = _optional_float(coordinates[1])
    depth = _optional_float(coordinates[2]) if len(coordinates) > 2 else None
    if lat is None or lon is None:
        return None, depth
    return Coord(lat=lat, lon=lon), depth


def _optional_float(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _optional_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return None


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None
