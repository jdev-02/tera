from __future__ import annotations

from integrations.us_disaster import nws


def test_normalize_alerts() -> None:
    raw = {
        "features": [
            {
                "id": "alert-1",
                "geometry": {"type": "Polygon", "coordinates": []},
                "properties": {
                    "id": "nws-alert-1",
                    "event": "Red Flag Warning",
                    "severity": "Severe",
                    "urgency": "Expected",
                    "certainty": "Likely",
                    "areaDesc": "Bay Area",
                    "instruction": "Avoid exposed ridges.",
                },
            }
        ]
    }

    alerts = nws.normalize_alerts(raw)

    assert len(alerts) == 1
    assert alerts[0].id == "nws-alert-1"
    assert alerts[0].event == "Red Flag Warning"
    assert alerts[0].severity == "Severe"
