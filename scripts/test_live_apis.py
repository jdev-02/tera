"""Optional live API smoke test for TERA v2.

Normal unit tests do not call the network. This script is for operator/demo
preflight only. It skips key-based APIs when the relevant environment variable
is missing and keeps running if any single API fails.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from typing import Any

from agent.mission_schemas import Coord
from integrations.google import maps_routes
from integrations.security import safe_browsing, urlscan, virustotal
from integrations.us_disaster import (
    airnow,
    bridge_inventory,
    eonet,
    fema,
    hifld,
    nifc_wfigs,
    noaa_nwps,
    nrel_fuel,
    nws,
    reliefweb,
    sf511,
    usgs_earthquake,
    usgs_water,
)


def main() -> None:
    submit_urlscan = "--submit-urlscan" in sys.argv
    checks: list[tuple[str, str | None, Callable[[], Any]]] = [
        ("NOAA/NWS Alerts", None, lambda: nws.get_active_alerts("CA")),
        ("NOAA/NWS Points", None, lambda: nws.get_point_metadata(37.7749, -122.4194)),
        ("FEMA OpenFEMA", None, lambda: fema.get_recent_disaster_declarations(5)),
        ("HIFLD Hospitals", None, lambda: hifld.get_hospitals_by_state("CA")),
        (
            "HIFLD Critical Infrastructure",
            None,
            hifld.get_critical_infrastructure_layers,
        ),
        ("WFIGS Fire Perimeters", None, nifc_wfigs.get_current_fire_perimeters),
        ("USGS Earthquake", None, usgs_earthquake.get_significant_earthquakes_week),
        ("USGS Water", None, lambda: usgs_water.get_streamflow_and_gage_height("ca")),
        ("NOAA NWPS", None, noaa_nwps.get_nwps_docs_or_health),
        (
            "National Bridge Inventory",
            None,
            lambda: bridge_inventory.get_bridge_inventory_sample(10),
        ),
        ("NASA EONET", None, lambda: eonet.get_open_events(20)),
        ("ReliefWeb", "RELIEFWEB_APPNAME", lambda: reliefweb.get_recent_us_reports(5)),
        (
            "Google Routes",
            "GOOGLE_MAPS_API_KEY",
            lambda: maps_routes.compute_routes(
                Coord(lat=37.7749, lon=-122.4194),
                Coord(lat=37.6879, lon=-122.4702),
            ),
        ),
        ("AirNow", "AIRNOW_API_KEY", lambda: airnow.get_current_air_quality(37.7749, -122.4194)),
        ("SF511", "SF511_API_KEY", sf511.get_traffic_events),
        (
            "NREL Fuel",
            "NREL_API_KEY",
            lambda: nrel_fuel.get_nearest_fuel_stations(37.7749, -122.4194),
        ),
        (
            "Google Safe Browsing",
            "GOOGLE_SAFE_BROWSING_API_KEY",
            lambda: safe_browsing.check_url_threats(["https://www.fema.gov/"]),
        ),
        (
            "VirusTotal URL",
            "VT_API_KEY",
            lambda: virustotal.get_url_report("https://www.fema.gov/"),
        ),
        ("VirusTotal Domain", "VT_API_KEY", lambda: virustotal.get_domain_report("fema.gov")),
    ]
    if submit_urlscan:
        checks.append(
            (
                "urlscan Submit",
                "URLSCAN_API_KEY",
                lambda: urlscan.submit_url_scan("https://www.fema.gov/", visibility="unlisted"),
            )
        )
    else:
        print("urlscan Submit: SKIPPED use --submit-urlscan to consume quota")

    for name, env_var, check in checks:
        if env_var and not os.getenv(env_var):
            print(f"{name}: SKIPPED missing {env_var}")
            continue
        try:
            check()
        except Exception as exc:  # noqa: BLE001
            print(f"{name}: WARN {exc}")
            continue
        print(f"{name}: OK")


if __name__ == "__main__":
    main()
