"""Deterministic logistics planning tools for degraded connectivity."""

from __future__ import annotations

from typing import Any

from agent.mission_schemas import (
    Resource,
    ResourceAllocation,
    Shelter,
    SupplyNeed,
    Vehicle,
    VehicleAssignment,
)
from integrations.google import route_optimization


def score_shelter_needs(
    shelters: list[Shelter],
    hazards: list[dict[str, Any]],
    air_quality: list[dict[str, Any]],
) -> dict[str, float]:
    scores: dict[str, float] = {}
    hazard_pressure = min(len(hazards), 5)
    high_smoke = any(item.get("aqi", 0) >= 151 for item in air_quality)
    for shelter in shelters:
        occupancy_ratio = shelter.occupancy / shelter.capacity if shelter.capacity else 1.0
        need_pressure = sum(need.urgency for need in shelter.needs)
        score = occupancy_ratio * 5 + need_pressure + hazard_pressure
        if shelter.smoke_risk == "high" or high_smoke:
            score += 2
        scores[shelter.id] = round(score, 2)
    return scores


def build_resource_allocation_plan(
    vehicles: list[Vehicle],
    resources: list[Resource],
    shelters: list[Shelter],
) -> list[ResourceAllocation]:
    available_vehicles = [
        vehicle for vehicle in vehicles if vehicle.status in {"available", "standby"}
    ]
    inventory = {resource.name.lower(): resource.model_copy() for resource in resources}
    allocations: list[ResourceAllocation] = []
    vehicle_index = 0
    for shelter in sorted(shelters, key=_shelter_pressure, reverse=True):
        assignments: list[VehicleAssignment] = []
        unmet: list[SupplyNeed] = []
        shipment: list[Resource] = []
        for need in shelter.needs:
            stock = inventory.get(need.resource.lower())
            if stock is None or stock.quantity <= 0:
                unmet.append(need)
                continue
            amount = min(stock.quantity, need.quantity)
            stock.quantity -= amount
            shipment.append(Resource(name=need.resource, quantity=amount, unit=need.unit))
            if amount < need.quantity:
                unmet.append(
                    SupplyNeed(
                        resource=need.resource,
                        quantity=need.quantity - amount,
                        unit=need.unit,
                        urgency=need.urgency,
                    )
                )
        if shipment and available_vehicles:
            vehicle = available_vehicles[vehicle_index % len(available_vehicles)]
            vehicle_index += 1
            assignments.append(
                VehicleAssignment(
                    vehicle_id=vehicle.id,
                    destination_id=shelter.id,
                    resources=shipment,
                    status="fallback",
                    rationale=(
                        "Deterministic offline allocator matched highest-priority shelter needs."
                    ),
                )
            )
        allocations.append(
            ResourceAllocation(
                shelter_id=shelter.id,
                priority_score=_shelter_pressure(shelter),
                assignments=assignments,
                unmet_needs=unmet,
            )
        )
    return allocations


def optimize_dispatch_plan(
    vehicles: list[dict[str, Any]],
    shipments: list[dict[str, Any]],
) -> list[VehicleAssignment]:
    request = route_optimization.build_basic_supply_dispatch_request(vehicles, shipments)
    raw = route_optimization.optimize_tours(request)
    return route_optimization.normalize_optimized_routes(raw)


def recommend_staging_point(
    infrastructure: list[dict[str, Any]],
    hazards: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not infrastructure:
        return None
    hazard_text = str(hazards).lower()
    for site in infrastructure:
        if str(site.get("name", "")).lower() not in hazard_text:
            return site
    return infrastructure[0]


def _shelter_pressure(shelter: Shelter) -> float:
    occupancy_ratio = shelter.occupancy / shelter.capacity if shelter.capacity else 1.0
    return round(occupancy_ratio * 5 + sum(need.urgency for need in shelter.needs), 2)
