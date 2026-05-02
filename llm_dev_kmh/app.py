from __future__ import annotations

import json
import os
from pathlib import Path
import re
from textwrap import dedent

import httpx
import structlog
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

log = structlog.get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "static" / "index.html"
STATIC_DIR = BASE_DIR / "static"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:2b")
REQUEST_TIMEOUT_S = float(os.getenv("REQUEST_TIMEOUT_S", "120"))
CESIUM_ION_TOKEN = os.getenv("CESIUM_ION_TOKEN", "")
DEFAULT_LAT = float(os.getenv("DEFAULT_LAT", "37.7749"))
DEFAULT_LON = float(os.getenv("DEFAULT_LON", "-122.4194"))
DEFAULT_HEIGHT_M = float(os.getenv("DEFAULT_HEIGHT_M", "14000"))

app = FastAPI(title="LLM Dev KMH MVP", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class PromptRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)
    system: str | None = Field(default=None, max_length=4000)
    model: str | None = Field(default=None, max_length=200)
    agent_profile: str | None = Field(default="terrain-route", max_length=80)
    map_context: "MapContext | None" = None


class PromptResponse(BaseModel):
    model: str
    response: str


class ModelsResponse(BaseModel):
    default_model: str
    models: list[str]


class RuntimeConfigResponse(BaseModel):
    cesium_ion_token: str
    default_model: str
    default_lat: float
    default_lon: float
    default_height_m: float


class MapPoint(BaseModel):
    lat: float
    lon: float
    height_m: float | None = None


class ViewBounds(BaseModel):
    west: float
    south: float
    east: float
    north: float
    center_lat: float | None = None
    center_lon: float | None = None


class MapContext(BaseModel):
    selected_point: MapPoint | None = None
    camera: MapPoint | None = None
    view_bounds: ViewBounds | None = None
    imagery_source: str | None = Field(default=None, max_length=200)
    terrain_source: str | None = Field(default=None, max_length=200)


AGENT_PROFILE_PROMPTS: dict[str, str] = {
    "terrain-route": dedent(
        """
        You are TERA's local terrain-aware routing copilot.
        Focus on route selection, slope, elevation change, cover, trails, water access,
        shelter, and terrain obstacles visible or implied by the provided map context.
        Favor concise operational recommendations grounded in the current map view.
        """
    ).strip(),
    "map-analysis": dedent(
        """
        You are TERA's local map interrogation agent.
        Explain terrain, identify likely movement corridors, water, exposure, ridgelines,
        valleys, road and trail relationships, and uncertainty in the visible area.
        Keep outputs analytical and tied to the map context.
        """
    ).strip(),
    "survival-sar": dedent(
        """
        You are TERA's survival and SAR terrain assistant.
        Prioritize water, shelter, evacuation corridors, lower-risk travel, exposure,
        communication vantage points, and emergency access in the current terrain.
        Give practical, safety-oriented recommendations.
        """
    ).strip(),
}

PROMPT_FAMILY_GUIDANCE: dict[str, str] = {
    "emergency-survival-routing": (
        "water, shelter, lower exposure, safe movement, evacuation back to safety"
    ),
    "medical-and-rescue": (
        "casualty evacuation, litter routes, ambulance access, trailheads, LZs, rescue pickup"
    ),
    "communication-and-signaling": (
        "ridgelines, high points, clearings, line-of-sight, cell or satellite signal opportunity"
    ),
    "navigation-back-to-safety": (
        "trailheads, roads, settlements, descent corridors, natural handrails, low-risk return"
    ),
    "terrain-aware-routing": (
        "slope, elevation gain, brush, wetlands, talus, avalanche, floodplain, roads and trails"
    ),
    "weather-and-environmental-risk": (
        "flash flood, wildfire, lightning, wind, heat, freezing, daylight, unstable slopes"
    ),
    "food-fire-and-sustenance": (
        "water, fuel, fishing access, edible terrain, sheltered campsites with supplies"
    ),
    "search-and-rescue-planning": (
        "travel corridors, search sectors, hasty search, dog teams, likely subject movement"
    ),
    "hiking-and-outdoor-navigation": (
        "beginner routes, bailout options, public land, scenic but safe movement, landmarks"
    ),
    "marine-river-coastal": (
        "landing points, river crossings, portages, shoreline egress, floodplain escape"
    ),
    "desert-survival": (
        "shade, wells, troughs, powerlines, dry washes, heat exposure, energy conservation"
    ),
    "winter-and-alpine": (
        "below treeline routes, low-angle slopes, hut access, avalanche avoidance, alpine descent"
    ),
    "disaster-logistics": (
        "aid delivery, civilian evacuation, convoy routing, responder staging, remote resupply"
    ),
    "multi-objective-routing": (
        "sequence water, shelter, signal, or compare fastest, safest, easiest alternatives"
    ),
    "situational-awareness": (
        "stay or move, safest direction, terrain traps, fallback routes, landmarks, hazards"
    ),
}

