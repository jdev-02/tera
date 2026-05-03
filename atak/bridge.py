"""ATAK bridge entry points."""

from __future__ import annotations

import json
from pathlib import Path

from atak.cot import PlanMapping, write_plan_kml


def export_plan_kml(plan: PlanMapping, output_path: str | Path) -> Path:
    """Export a plan response to a KML file for manual ATAK import."""
    return write_plan_kml(plan, output_path)


def export_plan_json_kml(plan_json: str, output_path: str | Path) -> Path:
    """Export a JSON-encoded plan response to KML."""
    decoded = json.loads(plan_json)
    if not isinstance(decoded, dict):
        msg = "plan JSON must decode to an object"
        raise ValueError(msg)
    return export_plan_kml(decoded, output_path)
