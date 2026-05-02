"""Smoke tests. Must always pass on main."""

from __future__ import annotations

from agent.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "phase" in body


def test_plan_stub_shape() -> None:
    r = client.post(
        "/plan",
        json={
            "prompt": "route to nearest freshwater within 5km",
            "current": {"lat": 37.7955, "lon": -122.3937},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "route" in body
    assert body["route"]["type"] == "Feature"
    assert body["route"]["geometry"]["type"] == "LineString"
    assert "waypoints" in body
    assert "rationale" in body


def test_plan_validation_rejects_bad_lat() -> None:
    r = client.post(
        "/plan",
        json={"prompt": "x", "current": {"lat": 999, "lon": 0}},
    )
    assert r.status_code == 422
