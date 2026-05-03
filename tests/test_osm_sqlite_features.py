from __future__ import annotations

import sqlite3
import struct
from pathlib import Path

from routing.osm_sqlite_features import (
    classify_osm_tags,
    discover_layers,
    query_osm_features,
)
from security.structured_query_validator import validate_route_query


def _wkb_point(lon: float, lat: float) -> bytes:
    return b"\x01" + struct.pack("<I", 1) + struct.pack("<dd", lon, lat)


def _wkb_line(points: list[tuple[float, float]]) -> bytes:
    data = b"\x01" + struct.pack("<I", 2) + struct.pack("<I", len(points))
    for lon, lat in points:
        data += struct.pack("<dd", lon, lat)
    return data


def _gpkg_geom(wkb: bytes) -> bytes:
    return b"GP\x00\x01" + struct.pack("<I", 4326) + wkb


def _build_fixture(path: Path) -> None:
    conn = sqlite3.connect(path)
    with conn:
        conn.executescript(
            """
            CREATE TABLE gpkg_geometry_columns (
              table_name TEXT,
              column_name TEXT,
              geometry_type_name TEXT,
              srs_id INTEGER,
              z INTEGER,
              m INTEGER
            );

            CREATE TABLE lines (
              id INTEGER PRIMARY KEY,
              geom BLOB NOT NULL,
              name TEXT,
              waterway TEXT,
              natural TEXT,
              access TEXT
            );

            CREATE TABLE points (
              id INTEGER PRIMARY KEY,
              geom BLOB NOT NULL,
              name TEXT,
              amenity TEXT,
              man_made TEXT,
              tourism TEXT,
              natural TEXT,
              "tower:type" TEXT,
              tags TEXT
            );
            """
        )
        conn.execute(
            "INSERT INTO gpkg_geometry_columns VALUES ('lines', 'geom', 'LINESTRING', 4326, 0, 0)"
        )
        conn.execute(
            "INSERT INTO gpkg_geometry_columns VALUES ('points', 'geom', 'POINT', 4326, 0, 0)"
        )
        conn.execute(
            """
            INSERT INTO lines (id, geom, name, waterway, natural, access)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                _gpkg_geom(_wkb_line([(-122.4000, 37.7900), (-122.4010, 37.7910)])),
                "Demo Creek",
                "stream",
                None,
                None,
            ),
        )
        conn.execute(
            """
            INSERT INTO lines (id, geom, name, waterway, natural, access)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                2,
                _gpkg_geom(_wkb_line([(-122.4020, 37.7900), (-122.4030, 37.7910)])),
                "Demo Coast",
                None,
                "coastline",
                None,
            ),
        )
        conn.execute(
            """
            INSERT INTO points
              (id, geom, name, amenity, man_made, tourism, natural, "tower:type", tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                10,
                _gpkg_geom(_wkb_point(-122.3990, 37.7890)),
                "Demo Clinic",
                "clinic",
                None,
                None,
                None,
                None,
                None,
            ),
        )
        conn.execute(
            """
            INSERT INTO points
              (id, geom, name, amenity, man_made, tourism, natural, "tower:type", tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                11,
                _gpkg_geom(_wkb_point(-122.3980, 37.7880)),
                "Demo Radio Tower",
                None,
                "tower",
                None,
                None,
                "communication",
                None,
            ),
        )
        conn.execute(
            """
            INSERT INTO points
              (id, geom, name, amenity, man_made, tourism, natural, "tower:type", tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                12,
                _gpkg_geom(_wkb_point(-122.3970, 37.7870)),
                "Demo Peak",
                None,
                None,
                None,
                "peak",
                None,
                '{"access": "private", "operator_note": "visible landmark"}',
            ),
        )
    conn.close()


def test_discovers_geopackage_layers(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "osm.gpkg"
    _build_fixture(sqlite_path)

    layers = discover_layers(sqlite_path)

    assert {(layer.table_name, layer.geometry_column) for layer in layers} == {
        ("lines", "geom"),
        ("points", "geom"),
    }


def test_queries_freshwater_without_returning_saltwater(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "osm.gpkg"
    _build_fixture(sqlite_path)

    features = query_osm_features(
        target_type="freshwater",
        origin={"lat": 37.7900, "lon": -122.4000},
        radius_m=2000,
        paths=[sqlite_path],
    )

    assert [feature.name for feature in features] == ["Demo Creek"]
    assert features[0].tags["waterway"] == "stream"


def test_queries_broad_prompt_targets(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "osm.gpkg"
    _build_fixture(sqlite_path)
    origin = {"lat": 37.7900, "lon": -122.4000}

    medical = query_osm_features(
        target_type="medical",
        origin=origin,
        radius_m=2000,
        paths=[sqlite_path],
    )
    signal = query_osm_features(
        target_type="signal",
        origin=origin,
        radius_m=2000,
        paths=[sqlite_path],
    )
    high_ground = query_osm_features(
        target_type="high_ground",
        origin=origin,
        radius_m=2000,
        paths=[sqlite_path],
    )

    assert medical[0].name == "Demo Clinic"
    assert signal[0].name == "Demo Radio Tower"
    assert high_ground[0].name == "Demo Peak"
    assert high_ground[0].tags["access"] == "private"


def test_classifies_common_osm_feature_tags() -> None:
    assert "shelter" in classify_osm_tags({"tourism": "alpine_hut", "name": "Hut"})
    assert "lz" in classify_osm_tags({"aeroway": "helipad"})
    assert "hazard" in classify_osm_tags({"natural": "cliff"})
    assert "land_access" in classify_osm_tags({"access": "private"})
    assert "road" in classify_osm_tags({"highway": "primary"})
    assert "trail" in classify_osm_tags({"highway": "path"})


def test_route_query_schema_accepts_survival_prompt_catalog_targets() -> None:
    query = {
        "mission_type": "search_and_rescue",
        "objective": "safest",
        "destination_type": "lz",
        "mode": "litter_team",
        "max_distance_km": 5,
        "constraints": ["avoid_steep_terrain", "prefer_open_ground"],
        "allowed_data_layers": ["osm_features", "terrain", "landcover"],
        "authority_context": {"user_role": "team_lead", "requires_approval": True},
    }

    assert validate_route_query(query) == {"valid": True, "errors": []}
