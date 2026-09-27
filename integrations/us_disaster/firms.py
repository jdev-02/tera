"""NASA FIRMS satellite fire detection adapter."""

from __future__ import annotations

import csv
import os
from io import StringIO
from typing import Any

from agent.mission_schemas import FireDetection
from integrations.common import http

FIRMS_AREA_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def get_viirs_fire_detections_bbox(
    bbox: tuple[float, float, float, float],
    days: int = 1,
) -> list[dict[str, Any]]:
    map_key = http.require_env("FIRMS_MAP_KEY", os.getenv("FIRMS_MAP_KEY"))
    bbox_text = ",".join(str(value) for value in bbox)
    text = http.get_text(f"{FIRMS_AREA_URL}/{map_key}/VIIRS_SNPP_NRT/{bbox_text}/{days}")
    return [item.model_dump() for item in parse_firms_csv(text)]


def parse_firms_csv(text: str) -> list[FireDetection]:
    detections: list[FireDetection] = []
    for row in csv.DictReader(StringIO(text)):
        lat = _optional_float(row.get("latitude"))
        lon = _optional_float(row.get("longitude"))
        if lat is None or lon is None:
            continue
        acquired_at = None
        acq_date = row.get("acq_date")
        acq_time = row.get("acq_time")
        if acq_date:
            acquired_at = f"{acq_date} {acq_time or ''}".strip()
        detections.append(
            FireDetection(
                latitude=lat,
                longitude=lon,
                brightness=_optional_float(row.get("bright_ti4") or row.get("brightness")),
                confidence=row.get("confidence"),
                satellite=row.get("satellite"),
                acquired_at=acquired_at,
                properties=dict(row),
            )
        )
    return detections


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
