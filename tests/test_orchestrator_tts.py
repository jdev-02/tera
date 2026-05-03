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


# ---------------------------------------------------------------------------
# Voice profile toggle (#54)
# ---------------------------------------------------------------------------


def _capture_orchestrate_call(captured: dict) -> Any:
    """Side-effect factory that records the PlanRequest the handler passed
    to orchestrate_plan. Lets us assert the plumbing without running the
    full pipeline."""

    def _impl(req: Any, *args: Any, **kwargs: Any) -> Any:
        captured["req"] = req
        captured["kwargs"] = kwargs
        return _fake_orchestrate_response(req, *args, **kwargs)

    return _impl


def test_voice_profile_query_param_promoted_to_body(client: TestClient) -> None:
    """?profile=critical without a body field becomes req.voice_profile=critical."""
    captured: dict[str, Any] = {}
    with patch("agent.app.orchestrate_plan", side_effect=_capture_orchestrate_call(captured)):
        r = client.post(
            "/plan?tts=true&profile=critical",
            json={
                "prompt": "CASEVAC, plot route",
                "current": {"lat": 37.78, "lon": -122.46},
            },
        )
    assert r.status_code == 200, r.text
    assert captured["req"].voice_profile == "critical"


def test_voice_profile_body_field_wins_over_query_param(client: TestClient) -> None:
    """If both forms are set, the body wins (explicit > implicit)."""
    captured: dict[str, Any] = {}
    with patch("agent.app.orchestrate_plan", side_effect=_capture_orchestrate_call(captured)):
        r = client.post(
            "/plan?tts=true&profile=calm",
            json={
                "prompt": "route to creek",
                "current": {"lat": 37.78, "lon": -122.46},
                "voice_profile": "critical",
            },
        )
    assert r.status_code == 200, r.text
    assert captured["req"].voice_profile == "critical"


def test_voice_profile_unknown_value_rejected(client: TestClient) -> None:
    """FastAPI / Pydantic should 422 on an unknown profile string."""
    r = client.post(
        "/plan",
        json={
            "prompt": "route to creek",
            "current": {"lat": 37.78, "lon": -122.46},
            "voice_profile": "tactical",  # not in the Literal
        },
    )
    assert r.status_code == 422, r.text


def test_voice_profile_default_is_none(client: TestClient) -> None:
    """No profile in body or query -> req.voice_profile is None (orchestrator
    falls back to env var or 'comms')."""
    captured: dict[str, Any] = {}
    with patch("agent.app.orchestrate_plan", side_effect=_capture_orchestrate_call(captured)):
        r = client.post(
            "/plan",
            json={
                "prompt": "route to creek",
                "current": {"lat": 37.78, "lon": -122.46},
            },
        )
    assert r.status_code == 200, r.text
    assert captured["req"].voice_profile is None
