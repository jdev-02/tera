from __future__ import annotations

import base64
import json
import os
import zipfile
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
import pytest

from llm_dev_kmh import app as kmh_app
from llm_dev_kmh import geo_algorithms


class _FakeStreamContext:
    def __init__(self, response: object) -> None:
        self.response = response

    async def __aenter__(self) -> object:
        return self.response

    async def __aexit__(self, *_exc_info: object) -> None:
        return None


class _FakeAsyncClient:
    response: object
    models_response: object | None = None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        return None

    def stream(self, *_args: object, **_kwargs: Any) -> _FakeStreamContext:
        return _FakeStreamContext(self.response)

    async def get(self, *_args: object, **_kwargs: Any) -> object:
        return self.models_response or _ModelsResponse()

    async def post(self, *_args: object, **_kwargs: Any) -> object:
        return self.response


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


class _ClaudeResponse:
    status_code = 200
    text = '{"content":[{"type":"text","text":"Claude source recommendation."}]}'

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {"content": [{"type": "text", "text": "Claude source recommendation."}]}


class _ModelsResponse:
    status_code = 200
    text = '{"data":[{"id":"claude-sonnet-4-6","type":"model"}]}'

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {
            "data": [
                {
                    "id": "claude-sonnet-4-6",
                    "type": "model",
                }
            ]
        }


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
        kmh_app.PromptRequest(
            prompt="What can you do?",
            model="gemma4:e4b",
            llm_provider="ollama",
        )
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
        kmh_app.PromptRequest(
            prompt="What can you do?",
            model="missing",
            llm_provider="ollama",
        )
    )

    body = await _collect_stream(response)

    assert '"type": "error"' in body
    assert "model missing" in body


@pytest.mark.asyncio
async def test_prompt_stream_can_use_claude_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeAsyncClient.response = _ClaudeResponse()
    monkeypatch.setattr(kmh_app.httpx, "AsyncClient", _FakeAsyncClient)

    response = await kmh_app.prompt_ollama_stream(
        kmh_app.PromptRequest(
            prompt="Recommend sources.",
            llm_provider="claude",
            cloud_model="Claude Sonnet 4",
            cloud_api_key="sk-ant-test",
        )
    )

    body = await _collect_stream(response)

    assert '"provider": "claude"' in body
    assert "Waiting for Claude API response" in body
    assert "Claude source recommendation." in body
    assert '"type": "done"' in body


@pytest.mark.asyncio
async def test_prompt_stream_reports_missing_claude_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeAsyncClient.response = _ErrorResponse()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(kmh_app.httpx, "AsyncClient", _FakeAsyncClient)
    response = await kmh_app.prompt_ollama_stream(
        kmh_app.PromptRequest(
            prompt="Recommend sources.",
            llm_provider="claude",
            cloud_model="claude-sonnet-4-6",
        )
    )

    body = await _collect_stream(response)

    assert '"type": "fallback"' in body
    assert '"type": "error"' in body
    assert "Claude API key required" in body
    assert "model missing" in body


@pytest.mark.asyncio
async def test_prompt_stream_uses_server_claude_key_when_browser_key_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeAsyncClient.response = _ClaudeResponse()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-server-test")
    monkeypatch.setattr(kmh_app.httpx, "AsyncClient", _FakeAsyncClient)

    response = await kmh_app.prompt_ollama_stream(
        kmh_app.PromptRequest(
            prompt="Recommend sources.",
            llm_provider="claude",
            cloud_model="Claude Sonnet 4",
        )
    )

    body = await _collect_stream(response)

    assert '"provider": "claude"' in body
    assert "Claude source recommendation." in body
    assert '"type": "done"' in body


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


def test_atak_prompt_uses_client_location_and_display_bounds() -> None:
    request = kmh_app.PromptRequest(
        prompt="Route me to nearest freshwater.",
        llm_provider="ollama",
        agent_profile="tera-atak-live",
        map_context=kmh_app.MapContext(
            client_location=kmh_app.MapPoint(lat=37.79, lon=-122.4),
            camera=kmh_app.MapPoint(lat=37.791, lon=-122.399),
            view_bounds=kmh_app.ViewBounds(
                west=-122.405,
                south=37.785,
                east=-122.390,
                north=37.800,
                center_lat=37.7925,
                center_lon=-122.3975,
            ),
        ),
    )

    system_prompt = kmh_app._build_system_prompt(request)

    assert "TAK client location (route origin): lat 37.790000, lon -122.400000" in system_prompt
    assert "Displayed ATAK map bounds:" in system_prompt
    assert "displayed ATAK map view via plugin" in system_prompt
    assert "Use the displayed ATAK map bounds as the visible operating area" in system_prompt
    assert "OSM vectors from /WINTAK Imagery and DTED terrain from /DTED" in system_prompt


def test_atak_prompt_source_catalog_is_limited_to_root_osm_and_dted() -> None:
    request = kmh_app.PromptRequest(
        prompt="Need slope analysis and viewshed for a route.",
        llm_provider="ollama",
        agent_profile="tera-atak-live",
        map_context=kmh_app.MapContext(
            client_location=kmh_app.MapPoint(lat=37.79, lon=-122.4),
        ),
    )

    system_prompt = kmh_app._build_system_prompt(request)

    assert "local OSM vectors from /WINTAK Imagery" in system_prompt
    assert "local DTED terrain from /DTED" in system_prompt
    assert "Root DTED Terrain" in system_prompt
    assert "Root-staged OSM vector data" in system_prompt
    assert "USGS 3DEP" not in system_prompt
    assert "Cesium World Terrain" not in system_prompt
    assert "Copernicus DEM" not in system_prompt
    assert "Sentinel" not in system_prompt


def test_atak_mirror_event_records_client_location_and_query_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("TERA_ATAK_MIRROR_LOG", str(tmp_path / "atak-mirror.jsonl"))
    request = kmh_app.PromptRequest(
        prompt="Route me to nearest freshwater within 5km.",
        llm_provider="ollama",
        agent_profile="tera-atak-live",
        map_context=kmh_app.MapContext(
            client_location=kmh_app.MapPoint(lat=37.79, lon=-122.4, height_m=14.0),
            view_bounds=kmh_app.ViewBounds(
                west=-122.405,
                south=37.785,
                east=-122.390,
                north=37.800,
                center_lat=37.7925,
                center_lon=-122.3975,
            ),
        ),
    )

    event = kmh_app._append_atak_mirror_event(
        source="atak-plugin",
        role="operator",
        text=request.prompt,
        provider="ollama",
        direction="inbound",
        client_location=kmh_app._atak_monitor_client_location(request.map_context),
        view_bounds=kmh_app._atak_monitor_view_bounds(request.map_context),
        query_context=kmh_app._atak_monitor_query_context(request),
    )
    reloaded = kmh_app._read_atak_mirror_events()[0]

    assert event.client_location is not None
    assert reloaded.client_location is not None
    assert reloaded.client_location.lat == 37.79
    assert reloaded.view_bounds is not None
    assert reloaded.query_context["target_type"] == "freshwater"
    assert reloaded.query_context["radius_m"] == 5000.0
    assert reloaded.query_context["client_location_source"] == "atak_self_marker"
    assert "OSM vectors from /WINTAK Imagery" in reloaded.query_context["data_sources"]


def test_source_recommendation_questions_prioritize_source_scope() -> None:
    recommendation = kmh_app._infer_source_recommendation(
        "Build an offline package for a patrol to find reliable water while avoiding steep exposed terrain.",
        None,
    )
    questions = " ".join(recommendation.clarifying_questions).lower()

    assert "move the map" in questions
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


