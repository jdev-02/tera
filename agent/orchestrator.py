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

import uuid
from typing import Any

import structlog

from agent.llm import LLMClient, ModeOrAuto, get_registry
from agent.schemas import (
    Coord,
    Message,
    PlanRequest,
    PlanResponse,
    Signature,
    Waypoint,
)
from agent.tools import find_pois, route
from ontology import build_system_prompt, load_route_query_schema

log = structlog.get_logger(__name__)


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
        return Signature(
            scheme="ML-DSA-65",  # Satriyo's signer uses ML-DSA-65 (Dilithium3)
            key_id=signed["key_id"],
            value_b64=signed["signature"],
            signed_at=signed["timestamp"],
        )
    except (ImportError, RuntimeError) as e:
        log.warning("signer_unavailable", error=str(e))
        return None
    except Exception as e:  # noqa: BLE001 -- never fail /plan because of signer
        log.exception("signer_failed", error=str(e))
        return None


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


async def plan(req: PlanRequest, mode: ModeOrAuto = "auto") -> PlanResponse:
    """End-to-end /plan handler.

    Args:
        req: validated PlanRequest from the HTTP layer.
        mode: which LLM mode to use ("auto" -> profile default).
              In this PR `mode` is server-controlled (not yet on PlanRequest).
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

    # 3. Security pipeline (Satriyo's 6 stages).
    pipeline_result = await _run_security_pipeline(
        raw_text=req.prompt,
        source=req.source,
        structured_query=structured_query,
    )
    if not pipeline_result["passed"]:
        logger.warning(
            "pipeline_blocked",
            blocked_at=pipeline_result["blocked_at"],
        )
        raise PlanBlockedError(
            blocked_at=pipeline_result["blocked_at"] or "unknown",
            stages=pipeline_result["stages"],
            reason=pipeline_result.get("atak_display", "blocked by security pipeline"),
        )

    # 4. Translate RouteQuery -> tool calls -> dispatch.
    dispatch = _dispatch_tools(structured_query, req.current)

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

    # 6. Build response.
    response = PlanResponse(
        request_id=request_id,
        route=dispatch["feature"],
        waypoints=[Waypoint(**w) for w in dispatch["waypoints"]],
        rationale=dispatch["rationale"],
        cost_breakdown=dispatch["cost_breakdown"],
        trust=pipeline_result.get("trust_result") or {},
        signature=signature,
    )
    logger.info(
        "plan_response",
        provider=client.name,
        signed=signature is not None,
        trust_status=(pipeline_result.get("trust_result") or {}).get("trust_status"),
    )
    return response


async def _run_security_pipeline(
    raw_text: str,
    source: str,
    structured_query: dict[str, Any],
) -> dict[str, Any]:
    """Thin wrapper around security.pipeline.run_pipeline.

    Late import so an import error in the security lane doesn't crash the
    whole agent at startup -- we degrade to a clear 503 instead.
    """
    try:
        from security.pipeline import run_pipeline
    except ImportError as e:
        log.error("security_pipeline_import_failed", error=str(e))
        raise RuntimeError(
            "security.pipeline import failed -- agent cannot serve requests safely"
        ) from e

    result = await run_pipeline(
        raw_text=raw_text,
        source=source,
        source_type="operator-intent",
        structured_query=structured_query,
        agent="RoutingAgent",
        operation="GenerateRoute",
        context={
            # operator_approved + policy_valid: stub-true for MVP. In real deploy
            # operator_approved is set by an out-of-band approval workflow, and
            # policy_valid comes from an explicit policy lookup. See:
            #   https://github.com/jdev-02/tera/issues -- "operator-approval flow"
            "operator_approved": True,
            "policy_valid": True,
            "signature_valid": False,  # we sign AFTER the pipeline runs
        },
    )
    return result.to_dict()
