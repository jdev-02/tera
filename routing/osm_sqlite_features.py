"""Offline OSM feature queries over SQLite-backed vector files.

The Jetson runtime cannot depend on outbound map services. This module reads
local OSM SQLite packages directly, classifies all tag-bearing features into
operator-relevant target classes, and returns nearby candidates for the agent
tool layer.

Supported geometry encodings:
- GeoPackage binary geometry
- raw WKB / EWKB
- WKT text
- GeoJSON text

SpatiaLite metadata is discovered, and simple SpatiaLite blobs are decoded
when they contain a WKB-like payload. Features with unsupported geometry are
skipped rather than failing a whole prompt.
"""

from __future__ import annotations

import glob
import json
import math
import os
import re
import sqlite3
import struct
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_DATA_GLOBS = (
    "data/extracts/*.gpkg",
    "data/extracts/*.sqlite",
    "data/extracts/*.sqlite3",
    "data/extracts/*.db",
)

GEOMETRY_COLUMN_CANDIDATES = (
    "geom",
    "geometry",
    "wkb_geometry",
    "the_geom",
    "shape",
)

TAG_BLOB_COLUMNS = ("tags", "other_tags", "all_tags", "properties")

TARGET_ALIASES = {
    "freshwater": "water",
    "safe_zone": "shelter",
    "trailhead": "trailhead",
    "high_ground": "high_ground",
    "named_feature": "named_feature",
}

VALID_TARGET_TYPES = {
    "any",
    "water",
    "freshwater",
    "shelter",
    "medical",
    "road",
    "trail",
    "trailhead",
    "settlement",
    "building",
    "signal",
    "high_ground",
    "clearing",
    "lz",
    "campsite",
    "bridge",
    "ford",
    "barrier",
    "hazard",
    "land_access",
    "named_feature",
}


@dataclass(frozen=True)
class LayerInfo:
    table_name: str
    geometry_column: str
    geometry_type: str | None = None


@dataclass(frozen=True)
class GeometrySummary:
    geometry_type: str
    centroid_lon: float
    centroid_lat: float
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float
    point_count: int


@dataclass(frozen=True)
class OsmFeature:
    name: str | None
    lat: float
    lon: float
    geometry_type: str
    source_path: str
    source_layer: str
    source_id: str | int | None
    tags: dict[str, str]
    entity_types: tuple[str, ...]
    distance_m: float

    def to_poi(self) -> dict[str, Any]:
        """Return the shape consumed by the existing agent orchestrator."""
        label = self.name or _label_from_tags(self.tags) or self.entity_types[0]
        return {
            "name": label,
            "lat": self.lat,
            "lon": self.lon,
            "tags": self.tags,
            "distance_m": round(self.distance_m, 1),
            "entity_types": list(self.entity_types),
            "geometry_type": self.geometry_type,
            "source_layer": self.source_layer,
            "source_id": self.source_id,
        }


def configured_sqlite_paths() -> list[Path]:
    """Return configured local OSM SQLite files.

    `TERA_OSM_SQLITE_PATHS` accepts an OS-pathsep-separated list. If unset, the
    repo's AOI extract directory is searched for common SQLite vector suffixes.
    """
    configured = os.getenv("TERA_OSM_SQLITE_PATHS") or os.getenv("WAYFINDER_OSM_SQLITE_PATHS")
    if configured:
        return [Path(part) for part in configured.split(os.pathsep) if part.strip()]

    paths: list[Path] = []
    for pattern in DEFAULT_DATA_GLOBS:
        paths.extend(Path(p) for p in glob.glob(pattern))
    return sorted({path for path in paths if path.is_file()})


def normalize_target_type(target_type: str) -> str:
    normalized = target_type.strip().lower().replace("-", "_")
    return TARGET_ALIASES.get(normalized, normalized)


