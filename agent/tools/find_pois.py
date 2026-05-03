"""POI lookup tool backed by local OSM SQLite feature packages."""

from __future__ import annotations

from typing import Any

from agent.tools.stubs import find_pois as _stub_find_pois
from routing.osm_sqlite_features import configured_sqlite_paths, query_osm_features


def find_pois(
    type: str,
    from_: dict[str, float],
    radius_m: float,
    limit: int = 10,
    filters: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Find nearby features of `type` around `from_`.

    If no local OSM SQLite package is configured, fall back to the legacy demo
    stub so existing smoke tests and phase-1 demos still produce a route.
    """
    _ = filters  # Reserved for schema-validated tag filters in the next routing slice.

    if not configured_sqlite_paths():
        return _stub_find_pois(type=type, from_=from_, radius_m=radius_m)

    features = query_osm_features(
        target_type=type,
        origin=from_,
        radius_m=radius_m,
        limit=limit,
    )
    return [feature.to_poi() for feature in features]
