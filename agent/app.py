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
from typing import Any, Literal

import structlog
from fastapi import FastAPI, HTTPException

from agent.orchestrator import PlanBlockedError, approve_plan
from agent.orchestrator import plan as orchestrate_plan
from agent.schemas import (
    PlanApprovalRequest,
    PlanApprovalResponse,
    PlanBlocked,
    PlanRequest,
    PlanResponse,
)

log = structlog.get_logger(__name__)

PHASE = os.getenv("TERA_PHASE", "1")
PROFILE = os.getenv("TERA_DEVICE_PROFILE", "austere")

app = FastAPI(
    title="TERA Agent",
    version="0.1.0",
    description="Tactical Edge Route Agent. PRD: docs/PRD.md. By Team TruePoint.",
)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "phase": PHASE,
        "profile": PROFILE,
        "version": "0.1.0",
    }


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


@app.post("/plan/approve", response_model=PlanApprovalResponse)
async def plan_approve_endpoint(req: PlanApprovalRequest) -> PlanApprovalResponse:
    try:
        return approve_plan(req)
    except RuntimeError as e:
        log.exception("plan_approval_failed", error=str(e))
        raise HTTPException(status_code=503, detail=str(e)) from e