def query_osm_features(
    *,
    target_type: str,
    origin: Mapping[str, float],
    radius_m: float,
    limit: int = 10,
    paths: Iterable[Path] | None = None,
) -> list[OsmFeature]:
    """Find nearby OSM features from local SQLite files.

    The caller supplies a validated target type and bounded radius. This
    function never executes user-provided SQL; table and column names come only
    from SQLite metadata in local field packages.
    """
    normalized_target = normalize_target_type(target_type)
    if normalized_target not in VALID_TARGET_TYPES:
        return []

    origin_lat = float(origin["lat"])
    origin_lon = float(origin["lon"])
    max_rows_per_layer = int(os.getenv("TERA_OSM_MAX_ROWS_PER_LAYER", "50000"))
    features: list[OsmFeature] = []

    for path in paths if paths is not None else configured_sqlite_paths():
        if not path.is_file():
            continue
        features.extend(
            _query_one_path(
                path=path,
                target_type=normalized_target,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                radius_m=radius_m,
                max_rows_per_layer=max_rows_per_layer,
            )
        )

    features.sort(key=lambda feature: _rank_feature(feature, normalized_target))
    return features[:limit]


def discover_layers(path: Path) -> list[LayerInfo]:
    """Inspect a SQLite vector package and return feature layers."""
    if not path.is_file():
        return []
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        return _discover_layers(conn)


def classify_osm_tags(tags: Mapping[str, str], geometry_type: str | None = None) -> tuple[str, ...]:
    """Classify raw OSM tags into broad prompt target classes.

    Raw tags are still preserved. This classifier only adds deterministic
    operator categories so prompts can search by intent rather than by exact
    OSM key/value names.
    """
    tag = {str(k).lower(): str(v).lower() for k, v in tags.items() if v is not None}
    classes: set[str] = set()

    waterway = tag.get("waterway")
    natural = tag.get("natural")
    highway = tag.get("highway")
    amenity = tag.get("amenity")
    tourism = tag.get("tourism")
    emergency = tag.get("emergency")
    healthcare = tag.get("healthcare")
    man_made = tag.get("man_made")
    landuse = tag.get("landuse")
    leisure = tag.get("leisure")
    place = tag.get("place")
    aeroway = tag.get("aeroway")
    barrier = tag.get("barrier")
    access = tag.get("access")
    building = tag.get("building")

    if waterway in {"stream", "river", "brook", "creek", "canal", "ditch", "drain"}:
        classes.add("water")
    if natural in {"water", "spring", "wetland", "bay", "strait"} or tag.get("water"):
        classes.add("water")
    if amenity in {"drinking_water", "water_point"} or man_made in {
        "water_well",
        "water_tank",
        "reservoir_covered",
    }:
        classes.add("water")

    if amenity in {"shelter", "ranger_station"} or tourism in {
        "alpine_hut",
        "wilderness_hut",
        "camp_site",
        "caravan_site",
    }:
        classes.add("shelter")
    if building and building not in {"no", "false"}:
        classes.add("building")
        if building in {"hut", "cabin", "yes", "residential", "house"}:
            classes.add("shelter")

    if amenity in {"hospital", "clinic", "doctors", "pharmacy", "first_aid"}:
        classes.add("medical")
    if emergency in {"ambulance_station", "first_aid", "defibrillator"} or healthcare:
        classes.add("medical")

    if highway:
        if highway in {"path", "footway", "bridleway", "steps", "cycleway"}:
            classes.add("trail")
        elif highway in {"track", "service"}:
            classes.update({"road", "trail"})
        else:
            classes.add("road")
    if tourism == "information" and tag.get("information") == "trailhead":
        classes.add("trailhead")

    if place in {"city", "town", "village", "hamlet", "locality", "suburb"}:
        classes.add("settlement")

    if man_made in {"tower", "mast", "communications_tower"}:
        classes.add("signal")
    if tag.get("tower:type") in {"communication", "observation"}:
        classes.add("signal")
    if tourism in {"viewpoint", "fire_lookout"} or amenity == "telephone":
        classes.add("signal")

    if natural in {"peak", "ridge", "saddle"} or tag.get("mountain_pass") == "yes":
        classes.add("high_ground")

    if natural in {"grassland", "heath", "scrub"} or landuse in {
        "grass",
        "meadow",
        "recreation_ground",
        "farmland",
        "brownfield",
    }:
        classes.add("clearing")
    if leisure in {"park", "pitch", "common"} or amenity == "parking":
        classes.add("clearing")
    if aeroway in {"helipad", "aerodrome", "airstrip"}:
        classes.update({"lz", "clearing"})

    if tourism in {"camp_site", "camp_pitch", "caravan_site"}:
        classes.add("campsite")

    if tag.get("bridge") and tag.get("bridge") not in {"no", "false"}:
        classes.add("bridge")
    if tag.get("ford") and tag.get("ford") not in {"no", "false"}:
        classes.add("ford")
    if barrier:
        classes.add("barrier")

    if natural in {"cliff", "scree", "bare_rock", "shingle", "glacier", "wetland"}:
        classes.add("hazard")
    if tag.get("hazard") or tag.get("hazard_type"):
        classes.add("hazard")
    if landuse in {"industrial", "quarry", "landfill", "military"}:
        classes.add("hazard")

    if access in {"private", "no", "permissive", "customers", "permit"}:
        classes.add("land_access")
    if tag.get("boundary") in {"protected_area", "national_park"} or landuse == "military":
        classes.add("land_access")

    if _label_from_tags(tag):
        classes.add("named_feature")

    if geometry_type:
        geom = geometry_type.lower()
        if geom in {"polygon", "multipolygon"} and not classes:
            classes.add("area")

    return tuple(sorted(classes or {"unclassified"}))


