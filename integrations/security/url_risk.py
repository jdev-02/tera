"""URL risk aggregation for TERA Trust Shield."""

from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlparse

from agent.trust_schemas import RiskSignal, TrustAssessment, UrlThreatResult
from integrations.security import rdap, safe_browsing, virustotal

OFFICIAL_ALLOWLIST = {
    "fema.gov",
    "redcross.org",
    "ready.gov",
    "weather.gov",
    "noaa.gov",
    "cdc.gov",
    "usa.gov",
    "ca.gov",
    "sf.gov",
    "511.org",
    "airnow.gov",
}
SHORTENERS = {
    "bit.ly",
    "bitly.com",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "rebrand.ly",
    "cutt.ly",
}
SUSPICIOUS_TLDS = {"zip", "mov", "top", "xyz", "click", "quest", "country", "support"}
SUSPICIOUS_KEYWORDS = {
    "donate",
    "aid",
    "claim",
    "login",
    "verify",
    "urgent",
    "relief",
    "wallet",
    "crypto",
}
OFFICIAL_BRAND_TERMS = {"fema", "redcross", "ready", "noaa", "cdc", "airnow"}


def assess_url_risk(
    url: str,
    context: str | None = None,
    *,
    use_live_providers: bool = True,
) -> TrustAssessment:
    signals = score_url_heuristics(url)
    checked_sources = ["heuristic"]
    skipped_sources: list[str] = []

    if use_live_providers:
        safe_results = safe_browsing.check_url_threats([url])
        _merge_safe_browsing(signals, safe_results, checked_sources, skipped_sources)
        _merge_virustotal(url, signals, checked_sources, skipped_sources)
        _merge_rdap(url, checked_sources, skipped_sources)
    else:
        skipped_sources.extend(
            ["safe_browsing_offline_mode", "virustotal_offline_mode", "rdap_offline_mode"]
        )

    if context and any(word in context.lower() for word in ("donation", "aid", "claim", "login")):
        signals.append(
            RiskSignal(
                source="context",
                severity="low",
                code="CRISIS_FINANCIAL_CONTEXT",
                message="Crisis-related financial or login context increases review priority.",
            )
        )

    return aggregate_security_results(
        input_type="url",
        value=url,
        signals=signals,
        checked_sources=checked_sources,
        skipped_sources=skipped_sources,
    )


def score_url_heuristics(url: str) -> list[RiskSignal]:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").lower()
    signals: list[RiskSignal] = []
    official_domains = _official_domains()

    if parsed.scheme != "https":
        signals.append(
            RiskSignal(
                source="heuristic",
                severity="medium",
                code="NON_HTTPS",
                message="URL does not use HTTPS.",
            )
        )
    if parsed.username or parsed.password:
        signals.append(
            RiskSignal(
                source="heuristic",
                severity="high",
                code="EMBEDDED_CREDENTIALS",
                message="URL contains embedded credentials.",
            )
        )
    if _is_ip_literal(host):
        signals.append(
            RiskSignal(
                source="heuristic",
                severity="high",
                code="IP_LITERAL",
                message="URL uses an IP address instead of a domain name.",
            )
        )
    if "xn--" in host:
        signals.append(
            RiskSignal(
                source="heuristic",
                severity="medium",
                code="PUNYCODE_DOMAIN",
                message="Domain contains punycode, which can indicate homograph risk.",
            )
        )
    if host in SHORTENERS:
        signals.append(
            RiskSignal(
                source="heuristic",
                severity="medium",
                code="URL_SHORTENER",
                message="URL uses a shortener that hides the final destination.",
            )
        )
    labels = host.split(".") if host else []
    if len(labels) > 4:
        signals.append(
            RiskSignal(
                source="heuristic",
                severity="low",
                code="EXCESSIVE_SUBDOMAINS",
                message="Domain has many subdomains, which can obscure the registered domain.",
            )
        )
    tld = labels[-1] if labels else ""
    if tld in SUSPICIOUS_TLDS:
        signals.append(
            RiskSignal(
                source="heuristic",
                severity="medium",
                code="SUSPICIOUS_TLD",
                message="Domain uses a TLD commonly seen in abuse or impersonation campaigns.",
            )
        )
    url_text = url.lower()
    keyword_hits = sorted(keyword for keyword in SUSPICIOUS_KEYWORDS if keyword in url_text)
    if keyword_hits:
        signals.append(
            RiskSignal(
                source="heuristic",
                severity="low",
                code="CRISIS_KEYWORDS",
                message=f"URL contains crisis/fraud-sensitive keywords: {', '.join(keyword_hits)}.",
            )
        )
    if _resembles_official_but_not_allowed(host, official_domains):
        signals.append(
            RiskSignal(
                source="heuristic",
                severity="high",
                code="GOV_IMPERSONATION",
                message=(
                    "Domain appears to imitate an official emergency service but is not in "
                    "the configured official-source allowlist."
                ),
            )
        )
    return signals