FAMILY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "medical-and-rescue",
        (
            "hospital",
            "clinic",
            "aid station",
            "ambulance",
            "evac",
            "evacuation",
            "litter",
            "stretcher",
            "sar",
            "rescu",
            "trailhead",
            "helicopter",
            "landing zone",
            "lz",
            "pickup",
        ),
    ),
    (
        "communication-and-signaling",
        (
            "cell",
            "signal",
            "satellite",
            "ridgeline",
            "line-of-sight",
            "radio tower",
            "communications",
            "lookout",
            "visible from the air",
            "clear sky",
        ),
    ),
    (
        "weather-and-environmental-risk",
        (
            "flood",
            "wildfire",
            "smoke",
            "lightning",
            "avalanche",
            "wind chill",
            "freezing",
            "before sunset",
            "daylight",
            "storm",
            "heat",
            "rainfall",
        ),
    ),
    (
        "food-fire-and-sustenance",
        ("edible", "berries", "fishing", "firewood", "fuel", "supplies", "forage"),
    ),
    (
        "search-and-rescue-planning",
        (
            "last known",
            "search",
            "clue",
            "dog teams",
            "drone teams",
            "search sectors",
            "probable",
            "likely travel corridors",
            "hasty search",
            "grid search",
        ),
    ),
    (
        "marine-river-coastal",
        (
            "coast",
            "shoreline",
            "beach",
            "tidal",
            "rapids",
            "waterfalls",
            "portage",
            "river crossing",
            "floodplain",
            "downstream",
        ),
    ),
    (
        "desert-survival",
        (
            "desert",
            "shade",
            "sun exposure",
            "powerline",
            "well",
            "trough",
            "dry wash",
            "sand travel",
        ),
    ),
    (
        "winter-and-alpine",
        (
            "winter",
            "alpine",
            "treeline",
            "cornice",
            "crevasse",
            "snowfield",
            "warming shelter",
            "low-angle slopes",
        ),
    ),
    (
        "disaster-logistics",
        (
            "medical supplies",
            "field clinic",
            "civilians",
            "convoy",
            "base camp",
            "staging area",
            "responders",
            "isolated community",
            "hazardous industrial",
        ),
    ),
    (
        "multi-objective-routing",
        (
            "then",
            "balances",
            "three route options",
            "fastest, safest, and easiest",
            "bailout options",
            "survival priorities",
            "sequence",
        ),
    ),
    (
        "situational-awareness",
        (
            "stay put",
            "safest direction",
            "what landmarks",
            "what hazards",
            "what route should i avoid",
            "fallback route",
            "which nearby",
        ),
    ),
    (
        "hiking-and-outdoor-navigation",
        (
            "day hike",
            "loop route",
            "beginners",
            "children",
            "older hikers",
            "public land",
            "private property",
            "scenic route",
            "map and compass",
        ),
    ),
    (
        "terrain-aware-routing",
        (
            "slope",
            "elevation gain",
            "dense forest",
            "brush",
            "wetlands",
            "bogs",
            "talus",
            "scree",
            "roads and trails",
            "night movement",
        ),
    ),
    (
        "navigation-back-to-safety",
        (
            "starting point",
            "back to",
            "trailhead",
            "maintained trail",
            "nearest road",
            "closest inhabited structure",
            "civilization",
            "handrails",
        ),
    ),
    (
        "emergency-survival-routing",
        (
            "fresh water",
            "potable water",
            "stream",
            "river",
            "lake",
            "spring",
            "snowmelt",
            "camp",
            "bivy",
            "tree cover",
            "shelter",
        ),
    ),
)

