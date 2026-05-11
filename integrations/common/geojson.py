"""Tiny GeoJSON utilities used by disaster adapters and fallbacks."""

from __future__ import annotations

from typing import Any


def point_feature(lon: float, lat: float, properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": properties,
    }


def feature_collection(features: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": features}
