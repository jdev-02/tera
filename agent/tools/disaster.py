"""Higher-level disaster context tools for the v2 mission planner."""

from __future__ import annotations

from typing import Any

from integrations.us_disaster import eonet, fema, nifc_wfigs, nws, usgs_earthquake, usgs_water


def get_active_hazards(area: str = "CA") -> list[dict[str, Any]]:
    raw = nws.get_active_alerts(area)
    return [alert.model_dump() for alert in nws.normalize_alerts(raw)]


def collect_disaster_context(
    area: str = "CA",
    incident_type: str = "wildfire",
) -> dict[str, Any]:
    context: dict[str, Any] = {"area": area, "incident_type": incident_type, "sources": {}}
    context["sources"]["nws_alerts"] = get_active_hazards(area)
    context["sources"]["fema_declarations"] = [
        item.model_dump()
        for item in fema.normalize_declarations(fema.get_declarations_by_state(area))
    ]
    if incident_type == "wildfire":
        context["sources"]["fire_perimeters"] = [
            item.model_dump()
            for item in nifc_wfigs.normalize_fire_perimeters(
                nifc_wfigs.get_current_fire_perimeters()
            )
        ]
    if incident_type == "earthquake":
        context["sources"]["earthquakes"] = [
            item.model_dump()
            for item in usgs_earthquake.normalize_earthquakes(
                usgs_earthquake.get_significant_earthquakes_week()
            )
        ]
    if incident_type == "flood":
        context["sources"]["water_observations"] = [
            item.model_dump()
            for item in usgs_water.normalize_water_observations(
                usgs_water.get_streamflow_and_gage_height(area.lower())
            )
        ]
    if incident_type == "general":
        context["sources"]["global_events"] = [
            item.model_dump() for item in eonet.normalize_events(eonet.get_open_events(limit=10))
        ]
    return context
