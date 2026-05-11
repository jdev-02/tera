"""NIFC/WFIGS current fire perimeter adapter."""

from __future__ import annotations

from typing import Any

from agent.mission_schemas import HazardPolygon
from integrations.common import http

WFIGS_URL = (
    "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/"
    "WFIGS_Interagency_Perimeters_Current/FeatureServer/0/query"
)


def get_current_fire_perimeters() -> dict[str, Any]:
    raw = http.get_json(WFIGS_URL, params={"where": "1=1", "outFields": "*", "f": "geojson"})
    if not isinstance(raw, dict):
        raise http.ApiError("WFIGS response was not an object")
    return raw


def normalize_fire_perimeters(raw: dict[str, Any]) -> list[HazardPolygon]:
    polygons: list[HazardPolygon] = []
    for index, feature in enumerate(raw.get("features", [])):
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties", {})
        if not isinstance(props, dict):
            props = {}
        polygons.append(
            HazardPolygon(
                id=str(props.get("poly_IRWINID") or props.get("OBJECTID") or f"wfigs-{index}"),
                source="NIFC WFIGS",
                name=str(
                    props.get("poly_IncidentName") or props.get("IncidentName") or "Fire perimeter"
                ),
                incident_type="wildfire",
                geometry=feature.get("geometry")
                if isinstance(feature.get("geometry"), dict)
                else None,
                properties=props,
            )
        )
    return polygons
