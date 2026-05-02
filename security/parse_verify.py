"""Intrinsic parsing-verification gates for untrusted tactical inputs.

This module is deliberately small and deterministic. It validates shape and
grammar before downstream code treats OSM tags, LLM tool-call args, or CoT XML
as meaningful mission data. Cryptographic checks still live in crypto/.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from defusedxml.ElementTree import fromstring as safe_xml_fromstring
from jsonschema import Draft202012Validator

CONTRACT_PATH = (
    Path(__file__).resolve().parent.parent / "docs" / "contracts" / "agent_routing.schema.json"
)

FORBIDDEN_INSTRUCTION_TERMS = (
    "ignore previous instructions",
    "ignore all prior",
    "override policy",
    "disable approval",
    "bypass validation",
    "admin override",
    "sign this route",
    "export keys",
    "transmit data",
    "execute shell",
    "os.system",
    "subprocess",
    "__import__",
)

TAG_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:_-]{0,63}$")
SAFE_TAG_VALUE_RE = re.compile(r"^[^\x00-\x1f<>]{0,256}$")

TOOL_ARG_SCHEMAS = {
    "find_pois": "FindPoisArgs",
    "route": "RouteArgs",
}


@dataclass(frozen=True)
class ParseVerifyResult:
    artifact_type: str
    valid: bool
    errors: list[str] = field(default_factory=list)


def _contains_forbidden_instruction(value: object) -> str | None:
    text = json.dumps(value, sort_keys=True, default=str).lower()
    normalized = text.replace("_", " ").replace("-", " ")
    for term in FORBIDDEN_INSTRUCTION_TERMS:
        if term in text or term in normalized:
            return term
    return None


def validate_osm_tags(tags: Mapping[str, object]) -> ParseVerifyResult:
    """Validate OSM tag grammar and reject instruction-like tag content."""
    errors: list[str] = []

    if not isinstance(tags, Mapping):
        return ParseVerifyResult("osm_tags", False, ["OSM tags must be a mapping"])

    for key, value in tags.items():
        if not isinstance(key, str) or not TAG_KEY_RE.fullmatch(key):
            errors.append(f"Invalid OSM tag key: {key!r}")
            continue
        if not isinstance(value, str):
            errors.append(f"OSM tag '{key}' value must be a string")
            continue
        if not SAFE_TAG_VALUE_RE.fullmatch(value):
            errors.append(f"OSM tag '{key}' contains unsafe characters or is too long")

    if "waterway" in tags and "highway" in tags:
        errors.append("OSM tag set combines waterway and highway on one feature")

    term = _contains_forbidden_instruction(tags)
    if term:
        errors.append(f"OSM tags contain instruction-like text: {term!r}")

    return ParseVerifyResult("osm_tags", not errors, errors)


@lru_cache(maxsize=1)
def _contract_schema() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=len(TOOL_ARG_SCHEMAS))
def _tool_validator(tool_name: str) -> Draft202012Validator:
    contract = _contract_schema()
    definition_name = TOOL_ARG_SCHEMAS[tool_name]
    schema = {
        "$schema": contract["$schema"],
        "definitions": contract["definitions"],
        **contract["definitions"][definition_name],
    }
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _schema_error_message(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    return f"{path}: {error.message}" if path else str(error.message)


def validate_tool_call_args(tool_name: str, args: Mapping[str, object]) -> ParseVerifyResult:
    """Validate deterministic tool-call args before geospatial dispatch."""
    errors: list[str] = []

    if tool_name not in TOOL_ARG_SCHEMAS:
        return ParseVerifyResult("tool_call_args", False, [f"Unknown tool: {tool_name!r}"])

    if not isinstance(args, Mapping):
        return ParseVerifyResult("tool_call_args", False, ["Tool args must be a mapping"])

    validator = _tool_validator(tool_name)
    errors.extend(
        _schema_error_message(error)
        for error in sorted(
            validator.iter_errors(dict(args)), key=lambda err: list(err.absolute_path)
        )
    )

    term = _contains_forbidden_instruction(args)
    if term:
        errors.append(f"Tool args contain instruction-like text: {term!r}")

    return ParseVerifyResult("tool_call_args", not errors, errors)


def validate_cot_structure(cot_xml: str) -> ParseVerifyResult:
    """Validate CoT structure before crypto verification or ATAK forwarding."""
    errors: list[str] = []

    try:
        root = safe_xml_fromstring(cot_xml)
    except (ET.ParseError, ValueError) as exc:
        return ParseVerifyResult("cot_xml", False, [f"CoT XML parse error: {exc}"])

    if root.tag != "event":
        errors.append(f"CoT root must be <event>, got <{root.tag}>")

    for attr in ("uid", "type", "time", "start", "stale", "how"):
        if not root.get(attr):
            errors.append(f"CoT event missing required attribute: {attr}")

    point = root.find("point")
    if point is None:
        errors.append("CoT event missing <point>")
    else:
        for attr, low, high in (("lat", -90.0, 90.0), ("lon", -180.0, 180.0)):
            raw = point.get(attr)
            try:
                value = float(raw) if raw is not None else None
            except ValueError:
                value = None
            if value is None or not low <= value <= high:
                errors.append(f"CoT point {attr} must be within [{low}, {high}]")

    wayfinder = root.find(".//wayfinder")
    if wayfinder is None:
        errors.append("CoT missing <detail><wayfinder> signature block")
    else:
        for child in (
            "signature",
            "key_id",
            "algorithm",
            "timestamp",
            "payload_hash",
            "payload_json",
        ):
            if not (wayfinder.findtext(child) or "").strip():
                errors.append(f"CoT wayfinder missing <{child}>")

    term = _contains_forbidden_instruction(ET.tostring(root, encoding="unicode"))
    if term:
        errors.append(f"CoT contains instruction-like text: {term!r}")

    return ParseVerifyResult("cot_xml", not errors, errors)