def test_model_provider_menu_supports_local_and_claude() -> None:
    html = kmh_app.INDEX_FILE.read_text(encoding="utf-8")
    css = (kmh_app.STATIC_DIR / "styles.css").read_text(encoding="utf-8")
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")
    app_source = Path(kmh_app.__file__).read_text(encoding="utf-8")

    for token in [
        'id="modelProviderBtn"',
        'id="modelProviderMenu"',
        'id="atakAgentBtn"',
        'id="atakMirrorPanel"',
        'id="providerSelect"',
        'id="topModelSelect"',
        'id="claudeModelSelect"',
        'id="claudeApiKeyInput"',
        "Auto: Claude -> Local",
        "Claude API",
        "claude-sonnet-4-6",
        "Claude Sonnet 4.6",
        "TERA ATAK Link",
        "claude-opus-4-1-20250805",
    ]:
        assert token in html

    for token in [
        ".top-provider-shell",
        ".atak-mirror-panel",
        ".atak-mirror-event",
        ".atak-mirror-event-data",
        "grid-auto-rows: max-content",
        "align-content: start",
        ".chip-button",
        ".provider-menu",
        ".provider-actions",
    ]:
        assert token in css

    for token in [
        "teraLlmProvider",
        "activateAtakLocalAgent",
        "atakMirrorPanel",
        "atakClientLocationEntity",
        "syncAtakClientLocationFromEvents",
        "event.client_location",
        "query_context",
        "tak_cot_summary",
        "/api/jetson/atak-agent/activate",
        "/api/jetson/atak-agent/mirror",
        "gemma3:4b",
        "teraClaudeApiKey",
        "serverClaudeKeyAvailable",
        "hasClaudeProviderCredential",
        "anthropic_api_key_configured",
        "default_provider",
        "applyProviderSelection",
        "void loadModels();",
        "Detected local model:",
        "llm_provider",
        "cloud_model",
        "cloud_api_key",
        "Trying Claude, then local model if needed",
        "Claude API key required",
    ]:
        assert token in js

    for token in [
        "ANTHROPIC_API_URL",
        "ANTHROPIC_MODELS_URL",
        "ANTHROPIC_VERSION",
        "CLAUDE_MODEL",
        "CLAUDE_MODEL_ALIASES",
        "CLAUDE_MODEL_FALLBACKS",
        "JetsonAtakActivateRequest",
        "JetsonAtakModeResponse",
        "TERA_ATAK_MODEL",
        "JETSON_ATAK_MODE",
        "activate_jetson_atak_agent",
        "jetson_atak_agent_mirror",
        "_append_atak_mirror_event",
        "default_provider",
        "claude_default_model",
        "anthropic_api_key_configured",
        "_normalize_claude_model",
        "_claude_model_candidates",
        "_fetch_anthropic_model_ids",
        "_post_prompt_with_fallback",
        "_select_ollama_default_model",
        "Auto-detected installed Gemma model",
        "_post_claude_message",
        "_extract_claude_response_text",
    ]:
        assert token in app_source


def test_claude_model_labels_normalize_to_current_sonnet() -> None:
    assert kmh_app._normalize_claude_model("Claude Sonnet 4.6") == "claude-sonnet-4-6"
    assert kmh_app._normalize_claude_model("claude-sonnet-4.6") == "claude-sonnet-4-6"
    assert kmh_app._normalize_claude_model("claude-sonnet-4-6") == "claude-sonnet-4-6"
    assert kmh_app._normalize_claude_model("claude-sonnet-4-20250514") == "claude-sonnet-4-20250514"
    assert kmh_app._normalize_claude_model("Claude Opus 4.1") == "claude-opus-4-1-20250805"
    assert kmh_app._normalize_claude_model("Claude Opus 4.7") == "claude-opus-4-1-20250805"
    assert kmh_app._normalize_claude_model("Claude Haiku 4.5") == "claude-3-5-haiku-20241022"


