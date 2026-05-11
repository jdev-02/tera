"""Google Maps Routes API adapter."""

from __future__ import annotations

import os
from typing import Any

from agent.mission_schemas import Coord, RouteCandidate
from integrations.common import http

ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"


def compute_routes(
    origin: Coord,
    destination: Coord,
    alternatives: bool = True,
) -> dict[str, Any]:
    api_key = http.require_env("GOOGLE_MAPS_API_KEY", os.getenv("GOOGLE_MAPS_API_KEY"))
    body = {
        "origin": {"location": {"latLng": {"latitude": origin.lat, "longitude": origin.lon}}},
        "destination": {
            "location": {"latLng": {"latitude": destination.lat, "longitude": destination.lon}}
        },
        "travelMode": "DRIVE",
        "computeAlternativeRoutes": alternatives,
        "routingPreference": "TRAFFIC_AWARE",
    }
    raw = http.post_json(
        ROUTES_URL,
        json_body=body,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": (
                "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,"
                "routes.description"
            ),
        },
    )
    if not isinstance(raw, dict):
        raise http.ApiError("Google Maps Routes response was not an object")
    return raw


def normalize_routes(raw: dict[str, Any]) -> list[RouteCandidate]:
    candidates: list[RouteCandidate] = []
    for index, route in enumerate(raw.get("routes", [])):
        if not isinstance(route, dict):
            continue
        duration_s = _parse_duration_seconds(route.get("duration"))
        polyline = route.get("polyline", {})
        encoded = polyline.get("encodedPolyline") if isinstance(polyline, dict) else None
        candidates.append(
            RouteCandidate(
                id=f"google-route-{index + 1}",
                provider="google_maps_routes",
                distance_m=_optional_float(route.get("distanceMeters")),
                duration_s=duration_s,
                polyline=str(encoded) if encoded else None,
                summary=_optional_str(route.get("description")),
            )
        )
    return candidates


def _parse_duration_seconds(value: Any) -> float | None:
    if isinstance(value, str) and value.endswith("s"):
        try:
            return float(value[:-1])
        except ValueError:
            return None
    return _optional_float(value)


def _optional_float(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None
