"""NOAA/NWS Alerts API adapter."""

from __future__ import annotations

from typing import Any

from agent.mission_schemas import HazardAlert
from integrations.common import http

NWS_BASE = "https://api.weather.gov"


def get_active_alerts(area: str = "CA") -> dict[str, Any]:
    raw = http.get_json(f"{NWS_BASE}/alerts/active", params={"area": area.upper()})
    if not isinstance(raw, dict):
        raise http.ApiError("NWS alerts response was not an object")
    return raw


def get_point_metadata(lat: float, lon: float) -> dict[str, Any]:
    raw = http.get_json(f"{NWS_BASE}/points/{lat},{lon}")
    if not isinstance(raw, dict):
        raise http.ApiError("NWS points response was not an object")
    return raw


def normalize_alerts(raw: dict[str, Any]) -> list[HazardAlert]:
    alerts: list[HazardAlert] = []
    for index, feature in enumerate(raw.get("features", [])):
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties", {})
        if not isinstance(props, dict):
            props = {}
        alerts.append(
            HazardAlert(
                id=str(props.get("id") or feature.get("id") or f"nws-{index}"),
                event=str(props.get("event") or "Weather alert"),
                severity=_string_or_none(props.get("severity")),
                urgency=_string_or_none(props.get("urgency")),
                certainty=_string_or_none(props.get("certainty")),
                area_desc=_string_or_none(props.get("areaDesc")),
                instruction=_string_or_none(props.get("instruction")),
                geometry=feature.get("geometry")
                if isinstance(feature.get("geometry"), dict)
                else None,
            )
        )
    return alerts


def _string_or_none(value: Any) -> str | None:
    return str(value) if value is not None else None
