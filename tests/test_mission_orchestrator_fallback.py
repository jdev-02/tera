from __future__ import annotations

from fastapi.testclient import TestClient

from agent.app import app
from agent.mission_orchestrator import demo_bay_area_wildfire, mission_api_status, plan_mission
from agent.mission_schemas import Coord, MissionPlanRequest


def test_mission_orchestrator_uses_offline_fallback() -> None:
    req = MissionPlanRequest(
        prompt="Plan wildfire supplies to cleaner shelter.",
        current=Coord(lat=37.7749, lon=-122.4194),
        incident_type="wildfire",
        area="CA",
    )

    resp = plan_mission(req)

    assert resp.offline_fallback["used"] is True
    assert resp.route_candidates[0].provider == "offline_fallback"
    assert any("Shelter West" in action.action for action in resp.recommended_actions)
    assert resp.resource_allocations


def test_mission_demo_endpoint_returns_plan() -> None:
    client = TestClient(app)

    r = client.get("/mission/demo/bay-area-wildfire")

    assert r.status_code == 200
    body = r.json()
    assert body["incident_summary"]["incident_type"] == "wildfire"
    assert body["offline_fallback"]["used"] is True


def test_mission_api_status_does_not_expose_values(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "secret-value")

    status = mission_api_status()

    assert status["GOOGLE_MAPS_API_KEY"] is True
    assert "secret-value" not in str(status)


def test_demo_bay_area_wildfire_selects_west_shelter() -> None:
    resp = demo_bay_area_wildfire()

    assert resp.incident_summary["route_target"] == "Shelter West"
