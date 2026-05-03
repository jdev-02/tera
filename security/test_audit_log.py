from __future__ import annotations

import json
import shutil
import subprocess

from security.audit_log import audit_event, prompt_digest


def test_audit_event_writes_jsonl(tmp_path, monkeypatch) -> None:
    audit_path = tmp_path / "security_audit.jsonl"
    monkeypatch.setenv("WAYFINDER_AUDIT_LOG", str(audit_path))

    audit_event(
        "prompt_received",
        request_id="req-1",
        prompt_sha256=prompt_digest("route to freshwater"),
        prompt_len=len("route to freshwater"),
    )

    record = json.loads(audit_path.read_text(encoding="utf-8"))
    assert record["event"] == "prompt_received"
    assert record["request_id"] == "req-1"
    assert record["prompt_len"] == 19
    assert record["prompt_sha256"] == prompt_digest("route to freshwater")
    assert "route to freshwater" not in audit_path.read_text(encoding="utf-8")


def test_demo_shell_scripts_parse() -> None:
    bash = shutil.which("bash")
    if bash is None:
        return

    for script in (
        "infra/tcpdump_demo.sh",
        "infra/audit_log_scroll.sh",
        "infra/security_demo_monitors.sh",
    ):
        subprocess.run([bash, "-n", script], check=True)  # noqa: S603
