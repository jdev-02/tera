"""Public RDAP domain metadata adapter."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from agent.trust_schemas import DomainMetadata
from integrations.common import http

RDAP_BASE = "https://rdap.org/domain"


def extract_domain(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = parsed.hostname or ""
    return host.lower().rstrip(".")


def get_rdap_domain(domain: str) -> dict[str, Any]:
    raw = http.get_json(f"{RDAP_BASE}/{domain}")
    if not isinstance(raw, dict):
        raise http.ApiError("RDAP response was not an object")
    return raw


def normalize_rdap_domain(raw: dict[str, Any]) -> DomainMetadata:
    events = raw.get("events", []) if isinstance(raw.get("events"), list) else []
    return DomainMetadata(
        domain=str(raw.get("ldhName") or raw.get("handle") or ""),
        registrar=_registrar(raw),
        created_at=_event_date(events, "registration"),
        updated_at=_event_date(events, "last changed"),
        expires_at=_event_date(events, "expiration"),
        raw=raw,
    )


def _registrar(raw: dict[str, Any]) -> str | None:
    entities = raw.get("entities", [])
    if not isinstance(entities, list):
        return None
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        roles = entity.get("roles", [])
        if isinstance(roles, list) and "registrar" in roles:
            vcard = entity.get("vcardArray", [])
            if isinstance(vcard, list) and len(vcard) > 1 and isinstance(vcard[1], list):
                for row in vcard[1]:
                    if isinstance(row, list) and row and row[0] == "fn" and len(row) > 3:
                        return str(row[3])
    return None


def _event_date(events: list[Any], action: str) -> str | None:
    for event in events:
        if isinstance(event, dict) and event.get("eventAction") == action:
            date = event.get("eventDate")
            return str(date) if date is not None else None
    return None
