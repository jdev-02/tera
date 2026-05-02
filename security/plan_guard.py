"""
Security adapter for the future `/plan` orchestrator.

Jon owns the agent/orchestrator flow. P2 owns the trust boundary. This module
keeps that integration narrow: `/plan` can call one function before routing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from security.data_provenance import is_safe_to_forward, tag_input
from security.policy_gate import allow
from security.route_trust_score import atak_label, compute_route_trust
from security.structured_query_validator import validate_route_query
from security.superagent_integration import guard_input, redact_input


@dataclass(frozen=True)
class GuardStage:
    name: str
    passed: bool
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanGuardResult:
    allowed: bool
    blocked_at: str | None
    sanitized_text: str
    structured_query: dict[str, Any]
    stages: list[GuardStage]
    trust_result: dict[str, Any]
    atak_display: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "blocked_at": self.blocked_at,
            "sanitized_text": self.sanitized_text,
            "structured_query": self.structured_query,
            "stages": [
                {"name": stage.name, "passed": stage.passed, **stage.detail}
                for stage in self.stages
            ],
            "trust_result": self.trust_result,
            "atak_display": self.atak_display,
        }


def _first_failed_stage(stages: list[GuardStage]) -> str | None:
    for stage in stages:
        if not stage.passed:
            return stage.name
    return None


async def guard_plan_request(
    *,
    raw_text: str,
    structured_query: dict[str, Any],
    source: str = "operator",
    source_type: str = "operator-intent",
    target_agent: str = "RoutingAgent",
    operation: str = "ComputeRoute",
    force_local_guard: bool = False,
    operator_approved: bool = False,
    signature_valid: bool = False,
) -> PlanGuardResult:
    """
    Run a proposed `/plan` request through the P2 trust boundary.

    This function is intentionally pre-routing. It decides whether the route
    engine may compute a route. Rendering as a fully trusted ATAK route still
    requires later signing and verification.
    """
    stages: list[GuardStage] = []

    guard = await guard_input(raw_text, force_local=force_local_guard)
    stages.append(
        GuardStage(
            name="prompt_guard",
            passed=not guard.blocked,
            detail={
                "classification": guard.classification,
                "reasoning": guard.reasoning,
                "source": guard.source,
                "violation_types": guard.violation_types,
                "cwe_codes": guard.cwe_codes,
            },
        )
    )
    if guard.blocked:
        return _blocked_result(
            raw_text=raw_text,
            structured_query=structured_query,
            stages=stages,
            blocked_at="prompt_guard",
        )

    redacted = await redact_input(raw_text, force_local=force_local_guard)
    stages.append(
        GuardStage(
            name="redaction",
            passed=True,
            detail={"findings": redacted.findings, "source": redacted.source},
        )
    )

    tagged = tag_input(redacted.redacted, source=source, source_type=source_type)
    provenance = is_safe_to_forward(tagged, target_agent)
    stages.append(
        GuardStage(
            name="provenance",
            passed=provenance["safe"],
            detail={
                "source_type": tagged["source_type"],
                "authority_level": tagged["authority_level"],
                "trusted_as_instruction": tagged["trusted_as_instruction"],
                "reason": provenance["reason"],
            },
        )
    )

    schema = validate_route_query(structured_query)
    stages.append(
        GuardStage(
            name="schema_validation",
            passed=schema["valid"],
            detail={"errors": schema["errors"]},
        )
    )

    policy = allow(
        target_agent,
        operation,
        context={"schema_valid": schema["valid"]},
    )
    stages.append(
        GuardStage(
            name="policy_gate",
            passed=policy["allowed"],
            detail={"reason": policy["reason"]},
        )
    )

    blocked_at = _first_failed_stage(stages)
    trust_result = compute_route_trust(
        {
            "schema_valid": schema["valid"],
            "policy_valid": policy["allowed"],
            "operator_approved": operator_approved,
            "signature_valid": signature_valid,
            "untrusted_inputs_used": not provenance["safe"],
            "superagent_guard_passed": not guard.blocked,
        }
    )

    return PlanGuardResult(
        allowed=blocked_at is None,
        blocked_at=blocked_at,
        sanitized_text=redacted.redacted,
        structured_query=structured_query,
        stages=stages,
        trust_result=trust_result,
        atak_display=atak_label(trust_result),
    )


def _blocked_result(
    *,
    raw_text: str,
    structured_query: dict[str, Any],
    stages: list[GuardStage],
    blocked_at: str,
) -> PlanGuardResult:
    trust_result = compute_route_trust(
        {
            "schema_valid": False,
            "policy_valid": False,
            "operator_approved": False,
            "signature_valid": False,
            "untrusted_inputs_used": True,
            "superagent_guard_passed": False,
        }
    )
    return PlanGuardResult(
        allowed=False,
        blocked_at=blocked_at,
        sanitized_text=raw_text,
        structured_query=structured_query,
        stages=stages,
        trust_result=trust_result,
        atak_display="BLOCKED - Prompt Injection Detected",
    )
