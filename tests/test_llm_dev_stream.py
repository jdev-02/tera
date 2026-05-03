from __future__ import annotations

import json
import os
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


@pytest.mark.asyncio
async def test_prompt_stream_can_use_claude_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeAsyncClient.response = _ClaudeResponse()
    monkeypatch.setattr(kmh_app.httpx, "AsyncClient", _FakeAsyncClient)

    response = await kmh_app.prompt_ollama_stream(
        kmh_app.PromptRequest(
            prompt="Recommend sources.",
            llm_provider="claude",
            cloud_model="Claude Sonnet 4.6",
            cloud_api_key="sk-ant-test",
        )
    )

    body = await _collect_stream(response)

    assert '"provider": "claude"' in body
    assert "Waiting for Claude API response" in body
    assert "Claude source recommendation." in body
    assert '"type": "done"' in body


@pytest.mark.asyncio
async def test_prompt_stream_reports_missing_claude_key() -> None:
    response = await kmh_app.prompt_ollama_stream(
        kmh_app.PromptRequest(
            prompt="Recommend sources.",
            llm_provider="claude",
            cloud_model="claude-sonnet-4-6",
        )
    )

    body = await _collect_stream(response)

    assert '"type": "error"' in body
    assert "Claude API key required" in body


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
        'id="providerSelect"',
        'id="topModelSelect"',
        'id="claudeModelSelect"',
        'id="claudeApiKeyInput"',
        "Claude API",
        "claude-sonnet-4-6",
        "Claude Sonnet 4.6",
    ]:
        assert token in html

    for token in [
        ".top-provider-shell",
        ".chip-button",
        ".provider-menu",
        ".provider-actions",
    ]:
        assert token in css

    for token in [
        "teraLlmProvider",
        "teraClaudeApiKey",
        "serverClaudeKeyAvailable",
        "anthropic_api_key_configured",
        "applyProviderSelection",
        "void loadModels();",
        "Detected local model:",
        "llm_provider",
        "cloud_model",
        "cloud_api_key",
        "Claude API key required",
    ]:
        assert token in js

    for token in [
        "ANTHROPIC_API_URL",
        "ANTHROPIC_VERSION",
        "CLAUDE_MODEL",
        "CLAUDE_MODEL_ALIASES",
        "claude_default_model",
        "anthropic_api_key_configured",
        "_normalize_claude_model",
        "_select_ollama_default_model",
        "Auto-detected installed Gemma model",
        "_post_claude_message",
        "_extract_claude_response_text",
    ]:
        assert token in app_source


def test_claude_model_labels_normalize_to_current_sonnet() -> None:
    assert kmh_app._normalize_claude_model("Claude Sonnet 4.6") == "claude-sonnet-4-6"
    assert kmh_app._normalize_claude_model("claude-sonnet-4.6") == "claude-sonnet-4-6"
    assert kmh_app._normalize_claude_model("claude-sonnet-4-20250514") == "claude-sonnet-4-6"


def test_local_model_detection_prefers_installed_gemma_alias() -> None:
    models = [
        "hf.co/unsloth/gemma-4-E4B-it-GGUF:UD-Q4_K_XL",
        "gemma4:e4b",
        "gemma3:4b",
    ]

    assert kmh_app._select_ollama_default_model(models) == "gemma4:e4b"


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

    assert 'article.className = "source-item compact-source-item";' in js
    assert 'article.title = `${source.category} | ${formatSourceStatus(source)}`;' in js
    assert 'purpose.className = "source-purpose"' not in js
    assert 'meta.className = "source-meta"' not in js

    assert "--text-base: 12px;" in css
    assert "max-height: min(18vh, 180px);" in css
    assert "grid-template-columns: auto minmax(0, 1fr);" in css
    assert "min-height: 76px;" in css


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

    assert "streamAssistantProvider" in js
    assert "resolveLocalModelForFallback" in js
    assert "Trying local model fallback" in js
    assert "Claude request failed. Check key, model access, or network." in js
    assert "deterministic planner response" in js
    assert "Model providers unavailable; deterministic planner response shown." in js
    assert 'provider === "ollama" && !state.localModelAvailable' not in js
    assert "Claude failed; trying local Ollama fallback" not in js
    assert "Claude key missing; trying local Ollama fallback" not in js
    assert "local fallback after Claude failure" not in js
    assert "Model providers unavailable; deterministic advisor response shown (" not in js

    claude_attempt = js.index('provider: "claude"')
    local_attempt = js.index('provider: "ollama"')
    deterministic = js.index("deterministic planner response")

    assert claude_attempt < local_attempt < deterministic


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
    assert "elevation_samples" in source.derived_layers
    assert "esri_world_elevation" in js
    assert "Esri World Elevation Terrain" in js
    assert "queryable-online" in js
    assert "download-required" in js
    assert "Esri World Elevation Terrain is a queryable online fallback" in prompt

    recommendation = kmh_app._infer_source_recommendation(
        "Need a terrain route that avoids steep exposed terrain.",
        None,
    )
    assert "esri_world_elevation" in recommendation.required_source_ids
    assert "esri_world_elevation" in recommendation.selected_source_ids


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
    assert "esri_world_elevation" in recommendation.required_source_ids
    assert any(
        source_id in recommendation.required_source_ids
        for source_id in ("usgs_3dep", "copernicus_dem")
    )
    assert any(
        source_id in recommendation.required_source_ids
        for source_id in ("usgs_3dhp", "hydrosheds")
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
