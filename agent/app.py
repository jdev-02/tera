"""Stub FastAPI app.

This is a placeholder skeleton committed at hackathon kickoff so that:
  - `make run` works from minute one.
  - AI agents have working code to reference when generating new endpoints.
  - The integrator can verify the full pull/push/ci/run loop before any real code lands.

Replace the hardcoded /plan response with the real orchestrator (see /.agents/21-agent.md).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import FastAPI
from pydantic import BaseModel, Field

log = structlog.get_logger(__name__)

PHASE = os.getenv("WAYFINDER_PHASE", "1")

app = FastAPI(
    title="Wayfinder Agent",
    version="0.0.1",
    description="Tactical edge route agent. PRD: /docs/PRD.md",
)


class Coord(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class PlanRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    current: Coord
    request_id: str | None = None


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "phase": PHASE, "version": "0.0.1"}


@app.post("/plan")
def plan(req: PlanRequest) -> dict[str, Any]:
    """STUB endpoint. Returns a hardcoded sample route.

    Replace with the real orchestrator. See /.agents/21-agent.md.
    """
    log.info(
        "plan_request_stub",
        request_id=req.request_id,
        prompt_len=len(req.prompt),
        phase=PHASE,
    )

    return {
        "request_id": req.request_id or "stub-" + datetime.now(UTC).isoformat(),
        "route": {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [req.current.lon, req.current.lat],
                    [req.current.lon + 0.001, req.current.lat + 0.001],
                ],
            },
            "properties": {"stub": True},
        },
        "waypoints": [
            {
                "lat": req.current.lat + 0.001,
                "lon": req.current.lon + 0.001,
                "label": "STUB-WAYPOINT",
            }
        ],
        "rationale": "STUB response. Replace with real orchestrator.",
        "cost_breakdown": {"distance_m": 150, "time_s": 120, "elevation_gain_m": 0},
        "signature": None,
    }
