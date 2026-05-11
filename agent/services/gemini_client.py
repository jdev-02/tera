"""Gemini service wrapper for v2 explanations.

The mission planner can run without this service. When keys are absent, it
returns deterministic text so demos remain offline-first and CI has no network
dependency.
"""

from __future__ import annotations

import os
from typing import Any


def gemini_configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))


def explain_decision(summary: dict[str, Any]) -> str:
    if not gemini_configured():
        return (
            "Offline explanation: TERA prioritized life-safety infrastructure, "
            "available shelter capacity, hazard avoidance, and vehicle/resource constraints."
        )
    return (
        "Gemini explanation placeholder: live Gemini can transform this structured "
        f"mission summary into an operator briefing. Sources: {sorted(summary.keys())}."
    )