def test_local_model_detection_prefers_installed_gemma_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the configured OLLAMA_MODEL is installed locally, pick it.

    Hermetic via monkeypatch so the test passes regardless of the
    operator's .env (which on the demo Jetson sets OLLAMA_MODEL=gemma2:2b
    pre-Phase-3-cutover; once Kyle pulls gemma3:4b on the Jetson, the
    .env switches and this test still pins the early-return behavior).
    """
    monkeypatch.setattr(kmh_app, "OLLAMA_MODEL", "gemma3:4b")
    models = [
        "hf.co/unsloth/gemma-4-E4B-it-GGUF:UD-Q4_K_XL",
        "gemma4:e4b",
        "gemma3:4b",
    ]

    assert kmh_app._select_ollama_default_model(models) == "gemma3:4b"


def test_location_search_prefers_curated_cascades_match() -> None:
    suggestions = kmh_app._local_location_suggestions("go to Cascades")

    assert suggestions
    assert suggestions[0].name == "Cascade Range, WA/OR/BC"
    assert suggestions[0].score > 0


def test_location_search_parses_google_maps_coordinate_links() -> None:
    suggestion = kmh_app._coordinate_location_suggestion(
        "https://www.google.com/maps/place/test/data=!3m1!4b1!4m6!3m5!8m2!3d47.8021!4d-123.6044"
    )

    assert suggestion is not None
    assert suggestion.source == "coordinate-query"
    assert suggestion.lat == 47.8021
    assert suggestion.lon == -123.6044


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


def test_planner_keeps_scope_questions_in_agent_response_only() -> None:
    html = kmh_app.INDEX_FILE.read_text(encoding="utf-8")
    css = (kmh_app.STATIC_DIR / "styles.css").read_text(encoding="utf-8")
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "ensureClarifyingQuestions" in js
    assert "state.workflowStageIndex = 1;" in js
    assert "Confirm sources when ready." in js
    assert "### Scope Check" in js
    assert 'data-workflow-slide="questions"' not in html
    assert 'id="clarifyingQuestions"' not in html
    assert "Socratic questions" not in html
    assert "renderClarifyingQuestions" not in js
    assert "Use Questions to scope, then confirm sources." not in js
    assert "Next questions:" not in js

    assert 'article.className = "source-item compact-source-item source-chip";' in js
    assert 'article.title = `${source.category} | ${formatSourceStatus(source)}`;' in js
    assert 'purpose.className = "source-purpose"' not in js
    assert 'meta.className = "source-meta"' not in js

    assert "--text-base: 12px;" in css
    assert "grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));" in css
    assert "max-height: min(11vh, 92px);" in css
    assert ".source-chip" in css
    assert "grid-template-columns: auto minmax(0, 1fr);" in css
    assert "min-height: 76px;" in css


def test_user_chat_transcript_hides_prompt_context_appendix() -> None:
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert 'const finalPrompt = `${prompt}${makeMapContextAppendix()}`;' in js
    assert 'prompt: finalPrompt,' in js
    assert 'appendMessage(\n    "user",\n    prompt,\n  );' in js
    assert 'focus: ${sourceContext.mission_focus}' not in js


def test_llm_dev_docker_runs_package_import_path() -> None:
    repo_root = Path(kmh_app.__file__).resolve().parents[1]
    compose = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")
    dockerfile = (repo_root / "llm_dev_kmh" / "Dockerfile").read_text(encoding="utf-8")

    assert "context: ." in compose
    assert "dockerfile: llm_dev_kmh/Dockerfile" in compose
    assert "COPY llm_dev_kmh ./llm_dev_kmh" in dockerfile
    assert "COPY prompts ./prompts" in dockerfile
    assert '"llm_dev_kmh.app:app"' in dockerfile
    assert '"app:app"' not in dockerfile


def test_prompt_composer_clears_after_submit_is_accepted() -> None:
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")

    clear_index = js.index('els.promptInput.value = "";')
    plan_index = js.index("await planSourcesFromMission(prompt, mapContext);")

    assert clear_index < plan_index


def test_data_package_empty_state_does_not_repeat_chat_instruction() -> None:
    html = kmh_app.INDEX_FILE.read_text(encoding="utf-8")
    css = (kmh_app.STATIC_DIR / "styles.css").read_text(encoding="utf-8")

    assert 'id="workflowEmpty" class="workflow-empty" aria-hidden="true"></div>' in html
    assert ".workflow-empty:empty" in css
    assert "Describe the mission in chat to begin source planning." not in html


def test_chat_panel_hides_advisor_header_and_status_noise() -> None:
    html = kmh_app.INDEX_FILE.read_text(encoding="utf-8")
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "<h2>Source Advisor</h2>" not in html
    assert '<div class="visually-hidden">' in html
    assert 'id="requestStatus" class="section-meta" aria-live="polite"' in html
    assert "Use the advisor response" not in js
    assert "Deterministic advisor response shown (" not in js


def test_advisor_settings_panel_opens_inside_chat_column() -> None:
    html = kmh_app.INDEX_FILE.read_text(encoding="utf-8")
    css = (kmh_app.STATIC_DIR / "styles.css").read_text(encoding="utf-8")

    settings_button_index = html.index('id="settingsToggleBtn"')
    settings_panel_index = html.index('id="settingsMenu"')
    chat_log_index = html.index('id="chatLog"')
    settings_css = css[css.index(".settings-menu {") : css.index(".settings-menu-header {")]

    assert settings_button_index < settings_panel_index < chat_log_index
    assert ".settings-menu {\n  width: 100%;" in css
    assert "max-height: min(44vh, 520px);" in css
    assert "overflow-y: auto;" in css
    assert "position: absolute;" not in settings_css
    assert "top:" not in settings_css


def test_map_stream_status_does_not_confuse_esri_tiles_with_missing_ion() -> None:
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")
    app_source = Path(kmh_app.__file__).read_text(encoding="utf-8")

    assert "_load_dotenv_file(BASE_DIR.parent / \".env\")" in app_source
    assert "_load_dotenv_file(BASE_DIR.parent / \".env.local\")" in app_source
    assert "CESIUM_ACCESS_TOKEN" in app_source
    assert "CESIUM_ION_ACCESS_TOKEN" in app_source
    assert "state.cesiumIonTokenAvailable = hasCesiumIonToken();" in js
    assert "function updateMapStreamChip" in js
    assert "Map stream: ${imageryLabel}" in js
    assert "Map stream active; ion fallback" in js
    assert "Cesium ion stream active" in js
    assert "Cesium token missing" not in js
    assert "Cesium token detected" not in js


def test_dotenv_loader_sets_missing_environment_values(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    key = "TERA_TEST_DOTENV_VALUE"
    monkeypatch.delenv(key, raising=False)
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text(f"{key}='loaded-from-dotenv'\n", encoding="utf-8")

    kmh_app._load_dotenv_file(dotenv_file)

    assert os.environ[key] == "loaded-from-dotenv"


def test_source_planner_degrades_without_false_inference_failure() -> None:
    html = kmh_app.INDEX_FILE.read_text(encoding="utf-8")
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "FALLBACK_SOURCE_CATALOG" in js
    assert "buildClientSourceRecommendation" in js
    assert "Planner fallback" in js
    assert "Source planner unavailable" in js
    assert "Planning source package" in js
    assert "Local model offline; rules active" in js
    assert "deterministic planner response" in js
    assert "plan the needed package" in html

    for stale_label in [
        "Inference failed",
        "Source inference failed",
        "Inferring source package",
        "Source catalog not loaded",
        "No source catalog loaded",
        "Source catalog failed",
        "Ollama lookup failed",
        "Model lookup failed",
    ]:
        assert stale_label not in js
        assert stale_label not in html


def test_prompt_submission_tries_selected_provider_then_local_then_deterministic() -> None:
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")
    app_source = Path(kmh_app.__file__).read_text(encoding="utf-8")

    assert "streamAssistantProvider" in js
    assert "Trying Claude, then local model if needed" in js
    assert "eventData.type === \"fallback\"" in js
    assert "deterministic planner response" in js
    assert "Prompt request failed; deterministic planner response shown." in js
    assert 'provider === "ollama" && !state.localModelAvailable' not in js
    assert "Claude failed; trying local Ollama fallback" not in js
    assert "Claude key missing; trying local Ollama fallback" not in js
    assert "local fallback after Claude failure" not in js
    assert "Model providers unavailable; deterministic advisor response shown (" not in js

    claude_attempt = app_source.index('return ["claude", "ollama"]')
    deterministic = js.index("deterministic planner response")

    assert claude_attempt >= 0
    assert deterministic >= 0


def test_backend_provider_sequence_is_claude_then_ollama() -> None:
    assert kmh_app._request_llm_provider(kmh_app.PromptRequest(prompt="x")) == "auto"
    assert kmh_app._provider_sequence(kmh_app.PromptRequest(prompt="x")) == ["claude", "ollama"]
    assert kmh_app._provider_sequence(
        kmh_app.PromptRequest(prompt="x", llm_provider="ollama")
    ) == ["ollama"]
    assert kmh_app._provider_sequence(
        kmh_app.PromptRequest(prompt="x", llm_provider="claude")
    ) == ["claude", "ollama"]


@pytest.mark.asyncio
async def test_atak_activation_forces_auto_prompts_to_local_gemma(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    original_mode = kmh_app.JETSON_ATAK_MODE.copy()
    original_active_model = kmh_app.ACTIVE_OLLAMA_MODEL
    original_active_base_url = kmh_app.ACTIVE_OLLAMA_BASE_URL

    async def fake_prepare(model: str, agent_profile: str) -> dict[str, object]:
        assert model == "gemma3:4b"
        assert agent_profile == "tera-atak-live"
        return {
            "ready": True,
            "base_url": "http://host.docker.internal:11434",
            "detail": "Ollama warmed for ATAK.",
        }

    monkeypatch.setenv("TERA_ATAK_MIRROR_LOG", str(tmp_path / "atak-mirror.jsonl"))
    monkeypatch.setattr(kmh_app, "TERA_ATAK_ACTIVATE_COMMAND", "")
    monkeypatch.setattr(kmh_app, "_prepare_ollama_for_atak", fake_prepare)

    class FakeUrl:
        scheme = "http"

    class FakeRequest:
        headers = {"host": "10.1.63.96:8080"}
        url = FakeUrl()

    try:
        response = await kmh_app.activate_jetson_atak_agent(
            kmh_app.JetsonAtakActivateRequest(),
            FakeRequest(),  # type: ignore[arg-type]
        )

        assert response.active is True
        assert response.status == "active"
        assert response.ollama_ready is True
        assert response.ollama_base_url == "http://host.docker.internal:11434"
        assert response.plugin_endpoint == "http://10.1.63.96:8080/api/prompt"
        assert response.model == "gemma3:4b"
        assert response.provider == "ollama"
        assert response.events
        assert response.events[-1].role == "assistant"
        assert response.events[-1].text == "TERA Agent ready. Send your traffic."
        assert response.events[-1].direction == "ready"
        assert kmh_app._provider_sequence(
            kmh_app.PromptRequest(prompt="x", llm_provider="auto")
        ) == ["ollama"]
        assert await kmh_app._resolve_ollama_model(
            kmh_app.PromptRequest(prompt="x")
        ) == "gemma3:4b"
    finally:
        kmh_app.JETSON_ATAK_MODE.clear()
        kmh_app.JETSON_ATAK_MODE.update(original_mode)
        kmh_app.ACTIVE_OLLAMA_MODEL = original_active_model
        kmh_app.ACTIVE_OLLAMA_BASE_URL = original_active_base_url


def test_atak_live_profile_uses_tactical_plugin_prompt() -> None:
    prompt = kmh_app._build_system_prompt(
        kmh_app.PromptRequest(
            prompt="Route me to water.",
            llm_provider="ollama",
            agent_profile="tera-atak-live",
        )
    )

    assert "live ATAK plugin agent" in prompt
    assert "Samsung ATAK end-user device" in prompt
    assert "supplied map context" in prompt
    assert "local imagery and geospatial data sourcing assistant" not in prompt


def test_atak_mode_coerces_prompt_requests_to_live_profile() -> None:
    original_mode = kmh_app.JETSON_ATAK_MODE.copy()
    try:
        kmh_app.JETSON_ATAK_MODE.update(
            {
                "active": True,
                "model": "gemma3:4b",
                "agent_profile": "tera-atak-live",
            }
        )
        request = kmh_app.PromptRequest(prompt="Hello from ATAK.")

        coerced = kmh_app._coerce_atak_prompt_request(request)

        assert coerced.llm_provider == "ollama"
        assert coerced.model == "gemma3:4b"
        assert coerced.agent_profile == "tera-atak-live"
        assert kmh_app._mirror_source_for_request(coerced) == "atak-plugin"
        assert "live ATAK plugin agent" in kmh_app._build_system_prompt(coerced)
    finally:
        kmh_app.JETSON_ATAK_MODE.clear()
        kmh_app.JETSON_ATAK_MODE.update(original_mode)


def test_atak_activation_normalizes_gemma3_4_alias() -> None:
    assert kmh_app._normalize_ollama_model_name("gemma3:4") == "gemma3:4b"
    assert kmh_app._normalize_ollama_model_name("gemma3:4b") == "gemma3:4b"


def test_tak_cot_payload_generates_route_from_local_osm(monkeypatch: pytest.MonkeyPatch) -> None:
    from routing import osm_sqlite_features

    def fake_query_osm_features(**kwargs: object) -> list[dict[str, object]]:
        assert kwargs["target_type"] == "freshwater"
        return [
            {
                "name": "Demo Creek",
                "lat": 37.795,
                "lon": -122.392,
                "distance_m": 420.0,
                "source_layer": "waterways",
            }
        ]

    monkeypatch.setattr(osm_sqlite_features, "query_osm_features", fake_query_osm_features)
    request = kmh_app.PromptRequest(
        prompt="Route me to the nearest freshwater within 5km on foot under cover.",
        llm_provider="ollama",
        agent_profile="tera-atak-live",
        map_context=kmh_app.MapContext(
            client_location=kmh_app.MapPoint(lat=37.79, lon=-122.4),
            selected_area=kmh_app.ViewBounds(
                west=-122.4,
                south=37.79,
                east=-122.4,
                north=37.79,
                center_lat=37.79,
                center_lon=-122.4,
            )
        ),
    )

    payload = kmh_app._build_tak_cot_payload(request, "Routing to nearest water.")

    assert payload.replace_existing is True
    assert payload.algorithm == "osm_nearest_feature_direct_route"
    assert len(payload.items) == 1
    item = payload.items[0]
    assert item.item_type == "route"
    assert item.cot_type == "b-m-r"
    assert item.title == "TERA route to Demo Creek"
    assert len(item.coordinates) == 3
    assert [checkpoint.label for checkpoint in item.checkpoints] == [
        "Start",
        "Checkpoint 1",
        "Demo Creek",
    ]
    assert "<event" in item.cot_xml
    root = ET.fromstring(item.cot_xml)
    assert root.attrib["type"] == "b-m-r"
    assert root.find("detail/route") is None
    detail = root.find("detail")
    assert detail is not None
    links = detail.findall("link")
    assert len(links) == len(item.coordinates)
    assert [link.attrib["type"] for link in links] == [
        "b-m-p-w",
        "b-m-p-c",
        "b-m-p-w",
    ]
    assert links[0].attrib["callsign"] == "TERA route to Demo Creek SP"
    assert links[-1].attrib["callsign"] == "TERA route to Demo Creek VDO"
    assert links[-1].attrib["point"] == "37.7950000,-122.3920000"
    detail_order = [child.tag for child in list(detail)]
    assert detail_order == [
        "link",
        "link",
        "link",
        "link_attr",
        "strokeColor",
        "strokeWeight",
        "__routeinfo",
        "contact",
        "remarks",
        "archive",
        "labels_on",
        "color",
    ]
    link_attr = detail.find("link_attr")
    assert link_attr is not None
    assert link_attr.attrib == {
        "planningmethod": "Infil",
        "color": "-1",
        "method": "Walking",
        "prefix": "CP",
        "type": "Foot",
        "stroke": "3",
        "direction": "Infil",
        "routetype": "Primary",
        "order": "Ascending Check Points",
    }
    assert detail.find("strokeColor").attrib["value"] == "-1"  # type: ignore[union-attr]
    assert detail.find("strokeWeight").attrib["value"] == "3.0"  # type: ignore[union-attr]
    assert detail.find("contact").attrib["callsign"] == "TERA route to Demo Creek"  # type: ignore[union-attr]
    assert detail.find("labels_on").attrib["value"] == "false"  # type: ignore[union-attr]
    assert item.metadata["target"]["source_layer"] == "waterways"
    assert item.metadata["takcot_schema"] == "Route.xsd"
    assert payload.package is not None
    assert payload.package.file_name == f"{payload.collection_uid}.kmz"
    assert payload.package.format == "kmz"
    assert payload.package.target_path == f"/sdcard/fromTERA/{payload.package.file_name}"
    package_bytes = base64.b64decode(payload.package.content_b64)
    assert payload.package.size_bytes == len(package_bytes)
    with zipfile.ZipFile(BytesIO(package_bytes)) as package:
        names = set(package.namelist())
        assert "doc.kml" in names
        assert "MANIFEST/manifest.xml" in names
        assert f"cot/{item.uid}.xml" in names
        kml = package.read("doc.kml").decode("utf-8")
        assert "TERA route to Demo Creek" in kml
        assert "-122.3920000,37.7950000,0.00" in kml
        assert "Generated 1 TAK item" in package.read("MANIFEST/manifest.xml").decode("utf-8")


def test_tak_cot_payload_prefers_client_location_and_visible_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from routing import osm_sqlite_features

    def fake_query_osm_features(**kwargs: object) -> list[dict[str, object]]:
        assert kwargs["origin"] == {"lat": 37.79, "lon": -122.4}
        assert kwargs["limit"] == 20
        return [
            {
                "name": "Offscreen Creek",
                "lat": 37.81,
                "lon": -122.42,
                "distance_m": 80.0,
            },
            {
                "name": "Visible Creek",
                "lat": 37.794,
                "lon": -122.397,
                "distance_m": 420.0,
            },
        ]

    monkeypatch.setattr(osm_sqlite_features, "query_osm_features", fake_query_osm_features)
    request = kmh_app.PromptRequest(
        prompt="Route me to nearest freshwater.",
        llm_provider="ollama",
        agent_profile="tera-atak-live",
        map_context=kmh_app.MapContext(
            client_location=kmh_app.MapPoint(lat=37.79, lon=-122.4),
            view_bounds=kmh_app.ViewBounds(
                west=-122.405,
                south=37.785,
                east=-122.390,
                north=37.800,
            ),
        ),
    )

    payload = kmh_app._build_tak_cot_payload(request, "Routing to visible water.")
    item = payload.items[0]

    assert item.title == "TERA route to Visible Creek"
    assert item.coordinates[0] == [-122.4, 37.79]
    assert item.metadata["target"]["inside_view_bounds"] is True


def test_osm_configured_paths_scan_wintak_imagery_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from routing.osm_sqlite_features import configured_sqlite_paths

    wintak_dir = tmp_path / "WINTAK Imagery"
    nested = wintak_dir / "OSM"
    nested.mkdir(parents=True)
    sqlite_path = nested / "demo.gpkg"
    sqlite_path.write_bytes(b"sqlite placeholder")

    monkeypatch.delenv("TERA_OSM_SQLITE_PATHS", raising=False)
    monkeypatch.delenv("WAYFINDER_OSM_SQLITE_PATHS", raising=False)
    monkeypatch.setenv("TERA_WINTAK_IMAGERY_DIR", str(wintak_dir))

    assert configured_sqlite_paths() == [sqlite_path]


def test_tak_cot_payload_uses_second_target_for_reroute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from routing import osm_sqlite_features

    def fake_query_osm_features(**_: object) -> list[dict[str, object]]:
        return [
            {"name": "Blocked Creek", "lat": 37.791, "lon": -122.401, "distance_m": 100.0},
            {"name": "Alternate Creek", "lat": 37.792, "lon": -122.402, "distance_m": 250.0},
        ]

    monkeypatch.setattr(osm_sqlite_features, "query_osm_features", fake_query_osm_features)
    request = kmh_app.PromptRequest(
        prompt="That route does not work.",
        llm_provider="ollama",
        agent_profile="tera-atak-live",
        map_context=kmh_app.MapContext(
            client_location=kmh_app.MapPoint(lat=37.79, lon=-122.4),
            selected_area=kmh_app.ViewBounds(
                west=-122.4,
                south=37.79,
                east=-122.4,
                north=37.79,
                center_lat=37.79,
                center_lon=-122.4,
            ),
            tera_active_items=[
                {
                    "uid": "TERA-OLD-route",
                    "item_type": "route",
                    "metadata": {"target_type": "freshwater"},
                }
            ],
        ),
    )

    payload = kmh_app._build_tak_cot_payload(request, "Rerouting.")

    assert payload.items[0].title == "TERA route to Alternate Creek"


def test_atak_plugin_understands_prompt_tak_cot_payload() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    plugin_source = (
        repo_root
        / "atak"
        / "plugin"
        / "app"
        / "src"
        / "main"
        / "java"
        / "TacticalEdgeRouteAgent"
        / "plugin"
        / "TERAPlugin.java"
    ).read_text(encoding="utf-8")
    client_source = (
        repo_root
        / "atak"
        / "plugin"
        / "app"
        / "src"
        / "main"
        / "java"
        / "TacticalEdgeRouteAgent"
        / "plugin"
        / "TeraPlanClient.java"
    ).read_text(encoding="utf-8")
    strings = (
        repo_root
        / "atak"
        / "plugin"
        / "app"
        / "src"
        / "main"
        / "res"
        / "values"
        / "strings.xml"
    ).read_text(encoding="utf-8")
    manifest = (
        repo_root
        / "atak"
        / "plugin"
        / "app"
        / "src"
        / "main"
        / "AndroidManifest.xml"
    ).read_text(encoding="utf-8")

    assert "applyTakCot" in plugin_source
    assert "saveTakPackage" in plugin_source
    assert 'TERA_SHARED_PACKAGE_DIR = "/sdcard/fromTERA"' in plugin_source
    assert "takPackageDirectories" in plugin_source
    assert "uniqueTakPackageFile" in plugin_source
    assert "sha256Hex" in plugin_source
    assert "Environment.getExternalStorageDirectory()" in plugin_source
    assert 'getExternalFilesDir("fromTERA")' in plugin_source
    assert '"fromTERA"' in plugin_source
    assert "content_b64" in plugin_source
    assert "activeTeraItemUids" in plugin_source
    assert "activeTeraItems" in plugin_source
    assert "client_location" in plugin_source
    assert "client_location" in client_source
    assert "tera_active_items" in plugin_source
    assert "tak_cot" in client_source
    assert "/sdcard/fromTERA" in client_source
    assert "/api/prompt" in strings
    assert "MANAGE_EXTERNAL_STORAGE" in manifest


@pytest.mark.asyncio
async def test_prepare_ollama_for_atak_requires_successful_warmup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch(_: str) -> list[str]:
        return ["gemma3:4b"]

    async def fake_warmup(_: str, model: str, __: str) -> str:
        raise RuntimeError(f"{model} did not answer readiness prompt")

    monkeypatch.setattr(kmh_app, "ACTIVE_OLLAMA_BASE_URL", None)
    monkeypatch.setattr(
        kmh_app,
        "_ollama_base_url_candidates",
        lambda: ["http://127.0.0.1:11434"],
    )
    monkeypatch.setattr(kmh_app, "_fetch_ollama_models_from", fake_fetch)
    monkeypatch.setattr(kmh_app, "_warm_ollama_atak_model", fake_warmup)

    result = await kmh_app._prepare_ollama_for_atak("gemma3:4b", "tera-atak-live")

    assert result["ready"] is False
    assert result["base_url"] == "http://127.0.0.1:11434"
    assert "Ollama warmup failed" in str(result["detail"])


def test_jetson_refresh_prepares_ollama_for_atak_mode() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "deploy"
        / "scripts"
        / "jetson_compose_refresh.sh"
    )
    script = script_path.read_text(encoding="utf-8")

    assert "start_ollama_for_atak" in script
    assert "ollama pull \"$model\"" in script
    assert "ollama run \"$model\"" in script
    assert "ollama-warmup.log" in script
    assert "TERA Agent ready. Send your traffic." in script
    assert "continuing with web app restart" in script


class _ClaudeInvalidModelResponse:
    status_code = 400
    text = '{"error":{"message":"model not found"}}'

    def raise_for_status(self) -> None:
        request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        response = httpx.Response(400, text=self.text, request=request)
        raise httpx.HTTPStatusError("bad request", request=request, response=response)


class _OllamaGenerateResponse:
    status_code = 200
    text = '{"response":"Ollama fallback response."}'

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {"response": "Ollama fallback response."}


@pytest.mark.asyncio
async def test_auto_prompt_falls_back_from_claude_to_ollama(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeClient:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *_exc_info: object) -> None:
            return None

        async def get(self, *_args: object, **_kwargs: Any) -> object:
            return _ModelsResponse()

        async def post(self, url: str, **_kwargs: Any) -> object:
            if "anthropic" in url:
                return _ClaudeInvalidModelResponse()
            return _OllamaGenerateResponse()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-server-test")
    monkeypatch.setattr(kmh_app.httpx, "AsyncClient", FakeClient)

    response = await kmh_app.prompt_ollama(
        kmh_app.PromptRequest(prompt="Recommend sources.", llm_provider="auto")
    )

    assert response.provider == "ollama"
    assert response.response == "Ollama fallback response."
    assert response.fallbacks
    assert "claude:" in response.fallbacks[0]


def test_runtime_config_advertises_auto_provider_when_claude_key_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-server-test")

    assert kmh_app._default_provider() == "auto"

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert kmh_app._default_provider() == "ollama"


@pytest.mark.asyncio
async def test_runtime_config_defaults_to_demo_mgrs_center() -> None:
    response = await kmh_app.runtime_config()

    assert kmh_app.DEFAULT_CENTER_MGRS == "11S KC 79790 48252"
    assert response.default_lat == pytest.approx(38.35537339313087)
    assert response.default_lon == pytest.approx(-119.52018528165966)
    assert response.default_height_m == pytest.approx(14000)


def test_esri_queryable_terrain_is_available_for_download_fallbacks() -> None:
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")
    prompt = (
        Path("prompts/local_model_prompts/imagery_sourcing_local_model_system_prompt.md")
        .read_text(encoding="utf-8")
    )

    source = kmh_app.SOURCE_BY_ID["esri_world_elevation"]

    assert source.category == "terrain"
    assert source.stream_status == "queryable-online"
    assert source.download_status == "download-required"
    assert source.download_methods
    assert source.jetson_query_formats
    assert source.source_url == kmh_app.ESRI_WORLD_ELEVATION_TERRAIN_URL
    assert "dem_cog" in source.derived_layers
    assert "elevation_samples" in source.derived_layers
    assert "esri_world_elevation" in js
    assert "Esri World Elevation Terrain" in js
    assert "queryable-online" in js
    assert "download-required" in js
    assert "DTED at `/DTED` is the terrain source" in prompt

    recommendation = kmh_app._infer_source_recommendation(
        "Need a terrain route that avoids steep exposed terrain.",
        None,
    )
    assert "dted_earth_explorer" in recommendation.required_source_ids
    assert "copernicus_dem" not in recommendation.required_source_ids
    assert "dted_earth_explorer" in recommendation.selected_source_ids


def test_esri_imagery_exports_use_official_export_tiles_contract() -> None:
    source = kmh_app.SOURCE_BY_ID["esri_world_imagery"]

    assert source.download_status == "export-tiles-with-account"
    assert source.download_methods
    export_method = source.download_methods[0]
    assert export_method.endpoint.endswith("/World_Imagery/MapServer/exportTiles")
    assert export_method.params["tilePackage"] == "true"
    assert export_method.params["token"] == "${ESRI_ARCGIS_TOKEN}"
    assert export_method.requires_account is True
    assert source.jetson_query_formats[0].artifact_type == "esri_tpkx_imagery_package"


def test_free_imagery_sources_use_wintak_osm_naip_and_dted() -> None:
    sentinel = kmh_app.SOURCE_BY_ID["sentinel_2"]
    naip = kmh_app.SOURCE_BY_ID["naip"]
    usgs = kmh_app.SOURCE_BY_ID["usgs_imagery_only"]
    nrl = kmh_app.SOURCE_BY_ID["nrl_naip_conus"]
    osm = kmh_app.SOURCE_BY_ID["osm_extract"]
    copernicus = kmh_app.SOURCE_BY_ID["copernicus_dem"]
    dted = kmh_app.SOURCE_BY_ID["dted_earth_explorer"]
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")
    prompt = (
        Path("prompts/local_model_prompts/imagery_sourcing_local_model_system_prompt.md")
        .read_text(encoding="utf-8")
    )

    assert naip.download_methods[0].id == "naip_earthexplorer_geotiff_import"
    assert naip.download_methods[0].endpoint == "${NAIP_EARTHEXPLORER_DIR}"
    assert naip.download_methods[0].requires_account is False
    assert naip.jetson_query_formats[0].artifact_type == "naip_imagery_index"
    assert sentinel.download_methods[0].endpoint == kmh_app.EARTH_SEARCH_STAC_SEARCH_URL
    assert sentinel.download_methods[0].params["collections"] == ["sentinel-2-l2a"]
    assert sentinel.download_methods[0].requires_token_env is None
    assert sentinel.jetson_query_formats[0].artifact_type == "sentinel2_cog_band_stack"
    assert osm.download_methods[0].id == "osm_wintak_imagery_import"
    assert osm.download_methods[0].endpoint == "${TERA_WINTAK_IMAGERY_DIR}"
    assert copernicus.download_methods[0].id == "copernicus_dem_glo30_cog"
    assert copernicus.download_methods[0].params["tile_urls"] == "{copernicus_dem_tile_urls}"
    assert dted.download_methods[0].id == "dted_earthexplorer_import_convert"
    assert dted.download_status == "manual-stage-import"
    assert usgs.download_methods[0].id == "usgs_imagery_tile_cache"
    assert usgs.download_methods[0].requires_token_env is None
    assert "basemap.nationalmap.gov" in usgs.source_url
    assert nrl.download_methods[0].id == "nrl_naip_tile_cache"
    assert "geoint.nrlssc.navy.mil" in nrl.source_url
    assert "Jetson analytical source selection is fixed to OSM vectors" in js
    assert "local OSM vectors under `/WINTAK Imagery` and local DTED terrain under" in prompt
    assert dted.name == "Root DTED Terrain"


def test_naip_osm_and_copernicus_download_params_are_aoi_scoped() -> None:
    bounds = kmh_app.ViewBounds(
        west=-117.5,
        south=36.0,
        east=-114.0,
        north=38.5,
        center_lat=37.2,
        center_lon=-116.0,
    )

    assert kmh_app._naip_state_code(bounds) == "nv"
    assert kmh_app._naip_s3_prefix(bounds) == "nv/2022/60cm/rgbir/"
    assert kmh_app._geofabrik_region_slug(bounds) == "north-america/us/nevada"
    assert kmh_app._geofabrik_osm_pbf_url(bounds).endswith(
        "/north-america/us/nevada-latest.osm.pbf"
    )

    tiles = kmh_app._copernicus_dem_tiles(bounds)
    tile_ids = {tile["tile_id"] for tile in tiles}
    assert "Copernicus_DSM_COG_10_N36_00_W118_00_DEM" in tile_ids
    assert "Copernicus_DSM_COG_10_N38_00_W115_00_DEM" in tile_ids


def test_cesium_sources_are_stream_only_not_offline_downloads() -> None:
    imagery = kmh_app.SOURCE_BY_ID["cesium_world_imagery"]
    terrain = kmh_app.SOURCE_BY_ID["cesium_world_terrain"]
    archive = kmh_app.SOURCE_BY_ID["cesium_ion_archive"]
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert imagery.download_status == "stream-only-no-offline-copy"
    assert terrain.download_status == "stream-only-no-offline-copy"
    assert imagery.download_methods == []
    assert terrain.download_methods == []
    assert archive.download_status == "download-required"
    assert {method.id for method in archive.download_methods} == {
        "cesium_ion_archive_download",
        "cesium_ion_clip_create_download",
    }
    assert archive.download_methods[0].endpoint == kmh_app.CESIUM_ION_ARCHIVE_DOWNLOAD_URL
    assert archive.download_methods[0].params["archive_id"] == "${CESIUM_ION_ARCHIVE_ID}"
    assert archive.download_methods[0].params["token"] == "${CESIUM_ION_TOKEN}"
    assert archive.jetson_query_formats[0].artifact_type == "cesium_offline_archive_index"
    assert 'download_status: "stream-only-no-offline-copy"' in js
    assert "cesium_ion_archive" in js


def test_cesium_archive_manifest_uses_configured_archive_or_clip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TERA_JETSON_LOCAL_SOURCES_ONLY", "0")
    bounds = kmh_app.ViewBounds(west=-122.5, south=37.7, east=-122.4, north=37.8)
    source = kmh_app.SOURCE_BY_ID["cesium_ion_archive"]

    monkeypatch.delenv("CESIUM_ION_ARCHIVE_ID", raising=False)
    monkeypatch.delenv("CESIUM_ARCHIVE_ID", raising=False)
    monkeypatch.delenv("CESIUM_ION_ASSET_IDS", raising=False)
    assert kmh_app._build_source_download_operations(
        package_id="pkgcesium",
        sources=[source],
        bounds=bounds,
    ) == []

    monkeypatch.setenv("CESIUM_ION_ARCHIVE_ID", "123")
    operations = kmh_app._build_source_download_operations(
        package_id="pkgcesium",
        sources=[source],
        bounds=bounds,
    )
    assert [operation["id"] for operation in operations] == ["cesium_ion_archive_download"]
    assert operations[0]["params"]["archive_id"] == "${CESIUM_ION_ARCHIVE_ID}"

    monkeypatch.delenv("CESIUM_ION_ARCHIVE_ID", raising=False)
    monkeypatch.setenv("CESIUM_ION_ASSET_IDS", "1001,1002")
    operations = kmh_app._build_source_download_operations(
        package_id="pkgcesium",
        sources=[source],
        bounds=bounds,
    )
    assert [operation["id"] for operation in operations] == ["cesium_ion_clip_create_download"]
    assert operations[0]["params"]["asset_ids"] == "${CESIUM_ION_ASSET_IDS}"
    assert operations[0]["params"]["clip_region"] == pytest.approx(
        [
            -2.138028333693054,
            0.6579891280011934,
            -2.1362820044410597,
            0.659734457253188,
        ]
    )


@pytest.mark.asyncio
async def test_cesium_archive_index_is_queryable_from_jetson(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OFFLINE_PACKAGE_ROOT", str(tmp_path / "packages"))
    package_id = "pkgcesium"
    manifest = {"package_id": package_id, "package_name": package_id, "download_operations": []}
    kmh_app.PACKAGE_MANIFESTS[package_id] = manifest
    kmh_app._persist_package_manifest(package_id, manifest)
    archive_path = (
        kmh_app._package_dir(package_id)
        / "cesium"
        / "archive"
        / "cesium_ion_archive.zip"
    )
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "tileset.json",
            json.dumps({"asset": {"version": "1.1"}, "root": {"refine": "ADD"}}),
        )
        archive.writestr(
            "terrain/layer.json",
            json.dumps({"format": "quantized-mesh-1.0", "version": "1.0"}),
        )

    operation = {
        "id": "cesium_ion_archive_download",
        "source_id": "cesium_ion_archive",
        "source_name": "Cesium ion Offline Archive",
        "output_format": "Cesium archive ZIP",
    }
    index_path, index = kmh_app._index_cesium_archive(
        package_id=package_id,
        operation=operation,
        archive_path=archive_path,
        archive_info={"id": 123, "status": "COMPLETE", "format": "ZIP"},
    )

    response = await kmh_app.query_package_cesium(package_id)
    file_response = await kmh_app.get_package_cesium_file(
        package_id,
        "cesium/archive/extracted/tileset.json",
    )

    assert index_path.exists()
    assert index["tilesets"][0]["asset_version"] == "1.1"
    assert index["terrain_layers"][0]["format"] == "quantized-mesh-1.0"
    assert response["index"]["archive_id"] == 123
    assert str(file_response.path).endswith("tileset.json")


@pytest.mark.asyncio
async def test_package_imagery_osm_and_terrain_files_are_served_to_plugin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OFFLINE_PACKAGE_ROOT", str(tmp_path / "packages"))
    package_id = "pkgdata"
    manifest = {"package_id": package_id, "package_name": package_id, "download_operations": []}
    kmh_app.PACKAGE_MANIFESTS[package_id] = manifest
    kmh_app._persist_package_manifest(package_id, manifest)
    package_dir = kmh_app._package_dir(package_id)
    imagery_index = package_dir / "imagery" / "naip" / "aws" / "naip_index.json"
    osm_index = package_dir / "vectors" / "osm" / "osm_index.json"
    terrain_tif = package_dir / "rasters" / "copernicus_dem" / "tile.tif"
    for path in (imagery_index, osm_index, terrain_tif):
        path.parent.mkdir(parents=True, exist_ok=True)
    imagery_index.write_text(json.dumps({"files": []}), encoding="utf-8")
    osm_index.write_text(json.dumps({"aoi_pbf": "vectors/osm/aoi.osm.pbf"}), encoding="utf-8")
    terrain_tif.write_bytes(b"tif")
    registry = kmh_app._empty_artifact_registry(package_id)
    registry["artifacts"].extend(
        [
            {
                "source_id": "naip",
                "artifact_type": "naip_imagery_index",
                "relative_path": imagery_index.relative_to(package_dir).as_posix(),
            },
            {
                "source_id": "osm_extract",
                "artifact_type": "osm_query_index",
                "relative_path": osm_index.relative_to(package_dir).as_posix(),
            },
            {
                "source_id": "copernicus_dem",
                "artifact_type": "copernicus_dem_cog",
                "relative_path": terrain_tif.relative_to(package_dir).as_posix(),
            },
        ]
    )
    kmh_app._save_artifact_registry(package_id, registry)

    imagery = await kmh_app.query_package_imagery(package_id)
    osm = await kmh_app.query_package_osm(package_id)
    imagery_file = await kmh_app.get_package_imagery_file(
        package_id,
        "imagery/naip/aws/naip_index.json",
    )
    osm_file = await kmh_app.get_package_osm_file(package_id, "vectors/osm/osm_index.json")
    terrain_file = await kmh_app.get_package_terrain_file(
        package_id,
        "rasters/copernicus_dem/tile.tif",
    )

    assert imagery["artifacts"][0]["artifact_type"] == "naip_imagery_index"
    assert osm["artifacts"][0]["artifact_type"] == "osm_query_index"
    assert str(imagery_file.path).endswith("naip_index.json")
    assert str(osm_file.path).endswith("osm_index.json")
    assert str(terrain_file.path).endswith("tile.tif")


def test_jetson_storage_reserve_is_reported(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class Usage:
        total = 100 * 1024 * 1024 * 1024
        used = 40 * 1024 * 1024 * 1024
        free = 60 * 1024 * 1024 * 1024

    monkeypatch.setenv("OFFLINE_PACKAGE_ROOT", str(tmp_path / "packages"))
    monkeypatch.setenv("PACKAGE_MIN_FREE_GB", "10")
    monkeypatch.setattr(kmh_app.shutil, "disk_usage", lambda _path: Usage)

    storage = kmh_app._storage_info()

    assert storage.package_root == str((tmp_path / "packages").resolve())
    assert storage.reserved_bytes == 10 * 1024 * 1024 * 1024
    assert storage.usable_bytes == 50 * 1024 * 1024 * 1024


@pytest.mark.asyncio
async def test_source_package_plan_persists_manifest_and_storage_urls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OFFLINE_PACKAGE_ROOT", str(tmp_path / "packages"))
    monkeypatch.setenv("DTED_SOURCE_DIR", str(tmp_path / "DTED"))
    monkeypatch.setenv("TERA_WINTAK_IMAGERY_DIR", str(tmp_path / "WINTAK Imagery"))
    monkeypatch.setenv("NAIP_EARTHEXPLORER_DIR", str(tmp_path / "WINTAK Imagery"))
    request = kmh_app.DownloadPlanRequest(
        source_ids=["naip", "osm_extract", "dted_earth_explorer"],
        mission_focus="terrain-routing",
        map_context=kmh_app.MapContext(
            selected_area=kmh_app.ViewBounds(
                west=-122.52,
                south=37.70,
                east=-122.35,
                north=37.84,
                center_lat=37.77,
                center_lon=-122.43,
            ),
            location_confirmed=True,
        ),
    )

    response = await kmh_app.plan_source_package(request)

    assert response.execute_url.endswith(f"/api/source-package/{response.package_id}/execute")
    assert response.status_url.endswith(f"/api/source-package/{response.package_id}/status")
    assert response.artifacts_url.endswith(f"/api/source-package/{response.package_id}/artifacts")
    assert response.estimated_bytes > 0
    assert (tmp_path / "packages" / response.package_id / "manifest.json").exists()


@pytest.mark.asyncio
async def test_package_execution_writes_jetson_artifacts_without_tokens(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OFFLINE_PACKAGE_ROOT", str(tmp_path / "packages"))
    monkeypatch.setenv("DTED_SOURCE_DIR", str(tmp_path / "DTED"))
    monkeypatch.setenv("TERA_WINTAK_IMAGERY_DIR", str(tmp_path / "WINTAK Imagery"))
    monkeypatch.setenv("NAIP_EARTHEXPLORER_DIR", str(tmp_path / "WINTAK Imagery"))
    request = kmh_app.DownloadPlanRequest(
        source_ids=["naip", "osm_extract", "dted_earth_explorer"],
        mission_focus="terrain-routing",
        map_context=kmh_app.MapContext(
            selected_area=kmh_app.ViewBounds(
                west=-122.52,
                south=37.70,
                east=-122.35,
                north=37.84,
            ),
            location_confirmed=True,
        ),
    )
    sources = kmh_app._get_source_options_by_ids(request.source_ids)
    manifest = kmh_app._build_package_manifest(
        package_id="pkgexec",
        package_name="pkgexec",
        request=request,
        sources=sources,
    )
    kmh_app.PACKAGE_MANIFESTS["pkgexec"] = manifest
    kmh_app._persist_package_manifest("pkgexec", manifest)
    kmh_app._save_package_status("pkgexec", kmh_app._initial_package_status("pkgexec", manifest))

    async def fake_execute_operation(
        _client: object,
        *,
        package_id: str,
        manifest: dict[str, object],
        operation: dict[str, object],
    ) -> list[dict[str, object]]:
        path = kmh_app._artifact_path(package_id, operation["local_artifact"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"offline artifact")
        return [
            kmh_app._artifact_record(
                package_id=package_id,
                operation=operation,
                path=path,
                artifact_type="mock_artifact",
                output_format=str(operation.get("output_format", "mock")),
            )
        ]

    monkeypatch.setattr(kmh_app, "_execute_operation", fake_execute_operation)

    await kmh_app._execute_package_job("pkgexec", manifest)

    status = kmh_app._load_package_status("pkgexec")
    registry = kmh_app._load_artifact_registry("pkgexec")
    registry_text = json.dumps(registry)

    assert status["state"] == "succeeded"
    assert registry["artifacts"]
    assert "${ESRI_ARCGIS_TOKEN}" not in registry_text


def _seed_grid_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("OFFLINE_PACKAGE_ROOT", str(tmp_path / "packages"))
    package_id = "pkggrid"
    manifest = {"package_id": package_id, "package_name": package_id, "download_operations": []}
    kmh_app.PACKAGE_MANIFESTS[package_id] = manifest
    kmh_app._persist_package_manifest(package_id, manifest)
    grid_path = kmh_app._package_dir(package_id) / "rasters" / "esri_world_elevation" / "grid.json"
    grid_path.parent.mkdir(parents=True, exist_ok=True)
    grid_path.write_text(
        json.dumps(
            {
                "elevation_grid": [[10, 11, 12], [9, 10, 14], [8, 9, 15]],
                "bbox": {"west": -122.5, "south": 37.7, "east": -122.4, "north": 37.8},
                "cell_size_m": 30,
            }
        ),
        encoding="utf-8",
    )
    registry = kmh_app._empty_artifact_registry(package_id)
    registry["artifacts"].append(
        {
            "artifact_id": "grid",
            "source_id": "esri_world_elevation",
            "source_name": "Esri World Elevation Terrain",
            "operation_id": "seed",
            "artifact_type": "elevation_grid_json",
            "format": "JSON elevation grid",
            "path": str(grid_path),
            "relative_path": grid_path.relative_to(kmh_app._package_dir(package_id)).as_posix(),
            "bytes": grid_path.stat().st_size,
            "sha256": kmh_app._sha256_file(grid_path),
            "query_interfaces": ["sample_dem(lat, lon)", "read_window(west, south, east, north)"],
            "feeds_algorithms": ["terrain_derivatives", "raster_cost_distance", "viewshed"],
            "metadata": {},
        }
    )
    kmh_app._save_artifact_registry(package_id, registry)
    return package_id


@pytest.mark.asyncio
async def test_package_terrain_query_algorithm_route_and_cot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    package_id = _seed_grid_package(tmp_path, monkeypatch)
    monkeypatch.setenv("WAYFINDER_KEY_DIR", str(tmp_path / "keys"))
    monkeypatch.setenv("WAYFINDER_HMAC_KEY", "test-only-dev-signing-key")

    sample = await kmh_app.query_package_terrain(
        package_id,
        kmh_app.TerrainQueryRequest(query_type="sample", lat=37.75, lon=-122.45),
    )
    algorithm = await kmh_app.run_package_algorithm(
        package_id,
        kmh_app.AlgorithmRequest(algorithm_id="terrain_derivatives"),
    )
    route = await kmh_app.create_package_route(
        package_id,
        kmh_app.PackageRouteRequest(
            start=kmh_app.MapPoint(lat=37.79, lon=-122.49),
            end=kmh_app.MapPoint(lat=37.71, lon=-122.41),
        ),
    )
    cot = await kmh_app.create_package_cot(
        package_id,
        kmh_app.PackageCotRequest(route_id=route["route_id"], cot_type="route"),
    )

    assert sample["elevation_m"] == 10.0
    assert "slope_degrees" in algorithm["layers"]
    assert route["route"]["geometry"]["type"] == "LineString"
    assert route["route_hash"]
    assert cot["events"][0]["signed"] is True
    assert "<wayfinder>" in cot["events"][0]["cot_xml"]
    cot_root = ET.fromstring(cot["events"][0]["cot_xml"])
    assert cot_root.attrib["type"] == "b-m-r"
    assert len(cot_root.findall("detail/link")) >= 2
    assert cot_root.find("detail/link_attr") is not None
    assert cot_root.find("detail/route") is None


def test_source_package_manifest_uses_jetson_root_osm_dted_sources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dted_dir = tmp_path / "DTED"
    imagery_dir = tmp_path / "WINTAK Imagery"
    dted_dir.mkdir()
    imagery_dir.mkdir()
    monkeypatch.setenv("DTED_SOURCE_DIR", str(dted_dir))
    monkeypatch.setenv("TERA_WINTAK_IMAGERY_DIR", str(imagery_dir))
    monkeypatch.setenv("NAIP_EARTHEXPLORER_DIR", str(imagery_dir))
    request = kmh_app.DownloadPlanRequest(
        source_ids=["naip", "osm_extract", "dted_earth_explorer"],
        mission_focus="terrain-routing",
        map_context=kmh_app.MapContext(
            selected_area=kmh_app.ViewBounds(
                west=-122.52,
                south=37.70,
                east=-122.35,
                north=37.84,
                center_lat=37.77,
                center_lon=-122.43,
            ),
            location_confirmed=True,
        ),
    )
    sources = kmh_app._get_source_options_by_ids(request.source_ids)
    manifest = kmh_app._build_package_manifest(
        package_id="pkgtest",
        package_name="pkgtest",
        request=request,
        sources=sources,
    )

    operations = {operation["id"]: operation for operation in manifest["download_operations"]}
    assert "naip_earthexplorer_geotiff_import" in operations
    assert "osm_wintak_imagery_import" in operations
    assert "dted_earthexplorer_import_convert" in operations
    assert "naip_aws_public_prefix" not in operations
    assert "osm_geofabrik_pbf" not in operations
    assert "copernicus_dem_glo30_cog" not in operations
    assert (
        operations["naip_earthexplorer_geotiff_import"]["params"]["source_dir"]
        == "${NAIP_EARTHEXPLORER_DIR}"
    )
    assert (
        operations["osm_wintak_imagery_import"]["params"]["source_dir"]
        == "${TERA_WINTAK_IMAGERY_DIR}"
    )
    assert (
        operations["dted_earthexplorer_import_convert"]["params"]["source_dir"]
        == "${DTED_SOURCE_DIR}"
    )
    assert any(
        item["id"] == "raster_cost_distance"
        for item in manifest["deterministic_algorithms"]
    )
    assert any(
        contract["artifact_type"] == "dted_geotiff_index"
        for contract in manifest["jetson_query_contracts"]
    )
    assert any(
        contract["artifact_type"] == "osm_wintak_index"
        for contract in manifest["jetson_query_contracts"]
    )


def test_web_package_workflow_shows_jetson_storage_and_server_download() -> None:
    html = kmh_app.INDEX_FILE.read_text(encoding="utf-8")
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "Jetson Storage" in html
    assert 'id="downloadToJetsonBtn"' in html
    assert "Download to Jetson" in html
    assert 'id="packageExecutionStatus"' in html
    assert 'id="packageArtifacts"' in html
    assert 'fetchJson("/api/storage")' in js
    assert "downloadPackageToJetson" in js
    assert "state.packagePlan.execute_url" in js
    assert "renderJetsonStorage(data.storage, data.estimated_bytes, data.storage_fit" in js


def test_geo_algorithms_cover_graph_raster_and_terrain_paths() -> None:
    graph = {
        "A": [("B", 1.0), ("C", 4.0)],
        "B": [("C", 1.0), ("D", 4.0)],
        "C": [("D", 1.0)],
        "D": [],
    }

    path, cost = geo_algorithms.astar(graph, "A", "D")
    assert path == ["A", "B", "C", "D"]
    assert cost == 3.0

    alternatives = geo_algorithms.yens_k_shortest_paths(graph, "A", "D", 2)
    assert alternatives[0][0] == ["A", "B", "C", "D"]
    assert len(alternatives) == 2

    elevation = [
        [14, 13, 12],
        [15, 12, 9],
        [16, 12, 8],
    ]
    terrain = geo_algorithms.derive_terrain_layers(elevation, cell_size_m=30)
    assert terrain["slope_degrees"][1][1] > 0
    assert "curvature" in terrain
    cost_surface = geo_algorithms.build_walking_cost_surface(terrain["slope_degrees"])
    result = geo_algorithms.raster_cost_distance(cost_surface, [(0, 0)])
    cell_path = geo_algorithms.backtrack_least_cost_path(result, (2, 2))
    assert cell_path[0] == (0, 0)
    assert cell_path[-1] == (2, 2)
    assert geo_algorithms.flow_accumulation_d8(elevation, cell_size_m=30)[2][2] >= 1
    assert geo_algorithms.viewshed(elevation, (0, 0), cell_size_m=30)[0][0] is True
    sectors = geo_algorithms.radial_sar_sectors(37.77, -122.43, 1000, 4)
    assert len(sectors["features"]) == 4
    probability = geo_algorithms.sar_probability_surface(3, 3, (1, 1))
    assert round(sum(sum(row) for row in probability), 6) == 1.0


def test_chat_streaming_does_not_force_scroll_when_reader_moves_up() -> None:
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "CHAT_AUTOSCROLL_THRESHOLD_PX" in js
    assert "function isChatPinnedToBottom()" in js
    assert "function maybeScrollChatToBottom" in js
    assert "const shouldFollowNewMessage = isChatPinnedToBottom();" in js
    assert "const shouldFollowStream = isChatPinnedToBottom();" in js
    assert "maybeScrollChatToBottom(shouldFollowStream);" in js
    assert js.count("els.chatLog.scrollTop = els.chatLog.scrollHeight;") == 1


def test_header_title_precedes_kicker_and_map_imports_kml_overlays() -> None:
    html = kmh_app.INDEX_FILE.read_text(encoding="utf-8")
    css = (kmh_app.STATIC_DIR / "styles.css").read_text(encoding="utf-8")
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert html.index("<h1>TERA Source Planner</h1>") < html.index(
        '<div class="eyebrow">Mission data sourcing workspace</div>'
    )
    assert 'id="importOverlayBtn"' in html
    assert 'id="overlayFileInput"' in html
    assert 'id="mapModeToggleBtn"' in html
    assert 'accept=".kml,.kmz' in html
    assert "jszip@3.10.1" in html
    assert ".file-input" in css
    assert ".map-mode-toggle" in css

    assert "overlayDataSource" in js
    assert "async function importMapOverlay" in js
    assert "sceneMode: Cesium.SceneMode.SCENE2D" in js
    assert "function setMapMode" in js
    assert "Cesium.ScreenSpaceEventType.MIDDLE_DOWN" in js
    assert "async function readOverlayFileText" in js
    assert "function parseKmlToGeoJson" in js
    assert "Cesium.GeoJsonDataSource.load" in js
    assert "function styleOverlayDataSource" in js
    assert "function loadNativeOverlayDataSource" in js
    assert "Cesium.KmlDataSource.load" in js
    assert "state.viewer.dataSources.add(dataSource)" in js
    assert "state.viewer.flyTo(state.overlayDataSource" in js
    assert 'els.mapModeToggleBtn.addEventListener("click", toggleMapMode)' in js
    assert 'els.importOverlayBtn.addEventListener("click", requestOverlayFile)' in js
    assert 'els.overlayFileInput.addEventListener("change", onOverlayFileSelected)' in js


def test_map_location_search_sets_context_and_center_grid() -> None:
    html = kmh_app.INDEX_FILE.read_text(encoding="utf-8")
    css = (kmh_app.STATIC_DIR / "styles.css").read_text(encoding="utf-8")
    js = (kmh_app.STATIC_DIR / "app.js").read_text(encoding="utf-8")
    app_source = Path(kmh_app.__file__).read_text(encoding="utf-8")
    prompt = (
        Path("prompts/local_model_prompts/imagery_sourcing_local_model_system_prompt.md")
        .read_text(encoding="utf-8")
    )

    assert 'id="locationSearchPanel"' in html
    assert 'id="locationSearchInput"' in html
    assert 'id="locationSearchSuggestions"' in html
    assert 'id="centerGridValue"' in html
    assert ".map-search-panel" in css
    assert "width: min(312px, max(240px, calc((100% - 340px) * 0.6)));" in css
    assert ".center-grid-panel" in css

    assert "LOCATION_GAZETTEER" in js
    assert "cleanLocationSearchQuery" in js
    assert "buildLocationSearchUrl" in js
    assert "fetchLocationSearchSuggestions" in js
    assert "renderLocationSearchLoading" in js
    assert "Joshua Tree National Park" in js
    assert "Cascade Range" in js
    assert "parseCoordinateQuery" in js
    assert "refreshOnlineLocationSuggestions" in js
    assert "/api/location-search" in js
    assert "score: Number.isFinite(serverScore)" in js
    assert "location-suggestion-status" in css
    assert "flyToLocationSuggestion" in js
    assert "latLonToUtm" in js
    assert "latLonToMgrs" in js
    assert "utmToMgrs" in js
    assert "MGRS " in js
    assert "MGRS_COLUMN_LETTER_SETS" in js
    assert "updateCenterGrid()" in js
    assert "location_confirmed" in js
    assert "location_focus_label" in js
    assert 'els.locationSearchForm.addEventListener("submit", onLocationSearchSubmit)' in js

    assert "location_confirmed: bool = False" in app_source
    assert '@app.get("/api/location-search"' in app_source
    assert "LOCATION_SEARCH_URL" in app_source
    assert "LOCATION_INTENT_PREFIX_RE" in app_source
    assert "_score_online_location" in app_source
    assert "GOOGLE_MAPS_API_KEY" in app_source
    assert "GOOGLE_PLACES_AUTOCOMPLETE_URL" in app_source
    assert "GOOGLE_PLACE_DETAILS_URL_BASE" in app_source
    assert "GOOGLE_PLACES_TEXT_SEARCH_URL" in app_source
    assert "_google_places_autocomplete_suggestions" in app_source
    assert "_google_place_details_suggestion" in app_source
    assert "_google_places_location_suggestions" in app_source
    assert "includeQueryPredictions" in app_source
    assert "suggestions.placePrediction.place" in app_source
    assert "X-Goog-FieldMask" in app_source
    assert "google-places" in app_source
    assert "q: str = Query(min_length=1" in app_source
    assert "parseGoogleMapsCoordinateQuery" in js
    assert "!3d" in js
    assert "!4d" in js
    assert "locationSearchDetail" in js
    assert "googleMapsSearchUrl" in js
    assert "Open Google Maps search" in js
    assert "cleanedQuery.length < 1" in js
    assert "cleanedQuery.length < 2" not in js
    assert "Planner-confirmed mission map focus" in app_source
    assert "Move the map to the mission AO" in app_source
    assert "use the map location search" in prompt


def test_source_recommendation_tolerates_rough_phrasing_and_spelling() -> None:
    recommendation = kmh_app._infer_source_recommendation(
        "Need off-line pakage near Joshu Tree for patroll to find watter and avoid steep terain.",
        None,
    )

    assert recommendation.mission_focus in {"water-access", "terrain-routing"}
    assert "osm_extract" in recommendation.required_source_ids
    assert "dted_earth_explorer" in recommendation.required_source_ids
    assert "copernicus_dem" not in recommendation.required_source_ids
    assert not any(
        source_id in recommendation.required_source_ids
        for source_id in ("usgs_3dhp", "hydrosheds", "nlcd", "esa_worldcover")
    )


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
    assert "body.is-resizing-panel" in css
    assert "user-select: none !important;" in css
    assert "touch-action: none;" in css
    assert "clearDocumentSelection" in js
    assert "event.preventDefault();" in js
    assert 'document.body.classList.add("is-resizing-panel")' in js
    assert 'document.body.classList.remove("is-resizing-panel")' in js

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
