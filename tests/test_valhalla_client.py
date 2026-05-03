"""Tests for local Valhalla route parsing."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from routing.valhalla_client import (
    Coord,
    ValhallaClient,
    ValhallaRouteError,
    decode_valhalla_polyline,
    parse_valhalla_route,
)


def _encode_polyline(coordinates: Sequence[tuple[float, float]], *, precision: int = 6) -> str:
    factor = 10**precision
    last_lat = 0
    last_lon = 0
    encoded = []

    for lat, lon in coordinates:
        next_lat = round(lat * factor)
        next_lon = round(lon * factor)
        encoded.append(_encode_polyline_value(next_lat - last_lat))
        encoded.append(_encode_polyline_value(next_lon - last_lon))
        last_lat = next_lat
        last_lon = next_lon

    return "".join(encoded)


def _encode_polyline_value(value: int) -> str:
    shifted = ~(value << 1) if value < 0 else value << 1
    chunks = []
    while shifted >= 0x20:
        chunks.append(chr((0x20 | (shifted & 0x1F)) + 63))
        shifted >>= 5
    chunks.append(chr(shifted + 63))
    return "".join(chunks)


def test_decode_valhalla_polyline_round_trips_coordinates() -> None:
    coordinates = [(37.7955, -122.3937), (37.7965, -122.3927)]
    shape = _encode_polyline(coordinates)

    assert decode_valhalla_polyline(shape) == coordinates


def test_parse_valhalla_route_returns_geojson_ready_result() -> None:
    coordinates = [(37.7955, -122.3937), (37.7965, -122.3927)]
    output = {
        "trip": {
            "summary": {"length": 0.15, "time": 120.0},
            "legs": [{"shape": _encode_polyline(coordinates)}],
        }
    }

    result = parse_valhalla_route(json.dumps(output))
    geojson = result.as_geojson_feature()

    assert result.distance_m == 150.0
    assert result.time_s == 120.0
    assert geojson["type"] == "Feature"
    assert geojson["geometry"] == {
        "type": "LineString",
        "coordinates": [[-122.3937, 37.7955], [-122.3927, 37.7965]],
    }


def test_parse_valhalla_route_rejects_missing_shape() -> None:
    output = {"trip": {"summary": {"length": 0.15, "time": 120.0}, "legs": [{}]}}

    with pytest.raises(ValhallaRouteError, match="encoded shape"):
        parse_valhalla_route(json.dumps(output))


def test_valhalla_client_invokes_local_cli(tmp_path: Path) -> None:
    shape = _encode_polyline([(37.7955, -122.3937), (37.7965, -122.3927)])
    output = json.dumps(
        {"trip": {"summary": {"length": 0.15, "time": 120.0}, "legs": [{"shape": shape}]}}
    )
    seen_command: list[str] = []

    def runner(command: Sequence[str]) -> str:
        seen_command.extend(command)
        return output

    client = ValhallaClient(tmp_path / "valhalla.json", runner=runner)
    result = client.route(
        Coord(lat=37.7955, lon=-122.3937),
        Coord(lat=37.7965, lon=-122.3927),
    )

    assert result.distance_m == 150.0
    assert seen_command[0] == "valhalla_run_route"
    assert "valhalla.json" in seen_command[1]
    assert '"costing":"pedestrian"' in seen_command[2]