OBJECTIVE_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("fastest", "fastest"),
    ("shortest", "shortest"),
    ("safest", "safest"),
    ("easiest", "easiest"),
    ("lowest-effort", "lowest effort"),
    ("least physical effort", "lowest effort"),
    ("energy-efficient", "lowest energy"),
    ("minimize elevation gain", "minimum elevation gain"),
    ("least elevation gain", "minimum elevation gain"),
    ("minimizes travel time", "minimum travel time"),
    ("multi-stop", "multi-stop"),
    ("three route", "compare alternates"),
    ("balances", "balanced objectives"),
)

MODE_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("injured", "injured foot"),
    ("leg injury", "injured foot"),
    ("litter", "litter carry"),
    ("stretcher", "litter carry"),
    ("ambulance", "vehicle"),
    ("vehicle", "vehicle"),
    ("atv", "atv"),
    ("snowmobile", "snowmobile"),
    ("boat", "boat"),
    ("drone", "drone team"),
    ("air rescue", "air rescue support"),
    ("heavy pack", "loaded foot"),
    ("dehydrated", "dehydrated foot"),
    ("older hikers", "reduced mobility foot"),
    ("children", "group foot"),
)

TARGET_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("water", "water source"),
    ("fresh water", "water source"),
    ("shelter", "shelter"),
    ("cabin", "shelter"),
    ("hut", "shelter"),
    ("hospital", "medical facility"),
    ("clinic", "medical facility"),
    ("road", "road access"),
    ("trail", "trail access"),
    ("trailhead", "trailhead"),
    ("cell service", "communications vantage"),
    ("signal", "communications vantage"),
    ("ridge", "high ground"),
    ("high ground", "high ground"),
    ("clearing", "open clearing"),
    ("landing zone", "air evacuation site"),
    ("lz", "air evacuation site"),
    ("settlement", "settlement"),
    ("town", "settlement"),
    ("staging area", "staging area"),
)

CONSTRAINT_KEYWORDS: tuple[str, ...] = (
    "avoid steep terrain",
    "avoid cliffs",
    "avoid avalanche",
    "avoid dense brush",
    "avoid private land",
    "avoid restricted",
    "avoid flood",
    "avoid wildfire",
    "avoid river crossings",
    "avoid snowfields",
    "avoid glaciers",
    "avoid scrambling",
    "avoid exposed slopes",
    "avoid wetlands",
    "avoid talus",
    "avoid scree",
    "avoid roads",
    "stay on public land",
    "near cover",
    "below treeline",
)


def _detect_prompt_family(prompt_text: str) -> str:
    for family, keywords in FAMILY_KEYWORDS:
        if any(keyword in prompt_text for keyword in keywords):
            return family
    return "terrain-aware-routing"


def _detect_objective(prompt_text: str) -> str:
    for needle, objective in OBJECTIVE_KEYWORDS:
        if needle in prompt_text:
            return objective
    if "nearest" in prompt_text:
        return "nearest reachable target"
    return "balanced safety and practicality"


def _detect_mode(prompt_text: str) -> str:
    for needle, mode in MODE_KEYWORDS:
        if needle in prompt_text:
            return mode
    return "foot"


def _detect_target_type(prompt_text: str) -> str:
    for needle, target in TARGET_KEYWORDS:
        if needle in prompt_text:
            return target
    if "route" in prompt_text or "safest direction" in prompt_text:
        return "route or directional recommendation"
    return "terrain-aware decision support"


def _extract_constraints(prompt_text: str) -> list[str]:
    constraints = [constraint for constraint in CONSTRAINT_KEYWORDS if constraint in prompt_text]
    slope_match = re.search(r"slopes? (?:steeper than|over) (\d+) degrees?", prompt_text)
    if slope_match:
        constraints.append(f"avoid slopes over {slope_match.group(1)} degrees")
    distance_match = re.search(
        r"within (\d+(?:\.\d+)?) (mile|miles|km|kilometer|kilometers)",
        prompt_text,
    )
    if distance_match:
        constraints.append(
            f"distance bound: within {distance_match.group(1)} {distance_match.group(2)}"
        )
    return constraints or ["no explicit extra constraints detected"]


def _infer_prompt_schema(prompt: str) -> dict[str, object]:
    prompt_text = prompt.strip().lower()
    family = _detect_prompt_family(prompt_text)
    return {
        "family": family,
        "objective": _detect_objective(prompt_text),
        "mode": _detect_mode(prompt_text),
        "target_type": _detect_target_type(prompt_text),
        "constraints": _extract_constraints(prompt_text),
        "supports_alternates": any(
            term in prompt_text
            for term in ("three routes", "alternate", "alternates", "fastest, safest, and easiest")
        ),
        "action_ready": any(
            term in prompt_text
            for term in ("find route", "route me", "evacuation route", "plan", "generate")
        ),
    }