def _query_one_path(
    *,
    path: Path,
    target_type: str,
    origin_lat: float,
    origin_lon: float,
    radius_m: float,
    max_rows_per_layer: int,
) -> list[OsmFeature]:
    features: list[OsmFeature] = []
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return features

    try:
        with conn:
            conn.row_factory = sqlite3.Row
            for layer in _discover_layers(conn):
                features.extend(
                    _iter_layer_features(
                        conn=conn,
                        path=path,
                        layer=layer,
                        target_type=target_type,
                        origin_lat=origin_lat,
                        origin_lon=origin_lon,
                        radius_m=radius_m,
                        max_rows=max_rows_per_layer,
                    )
                )
    finally:
        conn.close()
    return features


def _discover_layers(conn: sqlite3.Connection) -> list[LayerInfo]:
    layers: dict[tuple[str, str], LayerInfo] = {}

    if _table_exists(conn, "gpkg_geometry_columns"):
        for row in conn.execute(
            "SELECT table_name, column_name, geometry_type_name FROM gpkg_geometry_columns"
        ):
            layer = LayerInfo(
                table_name=str(row["table_name"]),
                geometry_column=str(row["column_name"]),
                geometry_type=str(row["geometry_type_name"]),
            )
            layers[(layer.table_name, layer.geometry_column)] = layer

    if _table_exists(conn, "geometry_columns"):
        column_names = _column_names(conn, "geometry_columns")
        table_key = "f_table_name" if "f_table_name" in column_names else "table_name"
        geom_key = (
            "f_geometry_column" if "f_geometry_column" in column_names else "geometry_column"
        )
        type_key = "geometry_type" if "geometry_type" in column_names else "type"
        query = (
            f"SELECT {_quote_identifier(table_key)} AS table_name, "
            f"{_quote_identifier(geom_key)} AS column_name, "
            f"{_quote_identifier(type_key)} AS geometry_type FROM geometry_columns"
        )  # nosec B608 - identifiers come from local SQLite metadata
        for row in conn.execute(query):
            layer = LayerInfo(
                table_name=str(row["table_name"]),
                geometry_column=str(row["column_name"]),
                geometry_type=str(row["geometry_type"]),
            )
            layers[(layer.table_name, layer.geometry_column)] = layer

    for table_name in _user_tables(conn):
        if table_name.startswith(("gpkg_", "rtree_", "sqlite_")):
            continue
        columns = _column_names(conn, table_name)
        for candidate in GEOMETRY_COLUMN_CANDIDATES:
            if candidate in columns and (table_name, candidate) not in layers:
                layers[(table_name, candidate)] = LayerInfo(table_name, candidate)

    return sorted(layers.values(), key=lambda layer: (layer.table_name, layer.geometry_column))


