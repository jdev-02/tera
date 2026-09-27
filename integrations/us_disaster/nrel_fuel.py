"""NREL Alternative Fuel Stations API adapter."""

from __future__ import annotations

import os
from typing import Any

from agent.mission_schemas import Coord, FuelStation
from integrations.common import http

NREL_NEAREST_URL = "https://developer.nrel.gov/api/alt-fuel-stations/v1/nearest.json"


def get_nearest_fuel_stations(lat: float, lon: float, radius: int = 50) -> dict[str, Any]:
    api_key = http.require_env("NREL_API_KEY", os.getenv("NREL_API_KEY"))
    raw = http.get_json(
        NREL_NEAREST_URL,
        params={
            "api_key": api_key,
            "latitude": lat,
            "longitude": lon,
            "fuel_type": "LNG,CNG,BD,RD,LPG,ELEC",
            "radius": radius,
        },
    )
    if not isinstance(raw, dict):
        raise http.ApiError("NREL response was not an object")
    return raw


def normalize_fuel_stations(raw: dict[str, Any]) -> list[FuelStation]:
    stations: list[FuelStation] = []
    for index, item in enumerate(raw.get("fuel_stations", [])):
        if not isinstance(item, dict):
            continue
        stations.append(
            FuelStation(
                id=str(item.get("id") or f"nrel-{index}"),
                name=str(item.get("station_name") or "Fuel station"),
                fuel_types=_fuel_types(item),
                address=_optional_str(item.get("street_address")),
                coord=_coord_from_item(item),
                distance_miles=_optional_float(item.get("distance")),
            )
        )
    return stations


def _fuel_types(item: dict[str, Any]) -> list[str]:
    code = item.get("fuel_type_code")
    groups = item.get("groups_with_access_code")
    values = [value for value in (code, groups) if value]
    return [str(value) for value in values]


def _coord_from_item(item: dict[str, Any]) -> Coord | None:
    lat = _optional_float(item.get("latitude"))
    lon = _optional_float(item.get("longitude"))
    if lat is None or lon is None:
        return None
    return Coord(lat=lat, lon=lon)


def _optional_float(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None
