"""ReliefWeb humanitarian reports adapter."""

from __future__ import annotations

import os
from typing import Any

from agent.mission_schemas import HumanitarianReport
from integrations.common import http

RELIEFWEB_REPORTS_URL = "https://api.reliefweb.int/v2/reports"


def get_recent_us_reports(limit: int = 5) -> dict[str, Any]:
    appname = os.getenv("RELIEFWEB_APPNAME")
    if not appname:
        return {
            "skipped": "missing_RELIEFWEB_APPNAME",
            "data": [],
            "note": "ReliefWeb v2 requires a pre-approved appname.",
        }
    body = {
        "limit": limit,
        "sort": ["date:desc"],
        "filter": {"field": "country.name", "value": "United States of America"},
        "fields": {"include": ["title", "date", "url", "country", "disaster"]},
    }
    raw = http.post_json(
        f"{RELIEFWEB_REPORTS_URL}?appname={appname}",
        json_body=body,
        headers={"Content-Type": "application/json"},
    )
    if not isinstance(raw, dict):
        raise http.ApiError("ReliefWeb response was not an object")
    return raw


def normalize_reports(raw: dict[str, Any]) -> list[HumanitarianReport]:
    reports: list[HumanitarianReport] = []
    for index, item in enumerate(raw.get("data", [])):
        if not isinstance(item, dict):
            continue
        fields = item.get("fields", {})
        if not isinstance(fields, dict):
            fields = {}
        reports.append(
            HumanitarianReport(
                id=str(item.get("id") or f"reliefweb-{index}"),
                title=str(fields.get("title") or "Humanitarian report"),
                date=_optional_str(fields.get("date")),
                url=_optional_str(fields.get("url")),
                country=_field_name(fields.get("country")),
                disaster=_field_name(fields.get("disaster")),
            )
        )
    return reports


def _field_name(value: Any) -> str | None:
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return _optional_str(first.get("name"))
    if isinstance(value, dict):
        return _optional_str(value.get("name"))
    return _optional_str(value)


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None