def _iter_layer_features(
    *,
    conn: sqlite3.Connection,
    path: Path,
    layer: LayerInfo,
    target_type: str,
    origin_lat: float,
    origin_lon: float,
    radius_m: float,
    max_rows: int,
) -> Iterator[OsmFeature]:
    table = _quote_identifier(layer.table_name)
    query = f"SELECT * FROM {table} LIMIT ?"  # nosec B608 - table from SQLite metadata
    try:
        rows = conn.execute(query, (max_rows,))
    except sqlite3.Error:
        return

    for row in rows:
        try:
            geom_value = row[layer.geometry_column]
        except (KeyError, IndexError):
            continue
        geometry = _decode_geometry(geom_value)
        if geometry is None:
            continue

        distance_m = _haversine_m(
            (origin_lat, origin_lon),
            (geometry.centroid_lat, geometry.centroid_lon),
        )
        if distance_m > radius_m:
            continue

        tags = _extract_tags(row, geometry_column=layer.geometry_column)
        entity_types = classify_osm_tags(tags, geometry.geometry_type)
        if not _matches_target(tags, entity_types, target_type):
            continue

        yield OsmFeature(
            name=_label_from_tags(tags),
            lat=geometry.centroid_lat,
            lon=geometry.centroid_lon,
            geometry_type=geometry.geometry_type,
            source_path=str(path),
            source_layer=layer.table_name,
            source_id=_source_id(row),
            tags=tags,
            entity_types=entity_types,
            distance_m=distance_m,
        )


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _user_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [str(row["name"]) for row in rows]


def _column_names(conn: sqlite3.Connection, table_name: str) -> set[str]:
    table = _quote_identifier(table_name)
    try:
        rows = conn.execute(f"PRAGMA table_info({table})")  # nosec B608
    except sqlite3.Error:
        return set()
    return {str(row["name"]) for row in rows}


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _extract_tags(row: sqlite3.Row, *, geometry_column: str) -> dict[str, str]:
    tags: dict[str, str] = {}
    for key in row.keys():
        if key == geometry_column:
            continue
        value = row[key]
        if value is None:
            continue
        if key in TAG_BLOB_COLUMNS:
            tags.update(_parse_tag_blob(value))
            continue
        if isinstance(value, bytes):
            continue
        text = str(value).strip()
        if text:
            tags[key] = text
    return tags


def _parse_tag_blob(value: object) -> dict[str, str]:
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            return {}
    if not isinstance(value, str):
        return {}
    text = value.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = _parse_hstore_like_tags(text)
    if not isinstance(parsed, Mapping):
        return {}
    return {str(k): str(v) for k, v in parsed.items() if v is not None}


def _parse_hstore_like_tags(text: str) -> dict[str, str]:
    tags: dict[str, str] = {}
    for match in re.finditer(r'"([^"]+)"\s*=>\s*"([^"]*)"', text):
        tags[match.group(1)] = match.group(2)
    return tags


def _source_id(row: sqlite3.Row) -> str | int | None:
    for key in ("id", "osm_id", "fid", "ogc_fid"):
        if key in row.keys() and row[key] is not None:
            value = row[key]
            return value if isinstance(value, int) else str(value)
    return None


def _matches_target(
    tags: Mapping[str, str],
    entity_types: tuple[str, ...],
    target_type: str,
) -> bool:
    if target_type == "any":
        return True
    if target_type == "water" and _is_saltwater(tags):
        return False
    if target_type == "named_feature":
        return _label_from_tags(tags) is not None
    if target_type == "trailhead":
        return "trailhead" in entity_types or (
            "trail" in entity_types and _label_from_tags(tags) is not None
        )
    if target_type == "lz":
        return "lz" in entity_types or "clearing" in entity_types
    return target_type in entity_types


