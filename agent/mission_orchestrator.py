"""Mission planner for TERA v2 emergency logistics.

This module is deliberately separate from the legacy tactical `/plan`
orchestrator. The default mode is offline-first: use cached/sample mission
state and deterministic fallbacks unless a request explicitly enables
`use_live_apis`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, cast

from agent.mission_schemas import (
    Coord,
    IncidentType,
    InfrastructureSite,
    MissionPlanRequest,
    MissionPlanResponse,
    MissionRecommendation,
    Resource,
    RouteCandidate,
    Shelter,
    Vehicle,
    VehicleAssignment,
)
from agent.services import gemini_client, gemma_local
from agent.tools import logistics, misinformation, routing_google
from agent.tools import trust as trust_tools
from agent.trust_schemas import TrustAssessment
from integrations.common import http
from integrations.us_disaster import (
    airnow,
    bridge_inventory,
    eonet,
    fema,
    hifld,
    nifc_wfigs,
    nws,
    sf511,
    usgs_earthquake,
    usgs_water,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = REPO_ROOT / "data" / "sample_scenarios"

API_STATUS_KEYS = (
    "GOOGLE_MAPS_API_KEY",
    "GOOGLE_PROJECT_ID",
    "GOOGLE_ACCESS_TOKEN",
    "AIRNOW_API_KEY",
    "SF511_API_KEY",
    "FIRMS_MAP_KEY",
    "NREL_API_KEY",
)


def mission_api_status() -> dict[str, bool]:
    return {name: bool(os.getenv(name)) for name in API_STATUS_KEYS}


def mission_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "product": "TERA emergency logistics v2",
        "legacy_tactical_available": True,
        "offline_default": True,
        "gemma_local_model": gemma_local.fallback_model_name(),
    }


def demo_bay_area_wildfire() -> MissionPlanResponse:
    scenario = _load_sample("bay_area_wildfire")
    request = _request_from_sample(scenario)
    return plan_mission(request)


def plan_mission(request: MissionPlanRequest) -> MissionPlanResponse:
    request, sample = _with_sample_defaults(request)
    warnings: list[str] = []
    live = request.use_live_apis
    if not live:
        warnings.append("Live APIs disabled; using offline fallback and sample cache.")

    hazards: list[dict[str, Any]] = []
    fire_perimeters: list[dict[str, Any]] = []
    traffic_events: list[dict[str, Any]] = []
    air_quality: list[dict[str, Any]] = []
    bridge_assets: list[dict[str, Any]] = []
    infrastructure: list[InfrastructureSite] = []

    hazards.extend(_sample_hazards(sample))
    if live:
        hazards.extend(_collect_live_hazards(request, warnings))
        fire_perimeters.extend(_collect_live_fire_perimeters(request, warnings))
        air_quality.extend(_collect_live_air_quality(request, warnings))
        traffic_events.extend(_collect_live_traffic(warnings))
        bridge_assets.extend(_collect_live_bridges(warnings))
        infrastructure.extend(_collect_live_infrastructure(request, warnings))

    if not infrastructure:
        infrastructure.extend(_fallback_infrastructure(request))

    route_target = _select_route_target(request.shelters)
    route_candidates = _generate_routes(request.current, route_target, live, warnings)
    route_risks = routing_google.score_route_safety(
        route_candidates,
        hazards=hazards,
        traffic=traffic_events,
        fire_perimeters=fire_perimeters,
        air_quality=air_quality,
        bridges=bridge_assets,
    )
    trust_assessments, unverified_claims, blocked_or_needs_approval = _assess_trust_inputs(
        request,
        hazards + fire_perimeters,
        live,
    )

    allocations = logistics.build_resource_allocation_plan(
        request.vehicles,
        request.resources,
        request.shelters,
    )
    optimized_assignments = _try_google_optimization(request, live, warnings)
    if optimized_assignments and allocations:
        allocations[0].assignments.extend(optimized_assignments)

    incident_summary = {
        "incident_type": request.incident_type,
        "area": request.area,
        "prompt": request.prompt,
        "hazard_count": len(hazards) + len(fire_perimeters),
        "shelter_count": len(request.shelters),
        "vehicle_count": len(request.vehicles),
        "resource_count": len(request.resources),
        "route_target": route_target.name if route_target else None,
    }
    recommendations = _recommend_actions(request, route_target, route_risks)
    explanation = _explain(incident_summary, route_target, route_risks, allocations)

    return MissionPlanResponse(
        incident_summary=incident_summary,
        hazards=hazards + fire_perimeters,
        critical_infrastructure=infrastructure,
        route_candidates=route_candidates,
        route_risks=route_risks,
        resource_allocations=allocations,
        recommended_actions=recommendations,
        trust_assessments=trust_assessments,
        unverified_claims=unverified_claims,
        blocked_or_needs_approval=blocked_or_needs_approval,
        explanation=explanation,
        offline_fallback={
            "used": not live,
            "sample_scenario": sample.get("name") if sample else None,
            "gemma_local_configured": gemma_local.gemma_configured(),
            "firebase_ready": False,
        },
        warnings=warnings,
    )


def _load_sample(name: str) -> dict[str, Any]:
    path = SAMPLE_DIR / f"{name}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError(f"Sample scenario {name} is not an object")
    return cast(dict[str, Any], raw)


def _request_from_sample(sample: dict[str, Any]) -> MissionPlanRequest:
    return MissionPlanRequest(
        prompt=str(sample.get("mission") or "Plan emergency logistics mission."),
        current=Coord.model_validate(sample["current"]),
        incident_type=cast(IncidentType, str(sample.get("incident_type", "general"))),
        area=str(sample.get("area", "CA")),
        resources=[Resource.model_validate(item) for item in sample.get("resources", [])],
        shelters=[Shelter.model_validate(item) for item in sample.get("shelters", [])],
        vehicles=[Vehicle.model_validate(item) for item in sample.get("vehicles", [])],
        constraints=[str(item) for item in sample.get("constraints", [])],
        external_messages=[
            item for item in sample.get("external_messages", []) if isinstance(item, dict)
        ],
        supply_requests=[
            item for item in sample.get("supply_requests", []) if isinstance(item, dict)
        ],
        use_live_apis=False,
    )


def _with_sample_defaults(
    request: MissionPlanRequest,
) -> tuple[MissionPlanRequest, dict[str, Any]]:
    sample_name = {
        "wildfire": "bay_area_wildfire",
        "flood": "flood_response",
        "earthquake": "earthquake_response",
    }.get(request.incident_type, "bay_area_wildfire")
    sample = _load_sample(sample_name)
    updates: dict[str, Any] = {}
    if not request.resources:
        updates["resources"] = [
            Resource.model_validate(item) for item in sample.get("resources", [])
        ]
    if not request.shelters:
        updates["shelters"] = [Shelter.model_validate(item) for item in sample.get("shelters", [])]
    if not request.vehicles:
        updates["vehicles"] = [Vehicle.model_validate(item) for item in sample.get("vehicles", [])]
    if not request.constraints:
        updates["constraints"] = [str(item) for item in sample.get("constraints", [])]
    if not request.external_messages:
        updates["external_messages"] = [
            item for item in sample.get("external_messages", []) if isinstance(item, dict)
        ]
    if not request.supply_requests:
        updates["supply_requests"] = [
            item for item in sample.get("supply_requests", []) if isinstance(item, dict)
        ]
    if updates:
        request = request.model_copy(update=updates)
    return request, sample


def _sample_hazards(sample: dict[str, Any]) -> list[dict[str, Any]]:
    hazards = sample.get("hazards", [])
    if not isinstance(hazards, list):
        return []
    return [item for item in hazards if isinstance(item, dict)]


def _collect_live_hazards(
    request: MissionPlanRequest,
    warnings: list[str],
) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    try:
        collected.extend(
            item.model_dump() for item in nws.normalize_alerts(nws.get_active_alerts(request.area))
        )
    except Exception as exc:  # noqa: BLE001 -- degrade, do not fail mission planning
        warnings.append(f"NWS unavailable: {exc}")
    try:
        declarations = fema.get_fire_declarations_by_state(request.area)
        collected.extend(item.model_dump() for item in fema.normalize_declarations(declarations))
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"FEMA unavailable: {exc}")
    if request.incident_type == "earthquake":
        try:
            collected.extend(
                item.model_dump()
                for item in usgs_earthquake.normalize_earthquakes(
                    usgs_earthquake.get_significant_earthquakes_week()
                )
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"USGS earthquake unavailable: {exc}")
    if request.incident_type == "flood":
        try:
            collected.extend(
                item.model_dump()
                for item in usgs_water.normalize_water_observations(
                    usgs_water.get_streamflow_and_gage_height(request.area.lower())
                )
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"USGS water unavailable: {exc}")
    if request.incident_type == "general":
        try:
            collected.extend(
                item.model_dump()
                for item in eonet.normalize_events(eonet.get_open_events(limit=10))
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"EONET unavailable: {exc}")
    return collected


def _collect_live_fire_perimeters(
    request: MissionPlanRequest,
    warnings: list[str],
) -> list[dict[str, Any]]:
    if request.incident_type != "wildfire":
        return []
    try:
        return [
            item.model_dump()
            for item in nifc_wfigs.normalize_fire_perimeters(
                nifc_wfigs.get_current_fire_perimeters()
            )
        ]
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"WFIGS unavailable: {exc}")
        return []


def _collect_live_air_quality(
    request: MissionPlanRequest,
    warnings: list[str],
) -> list[dict[str, Any]]:
    if request.incident_type not in {"wildfire", "heat"}:
        return []
    try:
        return [
            item.model_dump()
            for item in airnow.normalize_air_quality(
                airnow.get_current_air_quality(request.current.lat, request.current.lon)
            )
        ]
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"AirNow unavailable: {exc}")
        return []


def _collect_live_traffic(warnings: list[str]) -> list[dict[str, Any]]:
    try:
        return [
            item.model_dump() for item in sf511.normalize_traffic_events(sf511.get_traffic_events())
        ]
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"SF511 unavailable: {exc}")
        return []


def _collect_live_bridges(warnings: list[str]) -> list[dict[str, Any]]:
    try:
        return [
            item.model_dump()
            for item in bridge_inventory.normalize_bridges(
                bridge_inventory.get_bridge_inventory_sample(limit=10)
            )
        ]
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Bridge inventory unavailable: {exc}")
        return []


def _collect_live_infrastructure(
    request: MissionPlanRequest,
    warnings: list[str],
) -> list[InfrastructureSite]:
    try:
        return hifld.normalize_hospitals(hifld.get_hospitals_by_state(request.area))
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"HIFLD hospitals unavailable: {exc}")
        return []


def _fallback_infrastructure(request: MissionPlanRequest) -> list[InfrastructureSite]:
    return [
        InfrastructureSite(
            id="offline-hospital-1",
            name="Offline Hospital B",
            category="hospital",
            city="San Francisco",
            state=request.area,
            site_type="hospital",
            coord=Coord(lat=request.current.lat + 0.03, lon=request.current.lon - 0.04),
            properties={"source": "offline fallback"},
        )
    ]


def _select_route_target(shelters: list[Shelter]) -> Shelter | None:
    if not shelters:
        return None

    def target_score(shelter: Shelter) -> float:
        available_capacity = max(shelter.capacity - shelter.occupancy, 0)
        smoke_bonus = {"low": 3, "moderate": 1, "unknown": 0, "high": -4}[shelter.smoke_risk]
        need_score = sum(need.urgency for need in shelter.needs)
        return available_capacity / 50 + smoke_bonus + need_score / 5

    return max(shelters, key=target_score)


def _generate_routes(
    origin: Coord,
    target: Shelter | None,
    live: bool,
    warnings: list[str],
) -> list[RouteCandidate]:
    if target is None:
        return []
    if live and os.getenv("GOOGLE_MAPS_API_KEY"):
        try:
            return routing_google.generate_candidate_routes(origin, target.coord)
        except (http.ApiError, ValueError) as exc:
            warnings.append(f"Google Maps Routes unavailable: {exc}")
    return [
        RouteCandidate(
            id="offline-route-c",
            provider="offline_fallback",
            origin=origin,
            destination=target.coord,
            distance_m=8200,
            duration_s=1320,
            summary=(
                f"Offline route candidate to {target.name}; avoid hazard corridors "
                "when live data is absent."
            ),
        )
    ]


def _try_google_optimization(
    request: MissionPlanRequest,
    live: bool,
    warnings: list[str],
) -> list[VehicleAssignment]:
    if not live or not (os.getenv("GOOGLE_PROJECT_ID") and os.getenv("GOOGLE_ACCESS_TOKEN")):
        return []
    vehicles = [{"label": vehicle.id} for vehicle in request.vehicles]
    shipments = [{"label": shelter.id} for shelter in request.shelters]
    try:
        return logistics.optimize_dispatch_plan(vehicles, shipments)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Google Route Optimization unavailable: {exc}")
        return []


def _assess_trust_inputs(
    request: MissionPlanRequest,
    active_hazards: list[dict[str, Any]],
    live: bool,
) -> tuple[list[TrustAssessment], list[str], list[str]]:
    assessments: list[TrustAssessment] = []
    unverified_claims: list[str] = []
    blocked_or_needs_approval: list[str] = []
    verified_shelter_names = [shelter.name for shelter in request.shelters]

    for url in request.external_links:
        assessment = trust_tools.assess_url(url, use_live_providers=live)
        assessments.append(assessment)
        _collect_blocking_result(assessment, unverified_claims, blocked_or_needs_approval)

    for message_obj in request.external_messages:
        message = str(message_obj.get("message") or "")
        source = str(message_obj.get("source") or "unknown")
        if not message:
            continue
        assessment = trust_tools.assess_message_trust(
            message,
            source=source,
            use_live_providers=live,
        )
        assessments.append(assessment)
        _collect_blocking_result(assessment, unverified_claims, blocked_or_needs_approval)
        shelter_claim = misinformation.detect_unverified_shelter_claim(
            message,
            request.shelters,
        )
        if shelter_claim.signals:
            assessments.append(shelter_claim)
            _collect_blocking_result(
                shelter_claim,
                unverified_claims,
                blocked_or_needs_approval,
            )
        evacuation_claim = misinformation.detect_unverified_evacuation_instruction(
            message,
            active_hazards,
        )
        if evacuation_claim.signals:
            assessments.append(evacuation_claim)
            _collect_blocking_result(
                evacuation_claim,
                unverified_claims,
                blocked_or_needs_approval,
            )

    for instruction in request.shelter_instructions:
        assessment = misinformation.detect_unverified_shelter_claim(
            instruction,
            request.shelters,
        )
        assessments.append(assessment)
        _collect_blocking_result(assessment, unverified_claims, blocked_or_needs_approval)

    for supply_request in request.supply_requests:
        enriched = dict(supply_request)
        enriched["verified_shelters"] = verified_shelter_names
        assessment = trust_tools.assess_supply_request_trust(enriched)
        assessments.append(assessment)
        _collect_blocking_result(assessment, unverified_claims, blocked_or_needs_approval)

    return assessments, unverified_claims, blocked_or_needs_approval


def _collect_blocking_result(
    assessment: TrustAssessment,
    unverified_claims: list[str],
    blocked_or_needs_approval: list[str],
) -> None:
    if not assessment.requires_human_approval:
        return
    unverified_claims.append(assessment.value)
    blocked_or_needs_approval.append(
        f"{assessment.input_type}:{assessment.risk_level}:{assessment.recommendation}"
    )


def _recommend_actions(
    request: MissionPlanRequest,
    target: Shelter | None,
    route_risks: list[Any],
) -> list[MissionRecommendation]:
    actions: list[MissionRecommendation] = []
    if target:
        actions.append(
            MissionRecommendation(
                action=f"Prioritize {target.name} as the logistics destination.",
                priority="high",
                rationale=(
                    "It has usable capacity and lower exposure than overloaded "
                    "or smoke-heavy shelters."
                ),
                evidence=[target.id, target.smoke_risk],
            )
        )
    if route_risks:
        safest = min(route_risks, key=lambda risk: risk.score)
        actions.append(
            MissionRecommendation(
                action=f"Use {safest.route_id} unless live hazard data contradicts it.",
                priority="medium",
                rationale=f"Current route risk is {safest.risk_level} with score {safest.score}.",
                evidence=safest.factors,
            )
        )
    if request.incident_type == "wildfire":
        actions.append(
            MissionRecommendation(
                action="Send water and N95 masks first.",
                priority="critical",
                rationale=(
                    "Wildfire logistics should reduce dehydration and smoke exposure "
                    "before comfort items."
                ),
                evidence=["incident_type:wildfire"],
            )
        )
    return actions


def _explain(
    incident_summary: dict[str, Any],
    target: Shelter | None,
    route_risks: list[Any],
    allocations: list[Any],
) -> str:
    base = gemini_client.explain_decision(incident_summary)
    target_text = f"Selected {target.name} as the primary logistics destination. " if target else ""
    risk_text = ""
    if route_risks:
        safest = min(route_risks, key=lambda risk: risk.score)
        risk_text = (
            f"Recommended {safest.route_id} because available hazard, traffic, "
            f"and infrastructure data score it {safest.risk_level}. "
        )
    allocation_count = sum(len(allocation.assignments) for allocation in allocations)
    return (
        f"{base} {target_text}{risk_text}"
        f"Resource plan includes {allocation_count} vehicle assignment(s) "
        "and remains usable offline."
    ).strip()
