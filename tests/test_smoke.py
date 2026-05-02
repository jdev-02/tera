"""Smoke tests. Must always pass on main.

Keeps tests narrow:
- /health is a no-deps liveness probe.
- /plan validation (422 on bad input) doesn't require the LLM/pipeline to run.

Full /plan integration tests live in tests/test_orchestrator.py with mocks.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from agent.app import app

client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "phase" in body
    assert "profile" in body


def test_plan_validation_rejects_bad_lat() -> None:
    """422 from pydantic; doesn't require the orchestrator to run."""
    r = client.post(
        "/plan",
        json={"prompt": "x", "current": {"lat": 999, "lon": 0}},
    )
    assert r.status_code == 422


def test_plan_validation_rejects_empty_prompt() -> None:
    r = client.post(
        "/plan",
        json={"prompt": "", "current": {"lat": 37.7, "lon": -122.4}},
    )
    assert r.status_code == 422
