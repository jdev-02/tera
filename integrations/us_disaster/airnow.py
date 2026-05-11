"""EPA AirNow API adapter."""

from __future__ import annotations

import os
from typing import Any

from agent.mission_schemas import AirQualityObservation
from integrations.common import http

AIRNOW_URL = "https://www.airnowapi.org/aq/observation/latLong/current/"


def get_current_air_quality(lat: float, lon: float, distance: int = 25) -> list[dict[str, Any]]:
    api_key = http.require_env("AIRNOW_API_KEY", os.getenv("AIRNOW_API_KEY"))
    raw = http.get_json(
        AIRNOW_URL,
        params={
            "format": "application/json",
            "latitude": lat,
            "longitude": lon,
            "distance": distance,
            "API_KEY": api_key,
        },
    )
    if not isinstance(raw, list):
        raise http.ApiError("AirNow response was not a list")
    return [item for item in raw if isinstance(item, dict)]


def normalize_air_quality(raw: list[dict[str, Any]]) -> list[AirQualityObservation]:
    observations: list[AirQualityObservation] = []
    for item in raw:
        category = item.get("Category")
        category_name = None
        if isinstance(category, dict):
            category_name = category.get("Name")
        observations.append(
            AirQualityObservation(
                parameter=str(item.get("ParameterName") or "AQI"),
                aqi=_optional_int(item.get("AQI")),
                category=str(category_name) if category_name else None,
                reporting_area=_optional_str(item.get("ReportingArea")),
                latitude=_optional_float(item.get("Latitude")),
                longitude=_optional_float(item.get("Longitude")),
                observed_at=_optional_str(item.get("DateObserved")),
            )
        )
    return observations


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
