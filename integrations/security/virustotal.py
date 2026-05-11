"""VirusTotal v3 URL/domain reputation adapter."""

from __future__ import annotations

import base64
import os
from typing import Any, cast

import httpx

from agent.trust_schemas import DomainReputationResult, UrlReputationResult
from integrations.common import http

VT_BASE = "https://www.virustotal.com/api/v3"


def get_url_report(url: str) -> dict[str, Any]:
    api_key = os.getenv("VT_API_KEY")
    if not api_key:
        return {"skipped": "missing_api_key", "url": url}
    raw = http.get_json(f"{VT_BASE}/urls/{_url_id(url)}", headers={"x-apikey": api_key})
    if not isinstance(raw, dict):
        raise http.ApiError("VirusTotal URL report response was not an object")
    return raw


def submit_url_for_analysis(url: str) -> dict[str, Any]:
    api_key = os.getenv("VT_API_KEY")
    if not api_key:
        return {"skipped": "missing_api_key", "url": url}
    try:
        with httpx.Client(timeout=http.DEFAULT_TIMEOUT_S, follow_redirects=True) as client:
            response = client.post(
                f"{VT_BASE}/urls",
                headers={"x-apikey": api_key},
                data={"url": url},
            )
            response.raise_for_status()
            raw = response.json()
    except httpx.HTTPError as exc:
        raise http.ApiError(f"VirusTotal URL submit failed: {exc}") from exc
    if not isinstance(raw, dict):
        raise http.ApiError("VirusTotal URL submit response was not an object")
    return raw


def get_domain_report(domain: str) -> dict[str, Any]:
    api_key = os.getenv("VT_API_KEY")
    if not api_key:
        return {"skipped": "missing_api_key", "domain": domain}
    raw = http.get_json(f"{VT_BASE}/domains/{domain}", headers={"x-apikey": api_key})
    if not isinstance(raw, dict):
        raise http.ApiError("VirusTotal domain report response was not an object")
    return raw


def normalize_vt_url_report(raw: dict[str, Any]) -> UrlReputationResult:
    attrs = _attrs(raw)
    stats = attrs.get("last_analysis_stats", {}) if isinstance(attrs, dict) else {}
    return UrlReputationResult(
        url=str(raw.get("url") or raw.get("data", {}).get("id") or ""),
        provider="virustotal",
        malicious=_int_or_none(stats.get("malicious")) if isinstance(stats, dict) else None,
        suspicious=_int_or_none(stats.get("suspicious")) if isinstance(stats, dict) else None,
        harmless=_int_or_none(stats.get("harmless")) if isinstance(stats, dict) else None,
        undetected=_int_or_none(stats.get("undetected")) if isinstance(stats, dict) else None,
        raw=raw,
    )


def normalize_vt_domain_report(raw: dict[str, Any]) -> DomainReputationResult:
    attrs = _attrs(raw)
    domain = raw.get("domain") or raw.get("data", {}).get("id") or ""
    return DomainReputationResult(
        domain=str(domain),
        provider="virustotal",
        reputation=_int_or_none(attrs.get("reputation")) if isinstance(attrs, dict) else None,
        categories=attrs.get("categories") if isinstance(attrs.get("categories"), dict) else None,
        raw=raw,
    )


def _url_id(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii").rstrip("=")


def _attrs(raw: dict[str, Any]) -> dict[str, Any]:
    data = raw.get("data")
    if isinstance(data, dict):
        attrs = data.get("attributes")
        if isinstance(attrs, dict):
            return cast(dict[str, Any], attrs)
    return {}


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None
