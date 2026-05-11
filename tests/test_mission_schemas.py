from __future__ import annotations

from agent.mission_schemas import (
    Coord,
    MissionPlanRequest,
    MissionPlanResponse,
    Resource,
    Shelter,
    SupplyNeed,
    Vehicle,
)


def test_mission_plan_request_accepts_emergency_payload() -> None:
    req = MissionPlanRequest(
        prompt="Plan wildfire supply route to the safest shelter.",
        current=Coord(lat=37.7749, lon=-122.4194),
        incident_type="wildfire",
        resources=[Resource(name="water", quantity=100, unit="liters")],
        shelters=[
            Shelter(
                id="shelter-west",
                name="Shelter West",
                coord=Coord(lat=37.68, lon=-122.47),
                capacity=400,
                occupancy=200,
                needs=[SupplyNeed(resource="water", quantity=50, unit="liters")],
            )
        ],
        vehicles=[Vehicle(id="truck-1", name="Truck 1")],
    )

    assert req.incident_type == "wildfire"
    assert req.use_live_apis is False


def test_mission_plan_response_minimal_shape() -> None:
    resp = MissionPlanResponse(explanation="Offline fallback plan ready.")

    assert resp.hazards == []
    assert resp.critical_infrastructure == []
    assert "Offline" in resp.explanation