def _is_saltwater(tags: Mapping[str, str]) -> bool:
    normalized = {str(k).lower(): str(v).lower() for k, v in tags.items()}
    return (
        normalized.get("natural") == "coastline"
        or normalized.get("place") == "sea"
        or normalized.get("salt") == "yes"
        or normalized.get("water") in {"ocean", "sea", "salt"}
    )


def _rank_feature(feature: OsmFeature, target_type: str) -> tuple[float, int, str]:
    named_penalty = 0 if feature.name else 250
    exact_penalty = 0 if target_type in feature.entity_types or target_type == "any" else 100
    return (feature.distance_m + named_penalty + exact_penalty, named_penalty, feature.name or "")


def _label_from_tags(tags: Mapping[str, str]) -> str | None:
    for key in ("name", "operator_name", "official_name", "ref", "gnis:name"):
        value = tags.get(key)
        if value:
            return str(value)
    return None


def _decode_geometry(value: object) -> GeometrySummary | None:
    if value is None:
        return None
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytes):
        return _decode_geometry_bytes(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.startswith("{"):
            return _decode_geojson(text)
        return _decode_wkt(text)
    return None


def _decode_geometry_bytes(data: bytes) -> GeometrySummary | None:
    if len(data) < 5:
        return None
    if data.startswith(b"GP"):
        return _decode_geopackage_geometry(data)
    if data[0] in (0, 1):
        try:
            geometry, _ = _parse_wkb(data, 0)
            return geometry
        except (struct.error, ValueError):
            return _decode_spatialite_geometry(data)
    return _decode_spatialite_geometry(data)


def _decode_geopackage_geometry(data: bytes) -> GeometrySummary | None:
    if len(data) < 8:
        return None
    flags = data[3]
    envelope_code = (flags >> 1) & 0b111
    envelope_bytes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}.get(envelope_code)
    if envelope_bytes is None:
        return None
    offset = 8 + envelope_bytes
    if len(data) <= offset:
        return None
    try:
        geometry, _ = _parse_wkb(data, offset)
    except (struct.error, ValueError):
        return None
    return geometry


def _decode_spatialite_geometry(data: bytes) -> GeometrySummary | None:
    # SpatiaLite internal blobs commonly look like:
    # 0x00, byte-order, srid, mbr, 0x7c, geometry-type, coordinates, 0xfe.
    if len(data) < 44 or data[0] != 0 or data[38] != 0x7C or data[1] not in (0, 1):
        return None
    end = -1 if data[-1] == 0xFE else len(data)
    wkb_like = data[1:2] + data[39:end]
    try:
        geometry, _ = _parse_wkb(wkb_like, 0)
    except (struct.error, ValueError):
        return None
    return geometry


def _decode_wkt(text: str) -> GeometrySummary | None:
    match = re.match(r"^\s*([A-Za-z]+)", text)
    if not match:
        return None
    geometry_type = match.group(1).lower()
    numbers = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", text)]
    if len(numbers) < 2:
        return None
    pairs = list(zip(numbers[0::2], numbers[1::2], strict=False))
    return _summary_from_points(geometry_type, pairs)


def _decode_geojson(text: str) -> GeometrySummary | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, Mapping):
        return None
    geometry = data.get("geometry", data)
    if not isinstance(geometry, Mapping):
        return None
    geometry_type = str(geometry.get("type", "")).lower()
    coordinates = geometry.get("coordinates")
    points = list(_iter_geojson_points(coordinates))
    if not points:
        return None
    return _summary_from_points(geometry_type, points)


def _iter_geojson_points(value: object) -> Iterator[tuple[float, float]]:
    if not isinstance(value, list):
        return
    if len(value) >= 2 and all(isinstance(v, int | float) for v in value[:2]):
        yield (float(value[0]), float(value[1]))
        return
    for child in value:
        yield from _iter_geojson_points(child)


