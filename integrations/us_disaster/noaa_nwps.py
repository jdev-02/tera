"""NOAA National Water Prediction Service adapter."""

from __future__ import annotations

from typing import Any

from integrations.common import http

NWPS_DOCS_URL = "https://api.water.noaa.gov/nwps/v1/docs/"


def get_nwps_docs_or_health() -> dict[str, Any]:
    try:
        raw = http.get_json(NWPS_DOCS_URL)
    except http.ApiError:
        text = http.get_text(NWPS_DOCS_URL)
        return {
            "status": "ok",
            "content_type": "html",
            "bytes": len(text),
            "url": NWPS_DOCS_URL,
        }
    if isinstance(raw, dict):
        return raw
    return {"status": "ok", "raw": raw}


def todo_supported_endpoints() -> list[str]:
    return [
        "Inspect NWPS OpenAPI docs for observed/forecast flood endpoints.",
        "Add reach/station forecast lookup once stable schema is selected.",
    ]
