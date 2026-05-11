"""USGS water services adapter."""

from __future__ import annotations

from typing import Any

from agent.mission_schemas import WaterObservation
from integrations.common import http

USGS_WATER_URL = "https://waterservices.usgs.gov/nwis/iv/"


def get_streamflow_and_gage_height(state: str = "ca") -> dict[str, Any]:
    raw = http.get_json(
        USGS_WATER_URL,
        params={
            "format": "json",
            "stateCd": state.lower(),
            "parameterCd": "00060,00065",
            "siteStatus": "active",
        },
    )
    if not isinstance(raw, dict):
        raise http.ApiError("USGS water response was not an object")
    return raw


def normalize_water_observations(raw: dict[str, Any]) -> list[WaterObservation]:
    observations: list[WaterObservation] = []
    time_series = raw.get("value", {}).get("timeSeries", [])
    if not isinstance(time_series, list):
        return observations
    for index, series in enumerate(time_series):
        if not isinstance(series, dict):
            continue
        source_info = series.get("sourceInfo", {})
        variable = series.get("variable", {})
        values = series.get("values", [])
        latest_value = _latest_value(values)
        if not isinstance(source_info, dict):
            source_info = {}
        if not isinstance(variable, dict):
            variable = {}
        observations.append(
            WaterObservation(
                site_id=str(
                    source_info.get("siteCode", [{}])[0].get("value") or f"usgs-water-{index}"
                ),
                site_name=_optional_str(source_info.get("siteName")),
                parameter=_optional_str(variable.get("variableName")),
                value=_optional_float(latest_value.get("value")) if latest_value else None,
                unit=_optional_str(variable.get("unit", {}).get("unitCode"))
                if isinstance(variable.get("unit"), dict)
                else None,
                observed_at=_optional_str(latest_value.get("dateTime")) if latest_value else None,
            )
        )
    return observations


def _latest_value(values: Any) -> dict[str, Any] | None:
    if not isinstance(values, list) or not values:
        return None
    first_group = values[0]
    if not isinstance(first_group, dict):
        return None
    raw_values = first_group.get("value", [])
    if not isinstance(raw_values, list) or not raw_values:
        return None
    latest = raw_values[-1]
    return latest if isinstance(latest, dict) else None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None
