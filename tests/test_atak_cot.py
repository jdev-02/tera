"""Tests for ATAK route export helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from atak.cot import PlanExportError, plan_to_kml, write_plan_kml


def _sample_plan() -> dict[str, object]:
    return {
        "request_id": "req-1",
        "route": {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-122.3937, 37.7955],
                    [-122.3927, 37.7965],
                    [-122.3917, 37.7975],
                ],
            },
            "properties": {},
        },
        "waypoints": [
            {"lat": 37.7975, "lon": -122.3917, "label": "Freshwater source"},
        ],
        "rationale": "Route follows covered terrain to the nearest water source.",
        "cost_breakdown": {"distance_m": 150.0, "time_s": 120.0, "elevation_gain_m": 0.0},
    }


def test_plan_to_kml_exports_route_and_waypoint() -> None:
    kml = plan_to_kml(_sample_plan(), document_name="Demo route")

    assert "<name>Demo route</name>" in kml
    assert "<name>TERA route</name>" in kml
    assert "<name>Freshwater source</name>" in kml
    assert "-122.3937000,37.7955000,0.00" in kml
    assert "-122.3917000,37.7975000,0.00" in kml


def test_write_plan_kml_creates_parent_directory(tmp_path: Path) -> None:
    output_path = tmp_path / "exports" / "route.kml"

    written = write_plan_kml(_sample_plan(), output_path)

    assert written == output_path
    assert output_path.exists()
    assert "Freshwater source" in output_path.read_text(encoding="utf-8")


def test_plan_to_kml_rejects_non_linestring() -> None:
    plan = _sample_plan()
    route = plan["route"]
    assert isinstance(route, dict)
    geometry = route["geometry"]
    assert isinstance(geometry, dict)
    geometry["type"] = "Point"

    with pytest.raises(PlanExportError, match="LineString"):
        plan_to_kml(plan)


def test_plan_to_kml_rejects_single_coordinate_route() -> None:
    plan = _sample_plan()
    route = plan["route"]
    assert isinstance(route, dict)
    geometry = route["geometry"]
    assert isinstance(geometry, dict)
    geometry["coordinates"] = [[-122.3937, 37.7955]]

    with pytest.raises(PlanExportError, match="at least two"):
        plan_to_kml(plan)
