"""Google Safe Browsing adapter for crisis-related URL checks."""

from __future__ import annotations

import os
from typing import Any

from agent.trust_schemas import UrlThreatResult
from integrations.common import http

SAFE_BROWSING_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
THREAT_TYPES = [
    "MALWARE",
    "SOCIAL_ENGINEERING",
    "UNWANTED_SOFTWARE",
    "POTENTIALLY_HARMFUL_APPLICATION",
]


def build_safe_browsing_request(urls: list[str]) -> dict[str, Any]:
    return {
        "client": {"clientId": "tera", "clientVersion": "0.2"},
        "threatInfo": {
            "threatTypes": THREAT_TYPES,
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url} for url in urls],
        },
    }


def check_url_threats(urls: list[str]) -> list[UrlThreatResult]:
    api_key = os.getenv("GOOGLE_SAFE_BROWSING_API_KEY")
    if not api_key:
        return [
            UrlThreatResult(
                url=url,
                checked=False,
                provider="google_safe_browsing",
                matched=False,
                raw={"skipped": "missing_api_key"},
            )
            for url in urls
        ]
    raw = http.post_json(
        f"{SAFE_BROWSING_URL}?key={api_key}",
        json_body=build_safe_browsing_request(urls),
        headers={"Content-Type": "application/json"},
    )
    if not isinstance(raw, dict):
        raise http.ApiError("Safe Browsing response was not an object")
    return normalize_safe_browsing_response(raw, urls)


def normalize_safe_browsing_response(
    raw: dict[str, Any],
    urls: list[str],
) -> list[UrlThreatResult]:
    matches_by_url: dict[str, list[str]] = {url: [] for url in urls}
    for match in raw.get("matches", []):
        if not isinstance(match, dict):
            continue
        threat = match.get("threat", {})
        if not isinstance(threat, dict):
            continue
        url = threat.get("url")
        if not isinstance(url, str):
            continue
        matches_by_url.setdefault(url, []).append(str(match.get("threatType") or "UNKNOWN"))
    return [
        UrlThreatResult(
            url=url,
            checked=True,
            provider="google_safe_browsing",
            matched=bool(threat_types),
            threat_types=threat_types,
            raw=raw if threat_types else None,
        )
        for url, threat_types in matches_by_url.items()
    ]
