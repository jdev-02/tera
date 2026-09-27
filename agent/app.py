"""TERA Jetson-side HTTP service.

POST /plan: ATAK plugin text/STT request -> validated route intent -> signed response.
GET  /health: liveness + which mode is the default.

The orchestrator (`agent.orchestrator.plan`) does the actual work; this
module is just the FastAPI wrapper. The deployed path is:

ATAK plugin on the TAK device -> local IP -> Jetson TERA app -> local Gemma
intent translation + geo tools -> route/control measures/chat response/signed
CoT -> local IP -> ATAK plugin render.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal

import structlog
from fastapi import FastAPI, HTTPException

from agent.mission_orchestrator import (
    demo_bay_area_wildfire,
    mission_api_status,
    mission_health,
    plan_mission,
)
from agent.mission_schemas import MissionPlanRequest, MissionPlanResponse
from agent.orchestrator import PlanBlockedError, approve_plan, verify_plan_response
from agent.orchestrator import plan as orchestrate_plan
from agent.schemas import (
    PlanApprovalRequest,
    PlanApprovalResponse,
    PlanBlocked,
    PlanRequest,
    PlanResponse,
    PlanVerifyResponse,
)
from agent.tools.trust import (
    assess_message_trust,
    assess_supply_request_trust,
    assess_url,
    trust_api_status,
)
from agent.trust_schemas import (
    MessageTrustRequest,
    SupplyRequestTrustRequest,
    TrustAssessment,
    UrlCheckRequest,
)

log = structlog.get_logger(__name__)

PHASE = os.getenv("TERA_PHASE", "1")
PROFILE = os.getenv("TERA_DEVICE_PROFILE", "austere")


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hook.

    On startup, ensure this device's public key is in the trust list. PRD
    line 293-294 mandates verify-on-ingest against a trust list. Without a
    bootstrap, a fresh Jetson (`make jetson-compose-refresh`) would sign
    valid routes whose own key_id is not in the trust list -> /plan/verify
    rejects -> plugin refuses to render. The orchestrator also bootstraps on
    first sign as belt-and-suspenders, but doing it here as well guarantees
    the file exists before any verify call can land.
    """
    try:
        from agent.orchestrator import _bootstrap_device_trust
        from crypto.ml_dsa_signer import create_signer

        signer = create_signer()
        _bootstrap_device_trust(signer.key_id)
        log.info("trust_list_bootstrapped", key_id=signer.key_id)
    except Exception as e:  # noqa: BLE001 -- degrade gracefully
        log.warning("trust_list_bootstrap_skipped", error=str(e))
    yield


app = FastAPI(
    title="TERA Agent",
    version="0.1.0",
    description=(
        "TERA emergency logistics coordinator with legacy tactical route mode. "
        "PRD: docs/PRD.md. By Team TruePoint."
    ),
    lifespan=_lifespan,
)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "phase": PHASE,
        "profile": PROFILE,
        "version": "0.1.0",
    }


@app.get("/mission/health")
def mission_health_endpoint() -> dict[str, Any]:
    return mission_health()


@app.post("/plan", response_model=PlanResponse, responses={403: {"model": PlanBlocked}})
async def plan_endpoint(
    req: PlanRequest,
    tts: bool = False,
    profile: Literal["calm", "comms", "critical"] | None = None,
) -> PlanResponse:
    """POST /plan with optional TTS.

    Query / body params:
        ?tts=true            -- synthesize the rationale via Piper, return
                                base64 WAV in `audio_b64`.
        ?profile=<mode>      -- pin the voice profile for this request:
                                'calm' (briefer voice, no FX), 'comms'
                                (default ops cadence + radio FX), 'critical'
                                (degraded radio FX for urgent contexts).
                                Equivalent to setting `voice_profile` in
                                the request body. The query-param form is
                                here for curl ergonomics. If both forms are
                                set, the body wins (explicit > implicit).
                                None = read TERA_VOICE_PROFILE env var or
                                fall back to 'comms'.

    Defaults preserve old behavior: ?tts=false means audio_b64 is null.
    The hero demo (PRD §6) sets `?tts=true`. Severity cues in the
    rationale auto-elevate the chosen mode upward but never demote.
    """
    if profile is not None and req.voice_profile is None:
        # Promote query-param profile into the request body so the
        # orchestrator sees a single source of truth. If req.voice_profile
        # is already set in the body, keep that.
        req = req.model_copy(update={"voice_profile": profile})
    try:
        return await orchestrate_plan(req, with_tts=tts)
    except PlanBlockedError as e:
        # 403 with structured detail so operator UI can show *which* stage
        # blocked and why -- transparency over opacity.
        raise HTTPException(
            status_code=403,
            detail=PlanBlocked(
                request_id=req.request_id or "",
                blocked_at=e.blocked_at,
                reason=e.reason,
                stages=e.stages,
            ).model_dump(),
        ) from e
    except PermissionError as e:
        # Profile rejected the requested mode (e.g. austere + frontier).
        raise HTTPException(status_code=403, detail=str(e)) from e
    except RuntimeError as e:
        # LLM provider failed, security module failed to import, etc.
        log.exception("plan_failed", error=str(e))
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.post("/mission/plan", response_model=MissionPlanResponse)
async def mission_plan_endpoint(req: MissionPlanRequest) -> MissionPlanResponse:
    try:
        return plan_mission(req)
    except RuntimeError as e:
        log.exception("mission_plan_failed", error=str(e))
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.get("/mission/api-status")
def mission_api_status_endpoint() -> dict[str, bool]:
    return mission_api_status()


@app.get("/mission/demo/bay-area-wildfire", response_model=MissionPlanResponse)
def mission_demo_bay_area_wildfire_endpoint() -> MissionPlanResponse:
    return demo_bay_area_wildfire()


@app.post("/trust/check-url", response_model=TrustAssessment)
async def trust_check_url_endpoint(req: UrlCheckRequest) -> TrustAssessment:
    return assess_url(req.url, req.context)


@app.post("/trust/check-message", response_model=TrustAssessment)
async def trust_check_message_endpoint(req: MessageTrustRequest) -> TrustAssessment:
    return assess_message_trust(req.message, req.source)


@app.post("/trust/check-supply-request", response_model=TrustAssessment)
async def trust_check_supply_request_endpoint(
    req: SupplyRequestTrustRequest,
) -> TrustAssessment:
    return assess_supply_request_trust(req.request)


@app.get("/trust/api-status")
def trust_api_status_endpoint() -> dict[str, bool]:
    return trust_api_status()


@app.post("/plan/approve", response_model=PlanApprovalResponse)
async def plan_approve_endpoint(req: PlanApprovalRequest) -> PlanApprovalResponse:
    try:
        return approve_plan(req)
    except RuntimeError as e:
        log.exception("plan_approval_failed", error=str(e))
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.post("/plan/verify", response_model=PlanVerifyResponse)
async def plan_verify_endpoint(resp: PlanResponse) -> PlanVerifyResponse:
    """Verify a signed /plan response before ATAK renders it."""
    result = verify_plan_response(resp)
    if not result.valid:
        log.warning("plan_verify_rejected", reason=result.reason, key_id=result.key_id)
    return result
