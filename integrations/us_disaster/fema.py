"""FEMA OpenFEMA adapter."""

from __future__ import annotations

from typing import Any

from agent.mission_schemas import DisasterDeclaration
from integrations.common import http

FEMA_DATASET = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"


def get_recent_disaster_declarations(top: int = 5) -> dict[str, Any]:
    raw = http.get_json(FEMA_DATASET, params={"$top": top})
    if not isinstance(raw, dict):
        raise http.ApiError("FEMA response was not an object")
    return raw


def get_declarations_by_state(state: str = "CA", top: int = 5) -> dict[str, Any]:
    raw = http.get_json(
        FEMA_DATASET,
        params={"$filter": f"state eq '{state.upper()}'", "$top": top},
    )
    if not isinstance(raw, dict):
        raise http.ApiError("FEMA state response was not an object")
    return raw


def get_fire_declarations_by_state(state: str = "CA", top: int = 5) -> dict[str, Any]:
    raw = http.get_json(
        FEMA_DATASET,
        params={
            "$filter": f"state eq '{state.upper()}' and incidentType eq 'Fire'",
            "$top": top,
        },
    )
    if not isinstance(raw, dict):
        raise http.ApiError("FEMA fire response was not an object")
    return raw


def normalize_declarations(raw: dict[str, Any]) -> list[DisasterDeclaration]:
    declarations: list[DisasterDeclaration] = []
    rows = raw.get("value") or raw.get("DisasterDeclarationsSummaries") or []
    for index, item in enumerate(rows):
        if not isinstance(item, dict):
            continue
        disaster_number = item.get("disasterNumber")
        declarations.append(
            DisasterDeclaration(
                id=str(disaster_number or f"fema-{index}"),
                state=_optional_str(item.get("state")),
                county=_optional_str(item.get("designatedArea")),
                incident_type=_optional_str(item.get("incidentType")),
                title=_optional_str(item.get("declarationTitle")),
                declaration_date=_optional_str(item.get("declarationDate")),
                incident_begin_date=_optional_str(item.get("incidentBeginDate")),
            )
        )
    return declarations


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None
