from __future__ import annotations

from integrations.us_disaster import hifld


def test_normalize_hospitals_geojson() -> None:
    raw = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-122.42, 37.77]},
                "properties": {
                    "OBJECTID": 7,
                    "NAME": "Hospital B",
                    "ADDRESS": "1 Mission St",
                    "CITY": "San Francisco",
                    "STATE": "CA",
                    "TYPE": "GENERAL ACUTE CARE",
                },
            }
        ],
    }

    hospitals = hifld.normalize_hospitals(raw)

    assert hospitals[0].name == "Hospital B"
    assert hospitals[0].category == "hospital"
    assert hospitals[0].coord is not None
    assert hospitals[0].coord.lat == 37.77


def test_list_critical_infrastructure_layers(monkeypatch) -> None:
    monkeypatch.setattr(
        hifld,
        "get_critical_infrastructure_layers",
        lambda: {"layers": [{"id": 1, "name": "Fire Stations"}, "bad"]},
    )

    layers = hifld.list_critical_infrastructure_layers()

    assert layers == [{"id": 1, "name": "Fire Stations"}]
