"""National Bridge Inventory sample adapter."""

from __future__ import annotations

from typing import Any

from agent.mission_schemas import BridgeAsset
from integrations.common import http

BRIDGE_SAMPLE_URL = (
    "https://services.arcgis.com/xOi1kZaI0eWDREZv/ArcGIS/rest/services/"
    "NTAD_National_Bridge_Inventory/FeatureServer/0/query"
)


def get_bridge_inventory_sample(limit: int = 10) -> list[dict[str, Any]]:
    raw = http.get_json(
        BRIDGE_SAMPLE_URL,
        params={
            "where": "1=1",
            "outFields": (
                "STRUCTURE_NUMBER_008,FACILITY_CARRIED_007,STATE_CODE_001,"
                "COUNTY_CODE_003,FEATURES_DESC_006A"
            ),
            "f": "json",
            "resultRecordCount": limit,
        },
    )
    if not isinstance(raw, dict):
        raise http.ApiError("National Bridge Inventory response was not an object")
    rows: list[dict[str, Any]] = []
    for feature in raw.get("features", []):
        if isinstance(feature, dict) and isinstance(feature.get("attributes"), dict):
            rows.append(feature["attributes"])
    return rows


def normalize_bridges(raw: list[dict[str, Any]]) -> list[BridgeAsset]:
    bridges: list[BridgeAsset] = []
    for index, item in enumerate(raw):
        bridges.append(
            BridgeAsset(
                id=str(
                    item.get("structure_number_008")
                    or item.get("STRUCTURE_NUMBER_008")
                    or item.get("objectid")
                    or f"bridge-{index}"
                ),
                name=_optional_str(
                    item.get("facility_carried_by_structure_007")
                    or item.get("FACILITY_CARRIED_007")
                ),
                state=_optional_str(item.get("state_code_001") or item.get("STATE_CODE_001")),
                county=_optional_str(item.get("county_code_003") or item.get("COUNTY_CODE_003")),
                route=_optional_str(
                    item.get("features_desc_006a") or item.get("FEATURES_DESC_006A")
                ),
                condition=_optional_str(item.get("bridge_condition")),
                properties=item,
            )
        )
    return bridges


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None
