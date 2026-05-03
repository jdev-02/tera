from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest

from llm_dev_kmh import app as kmh_app


class _FakeStreamContext:
    def __init__(self, response: object) -> None:
        self.response = response

    async def __aenter__(self) -> object:
        return self.response

    async def __aexit__(self, *_exc_info: object) -> None:
        return None


class _FakeAsyncClient:
    response: object

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        return None

    def stream(self, *_args: object, **_kwargs: Any) -> _FakeStreamContext:
        return _FakeStreamContext(self.response)


class _TokenResponse:
    status_code = 200

    async def aiter_lines(self) -> AsyncIterator[str]:
        yield json.dumps({"response": "Hello ", "done": False})
        yield json.dumps({"response": "operator.", "done": False})
        yield json.dumps({"done": True})


class _ErrorResponse:
    status_code = 404

    async def aread(self) -> bytes:
        return b'{"error":"model missing"}'


async def _collect_stream(response: object) -> str:
    body_iterator = response.body_iterator
    chunks: list[str] = []
    async for chunk in body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
    return "".join(chunks)


@pytest.mark.asyncio
async def test_prompt_stream_yields_sse_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeAsyncClient.response = _TokenResponse()
    monkeypatch.setattr(kmh_app.httpx, "AsyncClient", _FakeAsyncClient)

    response = await kmh_app.prompt_ollama_stream(
        kmh_app.PromptRequest(prompt="What can you do?", model="gemma4:e4b")
    )

    body = await _collect_stream(response)

    assert '"type": "start"' in body
    assert '"type": "status"' in body
    assert '"text": "Hello "' in body
    assert '"text": "operator."' in body
    assert '"type": "done"' in body


@pytest.mark.asyncio
async def test_prompt_stream_reports_ollama_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeAsyncClient.response = _ErrorResponse()
    monkeypatch.setattr(kmh_app.httpx, "AsyncClient", _FakeAsyncClient)

    response = await kmh_app.prompt_ollama_stream(
        kmh_app.PromptRequest(prompt="What can you do?", model="missing")
    )

    body = await _collect_stream(response)

    assert '"type": "error"' in body
    assert "model missing" in body


def test_imagery_sourcing_prompt_uses_socratic_dialogue() -> None:
    request = kmh_app.PromptRequest(
        prompt="Build a water access package for a foot patrol.",
        source_context=kmh_app.SourceContext(
            mission_focus="terrain-routing",
            clarifying_questions=[
                (
                    "Is the operator asking for mapped water features only, "
                    "or confidence in current and potable water availability?"
                )
            ],
        ),
    )

    system_prompt = kmh_app._build_system_prompt(request)

    assert "Socratic sourcing dialogue" in system_prompt
    assert "reflect the mission read" in system_prompt
    assert "Socratic questions to ask next" in system_prompt


def test_source_recommendation_questions_prioritize_source_scope() -> None:
    recommendation = kmh_app._infer_source_recommendation(
        "Build an offline package for a patrol to find reliable water while avoiding steep exposed terrain.",
        None,
    )
    questions = " ".join(recommendation.clarifying_questions).lower()

    assert "movement" in questions
    assert "water" in questions
    assert "bounding box" not in questions


def test_planner_workflow_hides_ao_until_sources_are_confirmed() -> None:
    html = kmh_app.INDEX_FILE.read_text(encoding="utf-8")
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert 'id="sourcePanel" class="sidebar-card source-panel-shell workflow-panel is-empty"' in html
    assert 'id="workflowCarousel" class="workflow-carousel hidden"' in html
    assert 'id="areaControlSurface" class="area-controls hidden"' in html
    assert 'id="drawAreaBtn"' in html
    assert 'id="confirmSourcesBtn"' in html

    assert 'els.workflowCarousel.classList.toggle("hidden", !hasMission)' in js
    assert 'els.areaControlSurface.classList.toggle("hidden", !state.sourceConfirmed)' in js
    assert "els.drawAreaBtn.disabled = !state.sourceConfirmed" in js
    assert "state.sourceConfirmed = true" in js


def test_planner_workflow_has_carousel_and_resizable_ao_handles() -> None:
    html = kmh_app.INDEX_FILE.read_text(encoding="utf-8")
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert 'id="workflowPrevBtn"' in html
    assert 'id="workflowNextBtn"' in html
    assert "setWorkflowStage(state.workflowStageIndex - 1)" in js
    assert "setWorkflowStage(state.workflowStageIndex + 1)" in js

    assert "areaHandleEntities" in js
    assert "getPickedAreaHandle" in js
    assert "getResizeAnchorPoint" in js
    assert "finishAreaResize" in js


def test_map_ui_does_not_expose_point_pin_overlay() -> None:
    html = kmh_app.INDEX_FILE.read_text(encoding="utf-8")
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")
    css = (kmh_app.STATIC_DIR / "styles.css").read_text(encoding="utf-8")
    app_source = Path(kmh_app.__file__).read_text(encoding="utf-8")

    removed_tokens = [
        "mapHint",
        "overlay-card",
        "bottom-right",
        "selectedPoint",
        "selected_point",
        "markerEntity",
        "setMarker",
        "Click the map to pin context",
        "Selected point",
        "ScreenSpaceEventType.LEFT_CLICK",
    ]
    combined = "\n".join([html, js, css, app_source])
    for token in removed_tokens:
        assert token not in combined


def test_source_planner_uses_defense_design_system() -> None:
    html = kmh_app.INDEX_FILE.read_text(encoding="utf-8")
    css = (kmh_app.STATIC_DIR / "styles.css").read_text(encoding="utf-8")
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")

    required_tokens = [
        "--color-bg-primary: #0D0D0D;",
        "--color-bg-secondary: #141414;",
        "--color-bg-tertiary: #1C1C1C;",
        "--color-border-active: #F5C518;",
        "--color-accent-gold: #F5C518;",
        '--font-display: "IBM Plex Mono", monospace;',
        '--font-ui: "IBM Plex Mono", monospace;',
        "--panel-width: 520px;",
        "grid-template-rows: 40px 1fr;",
    ]
    for token in required_tokens:
        assert token in css

    assert "panelWidth: 520" in js
    assert "window.innerWidth * 0.58" in js
    assert "860" in js
    assert "body.panel-collapsed .workspace-shell" in css
    assert "grid-template-columns: minmax(0, 1fr);" in css
    assert 'els.workspaceShell.style.removeProperty("--panel-width")' in js

    forbidden_tokens = [
        "IBM Plex Sans",
        "Bebas Neue",
        "Bebas+Neue",
        "linear-gradient",
        "box-shadow",
        'fromCssColorString("#',
        "border-radius: 6px",
        "border-radius: 8px",
        "border-radius: 999px",
    ]
    for token in forbidden_tokens:
        assert token not in css
        assert token not in html
        assert token not in js

    assert "IBM+Plex+Mono" in html
