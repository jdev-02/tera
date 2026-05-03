"""Append-only JSONL audit log for demo-time security proof.

The audit log is intentionally local and file-backed. It gives P2 a real
second-screen scroll of prompt, tool, policy, signing, and approval events
without shipping raw prompt text or secrets into a durable artifact.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_AUDIT_LOG = Path("logs/security_audit.jsonl")


def audit_log_path() -> Path:
    return Path(os.environ.get("WAYFINDER_AUDIT_LOG", str(DEFAULT_AUDIT_LOG)))


def prompt_digest(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def audit_event(event: str, **fields: Any) -> None:
    """Append one structured audit event.

    This function is fail-closed for security semantics but fail-open for
    application availability: audit write errors must not break /plan during
    the demo. Callers should still run tests against the happy path.
    """
    record = {
        "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "event": event,
        **fields,
    }
    path = audit_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True, separators=(",", ":"), default=str) + "\n")
    except (OSError, TypeError):
        return
