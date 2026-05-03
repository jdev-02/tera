from __future__ import annotations

from pathlib import Path

from ontology.loader import build_system_prompt

PROMPT_DIR = Path("prompts/local_model_prompts")


def test_tera_prompts_include_tak_output_context() -> None:
    full_prompt = (PROMPT_DIR / "tera_full_system_prompt.md").read_text(encoding="utf-8")
    local_prompt = (PROMPT_DIR / "tera_local_model_system_prompt.md").read_text(encoding="utf-8")
    sourcing_prompt = (PROMPT_DIR / "imagery_sourcing_local_model_system_prompt.md").read_text(
        encoding="utf-8"
    )

    assert "## TAK Output Intent" in full_prompt
    assert "signed TAK CoT" in full_prompt
    assert "route.properties" in full_prompt
    assert "bridge-local adapter" in full_prompt
    assert "Emergency alert CoT is only appropriate" in full_prompt

    # Kyle's #73 rewrote the local prompt away from the RFSim-era action vocab
    # (draw-shape polyline / TAK OUTPUT CONTEXT) toward an ATAK-plugin
    # deployment narrative + JSON action contract. We now assert on the
    # semantic anchors that survived the rewrite (anti-fabrication guardrail,
    # ATAK-pipeline awareness, and identity hardening) instead of the old
    # literal phrases, which the production translator never depended on.
    assert "ATAK plugin" in local_prompt
    assert "Do not invent final route geometry" in local_prompt
    assert "TERA, the Tactical Edge Route Agent" in local_prompt

    assert "Downstream TAK output target:" in sourcing_prompt
    assert "primary/alternate routes" in sourcing_prompt
    assert (
        "Do not source data merely because it could make the TAK display prettier"
        in sourcing_prompt
    )


def test_route_translator_preserves_schema_only_tak_context() -> None:
    system_prompt = build_system_prompt()

    assert "Downstream TAK intent" in system_prompt
    assert "Do not add display-only fields" in system_prompt
    assert "TAK bridge" in system_prompt
