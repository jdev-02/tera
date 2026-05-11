"""Local Gemma/Ollama fallback status helpers."""

from __future__ import annotations

import os


def gemma_configured() -> bool:
    return bool(os.getenv("OLLAMA_HOST") or os.getenv("TERA_LOCAL_MODEL"))


def fallback_model_name() -> str:
    return os.getenv("TERA_LOCAL_MODEL", os.getenv("OLLAMA_MODEL", "gemma3:latest"))
