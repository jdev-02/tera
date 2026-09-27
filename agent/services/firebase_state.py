"""Offline-first Firebase/local state facade."""

from __future__ import annotations

from typing import Any

from integrations.google.firebase import firebase_configured, firebase_status


class FirebaseState:
    """Small facade for demo shared state.

    The real Firebase SDK can replace this without changing mission planner
    call sites. Until then, local memory demonstrates the offline cache story.
    """

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def configured(self) -> bool:
        return firebase_configured()

    def status(self) -> dict[str, bool]:
        return firebase_status()

    def put(self, key: str, value: Any) -> None:
        self._store[key] = value

    def get(self, key: str) -> Any:
        return self._store.get(key)
