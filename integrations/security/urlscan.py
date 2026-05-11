"""urlscan.io adapter for explicitly requested crisis-link scans."""

from __future__ import annotations

import os
from typing import Any

from agent.trust_schemas import UrlScanResult
from integrations.common import http

URLSCAN_BASE = "https://urlscan.io/api/v1"


def submit_url_scan(url: str, visibility: str = "unlisted") -> dict[str, Any]:
    api_key = os.getenv("URLSCAN_API_KEY")
    if not api_key:
        return {"skipped": "missing_api_key", "url": url}
    raw = http.post_json(
        f"{URLSCAN_BASE}/scan/",
        json_body={"url": url, "visibility": visibility},
        headers={"API-Key": api_key, "Content-Type": "application/json"},
    )
    if not isinstance(raw, dict):
        raise http.ApiError("urlscan submit response was not an object")
    return raw


def get_scan_result(uuid: str) -> dict[str, Any]:
    api_key = os.getenv("URLSCAN_API_KEY")
    if not api_key:
        return {"skipped": "missing_api_key", "uuid": uuid}
    raw = http.get_json(f"{URLSCAN_BASE}/result/{uuid}/", headers={"API-Key": api_key})
    if not isinstance(raw, dict):
        raise http.ApiError("urlscan result response was not an object")
    return raw


def normalize_urlscan_result(raw: dict[str, Any]) -> UrlScanResult:
    task = raw.get("task", {}) if isinstance(raw.get("task"), dict) else {}
    page = raw.get("page", {}) if isinstance(raw.get("page"), dict) else {}
    verdicts = raw.get("verdicts", {}) if isinstance(raw.get("verdicts"), dict) else {}
    overall = verdicts.get("overall", {}) if isinstance(verdicts.get("overall"), dict) else {}
    lists = raw.get("lists", {}) if isinstance(raw.get("lists"), dict) else {}
    domains = lists.get("domains", []) if isinstance(lists.get("domains"), list) else []
    verdict = "unknown"
    if overall.get("malicious"):
        verdict = "malicious"
    elif overall.get("suspicious"):
        verdict = "suspicious"
    return UrlScanResult(
        url=str(page.get("url") or task.get("url") or raw.get("url") or ""),
        scan_id=_optional_str(task.get("uuid") or raw.get("uuid")),
        verdict=verdict,
        contacted_domains=[str(domain) for domain in domains],
        screenshot_url=_optional_str(task.get("screenshotURL")),
        raw=raw,
    )


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None
