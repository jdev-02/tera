"""Firebase status helpers for v2 offline-first shared state."""

from __future__ import annotations

import os

FIREBASE_ENV_VARS = (
    "FIREBASE_PROJECT_ID",
    "FIREBASE_API_KEY",
    "FIREBASE_AUTH_DOMAIN",
    "FIREBASE_DATABASE_URL",
)


def firebase_configured() -> bool:
    return any(os.getenv(name) for name in FIREBASE_ENV_VARS)


def firebase_status() -> dict[str, bool]:
    return {name: bool(os.getenv(name)) for name in FIREBASE_ENV_VARS}