def _format_point(label: str, point: MapPoint | None) -> str:
    if point is None:
        return f"- {label}: unavailable"
    height = f", height {point.height_m:.1f} m" if point.height_m is not None else ""
    return f"- {label}: lat {point.lat:.6f}, lon {point.lon:.6f}{height}"


def _format_view_bounds(bounds: ViewBounds | None) -> str:
    if bounds is None:
        return "- Visible map bounds: unavailable"
    center = ""
    if bounds.center_lat is not None and bounds.center_lon is not None:
        center = f"; center lat {bounds.center_lat:.6f}, lon {bounds.center_lon:.6f}"
    return (
        "- Visible map bounds: "
        f"west {bounds.west:.6f}, south {bounds.south:.6f}, east {bounds.east:.6f}, "
        f"north {bounds.north:.6f}{center}"
    )


def _build_system_prompt(request: PromptRequest) -> str:
    profile = (request.agent_profile or "terrain-route").strip().lower()
    profile_prompt = AGENT_PROFILE_PROMPTS.get(profile, AGENT_PROFILE_PROMPTS["terrain-route"])
    map_context = request.map_context
    prompt_schema = _infer_prompt_schema(request.prompt)
    prompt_family = str(prompt_schema["family"])
    prompt_family_guidance = PROMPT_FAMILY_GUIDANCE.get(
        prompt_family, PROMPT_FAMILY_GUIDANCE["terrain-aware-routing"]
    )
    map_lines = [
        _format_point("Selected point", map_context.selected_point if map_context else None),
        _format_point("Camera position", map_context.camera if map_context else None),
        _format_view_bounds(map_context.view_bounds if map_context else None),
        f"- Imagery source: {(map_context.imagery_source if map_context else None) or 'unknown'}",
        f"- Terrain source: {(map_context.terrain_source if map_context else None) or 'unknown'}",
    ]
    normalized_request_lines = [
        f"- Prompt family: {prompt_schema['family']}",
        f"- Family focus: {prompt_family_guidance}",
        f"- Objective: {prompt_schema['objective']}",
        f"- Mode: {prompt_schema['mode']}",
        f"- Target type: {prompt_schema['target_type']}",
        f"- Constraints: {', '.join(prompt_schema['constraints'])}",
        f"- Alternates requested: {'yes' if prompt_schema['supports_alternates'] else 'no'}",
        f"- Future deterministic action likely: {'yes' if prompt_schema['action_ready'] else 'no'}",
    ]

    base_prompt = "\n\n".join(
        [
            profile_prompt,
            (
                "Support TERA navigation, survival, SAR, field logistics, and terrain-aware "
                "routing prompts. Ground the answer in the live map context. Prefer local context "
                "over generic advice, and state uncertainty when the map does not prove a claim."
            ),
            f"Inferred request normalization:\n{chr(10).join(normalized_request_lines)}",
            f"Current map context:\n{chr(10).join(map_lines)}",
            "\n".join(
                [
                    "Rules:",
                    "- Keep the answer concise and operational.",
                    "- Mention visible terrain relationships before recommendations.",
                    "- Do not invent exact trails, water, roads, hazards, or route geometry.",
                    (
                        "- For route-like requests, give assessment, recommended action, "
                        "and future deterministic actions."
                    ),
                    "- For alternates, compare fastest, safest, and easiest when feasible.",
                    "- If map context or deterministic tools are missing, say what is needed next.",
                ]
            ),
        ]
    )

    if request.system:
        return f"{base_prompt}\n\nAdditional operator instruction:\n{request.system.strip()}"
    return base_prompt


def _build_ollama_payload(request: PromptRequest, *, stream: bool) -> tuple[str, dict[str, object]]:
    model = request.model or OLLAMA_MODEL
    payload: dict[str, object] = {
        "model": model,
        "stream": stream,
        "prompt": request.prompt,
        "system": _build_system_prompt(request),
        "keep_alive": "10m",
        "options": {
            "temperature": 0.1,
            "num_predict": 512,
        },
    }
    return model, payload