def _parse_wkb(data: bytes, offset: int) -> tuple[GeometrySummary, int]:
    if len(data) < offset + 5:
        raise ValueError("WKB too short")
    byte_order = data[offset]
    if byte_order == 0:
        endian = ">"
    elif byte_order == 1:
        endian = "<"
    else:
        raise ValueError("Invalid WKB byte order")
    offset += 1
    raw_type = struct.unpack_from(f"{endian}I", data, offset)[0]
    offset += 4

    has_z = bool(raw_type & 0x80000000)
    has_m = bool(raw_type & 0x40000000)
    has_srid = bool(raw_type & 0x20000000)
    clean_type = raw_type & 0x0FFFFFFF
    if clean_type >= 3000:
        dimension = 4
        base_type = clean_type - 3000
    elif clean_type >= 2000:
        dimension = 3
        base_type = clean_type - 2000
    elif clean_type >= 1000:
        dimension = 3
        base_type = clean_type - 1000
    else:
        dimension = 2 + int(has_z) + int(has_m)
        base_type = clean_type
    if has_srid:
        offset += 4

    if base_type == 1:
        points, offset = _read_wkb_points(data, offset, endian, dimension, 1)
        return _summary_from_points("point", points), offset
    if base_type == 2:
        count = _read_count(data, offset, endian)
        offset += 4
        points, offset = _read_wkb_points(data, offset, endian, dimension, count)
        return _summary_from_points("linestring", points), offset
    if base_type == 3:
        ring_count = _read_count(data, offset, endian)
        offset += 4
        points: list[tuple[float, float]] = []
        for _ in range(ring_count):
            count = _read_count(data, offset, endian)
            offset += 4
            ring_points, offset = _read_wkb_points(data, offset, endian, dimension, count)
            points.extend(ring_points)
        return _summary_from_points("polygon", points), offset
    if base_type in {4, 5, 6, 7}:
        count = _read_count(data, offset, endian)
        offset += 4
        children: list[GeometrySummary] = []
        for _ in range(count):
            child, offset = _parse_wkb(data, offset)
            children.append(child)
        return _combine_summaries(_multi_geometry_name(base_type), children), offset
    raise ValueError(f"Unsupported WKB geometry type: {raw_type}")


def _read_count(data: bytes, offset: int, endian: str) -> int:
    return struct.unpack_from(f"{endian}I", data, offset)[0]


def _read_wkb_points(
    data: bytes,
    offset: int,
    endian: str,
    dimension: int,
    count: int,
) -> tuple[list[tuple[float, float]], int]:
    points: list[tuple[float, float]] = []
    stride = 8 * dimension
    for _ in range(count):
        lon, lat = struct.unpack_from(f"{endian}dd", data, offset)
        points.append((lon, lat))
        offset += stride
    return points, offset


def _summary_from_points(
    geometry_type: str,
    points: Iterable[tuple[float, float]],
) -> GeometrySummary:
    point_list = list(points)
    if not point_list:
        raise ValueError("No points in geometry")
    lons = [point[0] for point in point_list]
    lats = [point[1] for point in point_list]
    return GeometrySummary(
        geometry_type=geometry_type,
        centroid_lon=sum(lons) / len(lons),
        centroid_lat=sum(lats) / len(lats),
        min_lon=min(lons),
        min_lat=min(lats),
        max_lon=max(lons),
        max_lat=max(lats),
        point_count=len(point_list),
    )


def _combine_summaries(
    geometry_type: str,
    children: Iterable[GeometrySummary],
) -> GeometrySummary:
    child_list = list(children)
    if not child_list:
        raise ValueError("No child geometries")
    total_points = sum(child.point_count for child in child_list)
    return GeometrySummary(
        geometry_type=geometry_type,
        centroid_lon=sum(child.centroid_lon * child.point_count for child in child_list)
        / total_points,
        centroid_lat=sum(child.centroid_lat * child.point_count for child in child_list)
        / total_points,
        min_lon=min(child.min_lon for child in child_list),
        min_lat=min(child.min_lat for child in child_list),
        max_lon=max(child.max_lon for child in child_list),
        max_lat=max(child.max_lat for child in child_list),
        point_count=total_points,
    )


def _multi_geometry_name(base_type: int) -> str:
    return {
        4: "multipoint",
        5: "multilinestring",
        6: "multipolygon",
        7: "geometrycollection",
    }[base_type]


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))
