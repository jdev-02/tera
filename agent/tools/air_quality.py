"""Air-quality tools for smoke exposure scoring."""

from __future__ import annotations

from agent.mission_schemas import AirQualityObservation
from integrations.us_disaster import airnow


def get_smoke_exposure(lat: float, lon: float) -> list[AirQualityObservation]:
    raw = airnow.get_current_air_quality(lat, lon)
    return airnow.normalize_air_quality(raw)


def score_air_quality_risk(observations: list[AirQualityObservation]) -> str:
    max_aqi = max((obs.aqi or 0 for obs in observations), default=0)
    if max_aqi >= 151:
        return "high"
    if max_aqi >= 101:
        return "moderate"
    if max_aqi > 0:
        return "low"
    return "unknown"
