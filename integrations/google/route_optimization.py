"""Google Route Optimization API adapter."""

from __future__ import annotations

import os
from typing import Any

from agent.mission_schemas import Resource, VehicleAssignment
from integrations.common import http


def optimize_tours(request: dict[str, Any]) -> dict[str, Any]:
    project_id = http.require_env("GOOGLE_PROJECT_ID", os.getenv("GOOGLE_PROJECT_ID"))
    access_token = http.require_env("GOOGLE_ACCESS_TOKEN", os.getenv("GOOGLE_ACCESS_TOKEN"))
    raw = http.post_json(
        f"https://routeoptimization.googleapis.com/v1/projects/{project_id}:optimizeTours",
        json_body=request,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    if not isinstance(raw, dict):
        raise http.ApiError("Google Route Optimization response was not an object")
    return raw


def build_basic_supply_dispatch_request(
    vehicles: list[dict[str, Any]],
    shipments: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "model": {
            "globalStartTime": "2026-05-11T00:00:00Z",
            "globalEndTime": "2026-05-12T00:00:00Z",
            "vehicles": vehicles,
            "shipments": shipments,
        },
        "searchMode": "RETURN_FAST",
    }


def normalize_optimized_routes(raw: dict[str, Any]) -> list[VehicleAssignment]:
    assignments: list[VehicleAssignment] = []
    for index, route in enumerate(raw.get("routes", [])):
        if not isinstance(route, dict):
            continue
        vehicle_label = route.get("vehicleLabel") or route.get("vehicleIndex") or f"vehicle-{index}"
        visits = route.get("visits", [])
        destination = None
        if isinstance(visits, list) and visits:
            first_visit = visits[0]
            if isinstance(first_visit, dict):
                destination = _optional_str(first_visit.get("shipmentLabel"))
        assignments.append(
            VehicleAssignment(
                vehicle_id=str(vehicle_label),
                destination_id=destination,
                resources=[Resource(name="optimized shipment", quantity=1, unit="load")],
                status="optimized",
                rationale="Assigned by Google Route Optimization API.",
            )
        )
    return assignments


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None
