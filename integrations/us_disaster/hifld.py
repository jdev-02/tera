"""HIFLD hospital and critical infrastructure adapters."""

from __future__ import annotations

from typing import Any

from agent.mission_schemas import Coord, InfrastructureSite
from integrations.common import http

HOSPITALS_URL = (
    "https://services.arcgis.com/XG15cJAlne2vxtgt/ArcGIS/rest/services/"
    "Hospitals_hifld/FeatureServer/0/query"
)
CRITICAL_INFRA_URL = (
    "https://services.arcgis.com/XG15cJAlne2vxtgt/ArcGIS/rest/services/"
    "Critical_Infrastructure_Map_Service/FeatureServer"
)


def get_hospitals_by_state(state: str = "CA") -> dict[str, Any]:
    raw = http.get_json(
        HOSPITALS_URL,
        params={
            "where": f"STATE='{state.upper()}'",
            "outFields": "NAME,ADDRESS,CITY,STATE,TYPE",
            "f": "geojson",
        },
    )
    if not isinstance(raw, dict):
        raise http.ApiError("HIFLD hospitals response was not an object")
    return raw


def normalize_hospitals(raw: dict[str, Any]) -> list[InfrastructureSite]:
    sites: list[InfrastructureSite] = []
    for index, feature in enumerate(raw.get("features", [])):
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties", {})
        if not isinstance(props, dict):
            props = {}
        sites.append(
            InfrastructureSite(
                id=str(props.get("ID") or props.get("OBJECTID") or f"hifld-hospital-{index}"),
                name=str(props.get("NAME") or "Hospital"),
                category="hospital",
                address=_optional_str(props.get("ADDRESS")),
                city=_optional_str(props.get("CITY")),
                state=_optional_str(props.get("STATE")),
                site_type=_optional_str(props.get("TYPE")),
                coord=_coord_from_feature(feature),
                properties=props,
            )
        )
    return sites


def get_critical_infrastructure_layers() -> dict[str, Any]:
    raw = http.get_json(CRITICAL_INFRA_URL, params={"f": "json"})
    if not isinstance(raw, dict):
        raise http.ApiError("HIFLD critical infrastructure response was not an object")
    return raw


def list_critical_infrastructure_layers() -> list[dict[str, Any]]:
    raw = get_critical_infrastructure_layers()
    layers = raw.get("layers", [])
    return [layer for layer in layers if isinstance(layer, dict)]


def query_critical_infrastructure_layer(
    layer_id: int,
    where: str = "1=1",
    out_fields: str = "*",
) -> dict[str, Any]:
    raw = http.get_json(
        f"{CRITICAL_INFRA_URL}/{layer_id}/query",
        params={"where": where, "outFields": out_fields, "f": "geojson"},
    )
    if not isinstance(raw, dict):
        raise http.ApiError("HIFLD critical infrastructure layer response was not an object")
    return raw


def _coord_from_feature(feature: dict[str, Any]) -> Coord | None:
    geometry = feature.get("geometry")
    if not isinstance(geometry, dict):
        return None
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return None
    lon = coordinates[0]
    lat = coordinates[1]
    if not isinstance(lat, int | float) or not isinstance(lon, int | float):
        return None
    return Coord(lat=float(lat), lon=float(lon))


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None
