"""Stub implementations of the geospatial tools.

These return synthetic data so the orchestrator + ATAK bridge can be exercised
end-to-end before Ben fills in the real Valhalla / OSM / DEM logic. The
function signatures here are the CONTRACT with Ben's lane; changes need
signoff from both lane owners (Jon for the schema, Ben for the impl).

Each stub returns a structurally valid response that matches what the real
implementation will return. Tests should mock these; the orchestrator should
NOT special-case stubs vs real impls.
"""

from __future__ import annotations

import math
from typing import Any

# Common SF anchor used by the freshwater stub. When Ben replaces with real
# OSM lookup, this constant goes away.
_SF_LOBOS_CREEK = (37.7896, -122.4824)


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in meters between two (lat, lon) points."""
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


def find_pois(
    type: str,
    from_: dict[str, float],
    radius_m: float,
) -> list[dict[str, Any]]:
    """Find POIs of `type` within `radius_m` of `from_` (a Coord dict).

    Real impl: queries the local OSM PBF via osmium / Overpass-on-disk.

    Stub: returns one synthetic POI matching the type if the radius covers
    a hardcoded SF anchor; empty list otherwise. Always returns the contract
    shape so callers can be written against the real interface today.
    """
    origin = (from_["lat"], from_["lon"])

    if type == "freshwater":
        target = _SF_LOBOS_CREEK
        d = _haversine_m(origin, target)
        if d <= radius_m:
            return [
                {
                    "name": "Lobos Creek",
                    "lat": target[0],
                    "lon": target[1],
                    "tags": {"natural": "spring", "name": "Lobos Creek"},
                    "distance_m": round(d, 1),
                }
            ]
        return []

    # Other types not stubbed yet -- return empty so callers see "no results"
    # rather than a synthetic answer that may not match the real world.
    return []


def route(
    profile: str,
    start: dict[str, float],
    end: dict[str, float],
    avoid: list[str] | None = None,
    data_layers: list[str] | None = None,
) -> dict[str, Any]:
    """Compute a route between two coords with the given profile + avoidances.

    Real impl: calls local Valhalla with a custom cost model that consumes
    the data_layers (slope from DEM, ridgeline prominence, cover, etc.).

    Stub: returns a 2-point GeoJSON LineString and synthetic cost numbers.
    The shape matches what real Valhalla output will look like.
    """
    avoid = avoid or []
    data_layers = data_layers or []

    # Synthetic geometry: just a straight line from start to end.
    coords: list[list[float]] = [
        [start["lon"], start["lat"]],
        [end["lon"], end["lat"]],
    ]
    distance_m = _haversine_m((start["lat"], start["lon"]), (end["lat"], end["lon"]))
    # Foot speed ~1.1 m/s (4 kph); vehicle ~10 m/s.
    speed_mps = 1.1 if profile.startswith("foot") else 10.0
    time_s = distance_m / speed_mps

    return {
        "feature": {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "profile": profile,
                "stub": True,
                "avoid": avoid,
                "data_layers": data_layers,
            },
        },
        "cost_breakdown": {
            "distance_m": round(distance_m, 1),
            "time_s": round(time_s, 1),
            "elevation_gain_m": 0.0,  # stub
        },
    }


def terrain_query(
    geom: dict[str, Any],
) -> dict[str, Any]:
    """Compute slope / prominence / cover stats for a GeoJSON geometry.

    Real impl: rasterizes the geometry against the DEM + landcover and
    returns aggregate stats. Used by the routing cost model.

    Stub: returns plausible synthetic stats. Shape matches real output.
    """
    return {
        "max_slope_deg": 12.5,
        "mean_slope_deg": 4.0,
        "max_prominence_m": 30.0,
        "cover_fraction": 0.75,
        "stub": True,
    }