def aggregate_security_results(
    *,
    input_type: str,
    value: str,
    signals: list[RiskSignal],
    checked_sources: list[str],
    skipped_sources: list[str],
) -> TrustAssessment:
    score = min(sum(_severity_score(signal.severity) for signal in signals), 100)
    level = "low"
    if score >= 80:
        level = "critical"
    elif score >= 55:
        level = "high"
    elif score >= 25:
        level = "medium"
    requires_approval = score >= 25
    recommendation = _recommendation(level)
    return TrustAssessment(
        input_type=input_type,  # type: ignore[arg-type]
        value=value,
        risk_score=score,
        risk_level=level,  # type: ignore[arg-type]
        signals=signals,
        recommendation=recommendation,
        checked_sources=sorted(set(checked_sources)),
        skipped_sources=sorted(set(skipped_sources)),
        requires_human_approval=requires_approval,
    )


def _merge_safe_browsing(
    signals: list[RiskSignal],
    results: list[UrlThreatResult],
    checked_sources: list[str],
    skipped_sources: list[str],
) -> None:
    for result in results:
        if not result.checked:
            skipped_sources.append("safe_browsing_missing_key")
            continue
        checked_sources.append("safe_browsing")
        if result.matched:
            for threat_type in result.threat_types:
                signals.append(
                    RiskSignal(
                        source="safe_browsing",
                        severity="critical",
                        code=threat_type,
                        message=f"URL matched a Safe Browsing {threat_type} threat list.",
                    )
                )


def _merge_virustotal(
    url: str,
    signals: list[RiskSignal],
    checked_sources: list[str],
    skipped_sources: list[str],
) -> None:
    if not os.getenv("VT_API_KEY"):
        skipped_sources.append("virustotal_missing_key")
        return
    report = virustotal.normalize_vt_url_report(virustotal.get_url_report(url))
    checked_sources.append("virustotal")
    if (report.malicious or 0) > 0:
        signals.append(
            RiskSignal(
                source="virustotal",
                severity="critical",
                code="VT_MALICIOUS",
                message=f"VirusTotal reports {report.malicious} malicious detections.",
            )
        )
    elif (report.suspicious or 0) > 0:
        signals.append(
            RiskSignal(
                source="virustotal",
                severity="high",
                code="VT_SUSPICIOUS",
                message=f"VirusTotal reports {report.suspicious} suspicious detections.",
            )
        )


def _merge_rdap(url: str, checked_sources: list[str], skipped_sources: list[str]) -> None:
    domain = rdap.extract_domain(url)
    if not domain:
        skipped_sources.append("rdap_no_domain")
        return
    try:
        rdap.normalize_rdap_domain(rdap.get_rdap_domain(domain))
    except Exception:  # noqa: BLE001 -- RDAP varies by registry; treat as unknown
        skipped_sources.append("rdap_unavailable")
        return
    checked_sources.append("rdap")


def _official_domains() -> set[str]:
    configured = os.getenv("TERA_TRUST_OFFICIAL_DOMAINS")
    if not configured:
        return OFFICIAL_ALLOWLIST
    return {domain.strip().lower() for domain in configured.split(",") if domain.strip()}


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _resembles_official_but_not_allowed(host: str, official_domains: set[str]) -> bool:
    allowed = any(host == domain or host.endswith(f".{domain}") for domain in official_domains)
    if not host or allowed:
        return False
    return any(term in host.replace("-", "") for term in OFFICIAL_BRAND_TERMS)


def _severity_score(severity: str) -> int:
    return {"info": 0, "low": 10, "medium": 25, "high": 45, "critical": 80}.get(severity, 0)


def _recommendation(level: str) -> str:
    if level in {"critical", "high"}:
        return (
            "Do not use this information for automatic dispatch. Escalate to the "
            "incident commander and verify through official sources."
        )
    if level == "medium":
        return "Treat as unverified. Require human approval before it changes mission planning."
    return "No high-risk signal found in available checks; continue normal verification workflow."
