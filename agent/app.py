"""TERA agent HTTP service.

POST /plan: operator natural-language route request -> validated, signed route.
GET  /health: liveness + which mode is the default.

The orchestrator (`agent.orchestrator.plan`) does the actual work; this
module is just the FastAPI wrapper.
"""

from __future__ import annotations

import os
from typing import Any

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
async def plan_endpoint(req: PlanRequest) -> PlanResponse:
    try:
        return await orchestrate_plan(req)
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
