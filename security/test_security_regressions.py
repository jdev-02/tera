import importlib
import xml.etree.ElementTree as ET

from defusedxml.ElementTree import fromstring as safe_xml_fromstring

from crypto.cot_signer import CotRoute, embed_signature_in_cot_xml, sign_cot, verify_cot
from security.structured_query_validator import validate_route_query


def _sample_cot_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<event version="2.0" uid="WAYFINDER-001" type="b-m-r-w"'
        ' time="2026-05-02T12:00:00Z" start="2026-05-02T12:00:00Z"'
        ' stale="2026-05-02T13:00:00Z" how="m-g">'
        '<point lat="37.7955" lon="-122.3937" hae="0" ce="9999999" le="9999999"/>'
        "<detail/></event>"
    )


def _sample_route() -> CotRoute:
    return CotRoute(
        uid="WAYFINDER-001",
        lat=37.7955,
        lon=-122.3937,
        route_geojson={
            "type": "LineString",
            "coordinates": [[-122.3937, 37.7955], [-122.415, 37.803]],
        },
        rationale="Fastest covered route to freshwater via draw.",
        mission_type="search_and_rescue",
    )


def _signed_cot_xml() -> str:
    return embed_signature_in_cot_xml(_sample_cot_xml(), sign_cot(_sample_route()))


def test_cot_signer_imports_as_package() -> None:
    module = importlib.import_module("crypto.cot_signer")
    assert hasattr(module, "verify_cot")


def test_verify_cot_rejects_outer_uid_tamper() -> None:
    root = safe_xml_fromstring(_signed_cot_xml())
    root.set("uid", "EVIL-ROUTE-999")

    result = verify_cot(ET.tostring(root, encoding="unicode"))

    assert result.valid is False
    assert "uid mismatch" in result.reason


def test_verify_cot_rejects_outer_point_tamper() -> None:
    root = safe_xml_fromstring(_signed_cot_xml())
    point = root.find("point")
    assert point is not None
    point.set("lat", "99.999")

    result = verify_cot(ET.tostring(root, encoding="unicode"))

    assert result.valid is False
    assert "latitude" in result.reason


def test_validate_route_query_rejects_extra_fields_and_bad_destination() -> None:
    query = {
        "mission_type": "search_and_rescue",
        "objective": "fastest_covered_route",
        "destination_type": "not_a_real_destination",
        "max_distance_km": 5,
        "constraints": ["avoid_ridgelines"],
        "allowed_data_layers": ["terrain"],
        "authority_context": {"user_role": "operator", "requires_approval": True},
        "unexpected_tool": "transmit_data",
    }

    result = validate_route_query(query)

    assert result["valid"] is False
    assert any("destination_type" in error for error in result["errors"])
    assert any("Additional properties" in error for error in result["errors"])
    assert any("transmit data" in error for error in result["errors"])


def test_validate_route_query_accepts_declared_schema() -> None:
    query = {
        "mission_type": "search_and_rescue",
        "objective": "fastest_covered_route",
        "destination_type": "freshwater",
        "max_distance_km": 5,
        "constraints": ["avoid_ridgelines", "prefer_cover"],
        "allowed_data_layers": ["terrain", "trails", "hydrography"],
        "authority_context": {"user_role": "operator", "requires_approval": True},
    }

    assert validate_route_query(query) == {"valid": True, "errors": []}