def _sse_event(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@app.get("/")
async def serve_index() -> FileResponse:
    return FileResponse(INDEX_FILE)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "ollama_base_url": OLLAMA_BASE_URL}


@app.get("/api/config", response_model=RuntimeConfigResponse)
async def runtime_config() -> RuntimeConfigResponse:
    return RuntimeConfigResponse(
        cesium_ion_token=CESIUM_ION_TOKEN,
        default_model=OLLAMA_MODEL,
        default_lat=DEFAULT_LAT,
        default_lon=DEFAULT_LON,
        default_height_m=DEFAULT_HEIGHT_M,
    )


@app.get("/api/models", response_model=ModelsResponse)
async def list_ollama_models() -> ModelsResponse:
    timeout = httpx.Timeout(30.0, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500]
        log.error(
            "ollama_tags_http_error",
            status_code=exc.response.status_code,
            body=body,
            ollama_base_url=OLLAMA_BASE_URL,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Could not list models: Ollama returned {exc.response.status_code}: {body}",
        ) from exc
    except httpx.HTTPError as exc:
        log.error("ollama_tags_connection_error", error=str(exc), ollama_base_url=OLLAMA_BASE_URL)
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not reach Ollama to list models. Confirm it is running and that "
                f"OLLAMA_BASE_URL={OLLAMA_BASE_URL} is reachable."
            ),
        ) from exc

    data = response.json()
    models = [
        str(model.get("name", "")).strip()
        for model in data.get("models", [])
        if str(model.get("name", "")).strip()
    ]
    return ModelsResponse(default_model=OLLAMA_MODEL, models=models)


@app.post("/api/prompt", response_model=PromptResponse)
async def prompt_ollama(request: PromptRequest) -> PromptResponse:
    model, payload = _build_ollama_payload(request, stream=False)

    timeout = httpx.Timeout(REQUEST_TIMEOUT_S, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500]
        log.error(
            "ollama_http_error",
            status_code=exc.response.status_code,
            body=body,
            ollama_base_url=OLLAMA_BASE_URL,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Ollama returned {exc.response.status_code}: {body}",
        ) from exc
    except httpx.HTTPError as exc:
        log.error("ollama_connection_error", error=str(exc), ollama_base_url=OLLAMA_BASE_URL)
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not reach Ollama. Confirm it is running and that "
                f"OLLAMA_BASE_URL={OLLAMA_BASE_URL} is reachable from the container."
            ),
        ) from exc

    data = response.json()
    text = str(data.get("response", "")).strip()
    if not text:
        raise HTTPException(status_code=502, detail="Ollama returned an empty response.")

    return PromptResponse(model=model, response=text)
@app.post("/api/prompt/stream")
async def prompt_ollama_stream(request: PromptRequest) -> StreamingResponse:
    model, payload = _build_ollama_payload(request, stream=True)
    timeout = httpx.Timeout(REQUEST_TIMEOUT_S, connect=10.0)

    async def event_stream():
        yield _sse_event({"type": "start", "model": model})
        yield _sse_event(
            {"type": "status", "detail": "Waiting for local model tokens", "model": model}
        )
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST", f"{OLLAMA_BASE_URL}/api/generate", json=payload
                ) as response:
                    if response.status_code >= 400:
                        body = (await response.aread()).decode("utf-8", errors="replace")[:500]
                        log.error(
                            "ollama_stream_http_error",
                            status_code=response.status_code,
                            body=body,
                            ollama_base_url=OLLAMA_BASE_URL,
                        )
                        yield _sse_event(
                            {
                                "type": "error",
                                "detail": f"Ollama returned {response.status_code}: {body}",
                                "model": model,
                            }
                        )
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        text = str(chunk.get("response", ""))
                        if text:
                            yield _sse_event({"type": "token", "text": text, "model": model})

                        if chunk.get("done"):
                            yield _sse_event({"type": "done", "model": model})
                            return
        except httpx.HTTPError as exc:
            log.error(
                "ollama_stream_connection_error",
                error=str(exc),
                ollama_base_url=OLLAMA_BASE_URL,
            )
            yield _sse_event(
                {
                    "type": "error",
                    "detail": (
                        "Could not reach Ollama. Confirm it is running and that "
                        f"OLLAMA_BASE_URL={OLLAMA_BASE_URL} is reachable."
                    ),
                    "model": model,
                }
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
