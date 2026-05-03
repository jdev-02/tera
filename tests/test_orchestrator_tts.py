"""End-to-end test that POST /plan?tts=true populates audio_b64 in the response."""

from __future__ import annotations

import base64
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from agent.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _fake_orchestrate_response(*_args: Any, **_kwargs: Any) -> Any:
    """Stand-in for orchestrate_plan that the FastAPI handler will see.

    This sidesteps the LLM, security pipeline, and tool dispatch entirely --
    we're testing the wiring of the `tts` query param + audio_b64 field, not
    the upstream stages (those have their own tests).
    """
    from agent.schemas import PlanResponse, Waypoint

    audio = base64.b64encode(b"RIFF\x00\x00\x00\x00WAVE_fake_audio").decode("ascii")
    return PlanResponse(
        request_id="test-req-1",
        route={"type": "Feature", "geometry": {"type": "LineString", "coordinates": []}},
        waypoints=[Waypoint(label="origin", lat=37.78, lon=-122.46)],
        rationale="Routed to Lobos Creek, distance 2.1 kilometers.",
        cost_breakdown={},
        trust={"trust_status": "PASS"},
        signature=None,
        audio_b64=audio if _kwargs.get("with_tts") else None,
    )


def test_plan_without_tts_omits_audio(client: TestClient) -> None:
    with patch("agent.app.orchestrate_plan", side_effect=_fake_orchestrate_response):
        r = client.post(
            "/plan",
            json={
                "prompt": "route to nearest creek",
                "current": {"lat": 37.78, "lon": -122.46},
            },
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["audio_b64"] is None


def test_plan_with_tts_query_returns_audio(client: TestClient) -> None:
    with patch("agent.app.orchestrate_plan", side_effect=_fake_orchestrate_response):
        r = client.post(
            "/plan?tts=true",
            json={
                "prompt": "route to nearest creek",
                "current": {"lat": 37.78, "lon": -122.46},
            },
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["audio_b64"] is not None
    decoded = base64.b64decode(body["audio_b64"])
    assert decoded.startswith(b"RIFF")
