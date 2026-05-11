"""Misinformation and unverified-claim checks for disaster operations."""

from __future__ import annotations

from typing import Any

from agent.trust_schemas import RiskSignal, TrustAssessment
from integrations.security.url_risk import aggregate_security_results


def detect_unverified_shelter_claim(
    message: str,
    verified_shelters: list[Any],
) -> TrustAssessment:
    names = {_name(item).lower() for item in verified_shelters if _name(item)}
    lower = message.lower()
    signals: list[RiskSignal] = []
    if "shelter" in lower and names and not any(name in lower for name in names):
        signals.append(
            RiskSignal(
                source="misinformation",
                severity="medium",
                code="UNVERIFIED_SHELTER_CLAIM",
                message="Shelter claim is not found in the verified shelter list.",
            )
        )
    return aggregate_security_results(
        input_type="message",
        value=message,
        signals=signals,
        checked_sources=["verified_shelter_list"],
        skipped_sources=[],
    )


def detect_unverified_evacuation_instruction(
    message: str,
    active_alerts: list[Any],
) -> TrustAssessment:
    lower = message.lower()
    signals: list[RiskSignal] = []
    has_evacuation_claim = any(word in lower for word in ("evacuate", "evacuation", "leave now"))
    if has_evacuation_claim and not active_alerts:
        signals.append(
            RiskSignal(
                source="misinformation",
                severity="high",
                code="UNVERIFIED_EVACUATION_INSTRUCTION",
                message="Evacuation instruction has no matching active official alert in context.",
            )
        )
    return aggregate_security_results(
        input_type="message",
        value=message,
        signals=signals,
        checked_sources=["active_alerts"],
        skipped_sources=[],
    )


def flag_conflicting_field_report(
    report: dict[str, Any],
    current_state: dict[str, Any],
) -> TrustAssessment:
    signals: list[RiskSignal] = []
    report_status = report.get("status")
    state_status = current_state.get(str(report.get("asset_id")))
    if state_status is not None and report_status is not None and report_status != state_status:
        signals.append(
            RiskSignal(
                source="misinformation",
                severity="medium",
                code="CONFLICTING_FIELD_REPORT",
                message="Field report conflicts with the current verified state.",
            )
        )
    return aggregate_security_results(
        input_type="field_report",
        value=str(report),
        signals=signals,
        checked_sources=["current_state"],
        skipped_sources=[],
    )


def _name(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("name") or "")
    return str(getattr(item, "name", "") or "")
