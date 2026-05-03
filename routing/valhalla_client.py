"""Local Valhalla CLI client for offline route generation."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast


class ValhallaRouteError(RuntimeError):
    """Raised when Valhalla cannot return a usable route."""


@dataclass(frozen=True)
class Coord:
    lat: float
    lon: float


@dataclass(frozen=True)
class RouteResult:
    coordinates: list[tuple[float, float]]
    distance_m: float
    time_s: float

    def as_geojson_feature(self) -> dict[str, object]:
        return {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[lon, lat] for lat, lon in self.coordinates],
            },
            "properties": {
                "source": "valhalla",
                "distance_m": self.distance_m,
                "time_s": self.time_s,
            },
        }


class CommandRunner(Protocol):
    def __call__(self, command: Sequence[str]) -> str:
        """Run a local command and return stdout."""


class SubprocessRunner:
    def __call__(self, command: Sequence[str]) -> str:
        # Valhalla is a local binary in the offline path; callers pass argv, never shell text.
        completed = subprocess.run(  # noqa: S603
            list(command),
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout


class ValhallaClient:
    def __init__(
        self,
        config_path: str | Path,
        *,
        executable: str = "valhalla_run_route",
        runner: CommandRunner | None = None,
    ) -> None:
        self.config_path = Path(config_path)
        self.executable = executable
        self.runner = runner or SubprocessRunner()

    def route(
        self,
        origin: Coord,
        destination: Coord,
        *,
        costing: str = "pedestrian",
    ) -> RouteResult:
        request = {
            "locations": [
                {"lat": origin.lat, "lon": origin.lon},
                {"lat": destination.lat, "lon": destination.lon},
            ],
            "costing": costing,
            "directions_options": {"units": "kilometers"},
        }
        output = self.runner(
            [
                self.executable,
                str(self.config_path),
                json.dumps(request, separators=(",", ":")),
            ]
        )
        return parse_valhalla_route(output)


def parse_valhalla_route(output_json: str) -> RouteResult:
    decoded: object = json.loads(output_json)
    if not isinstance(decoded, dict):
        raise ValhallaRouteError("Valhalla output must be a JSON object")

    trip = _dict_field(decoded, "trip")
    legs = _list_field(trip, "legs")
    if not legs:
        raise ValhallaRouteError("Valhalla output did not include any legs")

    summary = _dict_field(trip, "summary")
    distance_m = _number(summary.get("length"), "trip summary length") * 1000.0
    time_s = _number(summary.get("time"), "trip summary time")

    coordinates: list[tuple[float, float]] = []
    for raw_leg in legs:
        if not isinstance(raw_leg, dict):
            raise ValhallaRouteError("Valhalla leg must be an object")
        leg = cast(dict[str, object], raw_leg)
        shape = leg.get("shape")
        if not isinstance(shape, str) or not shape:
            raise ValhallaRouteError("Valhalla leg did not include an encoded shape")
        leg_coordinates = decode_valhalla_polyline(shape)
        if coordinates and leg_coordinates:
            coordinates.extend(leg_coordinates[1:])
            continue
        coordinates.extend(leg_coordinates)

    if len(coordinates) < 2:
        raise ValhallaRouteError("Valhalla route must decode to at least two coordinates")

    return RouteResult(coordinates=coordinates, distance_m=distance_m, time_s=time_s)


def decode_valhalla_polyline(shape: str, *, precision: int = 6) -> list[tuple[float, float]]:
    factor = float(10**precision)
    lat = 0
    lon = 0
    index = 0
    coordinates: list[tuple[float, float]] = []

    while index < len(shape):
        lat_delta, index = _decode_polyline_value(shape, index)
        lon_delta, index = _decode_polyline_value(shape, index)
        lat += lat_delta
        lon += lon_delta
        coordinates.append((lat / factor, lon / factor))

    return coordinates


def _decode_polyline_value(shape: str, index: int) -> tuple[int, int]:
    result = 1
    shift = 0

    while True:
        if index >= len(shape):
            raise ValhallaRouteError("encoded shape ended unexpectedly")
        value = ord(shape[index]) - 63 - 1
        index += 1
        result += value << shift
        shift += 5
        if value < 0x1F:
            break

    delta = ~(result >> 1) if result & 1 else result >> 1
    return delta, index


def _dict_field(source: Mapping[str, object], name: str) -> dict[str, object]:
    value = source.get(name)
    if not isinstance(value, dict):
        raise ValhallaRouteError(f"Valhalla field {name!r} must be an object")
    return cast(dict[str, object], value)


def _list_field(source: dict[str, object], name: str) -> list[object]:
    value = source.get(name)
    if not isinstance(value, list):
        raise ValhallaRouteError(f"Valhalla field {name!r} must be a list")
    return value


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValhallaRouteError(f"{label} must be numeric")
    return float(value)
