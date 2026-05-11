"""Route generation and safety scoring tools."""

from __future__ import annotations

from typing import Any, Literal

from agent.mission_schemas import Coord, RouteCandidate, RouteRisk
from integrations.google import maps_routes


def generate_candidate_routes(origin: Coord, destination: Coord) -> list[RouteCandidate]:
    raw = maps_routes.compute_routes(origin, destination, alternatives=True)
    routes = maps_routes.normalize_routes(raw)
    return [
        route.model_copy(update={"origin": origin, "destination": destination}) for route in routes
    ]


def score_route_safety(
    routes: list[RouteCandidate],
    hazards: list[dict[str, Any]],
    traffic: list[dict[str, Any]],
    fire_perimeters: list[dict[str, Any]],
    air_quality: list[dict[str, Any]],
    bridges: list[dict[str, Any]],
) -> list[RouteRisk]:
    risks: list[RouteRisk] = []
    hazard_count = len(hazards) + len(fire_perimeters)
    traffic_count = len(traffic)
    bridge_count = len(bridges)
    high_aqi = any(_aqi_value(item) >= 151 for item in air_quality)
    for route in routes:
        score = float(hazard_count * 2 + traffic_count + bridge_count)
        factors: list[str] = []
        if hazard_count:
            factors.append(f"{hazard_count} active hazard overlays")
        if traffic_count:
            factors.append(f"{traffic_count} road events")
        if bridge_count:
            factors.append("bridge inventory requires heavy-vehicle review")
        if high_aqi:
            score += 2
            factors.append("AQI indicates unhealthy smoke exposure")
        risk_level: Literal["low", "moderate", "high", "unknown"] = "low"
        if score >= 5:
            risk_level = "high"
        elif score >= 2:
            risk_level = "moderate"
        risks.append(
            RouteRisk(
                route_id=route.id,
                score=score,
                risk_level=risk_level,
                factors=factors or ["No high-confidence hazard conflicts in available data"],
            )
        )
    return risks


def _aqi_value(item: dict[str, Any]) -> int:
    value = item.get("aqi")
    return value if isinstance(value, int) else 0
