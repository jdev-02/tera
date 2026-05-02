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


class OperatorSignature(BaseModel):
    """Operator commit signature for ADR-003 two-signature approval."""

    scheme: str
    key_id: str
    value_b64: str
    signed_at: str
    approves_route_hash: str
    payload_hash: str
    # Canonical approval payload JSON (sort_keys, no spaces).
    # Required for self-contained verification in atak/bridge.py - same
    # pattern as <payload_json> in CoT XML (cot_signer.py).
    payload_json: str


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


class PlanApprovalRequest(BaseModel):
    """Stage-3 operator approval request from ADR-003."""

    route_id: str = Field(..., min_length=1)
    route: dict[str, Any]
    waypoints: list[Waypoint] = Field(default_factory=list)
    device_signature: Signature
    operator_key_id: str = Field(default="operator-demo-001", min_length=3)
    approved_by: str | None = None


class PlanApprovalResponse(BaseModel):
    """Returned from POST /plan/approve when the operator commits a route."""

    route_id: str
    approval_state: Literal["operator_committed"] = "operator_committed"
    route_hash: str
    device_signature: Signature
    operator_signature: OperatorSignature
