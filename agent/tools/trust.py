"""TERA Trust Shield tools for disaster fraud and misinformation protection."""

from __future__ import annotations

import os
import re
from typing import Any

from agent.trust_schemas import RiskSignal, TrustAssessment
from integrations.security import url_risk

URL_PATTERN = re.compile(r"https?://[^\s)>\"]+", re.IGNORECASE)
TRUST_API_KEYS = ("GOOGLE_SAFE_BROWSING_API_KEY", "VT_API_KEY", "URLSCAN_API_KEY")


def trust_api_status() -> dict[str, bool]:
    return {name: bool(os.getenv(name)) for name in TRUST_API_KEYS}


def assess_url(
    url: str,
    context: str | None = None,
    *,
    use_live_providers: bool = True,
) -> TrustAssessment:
    return url_risk.assess_url_risk(url, context, use_live_providers=use_live_providers)


def assess_message_trust(
    message: str,
    source: str | None = None,
    *,
    use_live_providers: bool = True,
) -> TrustAssessment:
    signals: list[RiskSignal] = []
    checked_sources = ["message_heuristic"]
    skipped_sources: list[str] = []
    urls = _extract_urls(message)
    for url in urls:
        assessment = assess_url(url, message, use_live_providers=use_live_providers)
        signals.extend(assessment.signals)
        checked_sources.extend(assessment.checked_sources)
        skipped_sources.extend(assessment.skipped_sources)
    lower = message.lower()
    if source is None or source.lower() in {"unknown", "unknown_sms", "untrusted"}:
        signals.append(
            RiskSignal(
                source="message_heuristic",
                severity="medium",
                code="UNKNOWN_SOURCE",
                message="Message source is unknown or untrusted.",
            )
        )
    if any(word in lower for word in ("urgent", "login", "verify", "donate", "claim")):
        signals.append(
            RiskSignal(
                source="message_heuristic",
                severity="low",
                code="PRESSURE_LANGUAGE",
                message="Message uses urgency or credential/financial action language.",
            )
        )
    return url_risk.aggregate_security_results(
        input_type="message",
        value=message,
        signals=signals,
        checked_sources=checked_sources,
        skipped_sources=skipped_sources,
    )


def assess_supply_request_trust(request: dict[str, Any]) -> TrustAssessment:
    signals: list[RiskSignal] = []
    source = str(request.get("source") or "unknown")
    destination = str(request.get("destination") or "")
    verified_shelters = {
        str(item).lower() for item in request.get("verified_shelters", []) if item is not None
    }
    if source.lower() in {"unknown", "untrusted", "sms", "unknown_sms"}:
        signals.append(
            RiskSignal(
                source="supply_request_heuristic",
                severity="medium",
                code="UNKNOWN_REQUEST_SOURCE",
                message="Supply request source is not verified.",
            )
        )
    if destination and verified_shelters and destination.lower() not in verified_shelters:
        signals.append(
            RiskSignal(
                source="supply_request_heuristic",
                severity="high",
                code="UNVERIFIED_DESTINATION",
                message="Supply request destination is not in the verified shelter list.",
            )
        )
    elif destination.lower().startswith("unverified"):
        signals.append(
            RiskSignal(
                source="supply_request_heuristic",
                severity="high",
                code="UNVERIFIED_DESTINATION",
                message="Supply request names an unverified destination.",
            )
        )
    if str(request.get("urgency", "")).lower() == "critical":
        signals.append(
            RiskSignal(
                source="supply_request_heuristic",
                severity="low",
                code="CRITICAL_URGENCY_CLAIM",
                message="Critical urgency claim should be confirmed before dispatch.",
            )
        )
    if _large_medical_kit_request(request):
        signals.append(
            RiskSignal(
                source="supply_request_heuristic",
                severity="medium",
                code="UNUSUAL_SUPPLY_VOLUME",
                message="Requested supply quantity is unusually large for an unverified request.",
            )
        )
    return url_risk.aggregate_security_results(
        input_type="supply_request",
        value=str(request),
        signals=signals,
        checked_sources=["supply_request_heuristic"],
        skipped_sources=[],
    )


def verify_against_official_sources(
    message: str,
    official_context: dict[str, Any],
) -> TrustAssessment:
    signals: list[RiskSignal] = []
    official_terms = [str(item).lower() for item in official_context.get("verified_terms", [])]
    lower = message.lower()
    if official_terms and not any(term in lower for term in official_terms):
        signals.append(
            RiskSignal(
                source="official_source_match",
                severity="medium",
                code="NOT_FOUND_IN_OFFICIAL_CONTEXT",
                message="Message claim was not found in the provided official context.",
            )
        )
    return url_risk.aggregate_security_results(
        input_type="message",
        value=message,
        signals=signals,
        checked_sources=["official_source_match"],
        skipped_sources=[],
    )


def _extract_urls(message: str) -> list[str]:
    return [match.rstrip(".,;") for match in URL_PATTERN.findall(message)]


def _large_medical_kit_request(request: dict[str, Any]) -> bool:
    items = request.get("requested_items")
    if not isinstance(items, dict):
        return False
    for key, value in items.items():
        if "medical" in str(key).lower() and isinstance(value, int | float) and value >= 100:
            return True
    return False
