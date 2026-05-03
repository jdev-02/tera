"""POST /plan orchestrator: NL prompt -> RouteQuery -> security pipeline ->
tool dispatch -> signed response.

This is the brain. The LLM is sandboxed to emit RouteQuery JSON only. Every
other step is deterministic or runs through Satriyo's security pipeline.

Stage order:
    1. LLM produces RouteQuery (structured output, native to provider).
    2. security.pipeline.run_pipeline runs 6 stages:
       guard / redact / provenance / schema / policy / trust.
    3. translate_to_tool_calls maps RouteQuery -> tool args (deterministic).
    4. dispatch_tools runs the tool calls; resolves cross-call refs.
    5. crypto.cot_signer signs the response with ML-DSA (Satriyo's signer).
    6. Build PlanResponse + return.

If pipeline blocks -> raise HTTPException(403, PlanBlocked).
If the signer is unavailable -> emit unsigned with warning (never fail open).
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from agent.llm import LLMClient, ModeOrAuto, get_registry
from agent.schemas import (
    Coord,
    Message,
    OperatorSignature,
    PlanApprovalRequest,
    PlanApprovalResponse,
    PlanRequest,
    PlanResponse,
    PlanVerifyResponse,
    Signature,
    Waypoint,
)
from agent.tools import find_pois, route
from ontology import build_system_prompt, load_route_query_schema
from security.audit_log import audit_event, prompt_digest

log = structlog.get_logger(__name__)


def _canonical_json(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _timestamp_to_iso(value: Any) -> str:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(float(value), UTC).isoformat().replace("+00:00", "Z")
    return str(value)


def _hex_to_b64(value: str) -> str:
    return base64.b64encode(bytes.fromhex(value)).decode("ascii")


def _b64_to_hex(value: str) -> str:
    return base64.b64decode(value, validate=True).hex()


def _cot_route_hash(feature: dict[str, Any]) -> str:
    """Match crypto.cot_signer.sign_cot route_hash construction exactly."""
    return _sha256_hex(json.dumps(feature, sort_keys=True).encode())


# ---------------------------------------------------------------------------
# RouteQuery -> tool calls (deterministic translation)
# ---------------------------------------------------------------------------


_PROFILE_FROM_CONSTRAINTS: dict[frozenset[str], str] = {
    frozenset(): "foot",
    frozenset({"prefer_cover"}): "foot_covered",
    frozenset({"stay_on_trails"}): "foot_trails",
    frozenset({"prefer_cover", "stay_on_trails"}): "foot_covered_trails",
    frozenset({"prefer_cover", "avoid_ridgelines"}): "foot_covered",
}


def _profile_for(constraints: list[str]) -> str:
    cset = frozenset(c for c in constraints if not c.startswith("avoid_"))
    return _PROFILE_FROM_CONSTRAINTS.get(cset, "foot")


def _avoid_for(constraints: list[str]) -> list[str]:
    return [c.removeprefix("avoid_") for c in constraints if c.startswith("avoid_")]


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------


def _dispatch_tools(query: dict[str, Any], origin: Coord) -> dict[str, Any]:
    """Run the deterministic tool sequence for a validated RouteQuery.

    Returns a dict with:
        feature: GeoJSON LineString feature
        waypoints: list of Waypoint dicts
        cost_breakdown: dict
        rationale: operator-cadence explanation string
    """
    constraints = query.get("constraints", [])
    profile = _profile_for(constraints)
    avoid = _avoid_for(constraints)
    data_layers = query.get("allowed_data_layers", [])
    radius_m = int(query["max_distance_km"] * 1000)

    dest_type = query.get("destination_type", "none")
    origin_dict = origin.model_dump()

    # Step 1: resolve destination.
    if dest_type in {"freshwater", "safe_zone", "trailhead"}:
        pois = find_pois(type=dest_type, from_=origin_dict, radius_m=radius_m)
        if not pois:
            return {
                "feature": _empty_feature(origin_dict),
                "waypoints": [],
                "cost_breakdown": {"distance_m": 0.0, "time_s": 0.0, "elevation_gain_m": 0.0},
                "rationale": (
                    f"No {dest_type.replace('_', ' ')} found within "
                    f"{query['max_distance_km']} kilometers. Suggest expanding radius."
                ),
            }
        target = pois[0]
        dest_coord = {"lat": target["lat"], "lon": target["lon"]}
        dest_label = target.get("name", dest_type)
    elif dest_type == "known_location":
        # Real impl: pull destination from request payload (TODO when Ben adds
        # waypoint inputs). Stub: route to a point ~1km away for now.
        dest_coord = {"lat": origin.lat + 0.01, "lon": origin.lon}
        dest_label = "named location"
    else:
        # priority_search_area or none: no point-to-point route. Stub for now.
        return {
            "feature": _empty_feature(origin_dict),
            "waypoints": [],
            "cost_breakdown": {"distance_m": 0.0, "time_s": 0.0, "elevation_gain_m": 0.0},
            "rationale": (
                f"Objective {query.get('objective')!r} is not yet supported by the "
                "MVP pipeline. Coordinate with Ben on priority_grid tool."
            ),
        }

    # Step 2: route from origin to destination.
    route_result = route(
        profile=profile,
        start=origin_dict,
        end=dest_coord,
        avoid=avoid,
        data_layers=data_layers,
    )

    # Step 3: build waypoints + rationale.
    waypoints = [{"lat": dest_coord["lat"], "lon": dest_coord["lon"], "label": dest_label}]
    rationale = _build_rationale(
        dest_label=dest_label,
        cost=route_result["cost_breakdown"],
        profile=profile,
        avoid=avoid,
    )

    return {
        "feature": route_result["feature"],
        "waypoints": waypoints,
        "cost_breakdown": route_result["cost_breakdown"],
        "rationale": rationale,
    }


def _empty_feature(origin: dict[str, float]) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [[origin["lon"], origin["lat"]], [origin["lon"], origin["lat"]]],
        },
        "properties": {"empty": True},
    }


def _build_rationale(
    dest_label: str, cost: dict[str, float], profile: str, avoid: list[str]
) -> str:
    """Operator-cadence rationale text. Spoken aloud by Piper TTS later (#26).

    Avoid prose. Use military number-reading where possible. Ben (P4) refines
    this phrasing during the operator-cadence pairing session.
    """
    distance_km = cost.get("distance_m", 0.0) / 1000.0
    time_min = cost.get("time_s", 0.0) / 60.0
    avoid_str = f" Avoiding {', '.join(a.replace('_', ' ') for a in avoid)}." if avoid else ""
    return (
        f"Routed to {dest_label}, distance {distance_km:.1f} kilometers, "
        f"ETA {time_min:.0f} minutes on {profile.replace('_', ' ')}.{avoid_str}"
    )


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------


def _sign_response(
    request_id: str,
    feature: dict[str, Any],
    waypoints: list[dict[str, Any]],
    rationale: str,
    mission_type: str,
) -> Signature | None:
    """Sign the response with ML-DSA via Satriyo's `crypto.cot_signer.sign_cot`.

    Returns None if the signer isn't available (e.g. liboqs not installed).
    Never raises -- a missing signature is a degraded but valid response;
    raising would fail the entire /plan call.

    Field mapping note: Satriyo's signer returns
        {payload, signature, key_id, algorithm, timestamp, payload_hash}
    while our public Signature model uses
        {scheme, key_id, value_b64, signed_at}.
    The mapping below is documented in GH issue (TODO: open) "reconcile
    signature contract -- cot_signed.md vs ml_dsa_signer output".
    """
    try:
        # Late imports: crypto module may not be importable on machines without
        # liboqs system lib (Jon's laptop pre-`make install-crypto`).
        from crypto.cot_signer import CotRoute, sign_cot

        # CotRoute wants a single (lat, lon) for the destination -- use the
        # last waypoint, or origin if no waypoints. The full geometry is
        # hashed into the payload via route_geojson.
        if waypoints:
            dest_lat = waypoints[-1]["lat"]
            dest_lon = waypoints[-1]["lon"]
        else:
            coords = feature["geometry"]["coordinates"]
            dest_lon, dest_lat = coords[-1][0], coords[-1][1]

        route = CotRoute(
            uid=f"TERA-{request_id}",
            lat=dest_lat,
            lon=dest_lon,
            route_geojson=feature,
            rationale=rationale,
            mission_type=mission_type,
        )
        signed = sign_cot(route)
        payload_json = json.dumps(signed["payload"], sort_keys=True, separators=(",", ":"))
        return Signature(
            scheme=signed["algorithm"],
            key_id=signed["key_id"],
            value_b64=_hex_to_b64(signed["signature"]),
            signed_at=_timestamp_to_iso(signed["timestamp"]),
            canonicalization="route-payload-json-v1",
            payload_hash=signed["payload_hash"],
            payload_json=payload_json,
        )
    except (ImportError, RuntimeError) as e:
        log.warning("signer_unavailable", error=str(e))
        return None
    except Exception as e:  # noqa: BLE001 -- never fail /plan because of signer
        log.exception("signer_failed", error=str(e))
        return None


def _destination_for_response(response: PlanResponse) -> tuple[float, float]:
    if response.waypoints:
        last = response.waypoints[-1]
        return last.lat, last.lon

    coords = response.route.get("geometry", {}).get("coordinates", [])
    if not coords:
        raise ValueError("route geometry has no coordinates")
    dest_lon, dest_lat = coords[-1][0], coords[-1][1]
    return float(dest_lat), float(dest_lon)


def _payload_matches_plan_response(
    response: PlanResponse,
    payload: dict[str, Any],
) -> tuple[bool, str, str]:
    route_hash = _cot_route_hash(response.route)

    if payload.get("uid") != f"TERA-{response.request_id}":
        return False, "signed payload uid does not match response request_id", route_hash

    if payload.get("route_hash") != route_hash:
        return False, "signed payload route_hash does not match response route", route_hash

    if payload.get("rationale") != response.rationale:
        return False, "signed payload rationale does not match response rationale", route_hash

    try:
        expected_lat, expected_lon = _destination_for_response(response)
    except (KeyError, IndexError, TypeError, ValueError) as e:
        return False, f"response destination is malformed: {e}", route_hash

    payload_lat_raw = payload.get("lat")
    payload_lon_raw = payload.get("lon")
    if payload_lat_raw is None or payload_lon_raw is None:
        return False, "signed payload destination is missing", route_hash

    try:
        payload_lat = float(payload_lat_raw)
        payload_lon = float(payload_lon_raw)
    except (TypeError, ValueError) as e:
        return False, f"signed payload destination is malformed: {e}", route_hash

    if not math.isclose(payload_lat, expected_lat, rel_tol=0.0, abs_tol=1e-7):
        return False, "signed payload latitude does not match response destination", route_hash

    if not math.isclose(payload_lon, expected_lon, rel_tol=0.0, abs_tol=1e-7):
        return False, "signed payload longitude does not match response destination", route_hash

    if not isinstance(payload.get("mission_type"), str) or not payload["mission_type"]:
        return False, "signed payload mission_type is missing", route_hash

    return True, "payload binding valid", route_hash


def verify_plan_response(response: PlanResponse) -> PlanVerifyResponse:
    """Verify a /plan response before ATAK renders it.

    This is the hackathon verify-proxy path for issue #81. The signature is
    self-contained: payload_json is verified cryptographically, then bound back
    to the route/rationale fields ATAK is about to render.
    """
    signature = response.signature
    if signature is None:
        return PlanVerifyResponse(valid=False, reason="Route signature missing - REJECTED")

    if not signature.payload_hash or not signature.payload_json:
        return PlanVerifyResponse(
            valid=False,
            key_id=signature.key_id,
            scheme=signature.scheme,
            reason="Signature payload metadata missing - REJECTED",
        )

    try:
        payload = json.loads(signature.payload_json)
        canonical_payload = _canonical_json(payload)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        return PlanVerifyResponse(
            valid=False,
            key_id=signature.key_id,
            scheme=signature.scheme,
            reason=f"Signature payload_json malformed - REJECTED: {e}",
        )

    computed_hash = _sha256_hex(canonical_payload)
    if computed_hash != signature.payload_hash:
        return PlanVerifyResponse(
            valid=False,
            key_id=signature.key_id,
            scheme=signature.scheme,
            reason="Signature payload_hash mismatch - REJECTED",
        )

    bound, reason, route_hash = _payload_matches_plan_response(response, payload)
    if not bound:
        return PlanVerifyResponse(
            valid=False,
            key_id=signature.key_id,
            scheme=signature.scheme,
            route_hash=route_hash,
            reason=f"{reason} - REJECTED",
        )

    try:
        from crypto.ml_dsa_signer import SignedPayload, create_signer

        signed = SignedPayload(
            payload=payload,
            signature=_b64_to_hex(signature.value_b64),
            key_id=signature.key_id,
            algorithm=signature.scheme,
            timestamp=0.0,
            payload_hash=signature.payload_hash,
        )
        ok = create_signer(signature.key_id).verify(signed)
    except Exception as e:  # noqa: BLE001 -- fail closed for render gate
        return PlanVerifyResponse(
            valid=False,
            key_id=signature.key_id,
            scheme=signature.scheme,
            route_hash=route_hash,
            reason=f"Signature verification error - REJECTED: {e}",
        )

    if not ok:
        return PlanVerifyResponse(
            valid=False,
            key_id=signature.key_id,
            scheme=signature.scheme,
            route_hash=route_hash,
            reason="Signature invalid - route REJECTED",
        )

    return PlanVerifyResponse(
        valid=True,
        key_id=signature.key_id,
        scheme=signature.scheme,
        route_hash=route_hash,
        reason="Signature valid - route authentic",
    )


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


class PlanBlockedError(Exception):
    """Raised when the security pipeline blocks the request. Caller (FastAPI
    handler) should turn this into a 403 with the stage detail."""

    def __init__(self, blocked_at: str, stages: list[dict[str, Any]], reason: str):
        super().__init__(reason)
        self.blocked_at = blocked_at
        self.stages = stages
        self.reason = reason


async def plan(req: PlanRequest, mode: ModeOrAuto = "auto", with_tts: bool = False) -> PlanResponse:
    """End-to-end /plan handler.

    Args:
        req: validated PlanRequest from the HTTP layer.
        mode: which LLM mode to use ("auto" -> profile default).
              In this PR `mode` is server-controlled (not yet on PlanRequest).
        with_tts: if True, synthesize the operator-cadence rationale via
              Piper TTS and embed it in PlanResponse.audio_b64. Defaults to
              False so existing callers see no behavior change. Hands-free
              path (#21) sets this from the `?tts=true` query param.
              That contract change goes through Ben + Satriyo signoff at the
              Sat 1500 freeze and lands in a follow-up PR.
    """
    request_id = req.request_id or str(uuid.uuid4())
    logger = log.bind(request_id=request_id)
    logger.info(
        "plan_request",
        prompt_len=len(req.prompt),
        mode=mode,
        source=req.source,
    )
    audit_event(
        "prompt_received",
        request_id=request_id,
        prompt_sha256=prompt_digest(req.prompt),
        prompt_len=len(req.prompt),
        mode=mode,
        source=req.source,
    )

    # 1. Get the LLM client (profile + mode gated).
    client: LLMClient = get_registry().get(mode)

    # 2. LLM produces RouteQuery (structured output, native to provider).
    schema = load_route_query_schema()
    system_prompt = build_system_prompt()
    try:
        structured_query = client.complete_structured(
            messages=[
                Message(role="system", content=system_prompt),
                Message(role="user", content=req.prompt),
            ],
            schema=schema,
            temperature=0.0,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("llm_failed", provider=client.name, error=str(e))
        raise RuntimeError(f"LLM ({client.name}) failed to produce RouteQuery: {e}") from e

    logger.info(
        "llm_emitted_route_query",
        provider=client.name,
        objective=structured_query.get("objective"),
        destination_type=structured_query.get("destination_type"),
    )
    audit_event(
        "route_query_emitted",
        request_id=request_id,
        provider=client.name,
        mission_type=structured_query.get("mission_type"),
        objective=structured_query.get("objective"),
        destination_type=structured_query.get("destination_type"),
        max_distance_km=structured_query.get("max_distance_km"),
    )

    # 3. Security pipeline (Satriyo's 6 stages).
    pipeline_result = await _run_security_pipeline(
        raw_text=req.prompt,
        source=req.source,
        structured_query=structured_query,
    )
    if not _pipeline_passed(pipeline_result):
        logger.warning(
            "pipeline_blocked",
            blocked_at=pipeline_result["blocked_at"],
        )
        audit_event(
            "security_pipeline_blocked",
            request_id=request_id,
            blocked_at=pipeline_result["blocked_at"],
            stage_count=len(pipeline_result.get("stages", [])),
            atak_display=pipeline_result.get("atak_display"),
        )
        raise PlanBlockedError(
            blocked_at=pipeline_result["blocked_at"] or "unknown",
            stages=pipeline_result["stages"],
            reason=pipeline_result.get("atak_display", "blocked by security pipeline"),
        )

    audit_event(
        "security_pipeline_allowed",
        request_id=request_id,
        stage_count=len(pipeline_result.get("stages", [])),
        trust_status=(pipeline_result.get("trust_result") or {}).get("trust_status"),
    )

    # 4. Translate RouteQuery -> tool calls -> dispatch.
    planned_tools = _tool_names_for_query(structured_query)
    audit_event(
        "tool_dispatch_started",
        request_id=request_id,
        tools=planned_tools,
    )
    dispatch = _dispatch_tools(structured_query, req.current)
    audit_event(
        "tool_dispatch_completed",
        request_id=request_id,
        tools=planned_tools,
        waypoint_count=len(dispatch["waypoints"]),
        distance_m=dispatch["cost_breakdown"].get("distance_m"),
    )

    # 5. Sign.
    signature = _sign_response(
        request_id=request_id,
        feature=dispatch["feature"],
        waypoints=dispatch["waypoints"],
        rationale=dispatch["rationale"],
        mission_type=structured_query["mission_type"],
    )
    if signature is None:
        logger.warning("plan_unsigned", note="ML-DSA signer unavailable; degraded mode")
        audit_event(
            "route_signing_degraded",
            request_id=request_id,
            signed=False,
            reason="signer_unavailable",
        )
    else:
        audit_event(
            "route_signed",
            request_id=request_id,
            signed=True,
            scheme=signature.scheme,
            key_id=signature.key_id,
        )

    # 6. Optional TTS (hands-free path). Synthesize the rationale into a
    #    base64-encoded WAV in operator cadence. Lazy-imported so machines
    #    without piper-tts installed (e.g. CI without the [voice] extra) don't
    #    even load the module.
    audio_b64: str | None = None
    if with_tts:
        try:
            from voice.tts import synthesize_rationale_b64

            audio_b64 = synthesize_rationale_b64(
                dispatch["rationale"],
                operator_mode=req.voice_profile,
            )
        except Exception as e:  # noqa: BLE001 -- TTS failure must not fail /plan
            logger.warning("tts_synth_failed", error=str(e))

    # 7. Build response.
    response = PlanResponse(
        request_id=request_id,
        route=dispatch["feature"],
        waypoints=[Waypoint(**w) for w in dispatch["waypoints"]],
        rationale=dispatch["rationale"],
        cost_breakdown=dispatch["cost_breakdown"],
        trust=pipeline_result.get("trust_result") or {},
        signature=signature,
        audio_b64=audio_b64,
    )
    logger.info(
        "plan_response",
        provider=client.name,
        signed=signature is not None,
        spoken=audio_b64 is not None,
        trust_status=(pipeline_result.get("trust_result") or {}).get("trust_status"),
    )
    audit_event(
        "plan_response_ready",
        request_id=request_id,
        signed=signature is not None,
        trust_status=(pipeline_result.get("trust_result") or {}).get("trust_status"),
        waypoint_count=len(response.waypoints),
    )
    return response


async def _run_security_pipeline(
    raw_text: str,
    source: str,
    structured_query: dict[str, Any],
) -> dict[str, Any]:
    """Thin wrapper around security.plan_guard.guard_plan_request.

    Late import so an import error in the security lane doesn't crash the whole
    agent at startup. Stage-1 /plan routes are provisional by design; operator
    approval only happens through /plan/approve.
    """
    try:
        from security.plan_guard import guard_plan_request
    except ImportError as e:
        log.error("security_pipeline_import_failed", error=str(e))
        raise RuntimeError(
            "security.plan_guard import failed -- agent cannot serve requests safely"
        ) from e

    result = await guard_plan_request(
        raw_text=raw_text,
        source=source,
        source_type="operator-intent",
        structured_query=structured_query,
        target_agent="RoutingAgent",
        operation="ComputeRoute",
        operator_approved=False,
        signature_valid=False,
    )
    return result.to_dict()


def _pipeline_passed(result: dict[str, Any]) -> bool:
    if "passed" in result:
        return bool(result["passed"])
    if "pipeline_passed" in result:
        return bool(result["pipeline_passed"])
    return bool(result.get("allowed", False))


def _tool_names_for_query(query: dict[str, Any]) -> list[str]:
    dest_type = query.get("destination_type", "none")
    objective = query.get("objective")
    tools: list[str] = []
    if dest_type in {"freshwater", "safe_zone", "trailhead"}:
        tools.append("find_pois")
    if (
        objective in {"fastest_route", "fastest_covered_route", "nearest_water"}
        and dest_type != "none"
    ):
        tools.append("route")
    return tools


def _route_hash(route: dict[str, Any], waypoints: list[Waypoint]) -> str:
    canonical = _canonical_json(
        {
            "route": route,
            "waypoints": [w.model_dump(exclude_none=True) for w in waypoints],
        }
    )
    return _sha256_hex(canonical)


def _sign_operator_commit(
    *,
    route_id: str,
    route_hash: str,
    device_signature: Signature,
    operator_key_id: str,
    approved_by: str | None,
) -> OperatorSignature:
    """Create the operator's stage-3 approval signature.

    Fails closed: if the signer cannot load, the route is not operator-committed.
    """
    try:
        from crypto.ml_dsa_signer import create_signer
    except ImportError as e:
        raise RuntimeError("operator signer import failed") from e

    payload = {
        "route_id": route_id,
        "approves_route_hash": route_hash,
        "device_signature": device_signature.model_dump(),
        "approved_by": approved_by,
    }
    signed = create_signer(operator_key_id).sign(payload)
    envelope = signed.to_signature_dict(canonicalization="route-approval-json-v1")
    canonical_payload_str = _canonical_json(payload).decode("utf-8")
    return OperatorSignature(
        scheme=str(envelope["scheme"]),
        key_id=str(envelope["key_id"]),
        value_b64=str(envelope["value_b64"]),
        signed_at=_timestamp_to_iso(envelope["signed_at"]),
        approves_route_hash=route_hash,
        payload_hash=str(envelope["payload_hash"]),
        payload_json=canonical_payload_str,
    )


def approve_plan(req: PlanApprovalRequest) -> PlanApprovalResponse:
    """Commit a provisional device-signed route after operator review."""
    route_hash = _route_hash(req.route, req.waypoints)
    audit_event(
        "operator_approval_requested",
        route_id=req.route_id,
        route_hash=route_hash,
        operator_key_id=req.operator_key_id,
        waypoint_count=len(req.waypoints),
    )
    operator_signature = _sign_operator_commit(
        route_id=req.route_id,
        route_hash=route_hash,
        device_signature=req.device_signature,
        operator_key_id=req.operator_key_id,
        approved_by=req.approved_by,
    )
    audit_event(
        "operator_approval_committed",
        route_id=req.route_id,
        route_hash=route_hash,
        operator_key_id=operator_signature.key_id,
        scheme=operator_signature.scheme,
    )
    return PlanApprovalResponse(
        route_id=req.route_id,
        route_hash=route_hash,
        device_signature=req.device_signature,
        operator_signature=operator_signature,
    )
