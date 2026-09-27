"""HTTP helpers for thin API adapters.

All network calls live in integrations, not in the legacy Phase 3 agent path.
Adapters use explicit timeouts and raise ApiError with source context.
"""

from __future__ import annotations

from typing import Any

import httpx

DEFAULT_TIMEOUT_S = 10.0
USER_AGENT = "tera-emergency-coordinator/0.2"


class ApiError(RuntimeError):
    """Raised when an external API call fails or is unavailable."""


def _headers(headers: dict[str, str] | None = None) -> dict[str, str]:
    merged = {"User-Agent": USER_AGENT}
    if headers:
        merged.update(headers)
    return merged


def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_S,
) -> Any:
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers=_headers(headers),
        ) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise ApiError(f"GET {url} failed: {exc}") from exc
    except ValueError as exc:
        raise ApiError(f"GET {url} returned non-JSON response") from exc


def post_json(
    url: str,
    *,
    json_body: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_S,
) -> Any:
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers=_headers(headers),
        ) as client:
            response = client.post(url, json=json_body)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise ApiError(f"POST {url} failed: {exc}") from exc
    except ValueError as exc:
        raise ApiError(f"POST {url} returned non-JSON response") from exc


def get_text(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_S,
) -> str:
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers=_headers(headers),
        ) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.text
    except httpx.HTTPError as exc:
        raise ApiError(f"GET {url} failed: {exc}") from exc


def require_env(name: str, value: str | None) -> str:
    if not value:
        raise ApiError(f"Missing required environment variable: {name}")
    return value
