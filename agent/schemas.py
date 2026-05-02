"""Pydantic models shared across the agent.

Provider-agnostic shapes for LLM messages + tool calls + completions, plus
the public TERA HTTP contract (PlanRequest, PlanResponse).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# LLM provider-agnostic shapes
# ---------------------------------------------------------------------------


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_call_id: str | None = None
    name: str | None = None


class ToolDef(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema object for the tool's arguments.",
    )


class ToolCall(BaseModel):
    name: str
    args_json: str


class Completion(BaseModel):
    text: str | None = None
    tool_call: ToolCall | None = None
    finish_reason: Literal["stop", "length", "tool_call", "error"]
    model: str
    usage_prompt_tokens: int = 0
    usage_completion_tokens: int = 0


# ---------------------------------------------------------------------------
# TERA public HTTP contract -- POST /plan
# Co-owned with Ben (P4). Changes need both signoffs (PRD §13).
# ---------------------------------------------------------------------------


class Coord(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class PlanRequest(BaseModel):
    """The operator's natural-language request + their current position."""

    prompt: str = Field(..., min_length=1, max_length=2000)
    current: Coord
    request_id: str | None = None
    source: Literal["operator_voice", "operator_text", "test"] = "operator_text"


class Waypoint(BaseModel):
    lat: float
    lon: float
    label: str | None = None


class Signature(BaseModel):
    """ML-DSA signature wrapper. Source of truth: docs/contracts/cot_signed.md."""

    scheme: Literal["ML-DSA-65", "ML-DSA-44", "ML-DSA-87"]
    key_id: str
    value_b64: str
    signed_at: str


class PlanResponse(BaseModel):
    """Returned from POST /plan. The route + rationale + trust + signature."""

    request_id: str
    route: dict[str, Any]  # GeoJSON Feature with LineString geometry
    waypoints: list[Waypoint]
    rationale: str
    cost_breakdown: dict[str, float] = Field(default_factory=dict)
    trust: dict[str, Any] = Field(default_factory=dict)  # from security/route_trust_score
    signature: Signature | None = None


class PlanBlocked(BaseModel):
    """Returned with 403 when the security pipeline blocks the request."""

    request_id: str
    blocked_at: str
    reason: str
    stages: list[dict[str, Any]]
