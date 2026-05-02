"""Smoke tests. Must always pass on main.

Keeps tests narrow:
- /health is a no-deps liveness probe.
- /plan validation (422 on bad input) doesn't require the LLM/pipeline to run.

Full /plan integration tests live in tests/test_orchestrator.py with mocks.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from agent.app import app
from agent.schemas import (
    OperatorSignature,
    PlanApprovalRequest,
    PlanApprovalResponse,
    Signature,
)

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


def test_plan_approve_validation_requires_device_signature() -> None:
    r = client.post(
        "/plan/approve",
        json={
            "route_id": "TERA-test",
            "route": {"type": "Feature", "geometry": {"type": "LineString", "coordinates": []}},
        },
    )
    assert r.status_code == 422


def test_plan_approve_endpoint_returns_commit(
    monkeypatch,
) -> None:
    def fake_approve(req: PlanApprovalRequest) -> PlanApprovalResponse:
        return PlanApprovalResponse(
            route_id=req.route_id,
            route_hash="a" * 64,
            device_signature=req.device_signature,
            operator_signature=OperatorSignature(
                scheme="ML-DSA-65",
                key_id=req.operator_key_id,
                value_b64="b3BlcmF0b3I=",
                signed_at="2026-05-02T22:31:00Z",
                approves_route_hash="a" * 64,
                payload_hash="b" * 64,
                payload_json='{"approves_route_hash":"' + ("a" * 64) + '"}',
            ),
        )

    monkeypatch.setattr("agent.app.approve_plan", fake_approve)
    r = client.post(
        "/plan/approve",
        json={
            "route_id": "TERA-test",
            "route": {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-122.39, 37.79], [-122.40, 37.80]],
                },
            },
            "device_signature": Signature(
                scheme="ML-DSA-65",
                key_id="wayfinder-device-001",
                value_b64="ZGV2aWNl",
                signed_at="2026-05-02T22:30:00Z",
            ).model_dump(),
            "operator_key_id": "OPERATOR-VEGA-001",
        },
    )
    assert r.status_code == 200
    assert r.json()["approval_state"] == "operator_committed"
