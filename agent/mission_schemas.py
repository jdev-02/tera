"""Schemas for TERA v2 emergency logistics missions.

These models sit beside the legacy tactical `/plan` contract. They do not
replace the ATAK/CoT path; they add a humanitarian disaster-response layer for
offline-first coordination, routing, resource allocation, and explanation.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from agent.trust_schemas import TrustAssessment

IncidentType = Literal["wildfire", "flood", "earthquake", "storm", "heat", "general"]


class Coord(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class HazardAlert(BaseModel):
    id: str
    source: str = "NWS"
    event: str
    severity: str | None = None
    urgency: str | None = None
    certainty: str | None = None
    area_desc: str | None = None
    instruction: str | None = None
    geometry: dict[str, Any] | None = None


class HazardPolygon(BaseModel):
    id: str
    source: str
    name: str
    incident_type: str | None = None
    geometry: dict[str, Any] | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class InfrastructureSite(BaseModel):
    id: str
    name: str
    category: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    site_type: str | None = None
    coord: Coord | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class DisasterDeclaration(BaseModel):
    id: str
    state: str | None = None
    county: str | None = None
    incident_type: str | None = None
    title: str | None = None
    declaration_date: str | None = None
    incident_begin_date: str | None = None


class AirQualityObservation(BaseModel):
    parameter: str
    aqi: int | None = None
    category: str | None = None
    reporting_area: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    observed_at: str | None = None


class TrafficEvent(BaseModel):
    id: str
    source: str = "SF511"
    event_type: str | None = None
    description: str | None = None
    severity: str | None = None
    coord: Coord | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class FireDetection(BaseModel):
    latitude: float
    longitude: float
    brightness: float | None = None
    confidence: str | None = None
    satellite: str | None = None
    acquired_at: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class EarthquakeEvent(BaseModel):
    id: str
    magnitude: float | None = None
    place: str | None = None
    time: int | None = None
    coord: Coord | None = None
    depth_km: float | None = None
    url: str | None = None


class WaterObservation(BaseModel):
    site_id: str
    site_name: str | None = None
    parameter: str | None = None
    value: float | None = None
    unit: str | None = None
    observed_at: str | None = None


class BridgeAsset(BaseModel):
    id: str
    name: str | None = None
    state: str | None = None
    county: str | None = None
    route: str | None = None
    condition: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class FuelStation(BaseModel):
    id: str
    name: str
    fuel_types: list[str] = Field(default_factory=list)
    address: str | None = None
    coord: Coord | None = None
    distance_miles: float | None = None


class NaturalEvent(BaseModel):
    id: str
    title: str
    category: str | None = None
    source: str = "NASA EONET"
    geometry: dict[str, Any] | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class HumanitarianReport(BaseModel):
    id: str
    title: str
    date: str | None = None
    url: str | None = None
    country: str | None = None
    disaster: str | None = None


class Resource(BaseModel):
    name: str
    quantity: float = Field(..., ge=0)
    unit: str
    priority: int = Field(default=3, ge=1, le=5)


class SupplyNeed(BaseModel):
    resource: str
    quantity: float = Field(..., ge=0)
    unit: str = "units"
    urgency: int = Field(default=3, ge=1, le=5)


class Vehicle(BaseModel):
    id: str
    name: str
    capacity: dict[str, float] = Field(default_factory=dict)
    current: Coord | None = None
    status: Literal["available", "assigned", "standby", "offline"] = "available"


class Shelter(BaseModel):
    id: str
    name: str
    coord: Coord
    capacity: int = Field(..., ge=0)
    occupancy: int = Field(..., ge=0)
    needs: list[SupplyNeed] = Field(default_factory=list)
    smoke_risk: Literal["low", "moderate", "high", "unknown"] = "unknown"
    notes: str | None = None


class RouteCandidate(BaseModel):
    id: str
    provider: str
    origin: Coord | None = None
    destination: Coord | None = None
    distance_m: float | None = None
    duration_s: float | None = None
    polyline: str | None = None
    route_geojson: dict[str, Any] | None = None
    summary: str | None = None


class RouteRisk(BaseModel):
    route_id: str
    risk_level: Literal["low", "moderate", "high", "unknown"] = "unknown"
    score: float = Field(default=0, ge=0)
    factors: list[str] = Field(default_factory=list)


class VehicleAssignment(BaseModel):
    vehicle_id: str
    destination_id: str | None = None
    resources: list[Resource] = Field(default_factory=list)
    route_id: str | None = None
    status: Literal["planned", "optimized", "fallback"] = "planned"
    rationale: str | None = None


class ResourceAllocation(BaseModel):
    shelter_id: str
    priority_score: float = Field(default=0, ge=0)
    assignments: list[VehicleAssignment] = Field(default_factory=list)
    unmet_needs: list[SupplyNeed] = Field(default_factory=list)


class MissionRecommendation(BaseModel):
    action: str
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    rationale: str
    evidence: list[str] = Field(default_factory=list)


class MissionPlanRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    current: Coord
    incident_type: IncidentType = "general"
    area: str = Field(default="CA", min_length=2, max_length=32)
    resources: list[Resource] = Field(default_factory=list)
    shelters: list[Shelter] = Field(default_factory=list)
    vehicles: list[Vehicle] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    field_reports: list[dict[str, Any]] = Field(default_factory=list)
    external_links: list[str] = Field(default_factory=list)
    external_messages: list[dict[str, Any]] = Field(default_factory=list)
    shelter_instructions: list[str] = Field(default_factory=list)
    supply_requests: list[dict[str, Any]] = Field(default_factory=list)
    use_live_apis: bool = False


class MissionPlanResponse(BaseModel):
    incident_summary: dict[str, Any] = Field(default_factory=dict)
    hazards: list[dict[str, Any]] = Field(default_factory=list)
    critical_infrastructure: list[InfrastructureSite] = Field(default_factory=list)
    route_candidates: list[RouteCandidate] = Field(default_factory=list)
    route_risks: list[RouteRisk] = Field(default_factory=list)
    resource_allocations: list[ResourceAllocation] = Field(default_factory=list)
    recommended_actions: list[MissionRecommendation] = Field(default_factory=list)
    trust_assessments: list[TrustAssessment] = Field(default_factory=list)
    unverified_claims: list[str] = Field(default_factory=list)
    blocked_or_needs_approval: list[str] = Field(default_factory=list)
    explanation: str
    offline_fallback: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
