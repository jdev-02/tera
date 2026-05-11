from __future__ import annotations

from fastapi.testclient import TestClient

from agent.app import app
from agent.mission_orchestrator import demo_bay_area_wildfire
from agent.tools import misinformation
from agent.tools.trust import assess_supply_request_trust


def test_supply_request_to_unverified_shelter_requires_approval() -> None:
    assessment = assess_supply_request_trust(
        {
            "source": "unknown",
            "destination": "Unverified Shelter X",
            "requested_items": {"medical_kits": 500},
            "urgency": "critical",
            "verified_shelters": ["Shelter West"],
        }
    )

    assert assessment.requires_human_approval is True
    assert any(signal.code == "UNVERIFIED_DESTINATION" for signal in assessment.signals)


def test_message_conflicts_with_official_shelter_list() -> None:
    assessment = misinformation.detect_unverified_shelter_claim(
        "Go to Unverified Shelter X immediately.",
        [{"name": "Shelter West"}],
    )

    assert assessment.requires_human_approval is True
    assert assessment.signals[0].code == "UNVERIFIED_SHELTER_CLAIM"


def test_trust_endpoint_does_not_expose_secret(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_SAFE_BROWSING_API_KEY", "secret-key")
    client = TestClient(app)

    r = client.get("/trust/api-status")

    assert r.status_code == 200
    assert r.json()["GOOGLE_SAFE_BROWSING_API_KEY"] is True
    assert "secret-key" not in r.text


def test_mission_demo_includes_trust_shield_findings() -> None:
    resp = demo_bay_area_wildfire()

    assert resp.trust_assessments
    assert resp.blocked_or_needs_approval
    assert any("Unverified Shelter X" in claim for claim in resp.unverified_claims)
