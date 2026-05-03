"""KML and CoT-adjacent helpers for ATAK route export."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from xml.etree import ElementTree

KML_NS = "http://www.opengis.net/kml/2.2"
ElementTree.register_namespace("", KML_NS)

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | Mapping[str, "JsonValue"] | Sequence["JsonValue"]
PlanMapping = Mapping[str, JsonValue]


class PlanExportError(ValueError):
    """Raised when a plan response cannot be exported for ATAK."""


def plan_to_kml(plan: PlanMapping, *, document_name: str = "TERA route") -> str:
    """Serialize a PlanResponse-like mapping to a KML document."""
    coordinates = _extract_linestring_coordinates(plan)
    waypoints = _extract_waypoints(plan)

    kml = ElementTree.Element(_kml_tag("kml"))
    document = ElementTree.SubElement(kml, _kml_tag("Document"))
    ElementTree.SubElement(document, _kml_tag("name")).text = document_name

    route_placemark = ElementTree.SubElement(document, _kml_tag("Placemark"))
    ElementTree.SubElement(route_placemark, _kml_tag("name")).text = "TERA route"
    rationale = plan.get("rationale")
    if isinstance(rationale, str):
        ElementTree.SubElement(route_placemark, _kml_tag("description")).text = rationale

    line = ElementTree.SubElement(route_placemark, _kml_tag("LineString"))
    ElementTree.SubElement(line, _kml_tag("tessellate")).text = "1"
    ElementTree.SubElement(line, _kml_tag("coordinates")).text = " ".join(
        _format_kml_coordinate(lon, lat, alt) for lon, lat, alt in coordinates
    )

    for index, waypoint in enumerate(waypoints, start=1):
        placemark = ElementTree.SubElement(document, _kml_tag("Placemark"))
        ElementTree.SubElement(placemark, _kml_tag("name")).text = (
            waypoint.label or f"Waypoint {index}"
        )
        point = ElementTree.SubElement(placemark, _kml_tag("Point"))
        ElementTree.SubElement(point, _kml_tag("coordinates")).text = _format_kml_coordinate(
            waypoint.lon,
            waypoint.lat,
            None,
        )

    ElementTree.indent(kml, space="  ")
    xml = ElementTree.tostring(kml, encoding="utf-8", xml_declaration=True)
    return xml.decode("utf-8")


def write_plan_kml(
    plan: PlanMapping,
    output_path: str | Path,
    *,
    document_name: str = "TERA route",
) -> Path:
    """Write a PlanResponse-like mapping as a KML file and return the path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plan_to_kml(plan, document_name=document_name), encoding="utf-8")
    return path


class _Waypoint:
    def __init__(self, *, lat: float, lon: float, label: str | None) -> None:
        self.lat = lat
        self.lon = lon
        self.label = label


def _kml_tag(name: str) -> str:
    return f"{{{KML_NS}}}{name}"


def _extract_linestring_coordinates(plan: PlanMapping) -> list[tuple[float, float, float | None]]:
    route = _mapping_field(plan, "route")
    geometry = _mapping_field(route, "geometry")
    geometry_type = geometry.get("type")
    if geometry_type != "LineString":
        raise PlanExportError("plan route geometry must be a GeoJSON LineString")

    raw_coordinates = geometry.get("coordinates")
    if not isinstance(raw_coordinates, Sequence) or isinstance(raw_coordinates, str):
        raise PlanExportError("plan route geometry coordinates must be a sequence")

    coordinates: list[tuple[float, float, float | None]] = []
    for raw_coord in raw_coordinates:
        if not isinstance(raw_coord, Sequence) or isinstance(raw_coord, str):
            raise PlanExportError("each route coordinate must be a sequence")
        if len(raw_coord) not in {2, 3}:
            raise PlanExportError(
                "each route coordinate must contain lon, lat, and optional altitude"
            )

        lon = _number(raw_coord[0], "route longitude")
        lat = _number(raw_coord[1], "route latitude")
        alt = _number(raw_coord[2], "route altitude") if len(raw_coord) == 3 else None
        coordinates.append((lon, lat, alt))

    if len(coordinates) < 2:
        raise PlanExportError("route must contain at least two coordinates")

    return coordinates


def _extract_waypoints(plan: PlanMapping) -> list[_Waypoint]:
    raw_waypoints = plan.get("waypoints", [])
    if not isinstance(raw_waypoints, Sequence) or isinstance(raw_waypoints, str):
        raise PlanExportError("plan waypoints must be a sequence")

    waypoints: list[_Waypoint] = []
    for raw_waypoint in raw_waypoints:
        if not isinstance(raw_waypoint, Mapping):
            raise PlanExportError("each waypoint must be an object")
        lat = _number(raw_waypoint.get("lat"), "waypoint latitude")
        lon = _number(raw_waypoint.get("lon"), "waypoint longitude")
        raw_label = raw_waypoint.get("label")
        label = raw_label if isinstance(raw_label, str) else None
        waypoints.append(_Waypoint(lat=lat, lon=lon, label=label))

    return waypoints


def _mapping_field(source: Mapping[str, JsonValue], name: str) -> Mapping[str, JsonValue]:
    value = source.get(name)
    if not isinstance(value, Mapping):
        raise PlanExportError(f"plan field {name!r} must be an object")
    return value


def _number(value: JsonValue, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PlanExportError(f"{label} must be numeric")
    return float(value)


def _format_kml_coordinate(lon: float, lat: float, alt: float | None) -> str:
    altitude = 0.0 if alt is None else alt
    return f"{lon:.7f},{lat:.7f},{altitude:.2f}"
