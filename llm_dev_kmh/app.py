from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
from io import BytesIO
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from datetime import datetime, timedelta, timezone
from pathlib import Path
from textwrap import dedent
from typing import Any, Iterable, Literal
from urllib.parse import quote, urljoin
from uuid import uuid4

import httpx
import structlog
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from llm_dev_kmh.geo_algorithms import algorithm_catalog

log = structlog.get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent
PROMPT_DIR = BASE_DIR.parent / "prompts" / "local_model_prompts"
IMAGERY_SOURCING_PROMPT_FILE = (
    PROMPT_DIR / "imagery_sourcing_local_model_system_prompt.md"
)
INDEX_FILE = BASE_DIR / "static" / "index.html"
STATIC_DIR = BASE_DIR / "static"
DEFAULT_OFFLINE_PACKAGE_ROOT = BASE_DIR / "offline_packages"
ESRI_TILE_EXPORT_POLL_INTERVAL_S = float(os.getenv("ESRI_TILE_EXPORT_POLL_INTERVAL_S", "3"))
ESRI_TILE_EXPORT_MAX_POLLS = int(os.getenv("ESRI_TILE_EXPORT_MAX_POLLS", "120"))
CESIUM_ARCHIVE_POLL_INTERVAL_S = float(os.getenv("CESIUM_ARCHIVE_POLL_INTERVAL_S", "3"))
CESIUM_ARCHIVE_MAX_POLLS = int(os.getenv("CESIUM_ARCHIVE_MAX_POLLS", "240"))


def _load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, separator, value = line.partition("=")
        if not separator:
            continue
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue
        if key in os.environ:
            continue
        value = value.strip()
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {'"', "'"}
        ):
            value = value[1:-1]
        os.environ[key] = value


_load_dotenv_file(BASE_DIR.parent / ".env")
_load_dotenv_file(BASE_DIR.parent / ".env.local")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
ANTHROPIC_API_URL = os.getenv(
    "ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages"
)
ANTHROPIC_MODELS_URL = os.getenv(
    "ANTHROPIC_MODELS_URL", "https://api.anthropic.com/v1/models"
)
ANTHROPIC_VERSION = os.getenv("ANTHROPIC_VERSION", "2023-06-01")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
CLAUDE_MODEL_ALIASES = {
    "claude-sonnet-4-6": "claude-sonnet-4-6",
    "claude-sonnet-4.6": "claude-sonnet-4-6",
    "claude sonnet 4.6": "claude-sonnet-4-6",
    "sonnet 4.6": "claude-sonnet-4-6",
    "claude-sonnet-4-20250514": "claude-sonnet-4-20250514",
    "claude-sonnet-4-0": "claude-sonnet-4-20250514",
    "claude-sonnet-4": "claude-sonnet-4-20250514",
    "claude sonnet 4": "claude-sonnet-4-20250514",
    "claude-opus-4-1": "claude-opus-4-1-20250805",
    "claude opus 4.1": "claude-opus-4-1-20250805",
    "opus 4.1": "claude-opus-4-1-20250805",
    "claude-opus-4-7": "claude-opus-4-1-20250805",
    "claude opus 4.7": "claude-opus-4-1-20250805",
    "opus 4.7": "claude-opus-4-1-20250805",
    "claude-opus-4": "claude-opus-4-20250514",
    "claude opus 4": "claude-opus-4-20250514",
    "opus 4": "claude-opus-4-20250514",
    "claude-opus-4-20250514": "claude-opus-4-20250514",
    "claude-opus-4-1-20250805": "claude-opus-4-1-20250805",
    "claude-haiku-4-5": "claude-3-5-haiku-20241022",
    "claude-haiku-4.5": "claude-3-5-haiku-20241022",
    "claude haiku 4.5": "claude-3-5-haiku-20241022",
    "claude-haiku-4-5-20251001": "claude-3-5-haiku-20241022",
    "claude-haiku-3-5": "claude-3-5-haiku-20241022",
    "claude-3-7-sonnet-20250219": "claude-3-7-sonnet-20250219",
    "claude-3-5-haiku-20241022": "claude-3-5-haiku-20241022",
}
CLAUDE_MODEL_FALLBACKS = (
    "claude-sonnet-4-6",
    "claude-sonnet-4-20250514",
    "claude-opus-4-1-20250805",
    "claude-opus-4-20250514",
    "claude-3-7-sonnet-20250219",
    "claude-3-5-haiku-20241022",
)
REQUEST_TIMEOUT_S = float(os.getenv("REQUEST_TIMEOUT_S", "120"))
LOCATION_SEARCH_TIMEOUT_S = float(os.getenv("LOCATION_SEARCH_TIMEOUT_S", "4"))
LOCATION_SEARCH_URL = os.getenv(
    "LOCATION_SEARCH_URL", "https://nominatim.openstreetmap.org/search"
)
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
GOOGLE_PLACES_AUTOCOMPLETE_URL = os.getenv(
    "GOOGLE_PLACES_AUTOCOMPLETE_URL",
    "https://places.googleapis.com/v1/places:autocomplete",
)
GOOGLE_PLACE_DETAILS_URL_BASE = os.getenv(
    "GOOGLE_PLACE_DETAILS_URL_BASE",
    "https://places.googleapis.com/v1",
)
GOOGLE_PLACES_TEXT_SEARCH_URL = os.getenv(
    "GOOGLE_PLACES_TEXT_SEARCH_URL",
    "https://places.googleapis.com/v1/places:searchText",
)
LOCATION_INTENT_PREFIX_RE = re.compile(
    r"^(?:go to|goto|navigate to|take me to|move map to|move to|search for|"
    r"find|show me|zoom to|center on|focus on|look up|open)\s+",
    re.IGNORECASE,
)
GOOGLE_MAPS_COORD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"!3d(?P<lat>[+-]?\d+(?:\.\d+)?)!4d(?P<lon>[+-]?\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"@(?P<lat>[+-]?\d+(?:\.\d+)?),(?P<lon>[+-]?\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"[?&](?:q|ll|center)=(?P<lat>[+-]?\d+(?:\.\d+)?),(?P<lon>[+-]?\d+(?:\.\d+)?)", re.IGNORECASE),
)
CESIUM_ION_TOKEN = (
    os.getenv("CESIUM_ION_TOKEN")
    or os.getenv("CESIUM_TOKEN")
    or os.getenv("CESIUM_ACCESS_TOKEN")
    or os.getenv("CESIUM_ION_ACCESS_TOKEN")
    or ""
).strip()
ESRI_TOKEN_CONFIGURED = bool(
    (
        os.getenv("ESRI_ARCGIS_TOKEN")
        or os.getenv("ARCGIS_TOKEN")
        or os.getenv("ESRI_ACCESS_TOKEN")
        or ""
    ).strip()
)
DEFAULT_CENTER_MGRS = "11S KC 79790 48252"
DEFAULT_LAT = float(os.getenv("DEFAULT_LAT", "38.35537339313087"))
DEFAULT_LON = float(os.getenv("DEFAULT_LON", "-119.52018528165966"))
DEFAULT_HEIGHT_M = float(os.getenv("DEFAULT_HEIGHT_M", "14000"))
TERA_ATAK_MODEL = os.getenv("TERA_ATAK_MODEL", "gemma3:4b")
TERA_ATAK_AGENT_PROFILE = os.getenv("TERA_ATAK_AGENT_PROFILE", "tera-atak-live")
TERA_ATAK_DEVICE_URL = os.getenv("TERA_ATAK_DEVICE_URL", "").strip()
TERA_ATAK_ACTIVATE_COMMAND = os.getenv("TERA_ATAK_AGENT_COMMAND", "").strip()
TERA_ATAK_OLLAMA_KEEP_ALIVE = os.getenv("TERA_ATAK_OLLAMA_KEEP_ALIVE", "30m")
TERA_ATAK_WARMUP_TIMEOUT_S = float(os.getenv("TERA_ATAK_WARMUP_TIMEOUT_S", "20"))
TERA_ATAK_READY_MESSAGE = os.getenv(
    "TERA_ATAK_READY_MESSAGE",
    "TERA Agent ready. Send your traffic.",
).strip() or "TERA Agent ready. Send your traffic."
TERA_PUBLIC_BASE_URL = os.getenv("TERA_PUBLIC_BASE_URL", "").strip().rstrip("/")
TERA_JETSON_IP = os.getenv("TERA_JETSON_IP", "").strip()
ACTIVE_OLLAMA_BASE_URL: str | None = None
ACTIVE_OLLAMA_MODEL: str | None = None
ACTIVE_CLAUDE_MODELS: list[str] | None = None
JETSON_ATAK_PROCESS: subprocess.Popen[bytes] | None = None
JETSON_ATAK_MODE: dict[str, Any] = {
    "active": False,
    "status": "idle",
    "detail": "ATAK local agent mode is idle.",
    "model": TERA_ATAK_MODEL,
    "provider": "ollama",
    "agent_profile": TERA_ATAK_AGENT_PROFILE,
    "atak_device_url": TERA_ATAK_DEVICE_URL or None,
    "ollama_base_url": None,
    "ollama_ready": False,
    "jetson_ip": TERA_JETSON_IP or None,
    "plugin_endpoint": None,
    "activated_at": None,
}

app = FastAPI(title="TERA Source Planner", version="0.2.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class SourceContext(BaseModel):
    mission_focus: str | None = Field(default=None, max_length=120)
    mission_text: str | None = Field(default=None, max_length=2000)
    selected_source_ids: list[str] = Field(default_factory=list)
    selected_source_names: list[str] = Field(default_factory=list)
    required_source_ids: list[str] = Field(default_factory=list)
    optional_source_ids: list[str] = Field(default_factory=list)
    clarifying_questions: list[str] = Field(default_factory=list)
    package_summary: str | None = Field(default=None, max_length=2000)


class PromptRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)
    system: str | None = Field(default=None, max_length=4000)
    model: str | None = Field(default=None, max_length=200)
    llm_provider: str | None = Field(default="auto", max_length=40)
    cloud_model: str | None = Field(default=None, max_length=200)
    cloud_api_key: str | None = Field(default=None, max_length=500)
    agent_profile: str | None = Field(default="imagery-sourcing", max_length=80)
    map_context: "MapContext | None" = None
    source_context: SourceContext | None = None


class ModelsResponse(BaseModel):
    default_model: str
    models: list[str]
    online: bool = True
    base_url: str | None = None
    detail: str | None = None


class RuntimeConfigResponse(BaseModel):
    cesium_ion_token: str
    esri_token_configured: bool
    default_model: str
    default_provider: str
    claude_default_model: str
    anthropic_api_key_configured: bool
    default_lat: float
    default_lon: float
    default_height_m: float


class JetsonAtakActivateRequest(BaseModel):
    model: str | None = Field(default=None, max_length=200)
    atak_device_url: str | None = Field(default=None, max_length=500)
    agent_profile: str | None = Field(default=None, max_length=80)


class JetsonAtakMirrorEvent(BaseModel):
    id: str
    timestamp: str
    source: str
    role: str
    text: str
    model: str | None = None
    provider: str | None = None
    direction: str | None = None
    client_location: "MapPoint | None" = None
    view_bounds: "ViewBounds | None" = None
    query_context: dict[str, Any] = Field(default_factory=dict)
    tak_cot_summary: dict[str, Any] = Field(default_factory=dict)


class JetsonAtakModeResponse(BaseModel):
    active: bool
    status: str
    detail: str
    model: str
    provider: str
    agent_profile: str
    atak_device_url: str | None = None
    ollama_base_url: str | None = None
    ollama_ready: bool = False
    jetson_ip: str | None = None
    plugin_endpoint: str | None = None
    mirror_url: str
    events: list[JetsonAtakMirrorEvent] = Field(default_factory=list)


class LocationSuggestion(BaseModel):
    name: str
    detail: str = ""
    lat: float
    lon: float
    height_m: float = 12000
    source: str
    score: float = 0


class LocationSearchResponse(BaseModel):
    query: str
    suggestions: list[LocationSuggestion]
    online: bool
    detail: str | None = None


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
    selected_area: ViewBounds | None = None
    client_location: MapPoint | None = None
    camera: MapPoint | None = None
    view_bounds: ViewBounds | None = None
    imagery_source: str | None = Field(default=None, max_length=200)
    terrain_source: str | None = Field(default=None, max_length=200)
    location_focus_label: str | None = Field(default=None, max_length=200)
    location_focus_source: str | None = Field(default=None, max_length=80)
    location_confirmed: bool = False
    tera_active_items: list[dict[str, Any]] = Field(default_factory=list)


class TakCotCheckpoint(BaseModel):
    uid: str
    label: str
    lat: float
    lon: float


class TakCotItem(BaseModel):
    uid: str
    item_type: Literal["route", "point"]
    cot_type: str
    title: str
    lat: float | None = None
    lon: float | None = None
    coordinates: list[list[float]] = Field(default_factory=list)
    checkpoints: list[TakCotCheckpoint] = Field(default_factory=list)
    cot_xml: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class TakCotFilePackage(BaseModel):
    file_name: str
    format: Literal["kmz"] = "kmz"
    mime_type: str = "application/vnd.google-earth.kmz"
    encoding: Literal["base64"] = "base64"
    content_b64: str
    size_bytes: int
    sha256: str
    target_folder: str = "/sdcard/fromTERA"
    target_path: str
    kml_entry: str = "doc.kml"
    item_count: int = 0


class TakCotPayload(BaseModel):
    replace_existing: bool = True
    collection_uid: str | None = None
    summary: str = ""
    algorithm: str = ""
    items: list[TakCotItem] = Field(default_factory=list)
    package: TakCotFilePackage | None = None


class PromptResponse(BaseModel):
    model: str
    response: str
    provider: str | None = None
    fallbacks: list[str] = Field(default_factory=list)
    tak_cot: TakCotPayload = Field(default_factory=TakCotPayload)


class SourceDownloadMethod(BaseModel):
    id: str
    label: str
    endpoint: str
    method: str = "GET"
    output_format: str
    local_artifact_template: str
    params: dict[str, object] = Field(default_factory=dict)
    requires_token_env: str | None = None
    requires_account: bool = False
    terms_url: str | None = None
    notes: str = ""


class JetsonQueryFormat(BaseModel):
    artifact_type: str
    local_path_template: str
    query_interfaces: list[str]
    feeds_algorithms: list[str]
    notes: str = ""


class SourceOption(BaseModel):
    id: str
    name: str
    provider: str
    category: str
    purpose: str
    useful_for: list[str]
    analysis_role: str
    stream_status: str
    download_status: str
    stream_layer: str | None = None
    required_for: list[str] = Field(default_factory=list)
    recommended_for: list[str] = Field(default_factory=list)
    derived_layers: list[str] = Field(default_factory=list)
    source_url: str | None = None
    license_or_terms: str | None = None
    download_methods: list[SourceDownloadMethod] = Field(default_factory=list)
    jetson_query_formats: list[JetsonQueryFormat] = Field(default_factory=list)
    notes: str = ""


class SourceCatalogResponse(BaseModel):
    primary_streams: list[str]
    sources: list[SourceOption]


class SourceRecommendationRequest(BaseModel):
    mission_text: str = Field(min_length=1, max_length=12000)
    map_context: MapContext | None = None


class SourceRecommendationResponse(BaseModel):
    mission_focus: str
    mission_summary: str
    required_source_ids: list[str]
    optional_source_ids: list[str]
    selected_source_ids: list[str]
    sources: list[SourceOption]
    clarifying_questions: list[str]
    rationale: list[str]
    package_name_suggestion: str


class DownloadPlanRequest(BaseModel):
    source_ids: list[str] = Field(default_factory=list)
    mission_focus: str = Field(default="terrain-routing", max_length=120)
    map_context: MapContext | None = None
    package_name: str | None = Field(default=None, max_length=120)


class StorageInfoResponse(BaseModel):
    package_root: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    reserved_bytes: int
    usable_bytes: int
    existing_package_bytes: int


class DownloadPlanResponse(BaseModel):
    package_id: str
    package_name: str
    mission_focus: str
    sources: list[SourceOption]
    manifest: dict[str, object]
    warnings: list[str]
    download_url: str
    execute_url: str
    status_url: str
    artifacts_url: str
    estimated_bytes: int
    storage_fit: bool
    storage: StorageInfoResponse
    storage_warning: str | None = None


class PackageExecuteResponse(BaseModel):
    package_id: str
    state: str
    status_url: str
    artifacts_url: str
    storage: StorageInfoResponse
    message: str


class TerrainQueryRequest(BaseModel):
    query_type: Literal["sample", "window", "summary"] = "sample"
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    bbox: ViewBounds | None = None
    max_cells: int = Field(default=10000, ge=1, le=250000)


class AlgorithmRequest(BaseModel):
    algorithm_id: str = Field(min_length=1, max_length=80)
    parameters: dict[str, Any] = Field(default_factory=dict)


class PackageRouteRequest(BaseModel):
    start: MapPoint
    end: MapPoint
    profile: str = Field(default="foot_covered", max_length=80)
    avoid: list[str] = Field(default_factory=list)
    mission_type: str = Field(default="terrain_route", max_length=80)


class PackageCotRequest(BaseModel):
    route_id: str | None = Field(default=None, max_length=120)
    route: dict[str, Any] | None = None
    waypoints: list[MapPoint] = Field(default_factory=list)
    cot_type: Literal["route", "track"] = "route"
    mission_type: str = Field(default="terrain_route", max_length=80)
    rationale: str = Field(default="TERA generated route.", max_length=1000)


def _extract_prompt_code_block(markdown: str) -> str:
    match = re.search(r"```(?:\w+)?\n(?P<body>[\s\S]*?)\n```", markdown)
    if match:
        return match.group("body").strip()
    return markdown.strip()


def _load_imagery_sourcing_prompt() -> str:
    fallback = dedent(
        """
        You are TERA's local imagery and geospatial data sourcing assistant.
        Advise an intelligence planner which streamable and downloadable
        geospatial sources are required, optional, or unnecessary for an offline
        mission data package. Separate visual basemaps from analysis-grade
        server-side datasets, and explain the purpose of each source.
        """
    ).strip()

    try:
        return _extract_prompt_code_block(
            IMAGERY_SOURCING_PROMPT_FILE.read_text(encoding="utf-8")
        )
    except OSError:
        return fallback


ESRI_TERMS_URL = "https://www.esri.com/en-us/legal/terms/full-master-agreement"
ESRI_WORLD_IMAGERY_EXPORT_URL = (
    "https://tiledbasemaps.arcgis.com/arcgis/rest/services/World_Imagery/MapServer"
)
ESRI_WORLD_ELEVATION_TERRAIN_URL = (
    "https://elevation.arcgis.com/arcgis/rest/services/WorldElevation/Terrain/ImageServer"
)
EARTH_SEARCH_STAC_SEARCH_URL = "https://earth-search.aws.element84.com/v1/search"
CESIUM_ION_ARCHIVES_URL = "https://api.cesium.com/v1/archives"
CESIUM_ION_ARCHIVE_INFO_URL = "https://api.cesium.com/v1/archives/{archive_id}"
CESIUM_ION_ARCHIVE_DOWNLOAD_URL = "https://api.cesium.com/v1/archives/{archive_id}/download"
NAIP_AWS_BUCKET_URL_TEMPLATE = "https://{bucket}.s3.amazonaws.com"
NAIP_AWS_DEFAULT_BUCKET = "naip-analytic"
GEOFABRIK_BASE_URL = "https://download.geofabrik.de"
COPERNICUS_DEM_30M_BASE_URL = "https://copernicus-dem-30m.s3.amazonaws.com"
USGS_EARTHEXPLORER_URL = "https://earthexplorer.usgs.gov"
USGS_IMAGERY_ONLY_TILE_URL = (
    "https://basemap.nationalmap.gov/ArcGIS/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"
)
NRL_NAIP_TILE_URL = (
    "https://geoint.nrlssc.navy.mil/nrltileserver/wmts2?"
    "SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=NAIP&STYLE=_null&"
    "TILEMATRIXSET=GoogleMapsCompatible&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&"
    "FORMAT=image%2Fpng&WIDTH=256&HEIGHT=256"
)


SOURCE_CATALOG: list[SourceOption] = [
    SourceOption(
        id="esri_world_imagery",
        name="Esri World Imagery",
        provider="Esri ArcGIS Online",
        category="imagery",
        purpose=(
            "Optional visual imagery stream for AO inspection when an Esri account is "
            "available."
        ),
        useful_for=[
            "visual AO verification",
            "roads and tracks visible in imagery",
            "buildings and clearings",
            "vegetation and water body sanity checks",
        ],
        analysis_role=(
            "Display-only fallback. Do not select for downloads unless the Jetson has "
            "an ArcGIS token; use Sentinel-2 COGs or NAIP/open imagery for free offline files."
        ),
        stream_status="streamable",
        download_status="export-tiles-with-account",
        stream_layer="esri",
        recommended_for=["licensed-imagery-preview"],
        derived_layers=["cached_esri_imagery_tiles", "visual_aoi_reference"],
        source_url=ESRI_WORLD_IMAGERY_EXPORT_URL,
        license_or_terms=(
            "Esri World Imagery for Export requires an ArcGIS organizational or "
            "developer account and must be used under Esri terms."
        ),
        download_methods=[
            SourceDownloadMethod(
                id="esri_world_imagery_export_tiles",
                label="ArcGIS Export Tiles job",
                endpoint=f"{ESRI_WORLD_IMAGERY_EXPORT_URL}/exportTiles",
                method="POST",
                output_format="TPKX tile package",
                local_artifact_template=(
                    "offline_packages/{package_id}/tiles/esri_world_imagery/world_imagery.tpkx"
                ),
                params={
                    "tilePackage": "true",
                    "storageFormatType": "esriMapCacheStorageModeCompactV2",
                    "exportBy": "LevelID",
                    "levels": "{imagery_level_range}",
                    "exportExtent": "{aoi_wgs84_json}",
                    "optimizeTilesForSize": "true",
                    "compressionQuality": 75,
                    "f": "json",
                    "token": "${ESRI_ARCGIS_TOKEN}",
                },
                requires_token_env="ESRI_ARCGIS_TOKEN",
                requires_account=True,
                terms_url=ESRI_TERMS_URL,
                notes=(
                    "Use the World Imagery for Export service rather than scraping "
                    "individual stream tiles. Keep exports under Esri service limits."
                ),
            )
        ],
        jetson_query_formats=[
            JetsonQueryFormat(
                artifact_type="esri_tpkx_imagery_package",
                local_path_template=(
                    "offline_packages/{package_id}/tiles/esri_world_imagery/world_imagery.tpkx"
                ),
                query_interfaces=[
                    "package_metadata()",
                    "tile_package_bounds()",
                    "imagery_metadata_at(lat, lon)",
                ],
                feeds_algorithms=["visual_aoi_reference", "operator_route_review"],
                notes=(
                    "RGB basemap tiles are queryable for display and human sanity checks; "
                    "do not use them as the sole source for slope, hydrology, or graph routing."
                ),
            )
        ],
        notes=(
            "Not selected by default because this workflow only has a Cesium token. "
            "Keep it as an optional licensed source."
        ),
    ),
    SourceOption(
        id="cesium_world_imagery",
        name="Cesium World Imagery",
        provider="Cesium ion",
        category="imagery",
        purpose="Token-backed global imagery stream for Cesium preview using the token available on this Jetson.",
        useful_for=["3D mission preview", "route visualization backdrop", "AO briefing"],
        analysis_role=(
            "Primary stream/display imagery in the web app. It is not treated as the "
            "free downloadable analysis source; Sentinel-2 COGs fill that role."
        ),
        stream_status="streamable-with-token",
        download_status="stream-only-no-offline-copy",
        stream_layer="ion-satellite",
        recommended_for=["imagery-preview", "terrain-routing", "water-access", "sar-planning", "evacuation"],
        derived_layers=["preview_only_imagery_stream"],
        notes=(
            "Use for online preview with CESIUM_ION_TOKEN only. Do not download or "
            "cache Cesium ion data into the Jetson package unless a Cesium license "
            "explicitly grants offline clips/archives."
        ),
    ),
    SourceOption(
        id="cesium_ion_archive",
        name="Cesium ion Offline Archive",
        provider="Cesium ion",
        category="imagery-terrain-archive",
        purpose=(
            "Licensed/user-owned Cesium ion archive or AO clip downloaded to the "
            "Jetson for local preview, tile serving, and archive metadata queries."
        ),
        useful_for=[
            "local Cesium preview",
            "3D Tiles archive import",
            "offline imagery/terrain clip validation",
            "operator route review",
        ],
        analysis_role=(
            "Download an already-created Cesium archive by id, or create an AO "
            "clip from configured ion asset ids, then extract and index the files "
            "under the Jetson package root. This is the only Cesium download path; "
            "it does not scrape World Imagery or World Terrain stream tiles."
        ),
        stream_status="not-streamed",
        download_status="download-required",
        required_for=[],
        recommended_for=["imagery-preview", "terrain-routing", "signal-planning"],
        derived_layers=[
            "cesium_archive_zip",
            "cesium_tileset_index",
            "cesium_layer_json",
            "local_cesium_file_server",
        ],
        source_url=CESIUM_ION_ARCHIVES_URL,
        license_or_terms=(
            "Requires a Cesium ion token and an archive/export or clippable "
            "user-owned asset that is permitted for offline use."
        ),
        download_methods=[
            SourceDownloadMethod(
                id="cesium_ion_archive_download",
                label="Cesium ion archive download",
                endpoint=CESIUM_ION_ARCHIVE_DOWNLOAD_URL,
                output_format="Cesium archive ZIP",
                local_artifact_template=(
                    "offline_packages/{package_id}/cesium/archive/cesium_ion_archive.zip"
                ),
                params={
                    "archive_id": "${CESIUM_ION_ARCHIVE_ID}",
                    "token": "${CESIUM_ION_TOKEN}",
                    "extract": True,
                },
                requires_token_env="CESIUM_ION_TOKEN",
                requires_account=True,
                terms_url="https://cesium.com/learn/ion/cesium-ion-archives-and-exports/",
                notes=(
                    "Set CESIUM_ION_ARCHIVE_ID to a completed archive id. The token "
                    "is sent as an OAuth Bearer credential at download time and is "
                    "not written to the manifest or artifact registry."
                ),
            ),
            SourceDownloadMethod(
                id="cesium_ion_clip_create_download",
                label="Cesium ion AO clip create and download",
                endpoint=CESIUM_ION_ARCHIVES_URL,
                method="POST",
                output_format="Cesium 3D Tiles archive ZIP",
                local_artifact_template=(
                    "offline_packages/{package_id}/cesium/archive/cesium_ion_clip.zip"
                ),
                params={
                    "asset_ids": "${CESIUM_ION_ASSET_IDS}",
                    "token": "${CESIUM_ION_TOKEN}",
                    "type": "CLIP_LATITUDE_LONGITUDE_RECTANGLE",
                    "format": "TILESET",
                    "clip_region": "{aoi_bbox_radians}",
                    "extract": True,
                },
                requires_token_env="CESIUM_ION_TOKEN",
                requires_account=True,
                terms_url="https://cesium.com/learn/ion/cesium-ion-archives-and-exports/",
                notes=(
                    "Creates a bounded clip when CESIUM_ION_ASSET_IDS identifies "
                    "archive/export-permitted ion assets. This will fail for assets "
                    "that Cesium does not allow to be archived or clipped."
                ),
            ),
        ],
        jetson_query_formats=[
            JetsonQueryFormat(
                artifact_type="cesium_offline_archive_index",
                local_path_template=(
                    "offline_packages/{package_id}/cesium/archive/cesium_archive_index.json"
                ),
                query_interfaces=[
                    "cesium_archive_metadata()",
                    "cesium_file(relative_path)",
                    "tileset_json()",
                    "layer_json()",
                ],
                feeds_algorithms=[
                    "local_cesium_preview",
                    "operator_route_review",
                    "terrain_visual_context",
                ],
                notes=(
                    "Archive metadata and 3D Tiles/terrain descriptors are queryable "
                    "locally. DEM algorithms still prefer GeoTIFF/COG elevation unless "
                    "a quantized-mesh terrain decoder is added."
                ),
            )
        ],
        notes=(
            "Use this when the Jetson must actually download Cesium content. A plain "
            "World Imagery/Terrain stream token is not treated as offline download permission."
        ),
    ),
    SourceOption(
        id="usgs_imagery_only",
        name="USGS Imagery Only",
        provider="USGS The National Map",
        category="imagery",
        purpose="Free U.S. imagery tile stream from The National Map for AO preview and offline visual tile cache.",
        useful_for=["U.S. visual AO verification", "roads and clearings", "offline background tiles"],
        analysis_role=(
            "Free visual imagery layer from the WinTAK source folder. Cache bounded AO tiles "
            "to the Jetson for offline TAK/planner display; use Sentinel-2 COGs for raster analysis."
        ),
        stream_status="streamable",
        download_status="cache-tiles",
        stream_layer="usgs-imagery",
        recommended_for=["imagery-preview", "terrain-routing", "sar-planning", "evacuation"],
        derived_layers=["cached_usgs_imagery_tiles", "visual_aoi_reference"],
        source_url=USGS_IMAGERY_ONLY_TILE_URL,
        license_or_terms="U.S. public basemap imagery source; verify local attribution and cache policy before broad redistribution.",
        download_methods=[
            SourceDownloadMethod(
                id="usgs_imagery_tile_cache",
                label="USGS imagery AO tile cache",
                endpoint=USGS_IMAGERY_ONLY_TILE_URL,
                output_format="XYZ PNG tile cache",
                local_artifact_template=(
                    "offline_packages/{package_id}/tiles/usgs_imagery_only/{z}/{x}/{y}.png"
                ),
                params={
                    "tile_url_template": USGS_IMAGERY_ONLY_TILE_URL,
                    "levels": "{imagery_level_range}",
                    "min_zoom": 0,
                    "max_zoom": 15,
                },
                notes="Caches only AO-intersecting tiles under the Jetson package root.",
            )
        ],
        jetson_query_formats=[
            JetsonQueryFormat(
                artifact_type="xyz_imagery_tile_cache",
                local_path_template="offline_packages/{package_id}/tiles/usgs_imagery_only/{z}/{x}/{y}.png",
                query_interfaces=["tile(z, x, y)", "tiles_intersecting_bbox(west, south, east, north, zoom)"],
                feeds_algorithms=["visual_aoi_reference", "operator_route_review"],
                notes="Visual tiles are queryable for display, not for DEM/routing math.",
            )
        ],
        notes="Imported from the WinTAK imagery source list as a free U.S. visual imagery stream.",
    ),
    SourceOption(
        id="nrl_naip_conus",
        name="NRL NAIP (CONUS)",
        provider="NRL / USDA NAIP",
        category="imagery",
        purpose="Free CONUS NAIP tile stream from the WinTAK imagery folder for high-detail U.S. AO review.",
        useful_for=["CONUS aerial imagery", "small clearings", "roads and tracks", "offline visual review"],
        analysis_role=(
            "High-detail U.S. visual imagery tile cache. Useful for operator review and feature sanity checks; "
            "not a substitute for COG bands or DEMs in deterministic algorithms."
        ),
        stream_status="streamable",
        download_status="cache-tiles",
        recommended_for=["imagery-preview", "sar-planning", "evacuation"],
        derived_layers=["cached_naip_tiles", "high_detail_aerial_reference"],
        source_url=NRL_NAIP_TILE_URL,
        license_or_terms="NAIP imagery is public-domain with attribution; confirm NRL tile service use/caching constraints.",
        download_methods=[
            SourceDownloadMethod(
                id="nrl_naip_tile_cache",
                label="NRL NAIP AO tile cache",
                endpoint=NRL_NAIP_TILE_URL,
                output_format="XYZ PNG tile cache",
                local_artifact_template=(
                    "offline_packages/{package_id}/tiles/nrl_naip_conus/{z}/{x}/{y}.png"
                ),
                params={
                    "tile_url_template": NRL_NAIP_TILE_URL,
                    "levels": "{imagery_level_range}",
                    "min_zoom": 0,
                    "max_zoom": 18,
                },
                notes="Caches AO-intersecting NAIP tiles to the Jetson for disconnected display.",
            )
        ],
        jetson_query_formats=[
            JetsonQueryFormat(
                artifact_type="xyz_imagery_tile_cache",
                local_path_template="offline_packages/{package_id}/tiles/nrl_naip_conus/{z}/{x}/{y}.png",
                query_interfaces=["tile(z, x, y)", "tiles_intersecting_bbox(west, south, east, north, zoom)"],
                feeds_algorithms=["visual_aoi_reference", "operator_route_review"],
                notes="Visual cache for ATAK/planner background layers.",
            )
        ],
        notes="Useful when the AO is in CONUS and high-detail visual context matters.",
    ),
    SourceOption(
        id="cesium_world_terrain",
        name="Cesium World Terrain",
        provider="Cesium ion",
        category="terrain-display",
        purpose="3D terrain visualization for operator and planner preview.",
        useful_for=["3D landform awareness", "ridge/valley interpretation", "visual route review"],
        analysis_role="Display terrain; use DEM sources for deterministic slope and viewshed.",
        stream_status="streamable-with-token",
        download_status="stream-only-no-offline-copy",
        stream_layer="cesium-world",
        recommended_for=["terrain-routing", "signal-planning", "imagery-preview"],
        derived_layers=["preview_only_terrain_stream"],
        notes=(
            "Good for online visualization, not a substitute for indexed DEM rasters. "
            "Do not download Cesium World Terrain into offline packages by default."
        ),
    ),
    SourceOption(
        id="esri_world_elevation",
        name="Esri World Elevation Terrain",
        provider="Esri ArcGIS Online / Living Atlas",
        category="terrain",
        purpose=(
            "Primary queryable terrain source for AO elevation export, terrain sampling, "
            "slope, hillshade, viewshed, hydrology, and cost-surface preflight."
        ),
        useful_for=[
            "elevation sampling",
            "slope fallback",
            "hillshade",
            "viewshed preflight",
            "terrain sanity checks",
        ],
        analysis_role=(
            "Export clipped AO elevation rasters or LERC tiles, convert them to "
            "Cloud Optimized GeoTIFFs, and build derived rasters so the Jetson can "
            "answer terrain queries offline."
        ),
        stream_status="queryable-online",
        download_status="download-required",
        required_for=["terrain-routing", "signal-planning"],
        recommended_for=["water-access", "sar-planning", "evacuation"],
        derived_layers=[
            "dem_cog",
            "elevation_samples",
            "slope_degrees",
            "aspect",
            "roughness",
            "curvature",
            "flow_accumulation",
            "hillshade",
            "viewshed_surfaces",
            "walking_cost_surface",
        ],
        source_url=ESRI_WORLD_ELEVATION_TERRAIN_URL,
        license_or_terms=(
            "Use under ArcGIS Online/Living Atlas service terms with an authorized "
            "ArcGIS account or token."
        ),
        download_methods=[
            SourceDownloadMethod(
                id="esri_world_elevation_export_image_tiff",
                label="ArcGIS ImageServer exportImage",
                endpoint=f"{ESRI_WORLD_ELEVATION_TERRAIN_URL}/exportImage",
                method="POST",
                output_format="GeoTIFF DEM",
                local_artifact_template=(
                    "offline_packages/{package_id}/rasters/esri_world_elevation/dem.tif"
                ),
                params={
                    "bbox": "{aoi_bbox_wgs84}",
                    "bboxSR": 4326,
                    "imageSR": 4326,
                    "size": "{terrain_export_size}",
                    "format": "tiff",
                    "pixelType": "F32",
                    "interpolation": "RSP_BilinearInterpolation",
                    "f": "image",
                    "token": "${ESRI_ARCGIS_TOKEN}",
                },
                requires_token_env="ESRI_ARCGIS_TOKEN",
                requires_account=True,
                terms_url=ESRI_TERMS_URL,
                notes=(
                    "Use for clipped DEM files that become local COG inputs for "
                    "slope, flow, cost-distance, and viewshed algorithms."
                ),
            ),
            SourceDownloadMethod(
                id="esri_world_elevation_get_samples",
                label="ArcGIS ImageServer getSamples",
                endpoint=f"{ESRI_WORLD_ELEVATION_TERRAIN_URL}/getSamples",
                method="POST",
                output_format="JSON elevation samples",
                local_artifact_template=(
                    "offline_packages/{package_id}/samples/esri_world_elevation/grid_samples.json"
                ),
                params={
                    "geometry": "{sample_points_multipoint_json}",
                    "geometryType": "esriGeometryMultipoint",
                    "returnFirstValueOnly": "true",
                    "f": "json",
                    "token": "${ESRI_ARCGIS_TOKEN}",
                },
                requires_token_env="ESRI_ARCGIS_TOKEN",
                requires_account=True,
                terms_url=ESRI_TERMS_URL,
                notes="Use for quick AO preflight and point checks; prefer GeoTIFF export for full routing.",
            ),
        ],
        jetson_query_formats=[
            JetsonQueryFormat(
                artifact_type="cloud_optimized_geotiff_dem",
                local_path_template=(
                    "offline_packages/{package_id}/rasters/esri_world_elevation/dem_cog.tif"
                ),
                query_interfaces=[
                    "sample_dem(lat, lon)",
                    "read_window(west, south, east, north)",
                    "derive_slope_aspect_roughness(bounds)",
                ],
                feeds_algorithms=[
                    "terrain_derivatives",
                    "flow_accumulation_d8",
                    "raster_cost_distance",
                    "viewshed",
                    "isochrone_masks",
                ],
                notes="Main terrain artifact consumed by deterministic Jetson algorithms.",
            )
        ],
        notes=(
            "Main terrain source for this planner. Supplement with USGS 3DEP or "
            "Copernicus DEM when the AO needs an open authoritative DEM mirror."
        ),
    ),
    SourceOption(
        id="osm_basemap",
        name="OpenStreetMap Basemap",
        provider="OpenStreetMap contributors",
        category="basemap",
        purpose="Visual street/trail/place-name map stream for planner orientation.",
        useful_for=["orientation", "road and trail names", "POI discovery", "map sanity checks"],
        analysis_role="Display layer; use OSM PBF extract for local server queries.",
        stream_status="streamable",
        download_status="manifest-only",
        stream_layer="osm",
        recommended_for=["terrain-routing", "evacuation", "water-access", "sar-planning"],
        derived_layers=["visual_osm_reference"],
        notes="Tile usage should respect OSM tile policies; package OSM PBF for analysis.",
    ),
    SourceOption(
        id="osm_extract",
        name="OpenStreetMap PBF Extract",
        provider="Geofabrik / OpenStreetMap contributors",
        category="vector",
        purpose=(
            "Root-staged OSM vector data from the Jetson WinTAK imagery folder "
            "for roads, trails, waterways, buildings, POIs, and barriers."
        ),
        useful_for=[
            "routable graph",
            "nearest road or trail",
            "waterway and POI lookup",
            "barrier and bridge/crossing context",
        ],
        analysis_role=(
            "Primary local vector dataset for database-backed graph, POI, hydro, "
            "access, and Valhalla tile-build queries."
        ),
        stream_status="not-streamed",
        download_status="download-required",
        required_for=["terrain-routing", "water-access", "evacuation", "sar-planning"],
        recommended_for=["access-control", "signal-planning"],
        derived_layers=["routable_graph", "poi_index", "waterway_index", "barrier_index"],
        source_url=GEOFABRIK_BASE_URL,
        license_or_terms="OpenStreetMap data from Geofabrik is under the Open Database License.",
        download_methods=[
            SourceDownloadMethod(
                id="osm_wintak_imagery_import",
                label="Index staged WinTAK OSM vector files",
                endpoint="${TERA_WINTAK_IMAGERY_DIR}",
                output_format="OSM SQLite/GeoPackage/PBF index",
                local_artifact_template=(
                    "offline_packages/{package_id}/vectors/osm/wintak_osm_index.json"
                ),
                params={
                    "source_dir": "${TERA_WINTAK_IMAGERY_DIR}",
                    "bbox": "{aoi_bbox_wgs84}",
                },
                notes=(
                    "Defaults to /WINTAK Imagery on the Jetson and indexes local "
                    "OSM SQLite/GeoPackage/PBF files without outbound downloads."
                ),
            ),
            SourceDownloadMethod(
                id="osm_geofabrik_pbf",
                label="Geofabrik regional PBF download and AOI clip",
                endpoint="{geofabrik_osm_pbf_url}",
                output_format="OSM PBF",
                local_artifact_template=(
                    "offline_packages/{package_id}/vectors/osm/aoi.osm.pbf"
                ),
                params={
                    "region_url": "{geofabrik_osm_pbf_url}",
                    "region_slug": "{geofabrik_region_slug}",
                    "clip_bbox": "{aoi_bbox_wgs84}",
                    "clip_with_osmium": True,
                },
                terms_url="https://www.geofabrik.de/en/data/download.html",
                notes=(
                    "Fallback only. The Jetson ATAK demo should use staged files "
                    "under /WINTAK Imagery and avoid outbound downloads."
                ),
            )
        ],
        jetson_query_formats=[
            JetsonQueryFormat(
                artifact_type="osm_wintak_index",
                local_path_template=(
                    "offline_packages/{package_id}/vectors/osm/wintak_osm_index.json"
                ),
                query_interfaces=[
                    "query_osm_features(target_type, origin, radius_m)",
                    "valhalla_build_tiles",
                    "find_pois(osm_tags, bbox)",
                ],
                feeds_algorithms=[
                    "routable_graph",
                    "nearest_feature",
                    "water_source_lookup",
                    "evacuation_route",
                ],
                notes="Main vector artifact for deterministic route and POI algorithms.",
            )
        ],
        notes="Use staged files from /WINTAK Imagery for the Jetson demo.",
    ),
    SourceOption(
        id="usgs_3dep",
        name="USGS 3DEP DEM",
        provider="USGS",
        category="terrain",
        purpose="Best U.S. default elevation dataset for slope, hydrology, viewshed, and cost surfaces.",
        useful_for=["slope", "aspect", "roughness", "viewshed", "hydrology", "least-cost routing"],
        analysis_role="Primary analysis DEM for U.S. AO packages.",
        stream_status="not-streamed",
        download_status="download-required",
        required_for=["terrain-routing", "signal-planning", "water-access"],
        recommended_for=["sar-planning", "evacuation"],
        derived_layers=[
            "slope_degrees",
            "aspect",
            "roughness",
            "contours",
            "flow_accumulation",
            "viewshed_surfaces",
        ],
        notes="Use 1 m lidar where available; 10 m DEM is a practical broad-coverage default.",
    ),
    SourceOption(
        id="copernicus_dem",
        name="Copernicus DEM GLO-30 COG",
        provider="Copernicus",
        category="terrain",
        purpose=(
            "Free no-account 30 m terrain COG tiles from the public Copernicus DEM "
            "S3 mirror for slope, viewshed, hydrology, and terrain-cost analysis."
        ),
        useful_for=["global slope", "viewshed", "terrain cost", "AO outside U.S.", "no-login terrain"],
        analysis_role=(
            "Main no-login terrain download path. Select 1-degree GLO-30 COG tiles "
            "intersecting the AOI and store them under the Jetson package root."
        ),
        stream_status="not-streamed",
        download_status="download-required",
        required_for=["terrain-routing", "signal-planning"],
        recommended_for=["water-access", "sar-planning"],
        derived_layers=[
            "dem_cog",
            "slope_degrees",
            "aspect",
            "roughness",
            "flow_accumulation",
            "viewshed_surfaces",
            "walking_cost_surface",
        ],
        source_url=COPERNICUS_DEM_30M_BASE_URL,
        license_or_terms="Copernicus DEM GLO-30 Public is free for public use under Copernicus DEM terms.",
        download_methods=[
            SourceDownloadMethod(
                id="copernicus_dem_glo30_cog",
                label="Copernicus GLO-30 public S3 COG tiles",
                endpoint=COPERNICUS_DEM_30M_BASE_URL,
                output_format="Cloud Optimized GeoTIFF DEM tiles",
                local_artifact_template=(
                    "offline_packages/{package_id}/rasters/copernicus_dem/{tile_id}.tif"
                ),
                params={
                    "tile_urls": "{copernicus_dem_tile_urls}",
                    "bbox": "{aoi_bbox_wgs84}",
                    "resolution_arc_seconds": 10,
                },
                terms_url="https://copernicus-dem-30m.s3.amazonaws.com/readme.html",
                notes=(
                    "Downloads only AO-intersecting 1-degree COG tiles. Missing ocean "
                    "or unreleased tiles are recorded in the DEM index."
                ),
            )
        ],
        jetson_query_formats=[
            JetsonQueryFormat(
                artifact_type="copernicus_dem_cog_index",
                local_path_template="offline_packages/{package_id}/rasters/copernicus_dem/copernicus_dem_index.json",
                query_interfaces=[
                    "sample_dem(lat, lon)",
                    "read_window(west, south, east, north)",
                    "derive_slope_aspect_roughness(bounds)",
                ],
                feeds_algorithms=[
                    "terrain_derivatives",
                    "flow_accumulation_d8",
                    "raster_cost_distance",
                    "viewshed",
                ],
                notes="COG tiles are local raster inputs for deterministic terrain algorithms.",
            )
        ],
        notes="Use as the default no-login terrain source; add DTED when an EarthExplorer DTED package is staged.",
    ),
    SourceOption(
        id="dted_earth_explorer",
        name="Root DTED Terrain",
        provider="Local Jetson /DTED folder",
        category="terrain",
        purpose=(
            "Operator-staged DTED cells from the Jetson root /DTED folder for "
            "slope, terrain cost, elevation, and viewshed analysis."
        ),
        useful_for=["local DTED terrain", "slope analysis", "viewshed", "offline terrain cost"],
        analysis_role=(
            "The Jetson imports the root-staged local .dt0/.dt1/.dt2 files. "
            "It converts each file with gdal_translate when available and "
            "registers both raw DTED and GeoTIFF artifacts."
        ),
        stream_status="not-streamed",
        download_status="manual-stage-import",
        recommended_for=["terrain-routing", "signal-planning"],
        derived_layers=["dted_cells", "geotiff_dem", "slope_degrees", "viewshed_surfaces"],
        source_url=USGS_EARTHEXPLORER_URL,
        license_or_terms="Use under USGS EarthExplorer dataset terms for the downloaded DTED product.",
        download_methods=[
            SourceDownloadMethod(
                id="dted_earthexplorer_import_convert",
                label="Import root-staged Jetson DTED and convert with GDAL",
                endpoint="${DTED_SOURCE_DIR}",
                output_format="DTED cells and GeoTIFF DEMs",
                local_artifact_template=(
                    "offline_packages/{package_id}/rasters/dted/dted_index.json"
                ),
                params={
                    "source_dir": "${DTED_SOURCE_DIR}",
                    "bbox": "{aoi_bbox_wgs84}",
                    "convert_to_geotiff": True,
                },
                requires_account=False,
                notes=(
                    "Defaults to /DTED on the Jetson. gdal_translate input.dt2 "
                    "output.tif is used when present."
                ),
            )
        ],
        jetson_query_formats=[
            JetsonQueryFormat(
                artifact_type="dted_geotiff_index",
                local_path_template="offline_packages/{package_id}/rasters/dted/dted_index.json",
                query_interfaces=["sample_dem(lat, lon)", "read_window(west, south, east, north)", "gdalinfo"],
                feeds_algorithms=["terrain_derivatives", "raster_cost_distance", "viewshed"],
                notes="Converted GeoTIFFs are preferred; raw DTED remains available for GDAL readers.",
            )
        ],
        notes="Only DTED under /DTED is valid terrain for the Jetson demo; do not substitute another terrain source.",
    ),
    SourceOption(
        id="srtm",
        name="SRTM DEM",
        provider="NASA / USGS",
        category="terrain",
        purpose="Global fallback elevation source where higher-quality DEMs are not available.",
        useful_for=["fallback slope", "broad terrain context", "rough least-cost surfaces"],
        analysis_role="Fallback DEM for lower-resolution global packages.",
        stream_status="not-streamed",
        download_status="download-required",
        recommended_for=["terrain-routing", "signal-planning"],
        derived_layers=["fallback_slope", "fallback_hillshade"],
        notes="Use only when better DEMs are unavailable or package size is highly constrained.",
    ),
    SourceOption(
        id="nlcd",
        name="USGS Annual NLCD",
        provider="USGS",
        category="land-cover",
        purpose="U.S. land-cover baseline for surface friction and vegetation context.",
        useful_for=["off-road friction", "forest/brush/wetland screening", "cover and concealment"],
        analysis_role="Land-cover raster for friction and suitability layers in U.S. AOs.",
        stream_status="not-streamed",
        download_status="download-required",
        required_for=["terrain-routing", "sar-planning"],
        recommended_for=["water-access", "evacuation"],
        derived_layers=["surface_friction", "wetland_mask", "canopy_proxy", "cover_score"],
        notes="Pair with DEM and OSM; land cover alone is not enough for routing.",
    ),
    SourceOption(
        id="esa_worldcover",
        name="ESA WorldCover",
        provider="ESA",
        category="land-cover",
        purpose="Global 10 m land-cover baseline for non-U.S. AO surface friction.",
        useful_for=["global surface friction", "wetland/open-ground screening", "vegetation context"],
        analysis_role="Global land-cover raster for friction and cover layers.",
        stream_status="not-streamed",
        download_status="download-required",
        recommended_for=["terrain-routing", "sar-planning", "water-access"],
        derived_layers=["surface_friction", "wetland_mask", "open_ground_mask", "cover_score"],
        notes="Use when NLCD is unavailable or the AO is outside the U.S.",
    ),
    SourceOption(
        id="dynamic_world",
        name="Dynamic World",
        provider="Google / WRI",
        category="land-cover",
        purpose="More current global land-cover probabilities for recent surface changes.",
        useful_for=["recent land-cover confidence", "burn/clearing/change context", "uncertainty scoring"],
        analysis_role="Optional recency/confidence layer that complements baseline land cover.",
        stream_status="not-streamed",
        download_status="download-required",
        recommended_for=["sar-planning", "imagery-preview"],
        derived_layers=["landcover_confidence", "change_context"],
        notes="Useful when stale land-cover products could mislead the route planner.",
    ),
    SourceOption(
        id="usgs_3dhp",
        name="USGS 3D Hydrography Program / NHD",
        provider="USGS",
        category="hydrography",
        purpose="U.S. authoritative hydrography for streams, rivers, water bodies, and drainage.",
        useful_for=["water-source lookup", "crossings", "drainage", "floodplain context"],
        analysis_role="Primary U.S. hydrography layer for water and crossing queries.",
        stream_status="not-streamed",
        download_status="download-required",
        required_for=["water-access"],
        recommended_for=["terrain-routing", "sar-planning", "evacuation"],
        derived_layers=["water_source_index", "crossing_candidates", "drainage_lines"],
        notes="Use with NWIS for observed flow and with DEM-derived flow accumulation.",
    ),
    SourceOption(
        id="nhdplus_hr",
        name="NHDPlus High Resolution",
        provider="USGS",
        category="hydrography",
        purpose="Hydro network attributes and catchments for U.S. water analysis.",
        useful_for=["networked water flow", "catchments", "downstream/upstream logic"],
        analysis_role="Hydro network supplement for route constraints and water confidence.",
        stream_status="not-streamed",
        download_status="download-required",
        recommended_for=["water-access", "flood-risk"],
        derived_layers=["catchment_index", "hydro_network_graph"],
        notes="Helpful when the mission depends on connected drainage rather than visual water alone.",
    ),
    SourceOption(
        id="nwis",
        name="USGS NWIS",
        provider="USGS",
        category="water-observation",
        purpose="Observed gauge and water-condition data for U.S. streams and water bodies.",
        useful_for=["flow condition", "gauge status", "water availability confidence"],
        analysis_role="Optional live or cached observation feed for water confidence.",
        stream_status="not-streamed",
        download_status="cache-feed",
        recommended_for=["water-access", "flood-risk"],
        derived_layers=["water_observation_points", "flow_status"],
        notes="Time-sensitive; cache timestamp and stale-data warnings.",
    ),
    SourceOption(
        id="hydrosheds",
        name="HydroSHEDS / HydroRIVERS / HydroLAKES",
        provider="HydroSHEDS",
        category="hydrography",
        purpose="Global hydrography baseline for non-U.S. water and drainage queries.",
        useful_for=["global water-source lookup", "drainage", "lakes and rivers"],
        analysis_role="Global hydrography package when U.S. NHD is unavailable.",
        stream_status="not-streamed",
        download_status="download-required",
        recommended_for=["water-access", "terrain-routing", "sar-planning"],
        derived_layers=["global_water_index", "global_drainage_lines"],
        notes="Pair with OSM waterways and DEM-derived drainage for confidence.",
    ),
    SourceOption(
        id="sentinel_2",
        name="Sentinel-2 Multispectral",
        provider="ESA Copernicus / Element 84 Earth Search",
        category="imagery-analysis",
        purpose=(
            "Free global multispectral COG imagery for offline AO context, vegetation, "
            "water, burn, and surface-condition indices."
        ),
        useful_for=["NDVI", "NDWI", "water detection", "vegetation condition", "recent surface context"],
        analysis_role=(
            "Primary free downloadable imagery source for this planner. Download selected "
            "COG assets from the public Earth Search STAC API to the Jetson package root."
        ),
        stream_status="not-streamed",
        download_status="download-required",
        required_for=["imagery-preview"],
        recommended_for=["terrain-routing", "water-access", "sar-planning", "evacuation"],
        derived_layers=["sentinel2_visual_cog", "ndvi", "ndwi", "vegetation_condition", "water_detection"],
        source_url=EARTH_SEARCH_STAC_SEARCH_URL,
        license_or_terms="Sentinel data access is free, full, and open under Copernicus terms.",
        download_methods=[
            SourceDownloadMethod(
                id="sentinel_2_stac_cog",
                label="Earth Search Sentinel-2 COG STAC download",
                endpoint=EARTH_SEARCH_STAC_SEARCH_URL,
                method="POST",
                output_format="COG GeoTIFF bands",
                local_artifact_template=(
                    "offline_packages/{package_id}/imagery/sentinel_2/{item_id}_{asset}.tif"
                ),
                params={
                    "collections": ["sentinel-2-l2a"],
                    "bbox": "{aoi_bbox_array}",
                    "datetime": "{recent_24_month_interval}",
                    "limit": 1,
                    "query": {"eo:cloud_cover": {"lt": 30}},
                    "sortby": [{"field": "properties.datetime", "direction": "desc"}],
                    "assets": ["visual", "red", "green", "blue", "nir", "scl"],
                },
                terms_url="https://registry.opendata.aws/sentinel-2-l2a-cogs/",
                notes=(
                    "No Esri token or AWS account is required for Earth Search HTTP COG hrefs. "
                    "The Jetson downloads only selected scene assets intersecting the AO."
                ),
            )
        ],
        jetson_query_formats=[
            JetsonQueryFormat(
                artifact_type="sentinel2_cog_band_stack",
                local_path_template="offline_packages/{package_id}/imagery/sentinel_2/*.tif",
                query_interfaces=[
                    "read_band_window(asset, west, south, east, north)",
                    "compute_ndvi(red, nir)",
                    "compute_ndwi(green, nir)",
                    "visual_chip(west, south, east, north)",
                ],
                feeds_algorithms=[
                    "vegetation_condition",
                    "water_detection",
                    "operator_route_review",
                    "sar_probability_context",
                ],
                notes="Free imagery COGs are queryable by raster windows on the Jetson.",
            )
        ],
        notes="Cloud cover and date filtering matter; preserve acquisition timestamp and STAC metadata.",
    ),
    SourceOption(
        id="landsat_collection_2",
        name="Landsat Collection 2",
        provider="USGS / NASA",
        category="imagery-analysis",
        purpose="Long-running multispectral record for historical change and broad surface context.",
        useful_for=["historical change", "burn scars", "seasonal water", "broad land surface context"],
        analysis_role="Optional historical/change-detection imagery source.",
        stream_status="not-streamed",
        download_status="download-required",
        recommended_for=["sar-planning", "water-access"],
        derived_layers=["historical_change", "seasonal_water_context"],
        notes="Lower temporal/spatial immediacy than higher-resolution or current imagery.",
    ),
    SourceOption(
        id="naip",
        name="NAIP Aerial Imagery",
        provider="USDA / USGS EarthExplorer / AWS Open Data",
        category="imagery-analysis",
        purpose=(
            "High-resolution U.S. aerial imagery staged on the Jetson under the "
            "WinTAK imagery folder for display context."
        ),
        useful_for=["small roads/tracks", "buildings", "clearings", "agricultural features", "offline AO imagery"],
        analysis_role=(
            "Display-only context for the ATAK/planner UI. The Gemma agent does "
            "not query NAIP pixels for TAK CoT generation; action uses OSM and DTED."
        ),
        stream_status="not-streamed",
        download_status="download-required",
        required_for=["imagery-preview"],
        recommended_for=["sar-planning", "evacuation", "terrain-routing"],
        derived_layers=["naip_local_imagery", "high_detail_aerial_reference", "feature_extraction_review"],
        source_url="https://registry.opendata.aws/naip/",
        license_or_terms="NAIP on AWS is public domain with attribution; EarthExplorer downloads follow USGS terms.",
        download_methods=[
            SourceDownloadMethod(
                id="naip_earthexplorer_geotiff_import",
                label="Import staged WinTAK/NAIP GeoTIFFs",
                endpoint="${NAIP_EARTHEXPLORER_DIR}",
                output_format="NAIP GeoTIFF imagery",
                local_artifact_template=(
                    "offline_packages/{package_id}/imagery/naip/earthexplorer/naip_earthexplorer_index.json"
                ),
                params={
                    "source_dir": "${NAIP_EARTHEXPLORER_DIR}",
                    "bbox": "{aoi_bbox_wgs84}",
                    "max_files": "{naip_max_files}",
                },
                requires_account=False,
                notes=(
                    "Defaults to /WINTAK Imagery on the Jetson. Files are served "
                    "for display and operator review only."
                ),
            ),
            SourceDownloadMethod(
                id="naip_aws_public_prefix",
                label="NAIP AWS public S3 prefix download",
                endpoint=NAIP_AWS_BUCKET_URL_TEMPLATE,
                output_format="NAIP MRF/GeoTIFF/COG files",
                local_artifact_template=(
                    "offline_packages/{package_id}/imagery/naip/aws/naip_index.json"
                ),
                params={
                    "bucket": "{naip_aws_bucket}",
                    "prefix": "{naip_s3_prefix}",
                    "state": "{naip_state}",
                    "year": "{naip_year}",
                    "resolution": "{naip_resolution}",
                    "bandset": "{naip_bandset}",
                    "max_files": "{naip_max_files}",
                    "request_payer": "requester",
                },
                terms_url="https://registry.opendata.aws/naip/",
                notes=(
                    "Mirrors the operator workflow `aws s3 cp s3://naip-analytic/"
                    "<state>/<year>/<resolution>/rgbir/ ... --recursive`. Limit "
                    "max files and confirm storage before pulling large state prefixes."
                ),
            ),
        ],
        jetson_query_formats=[
            JetsonQueryFormat(
                artifact_type="naip_imagery_index",
                local_path_template="offline_packages/{package_id}/imagery/naip/**/naip*_index.json",
                query_interfaces=[
                    "imagery_file(relative_path)",
                    "rasterio.open()",
                    "read_window(west, south, east, north)",
                    "visual_chip(west, south, east, north)",
                ],
                feeds_algorithms=["operator_route_review"],
                notes="Local NAIP files are served to the planner/TERA plugin for display only.",
            )
        ],
        notes="Check acquisition date; do not use NAIP as deterministic model evidence for the demo.",
    ),
    SourceOption(
        id="sentinel_1_sar",
        name="Sentinel-1 SAR",
        provider="ESA Copernicus",
        category="imagery-analysis",
        purpose="Radar imagery that can support cloud/night/flood surface observation.",
        useful_for=["flood extent", "cloudy AO", "night/cloud independent context"],
        analysis_role="Specialized analysis imagery for weather-obscured or flood missions.",
        stream_status="not-streamed",
        download_status="download-required",
        recommended_for=["flood-risk", "sar-planning"],
        derived_layers=["sar_water_extent", "flood_extent"],
        notes="Requires SAR-specific processing before analyst use.",
    ),
    SourceOption(
        id="nasa_firms",
        name="NASA FIRMS",
        provider="NASA",
        category="hazards",
        purpose="Active fire/hotspot feed for wildfire context.",
        useful_for=["wildfire avoidance", "smoke/fire route risk", "current hazard context"],
        analysis_role="Time-sensitive hazard overlay for route exclusion and warnings.",
        stream_status="not-streamed",
        download_status="cache-feed",
        recommended_for=["hazard-routing", "evacuation", "sar-planning"],
        derived_layers=["active_fire_points", "fire_exclusion_zones"],
        notes="Cache timestamps and warn when stale.",
    ),
    SourceOption(
        id="noaa_alerts",
        name="NOAA / NWS Alerts",
        provider="NOAA",
        category="hazards",
        purpose="Weather watches, warnings, advisories, and hazard alerts.",
        useful_for=["storm risk", "heat/cold exposure", "flash flood warnings", "weather constraints"],
        analysis_role="Time-sensitive alert feed for planner warnings and route risk flags.",
        stream_status="not-streamed",
        download_status="cache-feed",
        recommended_for=["hazard-routing", "evacuation", "sar-planning", "water-access"],
        derived_layers=["weather_alert_zones", "stale_weather_warning"],
        notes="Offline package must record retrieval time and validity window.",
    ),
    SourceOption(
        id="fema_flood",
        name="FEMA Flood Products",
        provider="FEMA",
        category="hazards",
        purpose="Flood hazard and floodplain layers for U.S. route risk.",
        useful_for=["floodplain avoidance", "crossing risk", "evacuation constraints"],
        analysis_role="Flood hazard layer for route exclusion or high-cost areas.",
        stream_status="not-streamed",
        download_status="download-required",
        recommended_for=["flood-risk", "evacuation", "water-access"],
        derived_layers=["floodplain_mask", "flood_hazard_cost"],
        notes="Flood maps are hazard context, not real-time water levels.",
    ),
    SourceOption(
        id="pad_us",
        name="PAD-US Protected Areas",
        provider="USGS",
        category="boundaries-access",
        purpose="U.S. protected area ownership and management boundaries.",
        useful_for=["public/private access", "restricted movement", "land manager context"],
        analysis_role="Access and authority layer for route legality and planner warnings.",
        stream_status="not-streamed",
        download_status="download-required",
        recommended_for=["access-control", "terrain-routing", "sar-planning"],
        derived_layers=["access_boundaries", "land_management_index"],
        notes="Pair with local closures and parcels when legal access matters.",
    ),
    SourceOption(
        id="blm_usfs_nps",
        name="BLM / USFS / NPS Roads, Trails, Facilities, Closures",
        provider="U.S. land-management agencies",
        category="boundaries-access",
        purpose="Authoritative federal public-land roads, trails, facilities, and closure context.",
        useful_for=["public land movement", "trail authority", "closures", "rescue access"],
        analysis_role="Authoritative supplement to OSM for managed lands.",
        stream_status="not-streamed",
        download_status="download-required",
        recommended_for=["access-control", "evacuation", "sar-planning", "terrain-routing"],
        derived_layers=["authoritative_trails", "closure_zones", "facility_index"],
        notes="Useful when OSM coverage is incomplete or agency closures are decisive.",
    ),
    SourceOption(
        id="parcels_boundaries",
        name="Parcels / Local Boundaries",
        provider="County or local GIS",
        category="boundaries-access",
        purpose="Local ownership and parcel boundaries for access constraints.",
        useful_for=["private land avoidance", "permission planning", "access-control warnings"],
        analysis_role="Local access-control layer where parcel movement matters.",
        stream_status="not-streamed",
        download_status="download-required",
        recommended_for=["access-control", "evacuation"],
        derived_layers=["parcel_access_mask", "ownership_index"],
        notes="Availability and licensing vary by jurisdiction.",
    ),
    SourceOption(
        id="fcc_towers",
        name="FCC Antenna / Tower Data",
        provider="FCC",
        category="communications",
        purpose="Tower locations for communications planning context.",
        useful_for=["signal opportunity", "relay planning", "communications infrastructure context"],
        analysis_role="Vector point layer for comms planning and line-of-sight checks.",
        stream_status="not-streamed",
        download_status="download-required",
        recommended_for=["signal-planning"],
        derived_layers=["tower_index", "candidate_comms_points"],
        notes="Pair with DEM viewsheds; tower presence does not guarantee usable service.",
    ),
    SourceOption(
        id="osm_towers",
        name="OSM Towers, Peaks, Lookouts",
        provider="OpenStreetMap",
        category="communications",
        purpose="Mapped towers, peaks, masts, lookouts, and high-ground features.",
        useful_for=["field signal points", "lookout sites", "relay candidate discovery"],
        analysis_role="Extracted feature subset from OSM for signal planning.",
        stream_status="not-streamed",
        download_status="derived-from-osm",
        recommended_for=["signal-planning", "sar-planning"],
        derived_layers=["signal_feature_index", "lookout_candidates"],
        notes="Requires OSM PBF extract and tag filtering.",
    ),
    SourceOption(
        id="viewshed_surfaces",
        name="DEM-Derived Viewshed Surfaces",
        provider="Derived from package DEM",
        category="derived",
        purpose="Line-of-sight and visibility products for communications and observation planning.",
        useful_for=["radio line-of-sight", "open-sky checks", "observation points", "relay placement"],
        analysis_role="Derived raster/vector layer generated after DEM ingest.",
        stream_status="derived",
        download_status="derived-after-ingest",
        required_for=["signal-planning"],
        recommended_for=["sar-planning", "terrain-routing"],
        derived_layers=["viewshed_rasters", "visibility_score", "relay_candidate_scores"],
        notes="Cannot be downloaded directly; generate from selected DEM and candidate points.",
    ),
]

SOURCE_BY_ID: dict[str, SourceOption] = {source.id: source for source in SOURCE_CATALOG}
PRIMARY_STREAM_SOURCE_IDS = [
    "cesium_world_imagery",
    "usgs_imagery_only",
    "cesium_world_terrain",
    "osm_basemap",
]
PACKAGE_MANIFESTS: dict[str, dict[str, object]] = {}
PACKAGE_TASKS: dict[str, asyncio.Task[None]] = {}

FOCUS_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("water-access", ("water", "stream", "river", "spring", "lake", "potable", "hydrate")),
    ("sar-planning", ("search", "rescue", "sar", "missing", "lost person", "hasty")),
    ("evacuation", ("evac", "evacuation", "exfil", "casualty", "ambulance", "convoy")),
    ("signal-planning", ("signal", "radio", "comms", "communications", "line of sight", "relay")),
    ("hazard-routing", ("wildfire", "fire", "flood", "storm", "avalanche", "hazard", "closure")),
    ("access-control", ("private", "restricted", "public land", "access", "boundary", "parcel")),
    ("terrain-routing", ("route", "patrol", "walk", "foot", "trail", "slope", "terrain", "ridge")),
    ("imagery-preview", ("imagery", "aerial", "satellite", "visual", "inspect", "preview")),
)

US_CONTEXT_TERMS = (
    "united states",
    "u.s.",
    " usa",
    "california",
    "san francisco",
    "sf ",
    "national forest",
    "blm",
    "nps",
    "usfs",
)

LOCAL_LOCATION_GAZETTEER: tuple[dict[str, object], ...] = (
    {
        "name": "Cascade Range, WA/OR/BC",
        "detail": (
            "Pacific Northwest mountain range, national forests, volcanoes, "
            "SAR and terrain-routing context."
        ),
        "lat": 45.6500,
        "lon": -121.7000,
        "height_m": 26000,
        "aliases": (
            "cascades",
            "the cascades",
            "cascade mountains",
            "cascade range",
            "pnw cascades",
        ),
    },
    {
        "name": "North Cascades National Park, WA",
        "detail": "High alpine terrain, glaciers, steep valleys, trails, and SAR access constraints.",
        "lat": 48.7718,
        "lon": -121.2985,
        "height_m": 22000,
        "aliases": ("north cascades", "north cascades np", "cascades national park", "noca"),
    },
    {
        "name": "Olympic National Park, WA",
        "detail": "Dense forest, mountains, river valleys, coastline, and SAR mission terrain.",
        "lat": 47.8021,
        "lon": -123.6044,
        "height_m": 22000,
        "aliases": ("olympic", "olympics", "olympic peninsula", "olympic national park"),
    },
    {
        "name": "Mount Rainier National Park, WA",
        "detail": "Volcanic alpine terrain, glaciers, roads, trails, and high-risk weather.",
        "lat": 46.8523,
        "lon": -121.7603,
        "height_m": 20000,
        "aliases": ("rainier", "mount rainier", "mt rainier", "rainier national park"),
    },
    {
        "name": "Sierra Nevada, CA/NV",
        "detail": "Mountain range with alpine terrain, forest roads, trails, water, and winter hazards.",
        "lat": 38.9000,
        "lon": -120.0000,
        "height_m": 26000,
        "aliases": ("sierra", "sierras", "sierra nevada", "eastern sierra"),
    },
    {
        "name": "Rocky Mountains, CO/WY/MT",
        "detail": "Western mountain terrain, high elevation, passes, ridges, and SAR context.",
        "lat": 40.3772,
        "lon": -105.5250,
        "height_m": 30000,
        "aliases": ("rockies", "rocky mountains", "front range"),
    },
    {
        "name": "Appalachian Trail",
        "detail": "Long-distance eastern trail corridor with forest, ridges, road crossings, and shelters.",
        "lat": 39.0000,
        "lon": -77.9000,
        "height_m": 26000,
        "aliases": ("appalachian", "appalachians", "appalachian trail", "at trail"),
    },
    {
        "name": "Joshua Tree National Park, CA",
        "detail": "Desert terrain, trails, dry washes, roads, climbing areas, and water scarcity.",
        "lat": 33.8734,
        "lon": -115.9010,
        "height_m": 18000,
        "aliases": ("joshua tree", "joshua tree np", "jtnp", "joshu tree", "joshua"),
    },
    {
        "name": "San Francisco, CA",
        "detail": "City center and Bay Area mission staging reference.",
        "lat": 37.7749,
        "lon": -122.4194,
        "height_m": 14000,
        "aliases": ("sf", "san fran", "bay area"),
    },
    {
        "name": "Fort Irwin / National Training Center, CA",
        "detail": "Desert maneuver terrain, dry washes, roads, and range constraints.",
        "lat": 35.2627,
        "lon": -116.6848,
        "height_m": 26000,
        "aliases": ("fort irwin", "ntc", "national training center"),
    },
)

KEYWORD_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "route": ("route", "routing", "navigate", "navigation", "path", "corridor", "approach"),
    "patrol": ("patrol", "movement", "move", "walk", "team", "operator"),
    "water": (
        "water",
        "hydration",
        "hydrate",
        "stream",
        "river",
        "spring",
        "creek",
        "wash",
        "well",
        "source",
        "watter",
    ),
    "terrain": ("terrain", "terain", "topography", "elevation", "ground", "landform"),
    "slope": ("slope", "steep", "grade", "incline", "cliff", "exposed", "exposure"),
    "cover": ("cover", "concealment", "conceal", "canopy", "shade", "vegetation", "brush"),
    "hazard": ("hazard", "hazzard", "risk", "danger", "closure", "blocked", "unsafe"),
    "signal": ("signal", "comms", "communications", "radio", "relay", "antenna", "line of sight", "los"),
    "imagery": ("imagery", "image", "satellite", "satelite", "aerial", "visual", "photo"),
    "sar": ("sar", "search", "rescue", "missing", "lost", "hasty"),
    "access": ("access", "private", "restricted", "boundary", "parcel", "permission", "legal"),
}


def _get_source_options_by_ids(source_ids: list[str]) -> list[SourceOption]:
    seen: set[str] = set()
    sources: list[SourceOption] = []
    for source_id in source_ids:
        if source_id in seen:
            continue
        source = SOURCE_BY_ID.get(source_id)
        if source:
            sources.append(source)
            seen.add(source_id)
    return sources


JETSON_ANALYTIC_SOURCE_IDS = ("osm_extract", "dted_earth_explorer")


def _format_source_catalog_brief() -> str:
    lines = []
    lines.append(
        "Jetson analytical source allowlist: use only local OSM vectors from "
        "/WINTAK Imagery and local DTED terrain from /DTED. Do not recommend "
        "or require any source outside that allowlist for agentic TAK output."
    )
    for source_id in JETSON_ANALYTIC_SOURCE_IDS:
        source = SOURCE_BY_ID[source_id]
        lines.append(
            "- "
            f"{source.id}: {source.name} ({source.category}); "
            f"stream={source.stream_status}; package={source.download_status}; "
            f"use={source.purpose}"
        )
    return "\n".join(lines)


def _format_source_context(source_context: SourceContext | None) -> str:
    if source_context is None:
        return "- Mission focus: not provided\n- Selected data sources: none selected"

    names = source_context.selected_source_names
    if not names and source_context.selected_source_ids:
        names = [
            SOURCE_BY_ID[source_id].name
            for source_id in source_context.selected_source_ids
            if source_id in SOURCE_BY_ID
        ]

    selected_sources = ", ".join(names) if names else "none selected"
    lines = [
        f"- Mission focus: {source_context.mission_focus or 'not provided'}",
        f"- Mission text: {source_context.mission_text or 'not provided'}",
        f"- Selected data sources: {selected_sources}",
    ]
    if source_context.required_source_ids:
        required_names = [
            SOURCE_BY_ID[source_id].name
            for source_id in source_context.required_source_ids
            if source_id in SOURCE_BY_ID
        ]
        lines.append(f"- Required sources planned: {', '.join(required_names)}")
    if source_context.optional_source_ids:
        optional_names = [
            SOURCE_BY_ID[source_id].name
            for source_id in source_context.optional_source_ids
            if source_id in SOURCE_BY_ID
        ]
        lines.append(f"- Optional sources planned: {', '.join(optional_names)}")
    if source_context.clarifying_questions:
        lines.append(
            "- Socratic questions to ask next: "
            + " | ".join(source_context.clarifying_questions)
        )
    if source_context.package_summary:
        lines.append(f"- Package summary: {source_context.package_summary}")
    return "\n".join(lines)


def _format_manifest_bounds(map_context: MapContext | None) -> dict[str, float | None] | None:
    bounds = (map_context.selected_area or map_context.view_bounds) if map_context else None
    if bounds is None:
        return None
    return {
        "west": bounds.west,
        "south": bounds.south,
        "east": bounds.east,
        "north": bounds.north,
        "center_lat": bounds.center_lat,
        "center_lon": bounds.center_lon,
    }


def _manifest_bounds_from_context(map_context: MapContext | None) -> ViewBounds | None:
    if map_context is None:
        return None
    return map_context.selected_area or map_context.view_bounds


def _format_wgs84_extent_json(bounds: ViewBounds | None) -> dict[str, object] | str:
    if bounds is None:
        return "{aoi_wgs84_json}"
    return {
        "xmin": bounds.west,
        "ymin": bounds.south,
        "xmax": bounds.east,
        "ymax": bounds.north,
        "spatialReference": {"wkid": 4326},
    }


def _format_bbox_csv(bounds: ViewBounds | None) -> str:
    if bounds is None:
        return "{aoi_bbox_wgs84}"
    return f"{bounds.west},{bounds.south},{bounds.east},{bounds.north}"


def _format_bbox_array(bounds: ViewBounds | None) -> list[float] | str:
    if bounds is None:
        return "{aoi_bbox_array}"
    return [bounds.west, bounds.south, bounds.east, bounds.north]


def _format_bbox_radians(bounds: ViewBounds | None) -> list[float] | str:
    if bounds is None:
        return "{aoi_bbox_radians}"
    return [
        math.radians(bounds.west),
        math.radians(bounds.south),
        math.radians(bounds.east),
        math.radians(bounds.north),
    ]


US_STATE_BBOXES: dict[str, tuple[str, str, tuple[float, float, float, float]]] = {
    "al": ("alabama", "al", (-88.6, 30.1, -84.9, 35.1)),
    "az": ("arizona", "az", (-114.9, 31.2, -109.0, 37.1)),
    "ar": ("arkansas", "ar", (-94.7, 33.0, -89.6, 36.6)),
    "ca": ("california", "ca", (-124.5, 32.4, -114.1, 42.1)),
    "co": ("colorado", "co", (-109.1, 36.9, -102.0, 41.1)),
    "ct": ("connecticut", "ct", (-73.8, 40.9, -71.7, 42.1)),
    "de": ("delaware", "de", (-75.9, 38.4, -75.0, 39.9)),
    "fl": ("florida", "fl", (-87.7, 24.4, -80.0, 31.1)),
    "ga": ("georgia", "ga", (-85.7, 30.3, -80.8, 35.1)),
    "id": ("idaho", "id", (-117.3, 42.0, -111.0, 49.1)),
    "il": ("illinois", "il", (-91.6, 36.9, -87.5, 42.6)),
    "in": ("indiana", "in", (-88.2, 37.7, -84.7, 41.8)),
    "ia": ("iowa", "ia", (-96.7, 40.3, -90.1, 43.6)),
    "ks": ("kansas", "ks", (-102.1, 36.9, -94.5, 40.1)),
    "ky": ("kentucky", "ky", (-89.6, 36.4, -81.9, 39.2)),
    "la": ("louisiana", "la", (-94.1, 28.8, -88.7, 33.1)),
    "me": ("maine", "me", (-71.2, 43.0, -66.8, 47.5)),
    "md": ("maryland", "md", (-79.6, 37.8, -75.0, 39.8)),
    "ma": ("massachusetts", "ma", (-73.6, 41.1, -69.8, 42.9)),
    "mi": ("michigan", "mi", (-90.5, 41.6, -82.1, 48.4)),
    "mn": ("minnesota", "mn", (-97.3, 43.4, -89.4, 49.4)),
    "ms": ("mississippi", "ms", (-91.8, 30.1, -88.0, 35.1)),
    "mo": ("missouri", "mo", (-95.8, 35.9, -89.0, 40.7)),
    "mt": ("montana", "mt", (-116.1, 44.3, -104.0, 49.1)),
    "ne": ("nebraska", "ne", (-104.1, 39.9, -95.3, 43.1)),
    "nv": ("nevada", "nv", (-120.1, 35.0, -114.0, 42.1)),
    "nh": ("new-hampshire", "nh", (-72.6, 42.6, -70.6, 45.4)),
    "nj": ("new-jersey", "nj", (-75.6, 38.8, -73.8, 41.4)),
    "nm": ("new-mexico", "nm", (-109.1, 31.2, -103.0, 37.1)),
    "ny": ("new-york", "ny", (-79.8, 40.4, -71.8, 45.1)),
    "nc": ("north-carolina", "nc", (-84.4, 33.7, -75.4, 36.7)),
    "nd": ("north-dakota", "nd", (-104.1, 45.9, -96.5, 49.1)),
    "oh": ("ohio", "oh", (-84.9, 38.3, -80.5, 42.1)),
    "ok": ("oklahoma", "ok", (-103.1, 33.5, -94.4, 37.1)),
    "or": ("oregon", "or", (-124.7, 41.9, -116.4, 46.4)),
    "pa": ("pennsylvania", "pa", (-80.6, 39.7, -74.6, 42.6)),
    "ri": ("rhode-island", "ri", (-71.9, 41.1, -71.1, 42.1)),
    "sc": ("south-carolina", "sc", (-83.4, 32.0, -78.5, 35.3)),
    "sd": ("south-dakota", "sd", (-104.1, 42.4, -96.4, 45.9)),
    "tn": ("tennessee", "tn", (-90.4, 34.9, -81.6, 36.8)),
    "tx": ("texas", "tx", (-106.7, 25.8, -93.5, 36.6)),
    "ut": ("utah", "ut", (-114.1, 36.9, -109.0, 42.1)),
    "vt": ("vermont", "vt", (-73.5, 42.7, -71.4, 45.1)),
    "va": ("virginia", "va", (-83.8, 36.5, -75.2, 39.5)),
    "wa": ("washington", "wa", (-124.9, 45.5, -116.9, 49.1)),
    "wv": ("west-virginia", "wv", (-82.7, 37.1, -77.7, 40.7)),
    "wi": ("wisconsin", "wi", (-92.9, 42.4, -86.7, 47.1)),
    "wy": ("wyoming", "wy", (-111.1, 40.9, -104.0, 45.1)),
}


def _infer_us_state(bounds: ViewBounds | None) -> tuple[str, str] | None:
    if bounds is None:
        return None
    lat = bounds.center_lat if bounds.center_lat is not None else (bounds.south + bounds.north) / 2
    lon = bounds.center_lon if bounds.center_lon is not None else (bounds.west + bounds.east) / 2
    candidates: list[tuple[float, str, str]] = []
    for slug, code, (west, south, east, north) in US_STATE_BBOXES.values():
        if west <= lon <= east and south <= lat <= north:
            candidates.append(((east - west) * (north - south), slug, code))
    if not candidates:
        return None
    _area, slug, code = sorted(candidates)[0]
    return slug, code


def _naip_state_code(bounds: ViewBounds | None) -> str:
    configured = os.getenv("NAIP_AWS_STATE", "").strip().lower()
    if configured:
        return configured
    inferred = _infer_us_state(bounds)
    return inferred[1] if inferred else "nv"


def _naip_year() -> str:
    return os.getenv("NAIP_AWS_YEAR", "2022").strip() or "2022"


def _naip_resolution() -> str:
    return os.getenv("NAIP_AWS_RESOLUTION", "60cm").strip() or "60cm"


def _naip_bandset() -> str:
    return os.getenv("NAIP_AWS_BANDSET", "rgbir").strip() or "rgbir"


def _naip_bucket() -> str:
    return os.getenv("NAIP_AWS_BUCKET", NAIP_AWS_DEFAULT_BUCKET).strip() or NAIP_AWS_DEFAULT_BUCKET


def _naip_s3_prefix(bounds: ViewBounds | None) -> str:
    configured = os.getenv("NAIP_AWS_PREFIX", "").strip().strip("/")
    if configured:
        return f"{configured}/"
    return f"{_naip_state_code(bounds)}/{_naip_year()}/{_naip_resolution()}/{_naip_bandset()}/"


def _geofabrik_region_slug(bounds: ViewBounds | None) -> str:
    configured = os.getenv("GEOFABRIK_REGION_SLUG", "").strip().strip("/")
    if configured:
        return configured
    inferred = _infer_us_state(bounds)
    return f"north-america/us/{inferred[0]}" if inferred else "north-america/us/nevada"


def _geofabrik_osm_pbf_url(bounds: ViewBounds | None) -> str:
    configured = os.getenv("GEOFABRIK_PBF_URL", "").strip()
    if configured:
        return configured
    return f"{GEOFABRIK_BASE_URL}/{_geofabrik_region_slug(bounds)}-latest.osm.pbf"


def _format_lat_token(lat_floor: int) -> str:
    return ("N" if lat_floor >= 0 else "S") + f"{abs(lat_floor):02d}_00"


def _format_lon_token(lon_floor: int) -> str:
    return ("E" if lon_floor >= 0 else "W") + f"{abs(lon_floor):03d}_00"


def _copernicus_dem_tiles(bounds: ViewBounds | None) -> list[dict[str, object]]:
    if bounds is None:
        return []
    lat_start = math.floor(bounds.south)
    lat_end = math.ceil(bounds.north) - 1
    lon_start = math.floor(bounds.west)
    lon_end = math.ceil(bounds.east) - 1
    tiles: list[dict[str, object]] = []
    for lat_floor in range(lat_start, lat_end + 1):
        for lon_floor in range(lon_start, lon_end + 1):
            lat_token = _format_lat_token(lat_floor)
            lon_token = _format_lon_token(lon_floor)
            tile_id = f"Copernicus_DSM_COG_10_{lat_token}_{lon_token}_DEM"
            tiles.append(
                {
                    "tile_id": tile_id,
                    "lat_floor": lat_floor,
                    "lon_floor": lon_floor,
                    "url": f"{COPERNICUS_DEM_30M_BASE_URL}/{tile_id}/{tile_id}.tif",
                }
            )
    return tiles


def _env_path(name: str) -> str:
    configured = os.getenv(name, "").strip()
    if configured:
        return configured
    defaults = {
        "DTED_SOURCE_DIR": ("/DTED", "/mnt/jetson/DTED"),
        "NAIP_EARTHEXPLORER_DIR": (
            "/WINTAK Imagery",
            "/mnt/jetson/WINTAK Imagery",
        ),
        "TERA_WINTAK_IMAGERY_DIR": (
            "/WINTAK Imagery",
            "/mnt/jetson/WINTAK Imagery",
        ),
    }
    for candidate in defaults.get(name, ()):
        path = Path(candidate)
        if path.exists():
            return str(path)
    return ""


def _jetson_local_sources_only() -> bool:
    value = os.getenv("TERA_JETSON_LOCAL_SOURCES_ONLY", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _recent_interval(days: int = 730) -> str:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return f"{start.date().isoformat()}/{end.date().isoformat()}"


def _bbox_area_km2(bounds: ViewBounds | None) -> float:
    if bounds is None:
        return 0.0
    mid_lat = ((bounds.south + bounds.north) / 2.0) * math.pi / 180.0
    width_km = abs(bounds.east - bounds.west) * 111.32 * max(0.1, math.cos(mid_lat))
    height_km = abs(bounds.north - bounds.south) * 111.32
    return width_km * height_km


def _lon_to_tile_x(lon: float, zoom: int) -> int:
    return int((lon + 180.0) / 360.0 * (2**zoom))


def _lat_to_tile_y(lat: float, zoom: int) -> int:
    lat = max(min(lat, 85.05112878), -85.05112878)
    lat_rad = math.radians(lat)
    return int(
        (1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi)
        / 2.0
        * (2**zoom)
    )


def _estimate_slippy_tile_count(bounds: ViewBounds | None, levels: Iterable[int]) -> int:
    if bounds is None:
        return 0
    total = 0
    for zoom in levels:
        x_min = _lon_to_tile_x(bounds.west, zoom)
        x_max = _lon_to_tile_x(bounds.east, zoom)
        y_min = _lat_to_tile_y(bounds.north, zoom)
        y_max = _lat_to_tile_y(bounds.south, zoom)
        total += (abs(x_max - x_min) + 1) * (abs(y_max - y_min) + 1)
    return total


def _choose_imagery_levels(bounds: ViewBounds | None) -> list[int]:
    area_km2 = _bbox_area_km2(bounds)
    if area_km2 <= 0:
        return [10, 11, 12, 13, 14]
    if area_km2 <= 25:
        return [12, 13, 14, 15, 16]
    if area_km2 <= 150:
        return [11, 12, 13, 14, 15]
    if area_km2 <= 800:
        return [10, 11, 12, 13, 14]
    return [8, 9, 10, 11, 12]


def _levels_to_range(levels: list[int]) -> str:
    if not levels:
        return ""
    return f"{min(levels)}-{max(levels)}"


def _parse_level_range(value: object) -> list[int]:
    if isinstance(value, list):
        levels = []
        for item in value:
            try:
                levels.append(int(item))
            except (TypeError, ValueError):
                continue
        return levels
    text = str(value or "").strip()
    if not text:
        return []
    if "-" in text:
        left, _separator, right = text.partition("-")
        try:
            start = int(left)
            end = int(right)
        except ValueError:
            return []
        return list(range(min(start, end), max(start, end) + 1))
    try:
        return [int(text)]
    except ValueError:
        return []


def _tile_ranges(bounds: ViewBounds, levels: Iterable[int]) -> list[tuple[int, range, range]]:
    ranges: list[tuple[int, range, range]] = []
    for zoom in levels:
        x_min = min(_lon_to_tile_x(bounds.west, zoom), _lon_to_tile_x(bounds.east, zoom))
        x_max = max(_lon_to_tile_x(bounds.west, zoom), _lon_to_tile_x(bounds.east, zoom))
        y_min = min(_lat_to_tile_y(bounds.north, zoom), _lat_to_tile_y(bounds.south, zoom))
        y_max = max(_lat_to_tile_y(bounds.north, zoom), _lat_to_tile_y(bounds.south, zoom))
        ranges.append((zoom, range(x_min, x_max + 1), range(y_min, y_max + 1)))
    return ranges


def _choose_terrain_export_size(bounds: ViewBounds | None) -> str:
    area_km2 = _bbox_area_km2(bounds)
    if area_km2 <= 25:
        return "1024,1024"
    if area_km2 <= 150:
        return "1536,1536"
    if area_km2 <= 800:
        return "2048,2048"
    return "4096,4096"


def _sample_points_placeholder(bounds: ViewBounds | None) -> dict[str, object] | str:
    if bounds is None:
        return "{sample_points_multipoint_json}"
    center_lat = bounds.center_lat if bounds.center_lat is not None else (bounds.south + bounds.north) / 2
    center_lon = bounds.center_lon if bounds.center_lon is not None else (bounds.west + bounds.east) / 2
    return {
        "points": [
            [bounds.west, bounds.south],
            [bounds.east, bounds.south],
            [bounds.east, bounds.north],
            [bounds.west, bounds.north],
            [center_lon, center_lat],
        ],
        "spatialReference": {"wkid": 4326},
    }


def _substitute_download_params(
    params: dict[str, object],
    *,
    bounds: ViewBounds | None,
    imagery_levels: list[int],
) -> dict[str, object]:
    substituted: dict[str, object] = {}
    for key, value in params.items():
        if value == "{imagery_level_range}":
            substituted[key] = _levels_to_range(imagery_levels)
        elif value == "{aoi_wgs84_json}":
            substituted[key] = _format_wgs84_extent_json(bounds)
        elif value == "{aoi_bbox_wgs84}":
            substituted[key] = _format_bbox_csv(bounds)
        elif value == "{aoi_bbox_array}":
            substituted[key] = _format_bbox_array(bounds)
        elif value == "{aoi_bbox_radians}":
            substituted[key] = _format_bbox_radians(bounds)
        elif value == "{geofabrik_osm_pbf_url}":
            substituted[key] = _geofabrik_osm_pbf_url(bounds)
        elif value == "{geofabrik_region_slug}":
            substituted[key] = _geofabrik_region_slug(bounds)
        elif value == "{naip_aws_bucket}":
            substituted[key] = _naip_bucket()
        elif value == "{naip_s3_prefix}":
            substituted[key] = _naip_s3_prefix(bounds)
        elif value == "{naip_state}":
            substituted[key] = _naip_state_code(bounds)
        elif value == "{naip_year}":
            substituted[key] = _naip_year()
        elif value == "{naip_resolution}":
            substituted[key] = _naip_resolution()
        elif value == "{naip_bandset}":
            substituted[key] = _naip_bandset()
        elif value == "{naip_max_files}":
            substituted[key] = int(os.getenv("NAIP_MAX_FILES", "50"))
        elif value == "{copernicus_dem_tile_urls}":
            substituted[key] = _copernicus_dem_tiles(bounds)
        elif value == "{terrain_export_size}":
            substituted[key] = _choose_terrain_export_size(bounds)
        elif value == "{sample_points_multipoint_json}":
            substituted[key] = _sample_points_placeholder(bounds)
        elif value == "{recent_24_month_interval}":
            substituted[key] = _recent_interval()
        else:
            substituted[key] = value
    return substituted


def _substitute_download_endpoint(endpoint: str, bounds: ViewBounds | None) -> str:
    return (
        endpoint.replace("{geofabrik_osm_pbf_url}", _geofabrik_osm_pbf_url(bounds))
        .replace("{bucket}", _naip_bucket())
        .replace("${NAIP_EARTHEXPLORER_DIR}", "${NAIP_EARTHEXPLORER_DIR}")
        .replace("${DTED_SOURCE_DIR}", "${DTED_SOURCE_DIR}")
        .replace("${TERA_WINTAK_IMAGERY_DIR}", "${TERA_WINTAK_IMAGERY_DIR}")
    )


def _build_source_download_operations(
    *,
    package_id: str,
    sources: list[SourceOption],
    bounds: ViewBounds | None,
) -> list[dict[str, object]]:
    imagery_levels = _choose_imagery_levels(bounds)
    estimated_imagery_tiles = _estimate_slippy_tile_count(bounds, imagery_levels)
    operations: list[dict[str, object]] = []

    for source in sources:
        for method in source.download_methods:
            if _jetson_local_sources_only() and method.id in {
                "naip_aws_public_prefix",
                "osm_geofabrik_pbf",
                "copernicus_dem_glo30_cog",
                "sentinel2_cog_download",
                "usgs_imagery_tile_cache",
                "nrl_naip_tile_cache",
                "esri_world_imagery_export_tiles",
                "esri_world_elevation_export_image_tiff",
                "esri_world_elevation_get_samples",
                "cesium_ion_archive_download",
                "cesium_ion_clip_create_download",
            }:
                continue
            if source.id == "cesium_ion_archive":
                archive_id_configured = bool(_get_cesium_archive_id())
                asset_ids_configured = bool(
                    (
                        os.getenv("CESIUM_ION_ASSET_IDS")
                        or os.getenv("CESIUM_ASSET_IDS")
                        or os.getenv("CESIUM_ION_ASSET_ID")
                        or ""
                    ).strip()
                )
                if method.id == "cesium_ion_archive_download" and not archive_id_configured:
                    continue
                if method.id == "cesium_ion_clip_create_download" and (
                    archive_id_configured or not asset_ids_configured
                ):
                    continue
            if method.id == "naip_earthexplorer_geotiff_import" and not _env_path("NAIP_EARTHEXPLORER_DIR"):
                continue
            if method.id == "osm_wintak_imagery_import" and not _env_path(
                "TERA_WINTAK_IMAGERY_DIR"
            ):
                continue
            if method.id == "dted_earthexplorer_import_convert" and not _env_path("DTED_SOURCE_DIR"):
                continue
            local_artifact = method.local_artifact_template.replace("{package_id}", package_id)
            operation: dict[str, object] = {
                "id": method.id,
                "source_id": source.id,
                "source_name": source.name,
                "label": method.label,
                "method": method.method,
                "endpoint": _substitute_download_endpoint(method.endpoint, bounds),
                "params": _substitute_download_params(
                    method.params,
                    bounds=bounds,
                    imagery_levels=imagery_levels,
                ),
                "output_format": method.output_format,
                "local_artifact": local_artifact,
                "requires_token_env": method.requires_token_env,
                "requires_account": method.requires_account,
                "terms_url": method.terms_url,
                "notes": method.notes,
            }
            if source.id == "esri_world_imagery":
                operation["estimated_tile_count"] = estimated_imagery_tiles
                operation["tile_limit_warning"] = (
                    "Estimated AO exceeds Esri's common 100,000 tile export limit; "
                    "reduce AO or zoom levels."
                    if estimated_imagery_tiles > 100000
                    else ""
                )
            if source.id == "sentinel_2":
                operation["free_imagery_source"] = True
                operation["requires_account"] = False
            if method.id in {"usgs_imagery_tile_cache", "nrl_naip_tile_cache"}:
                levels = _parse_level_range(operation["params"].get("levels") if isinstance(operation.get("params"), dict) else "")
                if isinstance(operation.get("params"), dict):
                    max_zoom = int(operation["params"].get("max_zoom") or max(levels or [0]))
                    levels = [level for level in levels if level <= max_zoom]
                operation["estimated_tile_count"] = _estimate_slippy_tile_count(bounds, levels)
                operation["free_imagery_source"] = True
                operation["tile_limit_warning"] = (
                    "Estimated tile cache is large; reduce AO or zoom levels before Jetson download."
                    if int(operation["estimated_tile_count"]) > int(os.getenv("MAX_TILE_DOWNLOAD_COUNT", "5000"))
                    else ""
                )
            operations.append(operation)

    return operations


def _build_jetson_query_contracts(
    *,
    package_id: str,
    sources: list[SourceOption],
) -> list[dict[str, object]]:
    contracts: list[dict[str, object]] = []
    for source in sources:
        for query_format in source.jetson_query_formats:
            contracts.append(
                {
                    "source_id": source.id,
                    "source_name": source.name,
                    "artifact_type": query_format.artifact_type,
                    "local_path": query_format.local_path_template.replace(
                        "{package_id}",
                        package_id,
                    ),
                    "query_interfaces": query_format.query_interfaces,
                    "feeds_algorithms": query_format.feeds_algorithms,
                    "notes": query_format.notes,
                }
            )
    return contracts


def _offline_package_root() -> Path:
    configured = os.getenv("OFFLINE_PACKAGE_ROOT", "").strip()
    return Path(configured).expanduser().resolve() if configured else DEFAULT_OFFLINE_PACKAGE_ROOT.resolve()


def _package_reserve_bytes() -> int:
    gb = float(os.getenv("PACKAGE_MIN_FREE_GB", "10"))
    return max(0, int(gb * 1024 * 1024 * 1024))


def _safe_package_id(package_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "-", package_id).strip(".-")
    if not safe:
        raise HTTPException(status_code=400, detail="Invalid package id.")
    return safe[:120]


def _package_dir(package_id: str) -> Path:
    root = _offline_package_root()
    package_path = (root / _safe_package_id(package_id)).resolve()
    if root not in (package_path, *package_path.parents):
        raise HTTPException(status_code=400, detail="Package path escapes package root.")
    return package_path


def _existing_disk_path(path: Path) -> Path:
    cursor = path
    while not cursor.exists() and cursor.parent != cursor:
        cursor = cursor.parent
    return cursor


def _directory_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except OSError:
            continue
    return total


def _storage_info(package_id: str | None = None) -> StorageInfoResponse:
    root = _offline_package_root()
    usage = shutil.disk_usage(_existing_disk_path(root))
    reserved = _package_reserve_bytes()
    existing = _directory_size_bytes(_package_dir(package_id)) if package_id else (
        _directory_size_bytes(root) if root.exists() else 0
    )
    usable = max(0, int(usage.free) - reserved)
    return StorageInfoResponse(
        package_root=str(root),
        total_bytes=int(usage.total),
        used_bytes=int(usage.used),
        free_bytes=int(usage.free),
        reserved_bytes=reserved,
        usable_bytes=usable,
        existing_package_bytes=existing,
    )


def _parse_size_param(value: object) -> tuple[int, int]:
    if isinstance(value, str):
        left, _separator, right = value.partition(",")
        try:
            return max(1, int(left)), max(1, int(right))
        except ValueError:
            return 1024, 1024
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            return max(1, int(value[0])), max(1, int(value[1]))
        except (TypeError, ValueError):
            return 1024, 1024
    return 1024, 1024


def _estimate_operation_bytes(operation: dict[str, object]) -> int:
    operation_id = str(operation.get("id", ""))
    if operation_id in {"usgs_imagery_tile_cache", "nrl_naip_tile_cache"}:
        tile_count = int(operation.get("estimated_tile_count") or 0)
        avg_tile_bytes = int(os.getenv("OPEN_TILE_ESTIMATED_BYTES", "80000"))
        return max(10 * 1024 * 1024, tile_count * avg_tile_bytes)
    if operation_id == "sentinel_2_stac_cog":
        params = operation.get("params")
        assets = params.get("assets") if isinstance(params, dict) else []
        asset_count = len(assets) if isinstance(assets, list) else 4
        avg_asset_bytes = int(os.getenv("SENTINEL2_ESTIMATED_ASSET_BYTES", str(80 * 1024 * 1024)))
        return max(100 * 1024 * 1024, asset_count * avg_asset_bytes)
    if operation_id == "esri_world_imagery_export_tiles":
        tile_count = int(operation.get("estimated_tile_count") or 0)
        avg_tile_bytes = int(os.getenv("ESRI_ESTIMATED_TILE_BYTES", "50000"))
        return max(20 * 1024 * 1024, tile_count * avg_tile_bytes)
    if operation_id == "esri_world_elevation_export_image_tiff":
        params = operation.get("params")
        width, height = _parse_size_param(params.get("size") if isinstance(params, dict) else None)
        return int(width * height * 4 * 1.5) + (8 * 1024 * 1024)
    if operation_id == "esri_world_elevation_get_samples":
        return 512 * 1024
    if operation_id in {"cesium_ion_archive_download", "cesium_ion_clip_create_download"}:
        return int(os.getenv("CESIUM_ARCHIVE_ESTIMATED_BYTES", str(2 * 1024 * 1024 * 1024)))
    if operation_id == "naip_aws_public_prefix":
        params = operation.get("params")
        max_files_value = params.get("max_files") if isinstance(params, dict) else None
        max_files = int(max_files_value or os.getenv("NAIP_MAX_FILES", "50"))
        avg_bytes = int(os.getenv("NAIP_ESTIMATED_FILE_BYTES", str(25 * 1024 * 1024)))
        return max(50 * 1024 * 1024, max_files * avg_bytes)
    if operation_id == "naip_earthexplorer_geotiff_import":
        max_files = int(os.getenv("NAIP_MAX_FILES", "50"))
        avg_bytes = int(os.getenv("NAIP_ESTIMATED_FILE_BYTES", str(25 * 1024 * 1024)))
        return max(50 * 1024 * 1024, max_files * avg_bytes)
    if operation_id == "osm_geofabrik_pbf":
        return int(os.getenv("GEOFABRIK_ESTIMATED_BYTES", str(750 * 1024 * 1024)))
    if operation_id == "copernicus_dem_glo30_cog":
        params = operation.get("params")
        tiles = params.get("tile_urls") if isinstance(params, dict) else []
        tile_count = len(tiles) if isinstance(tiles, list) else 1
        avg_bytes = int(os.getenv("COPERNICUS_DEM_ESTIMATED_TILE_BYTES", str(25 * 1024 * 1024)))
        return max(25 * 1024 * 1024, tile_count * avg_bytes)
    if operation_id == "dted_earthexplorer_import_convert":
        max_files = int(os.getenv("DTED_IMPORT_MAX_FILES", "100"))
        avg_bytes = int(os.getenv("DTED_ESTIMATED_FILE_BYTES", str(25 * 1024 * 1024)))
        return max(25 * 1024 * 1024, max_files * avg_bytes)
    return 0


def _estimate_manifest_bytes(manifest: dict[str, object]) -> int:
    operations = manifest.get("download_operations")
    if not isinstance(operations, list):
        return 0
    return sum(
        _estimate_operation_bytes(operation)
        for operation in operations
        if isinstance(operation, dict)
    )


def _storage_warning(estimated_bytes: int, storage: StorageInfoResponse) -> str | None:
    if estimated_bytes <= storage.usable_bytes:
        return None
    shortage = estimated_bytes - storage.usable_bytes
    return (
        "Estimated package size exceeds Jetson usable storage after reserve "
        f"by {shortage} bytes."
    )


def _relative_artifact_path(local_artifact: object, package_id: str) -> Path:
    raw = str(local_artifact or "").replace("\\", "/").strip("/")
    parts = [part for part in raw.split("/") if part and part not in {".", ".."}]
    if package_id in parts:
        parts = parts[parts.index(package_id) + 1 :]
    elif parts[:2] == ["offline_packages", package_id]:
        parts = parts[2:]
    if not parts:
        parts = ["artifacts", "artifact.bin"]
    return Path(*parts)


def _artifact_path(package_id: str, local_artifact: object) -> Path:
    package_path = _package_dir(package_id)
    artifact_path = (package_path / _relative_artifact_path(local_artifact, package_id)).resolve()
    if package_path not in (artifact_path, *artifact_path.parents):
        raise HTTPException(status_code=400, detail="Artifact path escapes package root.")
    return artifact_path


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _runtime_dir() -> Path:
    configured = os.getenv("TERA_RUNTIME_DIR", "").strip()
    runtime_dir = Path(configured).expanduser().resolve() if configured else (
        _offline_package_root() / "runtime"
    )
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir


def _atak_mirror_log_path() -> Path:
    configured = os.getenv("TERA_ATAK_MIRROR_LOG", "").strip()
    return Path(configured).expanduser().resolve() if configured else (
        _runtime_dir() / "atak_agent_mirror.jsonl"
    )


def _append_atak_mirror_event(
    *,
    source: str,
    role: str,
    text: str,
    model: str | None = None,
    provider: str | None = None,
    direction: str | None = None,
    client_location: MapPoint | None = None,
    view_bounds: ViewBounds | None = None,
    query_context: dict[str, Any] | None = None,
    tak_cot_summary: dict[str, Any] | None = None,
) -> JetsonAtakMirrorEvent:
    event = JetsonAtakMirrorEvent(
        id=str(uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        source=source,
        role=role,
        text=text,
        model=model,
        provider=provider,
        direction=direction,
        client_location=client_location,
        view_bounds=view_bounds,
        query_context=query_context or {},
        tak_cot_summary=tak_cot_summary or {},
    )
    path = _atak_mirror_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(event.model_dump_json() + "\n")
    return event


def _read_atak_mirror_events(limit: int = 80) -> list[JetsonAtakMirrorEvent]:
    path = _atak_mirror_log_path()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    events: list[JetsonAtakMirrorEvent] = []
    for line in lines[-max(1, min(limit, 200)) :]:
        try:
            events.append(JetsonAtakMirrorEvent.model_validate_json(line))
        except ValueError:
            continue
    return events


def _request_is_atak_mirror_candidate(request: PromptRequest) -> bool:
    profile = (request.agent_profile or "").strip().lower()
    return bool(JETSON_ATAK_MODE.get("active")) or "atak" in profile


def _mirror_source_for_request(request: PromptRequest) -> str:
    profile = (request.agent_profile or "").strip().lower()
    if bool(JETSON_ATAK_MODE.get("active")) or "atak" in profile:
        return "atak-plugin"
    return "web-planner"


def _coerce_atak_prompt_request(request: PromptRequest) -> PromptRequest:
    if not bool(JETSON_ATAK_MODE.get("active")):
        return request

    profile = (request.agent_profile or "").strip().lower()
    if "atak" in profile and (request.llm_provider or "").strip().lower() == "ollama":
        return request

    return request.model_copy(
        update={
            "agent_profile": str(
                JETSON_ATAK_MODE.get("agent_profile") or TERA_ATAK_AGENT_PROFILE
            ),
            "llm_provider": "ollama",
            "model": request.model or str(JETSON_ATAK_MODE.get("model") or TERA_ATAK_MODEL),
        }
    )


def _jetson_atak_response(detail: str | None = None) -> JetsonAtakModeResponse:
    return JetsonAtakModeResponse(
        active=bool(JETSON_ATAK_MODE.get("active")),
        status=str(JETSON_ATAK_MODE.get("status") or "idle"),
        detail=detail or str(JETSON_ATAK_MODE.get("detail") or ""),
        model=str(JETSON_ATAK_MODE.get("model") or TERA_ATAK_MODEL),
        provider=str(JETSON_ATAK_MODE.get("provider") or "ollama"),
        agent_profile=str(
            JETSON_ATAK_MODE.get("agent_profile") or TERA_ATAK_AGENT_PROFILE
        ),
        atak_device_url=JETSON_ATAK_MODE.get("atak_device_url"),
        ollama_base_url=JETSON_ATAK_MODE.get("ollama_base_url"),
        ollama_ready=bool(JETSON_ATAK_MODE.get("ollama_ready")),
        jetson_ip=JETSON_ATAK_MODE.get("jetson_ip"),
        plugin_endpoint=JETSON_ATAK_MODE.get("plugin_endpoint"),
        mirror_url="/api/jetson/atak-agent/mirror",
        events=_read_atak_mirror_events(),
    )


def _normalize_ollama_model_name(model: str | None) -> str:
    candidate = (model or TERA_ATAK_MODEL).strip() or TERA_ATAK_MODEL
    compact = candidate.lower().replace(" ", "")
    if compact in {"gemma3:4", "gemma-3:4", "gemma3-4"}:
        return "gemma3:4b"
    return candidate


def _ollama_model_is_available(models: list[str], model: str) -> bool:
    requested = _normalize_ollama_model_name(model)
    requested_name = requested.split(":", 1)[0]
    for installed in models:
        if installed == requested:
            return True
        if ":" not in requested and installed.split(":", 1)[0] == requested_name:
            return True
    return False


def _public_base_url_from_request(http_request: Request | None = None) -> str | None:
    if TERA_PUBLIC_BASE_URL:
        return TERA_PUBLIC_BASE_URL
    if http_request is not None:
        forwarded_host = http_request.headers.get("x-forwarded-host", "").strip()
        host = forwarded_host or http_request.headers.get("host", "").strip()
        if host:
            scheme = (
                http_request.headers.get("x-forwarded-proto", "").strip()
                or http_request.url.scheme
                or "http"
            )
            return f"{scheme}://{host}".rstrip("/")
    if TERA_JETSON_IP:
        return f"http://{TERA_JETSON_IP}:8080"
    return None


def _plugin_endpoint_for_request(
    http_request: Request | None = None,
) -> tuple[str | None, str | None]:
    base_url = _public_base_url_from_request(http_request)
    if not base_url:
        return None, None
    host = base_url.split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0]
    return host, f"{base_url.rstrip('/')}/api/prompt"


def _start_jetson_atak_command(
    *, model: str, agent_profile: str, atak_device_url: str | None
) -> str | None:
    global JETSON_ATAK_PROCESS
    if not TERA_ATAK_ACTIVATE_COMMAND:
        return None
    if JETSON_ATAK_PROCESS and JETSON_ATAK_PROCESS.poll() is None:
        return f"activation command already running with pid {JETSON_ATAK_PROCESS.pid}"

    args = shlex.split(TERA_ATAK_ACTIVATE_COMMAND)
    if not args:
        return None

    command_log_path = _runtime_dir() / "atak_agent_command.log"
    env = os.environ.copy()
    env.update(
        {
            "OLLAMA_MODEL": model,
            "TERA_GEMMA_MODEL": model,
            "TERA_PHASE": "3",
            "TERA_DEVICE_PROFILE": "austere",
            "TERA_ATAK_AGENT_PROFILE": agent_profile,
            "TERA_ATAK_MIRROR_LOG": str(_atak_mirror_log_path()),
        }
    )
    if atak_device_url:
        env["TERA_ATAK_DEVICE_URL"] = atak_device_url

    with command_log_path.open("ab") as command_log:
        JETSON_ATAK_PROCESS = subprocess.Popen(
            args,
            cwd=str(BASE_DIR.parent),
            env=env,
            stdout=command_log,
            stderr=subprocess.STDOUT,
        )
    return f"activation command started with pid {JETSON_ATAK_PROCESS.pid}"


def _manifest_path(package_id: str) -> Path:
    return _package_dir(package_id) / "manifest.json"


def _status_path(package_id: str) -> Path:
    return _package_dir(package_id) / "status.json"


def _artifacts_path(package_id: str) -> Path:
    return _package_dir(package_id) / "artifacts.json"


def _routes_dir(package_id: str) -> Path:
    return _package_dir(package_id) / "routes"


def _cot_dir(package_id: str) -> Path:
    return _package_dir(package_id) / "cot"


def _load_package_manifest(package_id: str) -> dict[str, Any] | None:
    manifest = PACKAGE_MANIFESTS.get(package_id)
    if isinstance(manifest, dict):
        return manifest
    disk_manifest = _read_json(_manifest_path(package_id))
    if disk_manifest is not None:
        PACKAGE_MANIFESTS[package_id] = disk_manifest
    return disk_manifest


def _persist_package_manifest(package_id: str, manifest: dict[str, object]) -> None:
    package_path = _package_dir(package_id)
    package_path.mkdir(parents=True, exist_ok=True)
    _write_json(_manifest_path(package_id), manifest)


def _empty_artifact_registry(package_id: str) -> dict[str, Any]:
    manifest = _load_package_manifest(package_id) or {}
    return {
        "package_id": package_id,
        "package_name": manifest.get("package_name", package_id),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "artifacts": [],
    }


def _load_artifact_registry(package_id: str) -> dict[str, Any]:
    registry = _read_json(_artifacts_path(package_id))
    if registry is None:
        return _empty_artifact_registry(package_id)
    registry.setdefault("artifacts", [])
    return registry


def _save_artifact_registry(package_id: str, registry: dict[str, Any]) -> None:
    registry["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(_artifacts_path(package_id), registry)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _operation_status(
    operation: dict[str, object],
    *,
    state: str = "planned",
    message: str = "",
) -> dict[str, object]:
    return {
        "id": operation.get("id"),
        "source_id": operation.get("source_id"),
        "source_name": operation.get("source_name"),
        "state": state,
        "message": message,
        "estimated_bytes": _estimate_operation_bytes(operation),
        "bytes_written": 0,
        "artifact_path": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _initial_package_status(package_id: str, manifest: dict[str, object]) -> dict[str, Any]:
    operations = [
        _operation_status(operation)
        for operation in manifest.get("download_operations", [])
        if isinstance(operation, dict)
    ]
    return {
        "package_id": package_id,
        "package_name": manifest.get("package_name", package_id),
        "state": "planned",
        "message": "Package manifest is ready. Downloads have not started.",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "estimated_bytes": _estimate_manifest_bytes(manifest),
        "bytes_written": 0,
        "operations": operations,
    }


def _load_package_status(package_id: str) -> dict[str, Any]:
    status = _read_json(_status_path(package_id))
    if status is not None:
        return status
    manifest = _load_package_manifest(package_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Source package manifest not found.")
    return _initial_package_status(package_id, manifest)


def _save_package_status(package_id: str, status: dict[str, Any]) -> None:
    status["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(_status_path(package_id), status)


def _update_operation_status(
    status: dict[str, Any],
    operation_id: str,
    *,
    state: str,
    message: str = "",
    bytes_written: int | None = None,
    artifact_path: str | None = None,
) -> None:
    for operation in status.get("operations", []):
        if operation.get("id") == operation_id:
            operation["state"] = state
            operation["message"] = message
            operation["updated_at"] = datetime.now(timezone.utc).isoformat()
            if bytes_written is not None:
                operation["bytes_written"] = bytes_written
            if artifact_path is not None:
                operation["artifact_path"] = artifact_path
            break
    status["bytes_written"] = sum(
        int(operation.get("bytes_written") or 0)
        for operation in status.get("operations", [])
        if isinstance(operation, dict)
    )


def _get_esri_token() -> str:
    return (
        os.getenv("ESRI_ARCGIS_TOKEN")
        or os.getenv("ARCGIS_TOKEN")
        or os.getenv("ESRI_ACCESS_TOKEN")
        or ""
    ).strip()


def _get_cesium_token() -> str:
    return (
        os.getenv("CESIUM_ION_TOKEN")
        or os.getenv("CESIUM_TOKEN")
        or os.getenv("CESIUM_ACCESS_TOKEN")
        or os.getenv("CESIUM_ION_ACCESS_TOKEN")
        or ""
    ).strip()


def _get_cesium_archive_id() -> str:
    return (os.getenv("CESIUM_ION_ARCHIVE_ID") or os.getenv("CESIUM_ARCHIVE_ID") or "").strip()


def _get_cesium_asset_ids() -> list[int]:
    raw = (
        os.getenv("CESIUM_ION_ASSET_IDS")
        or os.getenv("CESIUM_ASSET_IDS")
        or os.getenv("CESIUM_ION_ASSET_ID")
        or ""
    )
    asset_ids: list[int] = []
    for item in re.split(r"[,;\s]+", raw.strip()):
        if not item:
            continue
        try:
            asset_ids.append(int(item))
        except ValueError as error:
            raise RuntimeError(f"Invalid Cesium asset id: {item}") from error
    return asset_ids


def _params_with_runtime_token(params: dict[str, object]) -> dict[str, object]:
    materialized: dict[str, object] = {}
    for key, value in params.items():
        if value == "${ESRI_ARCGIS_TOKEN}":
            token = _get_esri_token()
            if not token:
                raise RuntimeError("ESRI_ARCGIS_TOKEN is required on the Jetson for Esri downloads.")
            materialized[key] = token
        elif value == "${CESIUM_ION_TOKEN}":
            token = _get_cesium_token()
            if not token:
                raise RuntimeError("CESIUM_ION_TOKEN is required on the Jetson for Cesium archive downloads.")
            materialized[key] = token
        elif value == "${CESIUM_ION_ARCHIVE_ID}":
            archive_id = _get_cesium_archive_id()
            if not archive_id:
                raise RuntimeError(
                    "CESIUM_ION_ARCHIVE_ID is required to download a prebuilt Cesium archive."
                )
            materialized[key] = archive_id
        elif value == "${CESIUM_ION_ASSET_IDS}":
            asset_ids = _get_cesium_asset_ids()
            if not asset_ids:
                raise RuntimeError(
                    "CESIUM_ION_ASSET_IDS is required to create and download a Cesium AO clip."
                )
            materialized[key] = asset_ids
        elif value == "${NAIP_EARTHEXPLORER_DIR}":
            source_dir = _env_path("NAIP_EARTHEXPLORER_DIR")
            if not source_dir:
                raise RuntimeError("NAIP_EARTHEXPLORER_DIR is required to import staged NAIP GeoTIFFs.")
            materialized[key] = source_dir
        elif value == "${DTED_SOURCE_DIR}":
            source_dir = _env_path("DTED_SOURCE_DIR")
            if not source_dir:
                raise RuntimeError("DTED_SOURCE_DIR is required to import staged EarthExplorer DTED files.")
            materialized[key] = source_dir
        elif value == "${TERA_WINTAK_IMAGERY_DIR}":
            source_dir = _env_path("TERA_WINTAK_IMAGERY_DIR")
            if not source_dir:
                raise RuntimeError(
                    "TERA_WINTAK_IMAGERY_DIR is required to index staged WinTAK imagery files."
                )
            materialized[key] = source_dir
        else:
            materialized[key] = json.dumps(value) if isinstance(value, dict) else value
    return materialized


def _raise_for_esri_error(payload: dict[str, Any]) -> None:
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message") or error.get("details") or "Esri service error."
        raise RuntimeError(str(message))


def _extract_url_recursive(value: Any, base_url: str) -> str | None:
    if isinstance(value, str):
        lower = value.lower()
        if lower.startswith("http://") or lower.startswith("https://"):
            return value
        if any(suffix in lower for suffix in (".tpkx", ".tpk", ".zip", ".tif", ".tiff")):
            return urljoin(base_url, value)
    if isinstance(value, dict):
        for key in ("url", "href", "value", "itemUrl", "resultUrl", "paramUrl"):
            found = _extract_url_recursive(value.get(key), base_url)
            if found:
                return found
        for child in value.values():
            found = _extract_url_recursive(child, base_url)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = _extract_url_recursive(child, base_url)
            if found:
                return found
    return None


async def _request_esri_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    params: dict[str, object],
) -> dict[str, Any]:
    if method.upper() == "POST":
        response = await client.post(url, data=params)
    else:
        response = await client.get(url, params=params)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Esri response was not a JSON object.")
    _raise_for_esri_error(payload)
    return payload


async def _download_binary(
    client: httpx.AsyncClient,
    url: str,
    path: Path,
    *,
    params: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    bytes_written = 0
    async with client.stream("GET", url, params=params, headers=headers) as response:
        response.raise_for_status()
        with path.open("wb") as handle:
            async for chunk in response.aiter_bytes():
                if not chunk:
                    continue
                handle.write(chunk)
                bytes_written += len(chunk)
    return bytes_written


async def _poll_esri_export_job(
    client: httpx.AsyncClient,
    *,
    operation_endpoint: str,
    job_id: str,
    token: str,
) -> dict[str, Any]:
    service_url = operation_endpoint.rsplit("/exportTiles", 1)[0]
    job_url = f"{service_url}/jobs/{job_id}"
    for _attempt in range(ESRI_TILE_EXPORT_MAX_POLLS):
        payload = await _request_esri_json(
            client,
            "GET",
            job_url,
            {"f": "json", "token": token},
        )
        job_status = str(payload.get("jobStatus") or payload.get("status") or "").lower()
        if "failed" in job_status or "cancelled" in job_status:
            raise RuntimeError(f"Esri export job {job_id} ended with {job_status}.")
        if "succeeded" in job_status or "completed" in job_status:
            return payload
        await asyncio.sleep(ESRI_TILE_EXPORT_POLL_INTERVAL_S)
    raise RuntimeError(f"Timed out waiting for Esri export job {job_id}.")


def _copy_or_create_cog(src_path: Path, cog_path: Path) -> bool:
    cog_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import rasterio

        with rasterio.open(src_path) as src:
            profile = src.profile.copy()
            profile.update(
                driver="GTiff",
                tiled=True,
                blockxsize=256,
                blockysize=256,
                compress="deflate",
                BIGTIFF="IF_SAFER",
            )
            with rasterio.open(cog_path, "w", **profile) as dst:
                for index in range(1, src.count + 1):
                    dst.write(src.read(index), index)
        return True
    except Exception as error:
        log.warning("cog_conversion_fallback", error=str(error))
        shutil.copyfile(src_path, cog_path)
        return False


def _artifact_record(
    *,
    package_id: str,
    operation: dict[str, object],
    path: Path,
    artifact_type: str,
    output_format: str,
    query_interfaces: list[str] | None = None,
    feeds_algorithms: list[str] | None = None,
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    package_path = _package_dir(package_id)
    relative_path = path.resolve().relative_to(package_path).as_posix()
    return {
        "artifact_id": f"{operation.get('id')}-{hashlib.sha256(relative_path.encode()).hexdigest()[:8]}",
        "source_id": operation.get("source_id"),
        "source_name": operation.get("source_name"),
        "operation_id": operation.get("id"),
        "artifact_type": artifact_type,
        "format": output_format,
        "path": str(path),
        "relative_path": relative_path,
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": _sha256_file(path) if path.exists() and path.is_file() else "",
        "query_interfaces": query_interfaces or [],
        "feeds_algorithms": feeds_algorithms or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }


def _query_contract_for_operation(
    manifest: dict[str, object],
    operation: dict[str, object],
) -> dict[str, object] | None:
    source_id = operation.get("source_id")
    contracts = manifest.get("jetson_query_contracts")
    if not isinstance(contracts, list):
        return None
    for contract in contracts:
        if isinstance(contract, dict) and contract.get("source_id") == source_id:
            return contract
    return None


async def _execute_esri_imagery_export(
    client: httpx.AsyncClient,
    *,
    package_id: str,
    manifest: dict[str, object],
    operation: dict[str, object],
) -> dict[str, object]:
    params = _params_with_runtime_token(operation.get("params") if isinstance(operation.get("params"), dict) else {})
    endpoint = str(operation["endpoint"])
    submit_payload = await _request_esri_json(client, str(operation.get("method", "POST")), endpoint, params)
    package_url = _extract_url_recursive(submit_payload, endpoint)
    job_id = str(submit_payload.get("jobId") or submit_payload.get("job_id") or "").strip()
    if not package_url and job_id:
        poll_payload = await _poll_esri_export_job(
            client,
            operation_endpoint=endpoint,
            job_id=job_id,
            token=str(params["token"]),
        )
        package_url = _extract_url_recursive(poll_payload, endpoint)
    if not package_url:
        raise RuntimeError("Esri imagery export did not return a downloadable tile package URL.")

    path = _artifact_path(package_id, operation.get("local_artifact"))
    await _download_binary(client, package_url, path, params={"token": params["token"]})
    contract = _query_contract_for_operation(manifest, operation) or {}
    return _artifact_record(
        package_id=package_id,
        operation=operation,
        path=path,
        artifact_type=str(contract.get("artifact_type") or "esri_tpkx_imagery_package"),
        output_format=str(operation.get("output_format") or "TPKX tile package"),
        query_interfaces=list(contract.get("query_interfaces") or ["package_metadata()"]),
        feeds_algorithms=list(contract.get("feeds_algorithms") or ["operator_route_review"]),
        metadata={
            "download_url_redacted": True,
            "job_id": job_id or None,
            "estimated_tile_count": operation.get("estimated_tile_count"),
            "tile_limit_warning": operation.get("tile_limit_warning"),
        },
    )


async def _execute_esri_terrain_export(
    client: httpx.AsyncClient,
    *,
    package_id: str,
    manifest: dict[str, object],
    operation: dict[str, object],
) -> list[dict[str, object]]:
    params = _params_with_runtime_token(operation.get("params") if isinstance(operation.get("params"), dict) else {})
    endpoint = str(operation["endpoint"])
    raw_path = _artifact_path(package_id, operation.get("local_artifact"))
    if str(operation.get("method", "POST")).upper() == "POST":
        response = await client.post(endpoint, data=params)
    else:
        response = await client.get(endpoint, params=params)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "json" in content_type:
        payload = response.json()
        _raise_for_esri_error(payload)
        href = _extract_url_recursive(payload, endpoint)
        if not href:
            raise RuntimeError("Esri terrain export returned JSON without a raster URL.")
        await _download_binary(client, href, raw_path, params={"token": params["token"]})
    else:
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(response.content)

    cog_path = raw_path.with_name("dem_cog.tif")
    cog_native = _copy_or_create_cog(raw_path, cog_path)
    contract = _query_contract_for_operation(manifest, operation) or {}
    common_metadata = {
        "bbox": params.get("bbox"),
        "bboxSR": params.get("bboxSR"),
        "imageSR": params.get("imageSR"),
        "size": params.get("size"),
        "pixelType": params.get("pixelType"),
    }
    return [
        _artifact_record(
            package_id=package_id,
            operation=operation,
            path=raw_path,
            artifact_type="geotiff_dem",
            output_format="GeoTIFF DEM",
            query_interfaces=["rasterio.open()", "read_window()"],
            feeds_algorithms=["terrain_derivatives"],
            metadata=common_metadata,
        ),
        _artifact_record(
            package_id=package_id,
            operation=operation,
            path=cog_path,
            artifact_type=str(contract.get("artifact_type") or "cloud_optimized_geotiff_dem"),
            output_format="COG GeoTIFF DEM" if cog_native else "GeoTIFF DEM copied to COG path",
            query_interfaces=list(contract.get("query_interfaces") or ["sample_dem(lat, lon)", "read_window(west, south, east, north)"]),
            feeds_algorithms=list(contract.get("feeds_algorithms") or ["terrain_derivatives", "raster_cost_distance", "viewshed"]),
            metadata={**common_metadata, "cog_native": cog_native},
        ),
    ]


async def _execute_esri_samples(
    client: httpx.AsyncClient,
    *,
    package_id: str,
    operation: dict[str, object],
) -> dict[str, object]:
    params = _params_with_runtime_token(operation.get("params") if isinstance(operation.get("params"), dict) else {})
    endpoint = str(operation["endpoint"])
    payload = await _request_esri_json(client, str(operation.get("method", "POST")), endpoint, params)
    path = _artifact_path(package_id, operation.get("local_artifact"))
    _write_json(path, payload)
    return _artifact_record(
        package_id=package_id,
        operation=operation,
        path=path,
        artifact_type="elevation_samples_json",
        output_format="JSON elevation samples",
        query_interfaces=["sample_points()"],
        feeds_algorithms=["terrain_preflight"],
        metadata={"sample_count": len(payload.get("samples", [])) if isinstance(payload.get("samples"), list) else None},
    )


async def _execute_sentinel2_stac_cogs(
    client: httpx.AsyncClient,
    *,
    package_id: str,
    operation: dict[str, object],
) -> list[dict[str, object]]:
    params = operation.get("params") if isinstance(operation.get("params"), dict) else {}
    search_payload = {key: value for key, value in params.items() if key != "assets"}
    requested_assets = params.get("assets")
    asset_names = requested_assets if isinstance(requested_assets, list) else ["visual", "red", "green", "blue", "nir"]
    response = await client.post(str(operation["endpoint"]), json=search_payload)
    response.raise_for_status()
    payload = response.json()
    features = payload.get("features", []) if isinstance(payload, dict) else []
    if not features:
        raise RuntimeError("Earth Search returned no Sentinel-2 scenes for the AO/date/cloud filters.")
    item = features[0]
    if not isinstance(item, dict):
        raise RuntimeError("Earth Search returned an invalid Sentinel-2 item.")
    item_id = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(item.get("id") or "sentinel2")).strip("-")
    assets = item.get("assets", {})
    if not isinstance(assets, dict):
        raise RuntimeError("Sentinel-2 STAC item does not contain assets.")

    base_dir = _package_dir(package_id) / "imagery" / "sentinel_2"
    base_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = base_dir / f"{item_id}_stac_item.json"
    _write_json(metadata_path, item)
    records = [
        _artifact_record(
            package_id=package_id,
            operation=operation,
            path=metadata_path,
            artifact_type="sentinel2_stac_item",
            output_format="STAC Item JSON",
            query_interfaces=["stac_metadata()"],
            feeds_algorithms=["imagery_provenance"],
            metadata={
                "collection": item.get("collection"),
                "datetime": (item.get("properties") or {}).get("datetime")
                if isinstance(item.get("properties"), dict)
                else None,
            },
        )
    ]

    for asset_name in asset_names:
        asset = assets.get(str(asset_name))
        if not isinstance(asset, dict):
            continue
        href = str(asset.get("href") or "")
        if not href.lower().startswith(("http://", "https://")):
            continue
        suffix = ".tif"
        if href.lower().split("?", 1)[0].endswith(".jp2"):
            suffix = ".jp2"
        asset_path = base_dir / f"{item_id}_{asset_name}{suffix}"
        await _download_binary(client, href, asset_path)
        records.append(
            _artifact_record(
                package_id=package_id,
                operation=operation,
                path=asset_path,
                artifact_type="sentinel2_cog_band",
                output_format=str(asset.get("type") or "Cloud Optimized GeoTIFF"),
                query_interfaces=["rasterio.open()", "read_window(west, south, east, north)"],
                feeds_algorithms=["visual_aoi_reference", "ndvi", "ndwi", "water_detection"],
                metadata={
                    "stac_item_id": item_id,
                    "asset": asset_name,
                    "title": asset.get("title"),
                    "datetime": (item.get("properties") or {}).get("datetime")
                    if isinstance(item.get("properties"), dict)
                    else None,
                    "cloud_cover": (item.get("properties") or {}).get("eo:cloud_cover")
                    if isinstance(item.get("properties"), dict)
                    else None,
                },
            )
        )

    if len(records) == 1:
        raise RuntimeError("No downloadable Sentinel-2 COG assets were found in the STAC item.")
    return records


def _s3_request_headers(request_payer: object = None) -> dict[str, str]:
    if str(request_payer or "").lower() == "requester":
        return {"x-amz-request-payer": "requester"}
    return {}


def _parse_s3_list_response(xml_text: str) -> tuple[list[dict[str, object]], str | None]:
    root = ET.fromstring(xml_text)
    namespace = ""
    if root.tag.startswith("{"):
        namespace = root.tag.split("}", 1)[0] + "}"
    objects: list[dict[str, object]] = []
    for contents in root.findall(f".//{namespace}Contents"):
        key = contents.findtext(f"{namespace}Key")
        size_text = contents.findtext(f"{namespace}Size") or "0"
        if not key:
            continue
        try:
            size = int(size_text)
        except ValueError:
            size = 0
        objects.append({"key": key, "size": size})
    token = root.findtext(f"{namespace}NextContinuationToken")
    return objects, token


def _downloadable_naip_key(key: str) -> bool:
    suffixes = (
        ".tif",
        ".tiff",
        ".mrf",
        ".idx",
        ".lrc",
        ".xml",
        ".aux",
        ".json",
        ".txt",
    )
    return key.lower().endswith(suffixes)


async def _execute_naip_aws_prefix(
    client: httpx.AsyncClient,
    *,
    package_id: str,
    operation: dict[str, object],
) -> list[dict[str, object]]:
    params = operation.get("params") if isinstance(operation.get("params"), dict) else {}
    bucket = str(params.get("bucket") or _naip_bucket()).strip()
    prefix = str(params.get("prefix") or "").strip().lstrip("/")
    max_files = int(params.get("max_files") or os.getenv("NAIP_MAX_FILES", "50"))
    endpoint = str(operation.get("endpoint") or NAIP_AWS_BUCKET_URL_TEMPLATE).replace("{bucket}", bucket)
    headers = _s3_request_headers(params.get("request_payer"))

    listed: list[dict[str, object]] = []
    continuation: str | None = None
    while len(listed) < max_files:
        list_params: dict[str, object] = {
            "list-type": "2",
            "prefix": prefix,
            "max-keys": min(1000, max_files - len(listed)),
        }
        if continuation:
            list_params["continuation-token"] = continuation
        response = await client.get(endpoint, params=list_params, headers=headers)
        response.raise_for_status()
        objects, continuation = _parse_s3_list_response(response.text)
        listed.extend(
            item
            for item in objects
            if isinstance(item.get("key"), str) and _downloadable_naip_key(str(item["key"]))
        )
        if not continuation or not objects:
            break

    if not listed:
        raise RuntimeError(
            f"NAIP S3 prefix {bucket}/{prefix} returned no downloadable files. "
            "Check NAIP_AWS_STATE, NAIP_AWS_YEAR, NAIP_AWS_RESOLUTION, and bucket."
        )

    package_path = _package_dir(package_id)
    base_dir = package_path / "imagery" / "naip" / "aws"
    downloaded: list[dict[str, object]] = []
    errors: list[str] = []
    for item in listed[:max_files]:
        key = str(item["key"])
        relative_key = key[len(prefix) :].lstrip("/") if key.startswith(prefix) else key
        relative_key = relative_key or Path(key).name
        target = (base_dir / relative_key).resolve()
        if base_dir.resolve() not in (target, *target.parents):
            raise RuntimeError("NAIP S3 key escapes NAIP package directory.")
        url = f"https://{bucket}.s3.amazonaws.com/{quote(key)}"
        try:
            bytes_written = await _download_binary(client, url, target, headers=headers)
            downloaded.append(
                {
                    "key": key,
                    "relative_path": target.relative_to(package_path).as_posix(),
                    "bytes": bytes_written,
                    "query_url": (
                        f"/api/source-package/{package_id}/query/imagery/files/"
                        f"{target.relative_to(package_path).as_posix()}"
                    ),
                }
            )
        except Exception as error:
            if len(errors) < 10:
                errors.append(f"{key}: {error}")

    if not downloaded:
        raise RuntimeError(f"NAIP S3 prefix listed files but downloads failed: {'; '.join(errors)}")

    index_path = _artifact_path(package_id, operation.get("local_artifact"))
    _write_json(
        index_path,
        {
            "source_id": operation.get("source_id"),
            "source_name": operation.get("source_name"),
            "bucket": bucket,
            "prefix": prefix,
            "request_payer": params.get("request_payer"),
            "state": params.get("state"),
            "year": params.get("year"),
            "resolution": params.get("resolution"),
            "bandset": params.get("bandset"),
            "max_files": max_files,
            "listed_file_count": len(listed),
            "downloaded_file_count": len(downloaded),
            "files": downloaded,
            "errors": errors,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return [
        _artifact_record(
            package_id=package_id,
            operation=operation,
            path=index_path,
            artifact_type="naip_imagery_index",
            output_format="JSON NAIP imagery index",
            query_interfaces=["imagery_file(relative_path)", "rasterio.open()", "read_window(west, south, east, north)"],
            feeds_algorithms=["operator_route_review", "feature_extraction_review"],
            metadata={
                "bucket": bucket,
                "prefix": prefix,
                "downloaded_file_count": len(downloaded),
                "errors": errors,
            },
        )
    ]


async def _execute_naip_earthexplorer_import(
    *,
    package_id: str,
    operation: dict[str, object],
) -> list[dict[str, object]]:
    params = _params_with_runtime_token(operation.get("params") if isinstance(operation.get("params"), dict) else {})
    source_dir = Path(str(params["source_dir"])).expanduser().resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        raise RuntimeError(f"NAIP_EARTHEXPLORER_DIR does not exist or is not a directory: {source_dir}")
    max_files = int(params.get("max_files") or os.getenv("NAIP_MAX_FILES", "50"))
    files = [
        path
        for path in sorted(source_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in {".tif", ".tiff"}
    ][:max_files]
    if not files:
        raise RuntimeError("No NAIP GeoTIFF files found in NAIP_EARTHEXPLORER_DIR.")

    package_path = _package_dir(package_id)
    dest_dir = package_path / "imagery" / "naip" / "earthexplorer"
    copied: list[dict[str, object]] = []
    for src in files:
        target = dest_dir / src.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        copied.append(
            {
                "source_name": src.name,
                "relative_path": target.relative_to(package_path).as_posix(),
                "bytes": target.stat().st_size,
                "query_url": (
                    f"/api/source-package/{package_id}/query/imagery/files/"
                    f"{target.relative_to(package_path).as_posix()}"
                ),
            }
        )

    index_path = _artifact_path(package_id, operation.get("local_artifact"))
    _write_json(
        index_path,
        {
            "source_dir": str(source_dir),
            "file_count": len(copied),
            "files": copied,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return [
        _artifact_record(
            package_id=package_id,
            operation=operation,
            path=index_path,
            artifact_type="naip_imagery_index",
            output_format="JSON NAIP EarthExplorer import index",
            query_interfaces=["imagery_file(relative_path)", "rasterio.open()"],
            feeds_algorithms=["operator_route_review", "feature_extraction_review"],
            metadata={"file_count": len(copied), "source_dir": str(source_dir)},
        )
    ]


async def _execute_xyz_tile_cache(
    client: httpx.AsyncClient,
    *,
    package_id: str,
    operation: dict[str, object],
) -> list[dict[str, object]]:
    params = operation.get("params") if isinstance(operation.get("params"), dict) else {}
    template = str(params.get("tile_url_template") or operation.get("endpoint") or "")
    levels = _parse_level_range(params.get("levels"))
    min_zoom = int(params.get("min_zoom") or 0)
    max_zoom = int(params.get("max_zoom") or max(levels or [0]))
    levels = [level for level in levels if min_zoom <= level <= max_zoom]
    manifest = _load_package_manifest(package_id) or {}
    aoi = manifest.get("aoi") if isinstance(manifest.get("aoi"), dict) else {}
    bounds_data = aoi.get("selected_area") or aoi.get("view_bounds") if isinstance(aoi, dict) else None
    if not isinstance(bounds_data, dict):
        raise RuntimeError("Tile cache download requires AO bounds in the package manifest.")
    bounds = ViewBounds(**bounds_data)
    tile_limit = int(os.getenv("MAX_TILE_DOWNLOAD_COUNT", "5000"))
    tile_count = _estimate_slippy_tile_count(bounds, levels)
    if tile_count > tile_limit:
        raise RuntimeError(
            f"Tile cache would download {tile_count} tiles, above MAX_TILE_DOWNLOAD_COUNT={tile_limit}."
        )

    package_path = _package_dir(package_id)
    relative_template = _relative_artifact_path(operation.get("local_artifact"), package_id).as_posix()
    downloaded = 0
    bytes_written = 0
    errors: list[str] = []
    for zoom, xs, ys in _tile_ranges(bounds, levels):
        for x in xs:
            for y in ys:
                url = template.replace("{z}", str(zoom)).replace("{x}", str(x)).replace("{y}", str(y))
                url = url.replace("{$z}", str(zoom)).replace("{$x}", str(x)).replace("{$y}", str(y))
                relative = (
                    relative_template.replace("{z}", str(zoom))
                    .replace("{x}", str(x))
                    .replace("{y}", str(y))
                )
                path = (package_path / relative).resolve()
                if package_path not in (path, *path.parents):
                    raise RuntimeError("Tile cache path escapes package root.")
                try:
                    bytes_written += await _download_binary(client, url, path)
                    downloaded += 1
                except Exception as error:
                    if len(errors) < 5:
                        errors.append(f"{zoom}/{x}/{y}: {error}")

    index_path = package_path / "tiles" / str(operation.get("source_id")) / "tile_index.json"
    _write_json(
        index_path,
        {
            "source_id": operation.get("source_id"),
            "source_name": operation.get("source_name"),
            "url_template_redacted": False,
            "url_template": template,
            "levels": levels,
            "aoi": bounds.model_dump(),
            "estimated_tile_count": tile_count,
            "downloaded_tile_count": downloaded,
            "errors": errors,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return [
        _artifact_record(
            package_id=package_id,
            operation=operation,
            path=index_path,
            artifact_type="xyz_imagery_tile_cache",
            output_format=str(operation.get("output_format") or "XYZ tile cache"),
            query_interfaces=["tile(z, x, y)", "tiles_intersecting_bbox(west, south, east, north, zoom)"],
            feeds_algorithms=["visual_aoi_reference", "operator_route_review"],
            metadata={
                "levels": levels,
                "estimated_tile_count": tile_count,
                "downloaded_tile_count": downloaded,
                "bytes_written": bytes_written,
                "errors": errors,
            },
        )
    ]


def _cesium_headers(token: object) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _request_cesium_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    token: object,
    payload: dict[str, object] | None = None,
) -> dict[str, Any]:
    headers = _cesium_headers(token)
    if method.upper() == "POST":
        response = await client.post(url, json=payload or {}, headers=headers)
    else:
        response = await client.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("Cesium ion response was not a JSON object.")
    return data


async def _poll_cesium_archive(
    client: httpx.AsyncClient,
    *,
    archive_id: object,
    token: object,
) -> dict[str, Any]:
    info_url = CESIUM_ION_ARCHIVE_INFO_URL.replace("{archive_id}", str(archive_id))
    last_payload: dict[str, Any] = {}
    for _attempt in range(CESIUM_ARCHIVE_MAX_POLLS):
        payload = await _request_cesium_json(client, "GET", info_url, token=token)
        last_payload = payload
        status = str(payload.get("status") or "").upper()
        if status in {"COMPLETE", "COMPLETED"}:
            return payload
        if status in {"FAILED", "CANCELLED", "CANCELED"}:
            raise RuntimeError(f"Cesium archive {archive_id} ended with status {status}.")
        await asyncio.sleep(CESIUM_ARCHIVE_POLL_INTERVAL_S)
    raise RuntimeError(
        f"Timed out waiting for Cesium archive {archive_id}; last status={last_payload.get('status')!r}."
    )


def _safe_extract_zip(zip_path: Path, extract_dir: Path) -> list[Path]:
    extract_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for member in archive.infolist():
                target = (extract_dir / member.filename).resolve()
                if extract_dir not in (target, *target.parents):
                    raise RuntimeError("Cesium archive contains a path outside the extract directory.")
            archive.extractall(extract_dir)
    except zipfile.BadZipFile as error:
        raise RuntimeError("Cesium archive download was not a valid ZIP file.") from error

    for path in extract_dir.rglob("*"):
        if path.is_file():
            extracted.append(path)
    return extracted


def _read_descriptor_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _index_cesium_archive(
    *,
    package_id: str,
    operation: dict[str, object],
    archive_path: Path,
    archive_info: dict[str, Any],
) -> tuple[Path, dict[str, Any]]:
    package_path = _package_dir(package_id)
    extract_dir = package_path / "cesium" / "archive" / "extracted"
    extracted_files = _safe_extract_zip(archive_path, extract_dir)

    files: list[dict[str, object]] = []
    tilesets: list[dict[str, object]] = []
    terrain_layers: list[dict[str, object]] = []
    imagery_layers: list[dict[str, object]] = []
    for path in sorted(extracted_files):
        relative_path = path.resolve().relative_to(package_path).as_posix()
        name = path.name.lower()
        item: dict[str, object] = {
            "relative_path": relative_path,
            "bytes": path.stat().st_size,
            "query_url": f"/api/source-package/{package_id}/query/cesium/files/{relative_path}",
        }
        files.append(item)
        if name == "tileset.json":
            descriptor = _read_descriptor_json(path) or {}
            tilesets.append(
                {
                    **item,
                    "root_refine": (descriptor.get("root") or {}).get("refine")
                    if isinstance(descriptor.get("root"), dict)
                    else None,
                    "asset_version": (descriptor.get("asset") or {}).get("version")
                    if isinstance(descriptor.get("asset"), dict)
                    else None,
                }
            )
        elif name == "layer.json":
            descriptor = _read_descriptor_json(path) or {}
            layer_record = {
                **item,
                "format": descriptor.get("format"),
                "version": descriptor.get("version"),
                "attribution": descriptor.get("attribution"),
            }
            if str(descriptor.get("format") or "").lower() in {"quantized-mesh-1.0", "heightmap-1.0"}:
                terrain_layers.append(layer_record)
            else:
                imagery_layers.append(layer_record)

    index = {
        "package_id": package_id,
        "source_id": operation.get("source_id"),
        "source_name": operation.get("source_name"),
        "operation_id": operation.get("id"),
        "archive_id": archive_info.get("id"),
        "archive_name": archive_info.get("name"),
        "archive_type": archive_info.get("type"),
        "archive_format": archive_info.get("format"),
        "archive_status": archive_info.get("status"),
        "bytes_archived": archive_info.get("bytesArchived"),
        "archive_zip": archive_path.resolve().relative_to(package_path).as_posix(),
        "files": files,
        "tilesets": tilesets,
        "terrain_layers": terrain_layers,
        "imagery_layers": imagery_layers,
        "query_interfaces": [
            "GET /api/source-package/{package_id}/query/cesium",
            "GET /api/source-package/{package_id}/query/cesium/files/{relative_path}",
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    index_path = package_path / "cesium" / "archive" / "cesium_archive_index.json"
    _write_json(index_path, index)
    return index_path, index


async def _execute_cesium_archive_download(
    client: httpx.AsyncClient,
    *,
    package_id: str,
    manifest: dict[str, object],
    operation: dict[str, object],
) -> list[dict[str, object]]:
    params = _params_with_runtime_token(operation.get("params") if isinstance(operation.get("params"), dict) else {})
    token = params["token"]
    archive_id = params["archive_id"]
    archive_info = await _poll_cesium_archive(client, archive_id=archive_id, token=token)
    download_url = CESIUM_ION_ARCHIVE_DOWNLOAD_URL.replace("{archive_id}", str(archive_id))
    archive_path = _artifact_path(package_id, operation.get("local_artifact"))
    await _download_binary(client, download_url, archive_path, headers=_cesium_headers(token))
    index_path, index = _index_cesium_archive(
        package_id=package_id,
        operation=operation,
        archive_path=archive_path,
        archive_info=archive_info,
    )
    contract = _query_contract_for_operation(manifest, operation) or {}
    return [
        _artifact_record(
            package_id=package_id,
            operation=operation,
            path=archive_path,
            artifact_type="cesium_archive_zip",
            output_format=str(operation.get("output_format") or "Cesium archive ZIP"),
            query_interfaces=["downloaded_archive_zip()"],
            feeds_algorithms=["local_cesium_preview"],
            metadata={
                "archive_id": archive_info.get("id"),
                "archive_status": archive_info.get("status"),
                "bytes_archived": archive_info.get("bytesArchived"),
            },
        ),
        _artifact_record(
            package_id=package_id,
            operation=operation,
            path=index_path,
            artifact_type=str(contract.get("artifact_type") or "cesium_offline_archive_index"),
            output_format="JSON Cesium archive index",
            query_interfaces=list(
                contract.get("query_interfaces")
                or ["cesium_archive_metadata()", "cesium_file(relative_path)"]
            ),
            feeds_algorithms=list(contract.get("feeds_algorithms") or ["local_cesium_preview"]),
            metadata={
                "archive_id": archive_info.get("id"),
                "file_count": len(index.get("files", [])),
                "tileset_count": len(index.get("tilesets", [])),
                "terrain_layer_count": len(index.get("terrain_layers", [])),
                "imagery_layer_count": len(index.get("imagery_layers", [])),
            },
        ),
    ]


async def _execute_cesium_clip_create_download(
    client: httpx.AsyncClient,
    *,
    package_id: str,
    manifest: dict[str, object],
    operation: dict[str, object],
) -> list[dict[str, object]]:
    params = _params_with_runtime_token(operation.get("params") if isinstance(operation.get("params"), dict) else {})
    token = params["token"]
    if not isinstance(params.get("asset_ids"), list):
        raise RuntimeError("Cesium AO clip requires CESIUM_ION_ASSET_IDS.")
    if not isinstance(params.get("clip_region"), list):
        raise RuntimeError("Cesium AO clip requires confirmed AO bounds.")
    payload = {
        "assetIds": params["asset_ids"],
        "format": params.get("format", "TILESET"),
        "type": params.get("type", "CLIP_LATITUDE_LONGITUDE_RECTANGLE"),
        "clipRegion": params["clip_region"],
    }
    archive_info = await _request_cesium_json(
        client,
        "POST",
        str(operation["endpoint"]),
        token=token,
        payload=payload,
    )
    archive_id = archive_info.get("id")
    if archive_id is None:
        raise RuntimeError("Cesium ion did not return an archive id for the AO clip.")

    download_operation = {**operation}
    download_operation["params"] = {
        "archive_id": str(archive_id),
        "token": "${CESIUM_ION_TOKEN}",
        "extract": True,
    }
    records = await _execute_cesium_archive_download(
        client,
        package_id=package_id,
        manifest=manifest,
        operation=download_operation,
    )
    for record in records:
        metadata = record.setdefault("metadata", {})
        if isinstance(metadata, dict):
            metadata["created_from_asset_ids"] = params["asset_ids"]
            metadata["clip_region_radians"] = params["clip_region"]
    return records


def _run_subprocess(args: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=False)
    except OSError as error:
        return False, str(error)
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output.strip()


OSM_VECTOR_SUFFIXES = {".gpkg", ".sqlite", ".sqlite3", ".db", ".pbf", ".osm"}
OSM_SQLITE_SUFFIXES = {".gpkg", ".sqlite", ".sqlite3", ".db"}


async def _execute_osm_wintak_import(
    *,
    package_id: str,
    operation: dict[str, object],
) -> list[dict[str, object]]:
    params = _params_with_runtime_token(
        operation.get("params") if isinstance(operation.get("params"), dict) else {}
    )
    source_dir = Path(str(params["source_dir"])).expanduser().resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        raise RuntimeError(
            f"TERA_WINTAK_IMAGERY_DIR does not exist or is not a directory: {source_dir}"
        )

    files = [
        path
        for path in sorted(source_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in OSM_VECTOR_SUFFIXES
    ]
    if not files:
        raise RuntimeError("No OSM vector files found in TERA_WINTAK_IMAGERY_DIR.")

    sqlite_files = [path for path in files if path.suffix.lower() in OSM_SQLITE_SUFFIXES]
    pbf_files = [path for path in files if path.suffix.lower() in {".pbf", ".osm"}]
    index_path = _artifact_path(package_id, operation.get("local_artifact"))
    _write_json(
        index_path,
        {
            "source_dir": str(source_dir),
            "bbox": params.get("bbox"),
            "sqlite_files": [str(path) for path in sqlite_files],
            "pbf_files": [str(path) for path in pbf_files],
            "query_env": {
                "TERA_OSM_ROOT_DIRS": str(source_dir),
                "TERA_WINTAK_IMAGERY_DIR": str(source_dir),
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return [
        _artifact_record(
            package_id=package_id,
            operation=operation,
            path=index_path,
            artifact_type="osm_wintak_index",
            output_format="JSON staged WinTAK OSM index",
            query_interfaces=[
                "query_osm_features(target_type, origin, radius_m)",
                "valhalla_build_tiles",
                "osmium tags-filter",
            ],
            feeds_algorithms=["routable_graph", "nearest_feature", "water_source_lookup"],
            metadata={
                "source_dir": str(source_dir),
                "sqlite_file_count": len(sqlite_files),
                "pbf_file_count": len(pbf_files),
            },
        )
    ]


async def _execute_osm_geofabrik_pbf(
    client: httpx.AsyncClient,
    *,
    package_id: str,
    operation: dict[str, object],
) -> list[dict[str, object]]:
    params = operation.get("params") if isinstance(operation.get("params"), dict) else {}
    region_url = str(params.get("region_url") or operation.get("endpoint") or "").strip()
    if not region_url:
        raise RuntimeError("Geofabrik OSM operation did not include a region URL.")
    package_path = _package_dir(package_id)
    vector_dir = package_path / "vectors" / "osm"
    region_path = vector_dir / "geofabrik_region.osm.pbf"
    clipped_path = _artifact_path(package_id, operation.get("local_artifact"))
    await _download_binary(client, region_url, region_path)

    clip_bbox = str(params.get("clip_bbox") or "").strip()
    clipped = False
    clip_message = "osmium not available; regional PBF registered without AO clip."
    osmium = shutil.which("osmium")
    if osmium and clip_bbox and "{" not in clip_bbox:
        clipped_path.parent.mkdir(parents=True, exist_ok=True)
        ok, output = _run_subprocess(
            [
                osmium,
                "extract",
                f"--bbox={clip_bbox}",
                str(region_path),
                "-o",
                str(clipped_path),
                "--overwrite",
            ]
        )
        clipped = ok and clipped_path.exists()
        clip_message = output or ("AO clip created." if clipped else "osmium extract failed.")
    if not clipped:
        clipped_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(region_path, clipped_path)

    index_path = vector_dir / "osm_index.json"
    _write_json(
        index_path,
        {
            "source_id": operation.get("source_id"),
            "source_name": operation.get("source_name"),
            "region_url": region_url,
            "region_slug": params.get("region_slug"),
            "clip_bbox": clip_bbox,
            "clipped_with_osmium": clipped,
            "clip_message": clip_message,
            "region_pbf": region_path.relative_to(package_path).as_posix(),
            "aoi_pbf": clipped_path.relative_to(package_path).as_posix(),
            "query_interfaces": [
                "osmium tags-filter",
                "pyosmium scan",
                "valhalla_build_tiles",
                "find_pois(osm_tags, bbox)",
            ],
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return [
        _artifact_record(
            package_id=package_id,
            operation=operation,
            path=clipped_path,
            artifact_type="osm_pbf_extract",
            output_format="OSM PBF",
            query_interfaces=["osmium tags-filter", "pyosmium scan", "valhalla_build_tiles"],
            feeds_algorithms=["routable_graph", "nearest_feature", "water_source_lookup"],
            metadata={
                "region_url": region_url,
                "clip_bbox": clip_bbox,
                "clipped_with_osmium": clipped,
                "clip_message": clip_message,
            },
        ),
        _artifact_record(
            package_id=package_id,
            operation=operation,
            path=index_path,
            artifact_type="osm_query_index",
            output_format="JSON OSM package index",
            query_interfaces=["osm_artifacts()", "osm_file(relative_path)"],
            feeds_algorithms=["routable_graph", "nearest_feature"],
            metadata={"region_url": region_url, "clipped_with_osmium": clipped},
        ),
    ]


async def _execute_copernicus_dem_cogs(
    client: httpx.AsyncClient,
    *,
    package_id: str,
    operation: dict[str, object],
) -> list[dict[str, object]]:
    params = operation.get("params") if isinstance(operation.get("params"), dict) else {}
    tiles = params.get("tile_urls") if isinstance(params.get("tile_urls"), list) else []
    if not tiles:
        raise RuntimeError("Copernicus DEM download requires AO bounds to derive tile URLs.")
    package_path = _package_dir(package_id)
    dem_dir = package_path / "rasters" / "copernicus_dem"
    downloaded: list[dict[str, object]] = []
    errors: list[str] = []
    records: list[dict[str, object]] = []
    for tile in tiles:
        if not isinstance(tile, dict):
            continue
        tile_id = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(tile.get("tile_id") or "copernicus_dem"))
        url = str(tile.get("url") or "")
        if not url:
            continue
        path = dem_dir / f"{tile_id}.tif"
        try:
            await _download_binary(client, url, path)
        except Exception as error:
            if len(errors) < 10:
                errors.append(f"{tile_id}: {error}")
            continue
        downloaded.append(
            {
                "tile_id": tile_id,
                "url": url,
                "relative_path": path.relative_to(package_path).as_posix(),
                "bytes": path.stat().st_size,
                "query_url": f"/api/source-package/{package_id}/query/terrain/files/{path.relative_to(package_path).as_posix()}",
            }
        )
        records.append(
            _artifact_record(
                package_id=package_id,
                operation=operation,
                path=path,
                artifact_type="copernicus_dem_cog",
                output_format="Cloud Optimized GeoTIFF DEM",
                query_interfaces=["sample_dem(lat, lon)", "read_window(west, south, east, north)", "rasterio.open()"],
                feeds_algorithms=["terrain_derivatives", "raster_cost_distance", "viewshed"],
                metadata={"tile_id": tile_id, "url": url, "bbox": params.get("bbox")},
            )
        )

    if not downloaded:
        raise RuntimeError(f"No Copernicus DEM tiles downloaded. Errors: {'; '.join(errors)}")

    index_path = dem_dir / "copernicus_dem_index.json"
    _write_json(
        index_path,
        {
            "source_id": operation.get("source_id"),
            "source_name": operation.get("source_name"),
            "bbox": params.get("bbox"),
            "requested_tiles": tiles,
            "downloaded_tiles": downloaded,
            "errors": errors,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    records.append(
        _artifact_record(
            package_id=package_id,
            operation=operation,
            path=index_path,
            artifact_type="copernicus_dem_cog_index",
            output_format="JSON Copernicus DEM tile index",
            query_interfaces=["terrain_artifacts()", "terrain_file(relative_path)"],
            feeds_algorithms=["terrain_derivatives", "raster_cost_distance", "viewshed"],
            metadata={"tile_count": len(downloaded), "errors": errors},
        )
    )
    return records


def _dted_matches_aoi(path: Path, tiles: list[dict[str, object]]) -> bool:
    name = path.as_posix().lower()
    for tile in tiles:
        lat_floor = int(tile.get("lat_floor", 999))
        lon_floor = int(tile.get("lon_floor", 999))
        lat_tokens = {f"n{lat_floor:02d}", f"s{abs(lat_floor):02d}"}
        lon_tokens = {f"e{lon_floor:03d}", f"w{abs(lon_floor):03d}"}
        if any(token in name for token in lat_tokens) and any(token in name for token in lon_tokens):
            return True
    return False


async def _execute_dted_import_convert(
    *,
    package_id: str,
    operation: dict[str, object],
) -> list[dict[str, object]]:
    params = _params_with_runtime_token(operation.get("params") if isinstance(operation.get("params"), dict) else {})
    source_dir = Path(str(params["source_dir"])).expanduser().resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        raise RuntimeError(f"DTED_SOURCE_DIR does not exist or is not a directory: {source_dir}")
    manifest = _load_package_manifest(package_id) or {}
    aoi = manifest.get("aoi") if isinstance(manifest.get("aoi"), dict) else {}
    bounds = ViewBounds(**aoi) if aoi else None
    tiles = _copernicus_dem_tiles(bounds) if bounds else []
    all_dted = [
        path
        for path in sorted(source_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in {".dt0", ".dt1", ".dt2"}
    ]
    matched = [path for path in all_dted if _dted_matches_aoi(path, tiles)] if tiles else []
    selected = matched or all_dted
    selected = selected[: int(os.getenv("DTED_IMPORT_MAX_FILES", "100"))]
    if not selected:
        raise RuntimeError("No .dt0/.dt1/.dt2 files found in DTED_SOURCE_DIR.")

    package_path = _package_dir(package_id)
    raw_dir = package_path / "rasters" / "dted" / "raw"
    tif_dir = package_path / "rasters" / "dted" / "geotiff"
    gdal_translate = shutil.which("gdal_translate")
    raw_files: list[dict[str, object]] = []
    converted_files: list[dict[str, object]] = []
    records: list[dict[str, object]] = []
    conversion_errors: list[str] = []
    for src in selected:
        raw_target = raw_dir / src.name
        raw_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, raw_target)
        raw_record = {
            "source_name": src.name,
            "relative_path": raw_target.relative_to(package_path).as_posix(),
            "bytes": raw_target.stat().st_size,
        }
        raw_files.append(raw_record)
        if gdal_translate:
            tif_target = tif_dir / f"{src.stem}.tif"
            tif_target.parent.mkdir(parents=True, exist_ok=True)
            ok, output = _run_subprocess([gdal_translate, str(raw_target), str(tif_target)])
            if ok and tif_target.exists():
                converted_files.append(
                    {
                        "source_name": src.name,
                        "relative_path": tif_target.relative_to(package_path).as_posix(),
                        "bytes": tif_target.stat().st_size,
                        "query_url": f"/api/source-package/{package_id}/query/terrain/files/{tif_target.relative_to(package_path).as_posix()}",
                    }
                )
                records.append(
                    _artifact_record(
                        package_id=package_id,
                        operation=operation,
                        path=tif_target,
                        artifact_type="dted_geotiff_dem",
                        output_format="GeoTIFF DEM converted from DTED",
                        query_interfaces=["sample_dem(lat, lon)", "read_window(west, south, east, north)", "rasterio.open()"],
                        feeds_algorithms=["terrain_derivatives", "raster_cost_distance", "viewshed"],
                        metadata={"source_dted": raw_record["relative_path"]},
                    )
                )
            elif len(conversion_errors) < 10:
                conversion_errors.append(f"{src.name}: {output}")

    index_path = _artifact_path(package_id, operation.get("local_artifact"))
    _write_json(
        index_path,
        {
            "source_dir": str(source_dir),
            "raw_files": raw_files,
            "converted_files": converted_files,
            "gdal_translate": bool(gdal_translate),
            "conversion_errors": conversion_errors,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    records.append(
        _artifact_record(
            package_id=package_id,
            operation=operation,
            path=index_path,
            artifact_type="dted_geotiff_index",
            output_format="JSON DTED import index",
            query_interfaces=["terrain_artifacts()", "terrain_file(relative_path)", "gdalinfo"],
            feeds_algorithms=["terrain_derivatives", "raster_cost_distance", "viewshed"],
            metadata={
                "raw_file_count": len(raw_files),
                "converted_file_count": len(converted_files),
                "gdal_translate": bool(gdal_translate),
                "conversion_errors": conversion_errors,
            },
        )
    )
    return records


async def _execute_operation(
    client: httpx.AsyncClient,
    *,
    package_id: str,
    manifest: dict[str, object],
    operation: dict[str, object],
) -> list[dict[str, object]]:
    operation_id = str(operation.get("id", ""))
    if operation_id == "naip_aws_public_prefix":
        return await _execute_naip_aws_prefix(
            client,
            package_id=package_id,
            operation=operation,
        )
    if operation_id == "naip_earthexplorer_geotiff_import":
        return await _execute_naip_earthexplorer_import(
            package_id=package_id,
            operation=operation,
        )
    if operation_id == "osm_wintak_imagery_import":
        return await _execute_osm_wintak_import(
            package_id=package_id,
            operation=operation,
        )
    if operation_id == "osm_geofabrik_pbf":
        return await _execute_osm_geofabrik_pbf(
            client,
            package_id=package_id,
            operation=operation,
        )
    if operation_id == "copernicus_dem_glo30_cog":
        return await _execute_copernicus_dem_cogs(
            client,
            package_id=package_id,
            operation=operation,
        )
    if operation_id == "dted_earthexplorer_import_convert":
        return await _execute_dted_import_convert(
            package_id=package_id,
            operation=operation,
        )
    if operation_id in {"usgs_imagery_tile_cache", "nrl_naip_tile_cache"}:
        return await _execute_xyz_tile_cache(
            client,
            package_id=package_id,
            operation=operation,
        )
    if operation_id == "sentinel_2_stac_cog":
        return await _execute_sentinel2_stac_cogs(
            client,
            package_id=package_id,
            operation=operation,
        )
    if operation_id == "cesium_ion_archive_download":
        return await _execute_cesium_archive_download(
            client,
            package_id=package_id,
            manifest=manifest,
            operation=operation,
        )
    if operation_id == "cesium_ion_clip_create_download":
        return await _execute_cesium_clip_create_download(
            client,
            package_id=package_id,
            manifest=manifest,
            operation=operation,
        )
    if operation_id == "esri_world_imagery_export_tiles":
        return [
            await _execute_esri_imagery_export(
                client,
                package_id=package_id,
                manifest=manifest,
                operation=operation,
            )
        ]
    if operation_id == "esri_world_elevation_export_image_tiff":
        return await _execute_esri_terrain_export(
            client,
            package_id=package_id,
            manifest=manifest,
            operation=operation,
        )
    if operation_id == "esri_world_elevation_get_samples":
        return [
            await _execute_esri_samples(
                client,
                package_id=package_id,
                operation=operation,
            )
        ]
    return []


async def _execute_package_job(package_id: str, manifest: dict[str, object]) -> None:
    status = _load_package_status(package_id)
    status["state"] = "running"
    status["message"] = "Downloading selected sources to the Jetson package root."
    _save_package_status(package_id, status)

    registry = _load_artifact_registry(package_id)
    timeout = httpx.Timeout(REQUEST_TIMEOUT_S, connect=20.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            for operation in manifest.get("download_operations", []):
                if not isinstance(operation, dict):
                    continue
                operation_id = str(operation.get("id", ""))
                _update_operation_status(
                    status,
                    operation_id,
                    state="running",
                    message="Downloading on Jetson.",
                )
                _save_package_status(package_id, status)
                try:
                    artifacts = await _execute_operation(
                        client,
                        package_id=package_id,
                        manifest=manifest,
                        operation=operation,
                    )
                    if not artifacts:
                        _update_operation_status(
                            status,
                            operation_id,
                            state="skipped",
                            message="No executable downloader is implemented for this supplemental source.",
                        )
                        continue
                    registry["artifacts"].extend(artifacts)
                    _save_artifact_registry(package_id, registry)
                    bytes_written = sum(int(artifact.get("bytes") or 0) for artifact in artifacts)
                    artifact_paths = ", ".join(str(artifact.get("relative_path")) for artifact in artifacts)
                    _update_operation_status(
                        status,
                        operation_id,
                        state="succeeded",
                        message="Saved to Jetson package root.",
                        bytes_written=bytes_written,
                        artifact_path=artifact_paths,
                    )
                    _save_package_status(package_id, status)
                except Exception as error:
                    _update_operation_status(
                        status,
                        operation_id,
                        state="failed",
                        message=str(error),
                    )
                    status["state"] = "failed"
                    status["message"] = str(error)
                    _save_package_status(package_id, status)
                    return
        status["state"] = "succeeded"
        status["message"] = "Package downloads completed on Jetson."
        _save_package_status(package_id, status)
    finally:
        PACKAGE_TASKS.pop(package_id, None)


def _artifact_file(package_id: str, artifact: dict[str, Any]) -> Path:
    package_path = _package_dir(package_id)
    relative = str(artifact.get("relative_path") or "").replace("\\", "/")
    path = (package_path / relative).resolve()
    if package_path not in (path, *path.parents):
        raise HTTPException(status_code=400, detail="Artifact path escapes package root.")
    return path


def _package_file_response(
    package_id: str,
    relative_path: str,
    *,
    allowed_roots: tuple[str, ...],
) -> FileResponse:
    package_id = _safe_package_id(package_id)
    if _load_package_manifest(package_id) is None:
        raise HTTPException(status_code=404, detail="Source package manifest not found.")
    package_path = _package_dir(package_id)
    clean_parts = [
        part
        for part in relative_path.replace("\\", "/").split("/")
        if part and part not in {".", ".."}
    ]
    if not clean_parts:
        raise HTTPException(status_code=400, detail="Artifact file path is required.")
    target = (package_path / Path(*clean_parts)).resolve()
    allowed = [(package_path / root).resolve() for root in allowed_roots]
    if package_path not in (target, *target.parents) or not any(
        root in (target, *target.parents) for root in allowed
    ):
        raise HTTPException(status_code=400, detail="Artifact file path is outside the allowed package roots.")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Artifact file not found.")
    return FileResponse(target)


def _registry_artifacts_by_prefix(
    package_id: str,
    *,
    source_ids: set[str] | None = None,
    artifact_types: set[str] | None = None,
) -> list[dict[str, object]]:
    registry = _load_artifact_registry(package_id)
    artifacts: list[dict[str, object]] = []
    for artifact in registry.get("artifacts", []):
        if not isinstance(artifact, dict):
            continue
        if source_ids is not None and str(artifact.get("source_id")) not in source_ids:
            continue
        if artifact_types is not None and str(artifact.get("artifact_type")) not in artifact_types:
            continue
        artifacts.append(artifact)
    return artifacts


def _find_terrain_artifact(package_id: str) -> dict[str, Any] | None:
    registry = _load_artifact_registry(package_id)
    artifacts = registry.get("artifacts", [])
    priority = {
        "cloud_optimized_geotiff_dem": 0,
        "geotiff_dem": 1,
        "copernicus_dem_cog": 1,
        "dted_geotiff_dem": 1,
        "elevation_grid_json": 2,
        "elevation_samples_json": 3,
    }
    terrain = [
        artifact
        for artifact in artifacts
        if isinstance(artifact, dict)
        and artifact.get("artifact_type") in priority
        and artifact.get("source_id")
        in {"esri_world_elevation", "copernicus_dem", "dted_earth_explorer", "test_dem", None}
    ]
    terrain.sort(key=lambda item: priority.get(str(item.get("artifact_type")), 99))
    return terrain[0] if terrain else None


def _grid_bbox_from_artifact(artifact: dict[str, Any]) -> dict[str, float] | None:
    metadata = artifact.get("metadata") if isinstance(artifact.get("metadata"), dict) else {}
    bbox = metadata.get("bbox") if isinstance(metadata, dict) else None
    if isinstance(bbox, str):
        parts = [part.strip() for part in bbox.split(",")]
        if len(parts) == 4:
            try:
                return {
                    "west": float(parts[0]),
                    "south": float(parts[1]),
                    "east": float(parts[2]),
                    "north": float(parts[3]),
                }
            except ValueError:
                return None
    if isinstance(bbox, dict):
        try:
            return {
                "west": float(bbox["west"]),
                "south": float(bbox["south"]),
                "east": float(bbox["east"]),
                "north": float(bbox["north"]),
            }
        except (KeyError, TypeError, ValueError):
            return None
    return None


def _load_json_grid(path: Path) -> tuple[list[list[float]], dict[str, float] | None, float]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    grid = payload.get("elevation_grid") or payload.get("elevation") or payload.get("grid")
    if not isinstance(grid, list):
        raise RuntimeError("JSON terrain artifact does not contain an elevation grid.")
    numeric = [[float(value) for value in row] for row in grid]
    bbox = payload.get("bbox") if isinstance(payload.get("bbox"), dict) else None
    cell_size = float(payload.get("cell_size_m") or 30.0)
    return numeric, bbox, cell_size


def _load_raster_grid(path: Path, max_cells: int = 250000) -> tuple[list[list[float]], dict[str, float] | None, float]:
    try:
        import rasterio
    except ImportError as error:
        raise RuntimeError("rasterio is required to query GeoTIFF/COG terrain artifacts.") from error
    with rasterio.open(path) as dataset:
        width = dataset.width
        height = dataset.height
        if width * height > max_cells:
            scale = math.sqrt((width * height) / max_cells)
            out_width = max(1, int(width / scale))
            out_height = max(1, int(height / scale))
            data = dataset.read(1, out_shape=(out_height, out_width), masked=True)
        else:
            data = dataset.read(1, masked=True)
        rows = data.filled(float("nan")).tolist()
        bounds = dataset.bounds
        bbox = {
            "west": float(bounds.left),
            "south": float(bounds.bottom),
            "east": float(bounds.right),
            "north": float(bounds.top),
        }
        cell_size = abs(float(dataset.transform.a)) or 30.0
        return rows, bbox, cell_size


def _load_package_terrain_grid(
    package_id: str,
    *,
    max_cells: int = 250000,
) -> tuple[list[list[float]], dict[str, float] | None, float, dict[str, Any]]:
    artifact = _find_terrain_artifact(package_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="No queryable terrain artifact is registered.")
    path = _artifact_file(package_id, artifact)
    artifact_type = str(artifact.get("artifact_type") or "")
    if artifact_type == "elevation_grid_json" or path.suffix.lower() == ".json":
        grid, bbox, cell_size = _load_json_grid(path)
        return grid, bbox or _grid_bbox_from_artifact(artifact), cell_size, artifact
    grid, bbox, cell_size = _load_raster_grid(path, max_cells=max_cells)
    return grid, bbox or _grid_bbox_from_artifact(artifact), cell_size, artifact


def _coord_to_cell(
    lat: float,
    lon: float,
    bbox: dict[str, float] | None,
    rows: int,
    cols: int,
) -> tuple[int, int]:
    if not bbox or rows <= 0 or cols <= 0:
        return 0, 0
    lon_span = bbox["east"] - bbox["west"]
    lat_span = bbox["north"] - bbox["south"]
    if lon_span == 0 or lat_span == 0:
        return 0, 0
    col = int(round((lon - bbox["west"]) / lon_span * (cols - 1)))
    row = int(round((bbox["north"] - lat) / lat_span * (rows - 1)))
    return max(0, min(rows - 1, row)), max(0, min(cols - 1, col))


def _cell_to_coord(
    row: int,
    col: int,
    bbox: dict[str, float] | None,
    rows: int,
    cols: int,
) -> tuple[float, float]:
    if not bbox or rows <= 1 or cols <= 1:
        return 0.0, 0.0
    lon = bbox["west"] + (col / (cols - 1)) * (bbox["east"] - bbox["west"])
    lat = bbox["north"] - (row / (rows - 1)) * (bbox["north"] - bbox["south"])
    return lat, lon


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _route_hash(feature: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(feature, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _feature_distance_m(feature: dict[str, Any]) -> float:
    coords = feature.get("geometry", {}).get("coordinates", [])
    total = 0.0
    for left, right in zip(coords, coords[1:]):
        total += _haversine_m(float(left[1]), float(left[0]), float(right[1]), float(right[0]))
    return total


def _run_algorithm(package_id: str, request: AlgorithmRequest) -> dict[str, Any]:
    from llm_dev_kmh import geo_algorithms

    algorithm_id = request.algorithm_id
    params = request.parameters
    if algorithm_id == "sar_sector_partition":
        center = params.get("center") if isinstance(params.get("center"), dict) else {}
        return {
            "algorithm_id": algorithm_id,
            "sectors": geo_algorithms.radial_sar_sectors(
                float(center.get("lat", 0.0)),
                float(center.get("lon", 0.0)),
                float(params.get("radius_m", 1000.0)),
                int(params.get("sector_count", 8)),
            ),
        }

    grid, bbox, cell_size, artifact = _load_package_terrain_grid(package_id)
    rows = len(grid)
    cols = len(grid[0]) if rows else 0

    if algorithm_id in {"terrain_derivatives", "slope_aspect_roughness"}:
        return {
            "algorithm_id": algorithm_id,
            "artifact": artifact.get("relative_path"),
            "bbox": bbox,
            "cell_size_m": cell_size,
            "layers": geo_algorithms.derive_terrain_layers(grid, cell_size_m=cell_size),
        }
    if algorithm_id == "flow_accumulation_d8":
        return {
            "algorithm_id": algorithm_id,
            "artifact": artifact.get("relative_path"),
            "bbox": bbox,
            "accumulation": geo_algorithms.flow_accumulation_d8(grid, cell_size_m=cell_size),
        }
    if algorithm_id == "viewshed":
        observer = params.get("observer_cell") or [rows // 2, cols // 2]
        return {
            "algorithm_id": algorithm_id,
            "artifact": artifact.get("relative_path"),
            "bbox": bbox,
            "visible": geo_algorithms.viewshed(
                grid,
                (int(observer[0]), int(observer[1])),
                cell_size_m=cell_size,
                max_radius_cells=params.get("max_radius_cells"),
            ),
        }
    if algorithm_id == "raster_cost_distance":
        terrain = geo_algorithms.derive_terrain_layers(grid, cell_size_m=cell_size)
        cost = geo_algorithms.build_walking_cost_surface(
            terrain["slope_degrees"],
            max_slope_deg=float(params.get("max_slope_deg", 35.0)),
        )
        start = params.get("start_cell") or [0, 0]
        target = params.get("target_cell")
        result = geo_algorithms.raster_cost_distance(cost, [(int(start[0]), int(start[1]))])
        payload: dict[str, Any] = {
            "algorithm_id": algorithm_id,
            "artifact": artifact.get("relative_path"),
            "bbox": bbox,
            "distance": result.distance,
        }
        if target:
            payload["path"] = geo_algorithms.backtrack_least_cost_path(
                result,
                (int(target[0]), int(target[1])),
            )
        return payload
    if algorithm_id == "sar_probability_surface":
        last_known = params.get("last_known_cell") or [rows // 2, cols // 2]
        return {
            "algorithm_id": algorithm_id,
            "bbox": bbox,
            "probability": geo_algorithms.sar_probability_surface(
                rows,
                cols,
                (int(last_known[0]), int(last_known[1])),
                sigma_cells=float(params.get("sigma_cells", 6.0)),
            ),
        }
    if algorithm_id == "route_score":
        return {
            "algorithm_id": algorithm_id,
            "score": geo_algorithms.score_route(
                normalized_time=float(params.get("normalized_time", 0.5)),
                normalized_energy=float(params.get("normalized_energy", 0.5)),
                hazard_exposure=float(params.get("hazard_exposure", 0.2)),
                data_uncertainty=float(params.get("data_uncertainty", 0.2)),
                resource_value=float(params.get("resource_value", 0.0)),
                rescue_visibility=float(params.get("rescue_visibility", 0.0)),
            ),
        }
    raise HTTPException(status_code=400, detail=f"Unsupported algorithm_id: {algorithm_id}")


def _build_route_from_package(package_id: str, request: PackageRouteRequest) -> dict[str, Any]:
    from llm_dev_kmh import geo_algorithms

    route_id = f"TERA-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6]}"
    coordinates = [[request.start.lon, request.start.lat], [request.end.lon, request.end.lat]]
    cost_breakdown: dict[str, float] = {
        "distance_m": _haversine_m(request.start.lat, request.start.lon, request.end.lat, request.end.lon),
        "time_s": _haversine_m(request.start.lat, request.start.lon, request.end.lat, request.end.lon) / 1.1,
        "elevation_gain_m": 0.0,
    }
    provenance: dict[str, Any] = {"package_id": package_id, "terrain_artifact": None}

    try:
        grid, bbox, cell_size, artifact = _load_package_terrain_grid(package_id)
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        start_cell = _coord_to_cell(request.start.lat, request.start.lon, bbox, rows, cols)
        end_cell = _coord_to_cell(request.end.lat, request.end.lon, bbox, rows, cols)
        terrain = geo_algorithms.derive_terrain_layers(grid, cell_size_m=cell_size)
        cost_surface = geo_algorithms.build_walking_cost_surface(
            terrain["slope_degrees"],
            max_slope_deg=35.0 if "max_slope_35" in request.avoid else 45.0,
        )
        cost_result = geo_algorithms.raster_cost_distance(cost_surface, [start_cell])
        path = geo_algorithms.backtrack_least_cost_path(cost_result, end_cell)
        if path:
            coordinates = []
            elevation_gain = 0.0
            previous_elevation = grid[path[0][0]][path[0][1]]
            for row, col in path:
                lat, lon = _cell_to_coord(row, col, bbox, rows, cols)
                coordinates.append([lon, lat])
                elevation = grid[row][col]
                if math.isfinite(elevation) and math.isfinite(previous_elevation):
                    elevation_gain += max(0.0, elevation - previous_elevation)
                previous_elevation = elevation
            distance_m = sum(
                _haversine_m(left[1], left[0], right[1], right[0])
                for left, right in zip(coordinates, coordinates[1:])
            )
            cost_breakdown = {
                "distance_m": distance_m,
                "time_s": distance_m / 1.1,
                "elevation_gain_m": elevation_gain,
                "raster_cost": float(cost_result.distance[end_cell[0]][end_cell[1]]),
            }
            provenance = {
                "package_id": package_id,
                "terrain_artifact": artifact.get("relative_path"),
                "cell_size_m": cell_size,
                "routing_method": "raster_cost_distance",
            }
    except HTTPException:
        pass
    except Exception as error:
        provenance["terrain_route_error"] = str(error)

    feature = {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "properties": {
            "route_id": route_id,
            "profile": request.profile,
            "avoid": request.avoid,
            "package_id": package_id,
        },
    }
    route_hash = _route_hash(feature)
    response = {
        "route_id": route_id,
        "route_hash": route_hash,
        "route": feature,
        "waypoints": [
            {"lat": request.start.lat, "lon": request.start.lon, "label": "Start"},
            {"lat": request.end.lat, "lon": request.end.lon, "label": "End"},
        ],
        "rationale": (
            f"Generated {request.profile.replace('_', ' ')} route from Jetson package "
            f"{package_id}; distance {cost_breakdown['distance_m'] / 1000.0:.2f} km."
        ),
        "cost_breakdown": cost_breakdown,
        "provenance": provenance,
        "trust": {
            "schema_valid": True,
            "policy_valid": True,
            "operator_approved": False,
            "signature_valid": False,
            "untrusted_inputs_used": False,
            "trust_status": "needs_review",
        },
    }
    routes_dir = _routes_dir(package_id)
    _write_json(routes_dir / f"{route_id}.json", response)
    return response


def _load_route_artifact(package_id: str, route_id: str) -> dict[str, Any]:
    path = _routes_dir(package_id) / f"{_safe_package_id(route_id)}.json"
    route = _read_json(path)
    if route is None:
        raise HTTPException(status_code=404, detail="Route artifact not found.")
    return route


def _build_cot_xml(
    *,
    uid: str,
    cot_type: str,
    lat: float,
    lon: float,
    route: dict[str, Any],
    title: str | None = None,
    remarks: str | None = None,
) -> str:
    if cot_type == "b-m-r":
        return _build_takcot_route_xml(
            uid=uid,
            lat=lat,
            lon=lon,
            route=route,
            title=title,
            remarks=remarks,
        )

    now = datetime.now(timezone.utc)
    now_text = now.isoformat().replace("+00:00", "Z")
    stale_text = datetime.fromtimestamp(now.timestamp() + 3600, timezone.utc).isoformat().replace("+00:00", "Z")
    root = ET.Element(
        "event",
        {
            "version": "2.0",
            "uid": uid,
            "type": cot_type,
            "how": "m-g",
            "time": now_text,
            "start": now_text,
            "stale": stale_text,
        },
    )
    ET.SubElement(
        root,
        "point",
        {
            "lat": f"{lat:.7f}",
            "lon": f"{lon:.7f}",
            "hae": "9999999.0",
            "ce": "9999999.0",
            "le": "9999999.0",
        },
    )
    detail = ET.SubElement(root, "detail")
    route_el = ET.SubElement(detail, "route")
    for index, coordinate in enumerate(route.get("geometry", {}).get("coordinates", [])):
        ET.SubElement(
            route_el,
            "point",
            {
                "lat": f"{float(coordinate[1]):.7f}",
                "lon": f"{float(coordinate[0]):.7f}",
                "index": str(index),
            },
        )
    return ET.tostring(root, encoding="unicode")


def _build_takcot_route_xml(
    *,
    uid: str,
    lat: float,
    lon: float,
    route: dict[str, Any],
    title: str | None,
    remarks: str | None,
) -> str:
    coordinates = _normalized_route_coordinates(route)
    if len(coordinates) < 2:
        raise ValueError("TAK route CoT requires at least two route coordinates.")

    now = datetime.now(timezone.utc)
    now_text = now.isoformat().replace("+00:00", "Z")
    stale_text = (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    route_title = _cot_attr_text(title or _route_title_from_feature(route) or "TERA route")
    route_method, route_type = _takcot_route_method_and_type(route)
    root = ET.Element(
        "event",
        {
            "version": "2.0",
            "uid": uid,
            "type": "b-m-r",
            "how": "m-g",
            "time": now_text,
            "start": now_text,
            "stale": stale_text,
        },
    )
    ET.SubElement(
        root,
        "point",
        {
            "lat": f"{lat:.7f}",
            "lon": f"{lon:.7f}",
            "hae": "9999999.0",
            "ce": "9999999.0",
            "le": "9999999.0",
        },
    )
    detail = ET.SubElement(root, "detail")
    for index, (coord_lon, coord_lat) in enumerate(coordinates):
        callsign = _takcot_link_callsign(route_title, index, len(coordinates))
        link_type = "b-m-p-w" if index in {0, len(coordinates) - 1} else "b-m-p-c"
        ET.SubElement(
            detail,
            "link",
            {
                "uid": f"{uid}-cp-{index:03d}",
                "callsign": callsign,
                "type": link_type,
                "point": f"{coord_lat:.7f},{coord_lon:.7f}",
                "remarks": "",
                "relation": "c",
            },
        )
    ET.SubElement(
        detail,
        "link_attr",
        {
            "planningmethod": "Infil",
            "color": "-1",
            "method": route_method,
            "prefix": "CP",
            "type": route_type,
            "stroke": "3",
            "direction": "Infil",
            "routetype": "Primary",
            "order": "Ascending Check Points",
        },
    )
    ET.SubElement(detail, "strokeColor", {"value": "-1"})
    ET.SubElement(detail, "strokeWeight", {"value": "3.0"})
    routeinfo = ET.SubElement(detail, "__routeinfo")
    ET.SubElement(routeinfo, "__navcues")
    ET.SubElement(detail, "contact", {"callsign": route_title})
    remarks_el = ET.SubElement(detail, "remarks")
    remarks_el.text = _cot_text(remarks or "")
    ET.SubElement(detail, "archive")
    ET.SubElement(detail, "labels_on", {"value": "false"})
    ET.SubElement(detail, "color", {"value": "-1"})
    return ET.tostring(root, encoding="unicode")


def _normalized_route_coordinates(route: dict[str, Any]) -> list[tuple[float, float]]:
    raw_coordinates = route.get("geometry", {}).get("coordinates", [])
    coordinates: list[tuple[float, float]] = []
    if not isinstance(raw_coordinates, list):
        return coordinates
    for coordinate in raw_coordinates:
        if not isinstance(coordinate, list | tuple) or len(coordinate) < 2:
            continue
        coordinates.append((float(coordinate[0]), float(coordinate[1])))
    return coordinates


def _route_title_from_feature(route: dict[str, Any]) -> str:
    properties = route.get("properties")
    if not isinstance(properties, dict):
        return "TERA route"
    for key in ("title", "name", "route_id"):
        value = properties.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "TERA route"


def _takcot_route_method_and_type(route: dict[str, Any]) -> tuple[str, str]:
    properties = route.get("properties")
    profile = ""
    if isinstance(properties, dict):
        profile = str(properties.get("profile") or "").lower()
    if any(token in profile for token in ("vehicle", "truck", "mrap", "drive")):
        return "Driving", "Vehicle"
    if any(token in profile for token in ("water", "boat", "swim")):
        return "Watercraft", "Watercraft"
    return "Walking", "Foot"


def _takcot_link_callsign(route_title: str, index: int, total: int) -> str:
    if index == 0:
        return _cot_attr_text(f"{route_title} SP")
    if index == total - 1:
        return _cot_attr_text(f"{route_title} VDO")
    return _cot_attr_text(f"CP{index}")


def _cot_attr_text(text: str, *, max_length: int = 80) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return "TERA route"
    return cleaned[:max_length]


def _cot_text(text: str, *, max_length: int = 500) -> str:
    return re.sub(r"\s+", " ", text).strip()[:max_length]


def _safe_tak_package_name(value: str | None, *, fallback: str = "TERA-TAK") -> str:
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "_", (value or fallback).strip()).strip("._-")
    return candidate[:80] or fallback


def _kml_coord(lon: float, lat: float, altitude: float | None = None) -> str:
    return f"{lon:.7f},{lat:.7f},{0.0 if altitude is None else altitude:.2f}"


def _tak_cot_payload_to_kml(tak_cot: TakCotPayload) -> str:
    kml_ns = "http://www.opengis.net/kml/2.2"
    kml = ET.Element("kml", {"xmlns": kml_ns})
    document = ET.SubElement(kml, "Document")
    document_name = _safe_tak_package_name(tak_cot.collection_uid, fallback="TERA TAK package")
    ET.SubElement(document, "name").text = document_name
    ET.SubElement(document, "description").text = tak_cot.summary

    route_style = ET.SubElement(document, "Style", {"id": "tera-route"})
    line_style = ET.SubElement(route_style, "LineStyle")
    ET.SubElement(line_style, "color").text = "ffff8700"
    ET.SubElement(line_style, "width").text = "5"

    point_style = ET.SubElement(document, "Style", {"id": "tera-point"})
    icon_style = ET.SubElement(point_style, "IconStyle")
    ET.SubElement(icon_style, "scale").text = "1.1"

    for item in tak_cot.items:
        placemark = ET.SubElement(document, "Placemark")
        ET.SubElement(placemark, "name").text = item.title or item.uid
        description_parts = [
            f"uid={item.uid}",
            f"cot_type={item.cot_type}",
            f"item_type={item.item_type}",
        ]
        if item.metadata.get("distance_m") is not None:
            description_parts.append(f"distance_m={item.metadata['distance_m']}")
        ET.SubElement(placemark, "description").text = "\n".join(description_parts)
        extended = ET.SubElement(placemark, "ExtendedData")
        for key, value in (
            ("uid", item.uid),
            ("cot_type", item.cot_type),
            ("item_type", item.item_type),
        ):
            data = ET.SubElement(extended, "Data", {"name": key})
            ET.SubElement(data, "value").text = value

        if item.item_type == "route" and len(item.coordinates) >= 2:
            ET.SubElement(placemark, "styleUrl").text = "#tera-route"
            line = ET.SubElement(placemark, "LineString")
            ET.SubElement(line, "tessellate").text = "1"
            ET.SubElement(line, "coordinates").text = " ".join(
                _kml_coord(float(coord[0]), float(coord[1]))
                for coord in item.coordinates
                if len(coord) >= 2
            )
            for checkpoint in item.checkpoints:
                checkpoint_pm = ET.SubElement(document, "Placemark")
                ET.SubElement(checkpoint_pm, "name").text = checkpoint.label
                ET.SubElement(checkpoint_pm, "styleUrl").text = "#tera-point"
                cp_extended = ET.SubElement(checkpoint_pm, "ExtendedData")
                data = ET.SubElement(cp_extended, "Data", {"name": "uid"})
                ET.SubElement(data, "value").text = checkpoint.uid
                point = ET.SubElement(checkpoint_pm, "Point")
                ET.SubElement(point, "coordinates").text = _kml_coord(
                    checkpoint.lon,
                    checkpoint.lat,
                )
        elif item.lat is not None and item.lon is not None:
            ET.SubElement(placemark, "styleUrl").text = "#tera-point"
            point = ET.SubElement(placemark, "Point")
            ET.SubElement(point, "coordinates").text = _kml_coord(item.lon, item.lat)

    ET.indent(kml, space="  ")
    return ET.tostring(kml, encoding="utf-8", xml_declaration=True).decode("utf-8")


def _tak_data_package_manifest(tak_cot: TakCotPayload, cot_entries: list[str]) -> str:
    manifest = ET.Element("MissionPackageManifest", {"version": "2"})
    configuration = ET.SubElement(manifest, "Configuration")
    ET.SubElement(configuration, "Parameter", {"name": "uid", "value": tak_cot.collection_uid or "TERA-TAK"})
    ET.SubElement(configuration, "Parameter", {"name": "name", "value": "TERA TAK package"})
    ET.SubElement(configuration, "Parameter", {"name": "remarks", "value": tak_cot.summary})
    contents = ET.SubElement(manifest, "Contents")
    ET.SubElement(contents, "Content", {"ignore": "false", "zipEntry": "doc.kml"})
    for entry in cot_entries:
        ET.SubElement(contents, "Content", {"ignore": "false", "zipEntry": entry})
    ET.indent(manifest, space="  ")
    return ET.tostring(manifest, encoding="utf-8", xml_declaration=True).decode("utf-8")


def _tak_cot_file_package(tak_cot: TakCotPayload) -> TakCotFilePackage | None:
    if not tak_cot.items:
        return None

    file_stem = _safe_tak_package_name(tak_cot.collection_uid)
    file_name = f"{file_stem}.kmz"
    kml = _tak_cot_payload_to_kml(tak_cot)
    cot_entries: list[str] = []

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("doc.kml", kml)
        for item in tak_cot.items:
            if not item.cot_xml:
                continue
            entry_name = f"cot/{_safe_tak_package_name(item.uid)}.xml"
            cot_entries.append(entry_name)
            package.writestr(entry_name, item.cot_xml)
        package.writestr("MANIFEST/manifest.xml", _tak_data_package_manifest(tak_cot, cot_entries))

    content = buffer.getvalue()
    return TakCotFilePackage(
        file_name=file_name,
        content_b64=base64.b64encode(content).decode("ascii"),
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        target_path=f"/sdcard/fromTERA/{file_name}",
        item_count=len(tak_cot.items),
    )


def _sign_cot_xml(
    *,
    uid: str,
    lat: float,
    lon: float,
    route: dict[str, Any],
    rationale: str,
    mission_type: str,
    cot_xml: str,
) -> tuple[str, dict[str, Any]]:
    try:
        from crypto.cot_signer import CotRoute, embed_signature_in_cot_xml, sign_cot

        signed = sign_cot(
            CotRoute(
                uid=uid,
                lat=lat,
                lon=lon,
                route_geojson=route,
                rationale=rationale,
                mission_type=mission_type,
            )
        )
        return embed_signature_in_cot_xml(cot_xml, signed), signed
    except ImportError:
        pass

    try:
        from crypto.ml_dsa_signer import create_signer
    except ImportError as error:
        raise HTTPException(status_code=503, detail="TERA signing modules are unavailable.") from error

    payload = {
        "uid": uid,
        "lat": lat,
        "lon": lon,
        "route_hash": hashlib.sha256(json.dumps(route, sort_keys=True).encode()).hexdigest(),
        "rationale": rationale,
        "mission_type": mission_type,
    }
    try:
        signed = create_signer(os.getenv("WAYFINDER_KEY_ID", "wayfinder-device-001")).sign(payload).to_dict()
    except RuntimeError as error:
        dev_key = os.getenv("WAYFINDER_HMAC_KEY", "").encode("utf-8")
        if not dev_key:
            raise HTTPException(status_code=503, detail="TERA signing dependencies are unavailable.") from error
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        signed = {
            "payload": payload,
            "signature": hmac.new(dev_key, canonical, hashlib.sha256).hexdigest(),
            "key_id": os.getenv("WAYFINDER_KEY_ID", "wayfinder-device-001"),
            "algorithm": "HMAC-SHA256-dev-fallback",
            "timestamp": datetime.now(timezone.utc).timestamp(),
            "payload_hash": hashlib.sha256(canonical).hexdigest(),
        }
    root = ET.fromstring(cot_xml)
    detail = root.find("detail")
    if detail is None:
        detail = ET.SubElement(root, "detail")
    for old in detail.findall("wayfinder"):
        detail.remove(old)
    wayfinder = ET.SubElement(detail, "wayfinder")
    ET.SubElement(wayfinder, "signature").text = signed["signature"]
    ET.SubElement(wayfinder, "key_id").text = signed["key_id"]
    ET.SubElement(wayfinder, "algorithm").text = signed["algorithm"]
    ET.SubElement(wayfinder, "timestamp").text = str(signed["timestamp"])
    ET.SubElement(wayfinder, "payload_hash").text = signed["payload_hash"]
    ET.SubElement(wayfinder, "payload_json").text = json.dumps(
        signed["payload"],
        sort_keys=True,
        separators=(",", ":"),
    )
    return ET.tostring(root, encoding="unicode"), signed


def _active_tak_item_count(map_context: MapContext | None) -> int:
    if map_context is None:
        return 0
    return len(map_context.tera_active_items)


def _origin_from_map_context(map_context: MapContext | None) -> MapPoint | None:
    if map_context is None:
        return None
    if map_context.client_location is not None:
        return map_context.client_location
    for candidate in (
        map_context.selected_area,
        map_context.view_bounds,
    ):
        if (
            candidate is not None
            and candidate.center_lat is not None
            and candidate.center_lon is not None
        ):
            return MapPoint(lat=candidate.center_lat, lon=candidate.center_lon)
    if map_context.camera is not None:
        return map_context.camera
    return None


def _explicit_prompt_radius_m(prompt: str) -> float | None:
    match = re.search(
        r"within\s+(\d+(?:\.\d+)?)\s*(km|kilometer|kilometers|mile|miles|mi)\b",
        prompt.lower(),
    )
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2)
    if unit in {"mile", "miles", "mi"}:
        return value * 1609.344
    return value * 1000.0


def _prompt_radius_m(prompt: str) -> float:
    return _explicit_prompt_radius_m(prompt) or 5000.0


def _bounds_contains_point(bounds: ViewBounds | None, lat: float, lon: float) -> bool:
    if bounds is None:
        return False
    if lat < bounds.south or lat > bounds.north:
        return False
    if bounds.west <= bounds.east:
        return bounds.west <= lon <= bounds.east
    return lon >= bounds.west or lon <= bounds.east


def _view_bounds_radius_m(origin: MapPoint, bounds: ViewBounds | None) -> float | None:
    if bounds is None:
        return None
    corners = (
        (bounds.south, bounds.west),
        (bounds.south, bounds.east),
        (bounds.north, bounds.west),
        (bounds.north, bounds.east),
    )
    return max(_haversine_m(origin.lat, origin.lon, lat, lon) for lat, lon in corners)


def _tak_query_radius_m(
    prompt: str,
    map_context: MapContext | None,
    origin: MapPoint,
) -> float:
    explicit_radius = _explicit_prompt_radius_m(prompt)
    if explicit_radius is not None:
        return explicit_radius
    view_radius = _view_bounds_radius_m(
        origin,
        map_context.view_bounds if map_context else None,
    )
    if view_radius is None:
        return 5000.0
    return min(max(view_radius, 500.0), 50000.0)


def _tak_target_type_for_prompt(prompt: str) -> str | None:
    text = prompt.lower()
    if _text_has_any(text, ("water", "fresh water", "freshwater", "stream", "river", "spring")):
        return "freshwater"
    if _text_has_any(text, ("shelter", "cabin", "hut", "camp", "bivy")):
        return "shelter"
    if _text_has_any(text, ("hospital", "clinic", "aid station", "medic", "medical")):
        return "medical"
    if _text_has_any(text, ("trailhead", "trail head")):
        return "trailhead"
    if _text_has_any(text, ("road", "vehicle access", "extraction", "pickup")):
        return "road"
    if _text_has_any(text, ("trail", "path")):
        return "trail"
    if _text_has_any(text, ("signal", "comms", "communications", "radio", "tower")):
        return "signal"
    if _text_has_any(text, ("ridge", "high ground", "peak", "summit", "overlook")):
        return "high_ground"
    if _text_has_any(text, ("landing zone", "lz", "clearing", "open area")):
        return "lz"
    if _text_has_any(text, ("bridge", "ford", "crossing")):
        return "bridge"
    return None


def _tak_target_type_from_active_items(map_context: MapContext | None) -> str | None:
    if map_context is None:
        return None
    for item in map_context.tera_active_items:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata")
        if isinstance(metadata, dict) and metadata.get("target_type"):
            return str(metadata["target_type"])
        if item.get("target_type"):
            return str(item["target_type"])
    return None


def _tak_route_requested(prompt: str) -> bool:
    text = prompt.lower()
    return _text_has_any(
        text,
        (
            "route",
            "navigate",
            "navigation",
            "path",
            "walk",
            "move",
            "go to",
            "get to",
            "evac",
            "evacuation",
            "approach",
        ),
    )


def _tak_points_requested(prompt: str) -> bool:
    text = prompt.lower()
    return _text_has_any(
        text,
        (
            "mark",
            "show",
            "plot",
            "find",
            "where",
            "nearest",
            "points",
            "symbols",
        ),
    )


def _tak_alternate_requested(prompt: str, map_context: MapContext | None) -> bool:
    text = prompt.lower()
    return _active_tak_item_count(map_context) > 0 and _text_has_any(
        text,
        (
            "doesn't work",
            "does not work",
            "can't walk",
            "cannot walk",
            "rework",
            "reroute",
            "alternate",
            "different route",
            "blocked",
            "avoid that",
        ),
    )


def _atak_monitor_client_location(map_context: MapContext | None) -> MapPoint | None:
    return map_context.client_location if map_context and map_context.client_location else None


def _atak_monitor_view_bounds(map_context: MapContext | None) -> ViewBounds | None:
    return map_context.view_bounds if map_context and map_context.view_bounds else None


def _atak_monitor_query_context(request: PromptRequest) -> dict[str, Any]:
    map_context = request.map_context
    origin = _origin_from_map_context(map_context)
    target_type = _tak_target_type_for_prompt(request.prompt)
    alternate_requested = _tak_alternate_requested(request.prompt, map_context)
    if target_type is None and alternate_requested:
        target_type = _tak_target_type_from_active_items(map_context)

    context: dict[str, Any] = {
        "data_sources": [
            "OSM vectors from /WINTAK Imagery",
            "DTED terrain from /DTED",
        ],
        "active_tak_items": _active_tak_item_count(map_context),
        "route_requested": _tak_route_requested(request.prompt) or alternate_requested,
        "points_requested": _tak_points_requested(request.prompt),
    }
    if target_type:
        context["target_type"] = target_type
    if origin is not None:
        context["origin"] = origin.model_dump()
        context["radius_m"] = _tak_query_radius_m(request.prompt, map_context, origin)
    if alternate_requested:
        context["reroute"] = True
    if map_context and map_context.client_location:
        context["client_location_source"] = "atak_self_marker"
    if map_context and map_context.view_bounds:
        context["bounds_source"] = "atak_displayed_map_view"
    return context


def _tak_cot_monitor_summary(tak_cot: TakCotPayload) -> dict[str, Any]:
    return {
        "summary": tak_cot.summary,
        "algorithm": tak_cot.algorithm,
        "item_count": len(tak_cot.items),
        "items": [
            {
                "uid": item.uid,
                "item_type": item.item_type,
                "cot_type": item.cot_type,
                "title": item.title,
                "coordinate_count": len(item.coordinates),
                "checkpoint_count": len(item.checkpoints),
            }
            for item in tak_cot.items
        ],
    }


def _feature_to_poi(feature: Any) -> dict[str, Any]:
    if hasattr(feature, "to_poi"):
        poi = feature.to_poi()
        if isinstance(poi, dict):
            return poi
    if isinstance(feature, dict):
        return feature
    return {}


def _direct_route_coordinates(
    origin: MapPoint,
    target_lat: float,
    target_lon: float,
) -> list[list[float]]:
    mid_lat = (origin.lat + target_lat) / 2.0
    mid_lon = (origin.lon + target_lon) / 2.0
    return [
        [origin.lon, origin.lat],
        [mid_lon, mid_lat],
        [target_lon, target_lat],
    ]


def _route_checkpoints(
    *,
    uid: str,
    coordinates: list[list[float]],
    target_label: str,
) -> list[TakCotCheckpoint]:
    if len(coordinates) < 2:
        return []
    checkpoints = [
        TakCotCheckpoint(
            uid=f"{uid}-start",
            label="Start",
            lat=float(coordinates[0][1]),
            lon=float(coordinates[0][0]),
        )
    ]
    if len(coordinates) > 2:
        checkpoints.append(
            TakCotCheckpoint(
                uid=f"{uid}-cp1",
                label="Checkpoint 1",
                lat=float(coordinates[1][1]),
                lon=float(coordinates[1][0]),
            )
        )
    checkpoints.append(
        TakCotCheckpoint(
            uid=f"{uid}-target",
            label=target_label,
            lat=float(coordinates[-1][1]),
            lon=float(coordinates[-1][0]),
        )
    )
    return checkpoints


def _route_feature_from_coordinates(
    *, uid: str, coordinates: list[list[float]], profile: str, target_type: str
) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "properties": {
            "route_id": uid,
            "profile": profile,
            "target_type": target_type,
            "algorithm": "osm_nearest_feature_direct_route",
        },
    }


def _tak_item_uid(prompt: str, origin: MapPoint, target_lat: float, target_lon: float) -> str:
    digest = hashlib.sha256(
        f"{prompt}|{origin.lat:.6f}|{origin.lon:.6f}|{target_lat:.6f}|{target_lon:.6f}".encode(
            "utf-8"
        )
    ).hexdigest()[:10]
    return f"TERA-TAK-{digest}"


def _query_tak_targets(
    *, target_type: str, origin: MapPoint, radius_m: float, limit: int
) -> list[dict[str, Any]]:
    try:
        from routing.osm_sqlite_features import query_osm_features
    except ImportError:
        return []

    try:
        features = query_osm_features(
            target_type=target_type,
            origin={"lat": origin.lat, "lon": origin.lon},
            radius_m=radius_m,
            limit=limit,
        )
    except Exception as exc:  # noqa: BLE001 - local database shape should not break chat.
        log.warning("tak_cot_osm_query_failed", target_type=target_type, error=str(exc))
        return []
    targets: list[dict[str, Any]] = []
    for feature in features:
        poi = _feature_to_poi(feature)
        if poi:
            targets.append(poi)
    return targets


def _rank_tak_targets_for_map_context(
    targets: list[dict[str, Any]],
    map_context: MapContext | None,
) -> list[dict[str, Any]]:
    bounds = map_context.view_bounds if map_context else None
    ranked: list[dict[str, Any]] = []
    for target in targets:
        target_copy = dict(target)
        try:
            inside_view = _bounds_contains_point(
                bounds,
                float(target_copy["lat"]),
                float(target_copy["lon"]),
            )
        except (KeyError, TypeError, ValueError):
            inside_view = False
        target_copy["inside_view_bounds"] = inside_view
        ranked.append(target_copy)

    visible_targets = [target for target in ranked if target["inside_view_bounds"]]
    return visible_targets or ranked


def _build_tak_cot_payload(request: PromptRequest, response_text: str) -> TakCotPayload:
    profile = (request.agent_profile or "").strip().lower()
    if "atak" not in profile and not JETSON_ATAK_MODE.get("active"):
        return TakCotPayload()

    origin = _origin_from_map_context(request.map_context)
    target_type = _tak_target_type_for_prompt(request.prompt)
    alternate_requested = _tak_alternate_requested(request.prompt, request.map_context)
    if target_type is None and alternate_requested:
        target_type = _tak_target_type_from_active_items(request.map_context)
    if origin is None or target_type is None:
        return TakCotPayload()

    route_requested = _tak_route_requested(request.prompt) or alternate_requested
    points_requested = _tak_points_requested(request.prompt)
    if not route_requested and not points_requested:
        return TakCotPayload()

    limit = 5 if points_requested and not route_requested else 3
    query_limit = 20 if request.map_context and request.map_context.view_bounds else limit
    radius_m = _tak_query_radius_m(request.prompt, request.map_context, origin)
    targets = _query_tak_targets(
        target_type=target_type,
        origin=origin,
        radius_m=radius_m,
        limit=query_limit,
    )
    targets = _rank_tak_targets_for_map_context(targets, request.map_context)
    if not targets:
        return TakCotPayload(
            summary=f"No local {target_type} target found within {radius_m:.0f} m.",
            algorithm="osm_nearest_feature_lookup",
        )

    target_index = (
        1
        if alternate_requested and len(targets) > 1
        else 0
    )
    target = targets[target_index]
    target_label = str(target.get("name") or target_type.replace("_", " ").title())
    target_lat = float(target["lat"])
    target_lon = float(target["lon"])
    collection_uid = _tak_item_uid(request.prompt, origin, target_lat, target_lon)
    items: list[TakCotItem] = []

    if route_requested:
        coordinates = _direct_route_coordinates(origin, target_lat, target_lon)
        route_uid = f"{collection_uid}-route"
        route = _route_feature_from_coordinates(
            uid=route_uid,
            coordinates=coordinates,
            profile="foot_covered",
            target_type=target_type,
        )
        cot_xml = _build_cot_xml(
            uid=route_uid,
            cot_type="b-m-r",
            lat=target_lat,
            lon=target_lon,
            route=route,
            title=f"TERA route to {target_label}",
            remarks=response_text,
        )
        items.append(
            TakCotItem(
                uid=route_uid,
                item_type="route",
                cot_type="b-m-r",
                title=f"TERA route to {target_label}",
                lat=target_lat,
                lon=target_lon,
                coordinates=coordinates,
                checkpoints=_route_checkpoints(
                    uid=route_uid,
                    coordinates=coordinates,
                    target_label=target_label,
                ),
                cot_xml=cot_xml,
                metadata={
                    "target_type": target_type,
                    "target": target,
                    "distance_m": target.get("distance_m"),
                    "response_excerpt": response_text[:240],
                    "takcot_schema": "Route.xsd",
                    "takcot_type": "b-m-r",
                },
            )
        )
    else:
        for index, poi in enumerate(targets[:5], start=1):
            point_lat = float(poi["lat"])
            point_lon = float(poi["lon"])
            point_label = str(poi.get("name") or f"{target_type} {index}")
            point_uid = f"{collection_uid}-pt-{index:02d}"
            point_route = _route_feature_from_coordinates(
                uid=point_uid,
                coordinates=[[point_lon, point_lat]],
                profile="point",
                target_type=target_type,
            )
            cot_xml = _build_cot_xml(
                uid=point_uid,
                cot_type="a-f-G-U-C",
                lat=point_lat,
                lon=point_lon,
                route=point_route,
                title=point_label,
                remarks=response_text,
            )
            items.append(
                TakCotItem(
                    uid=point_uid,
                    item_type="point",
                    cot_type="a-f-G-U-C",
                    title=point_label,
                    lat=point_lat,
                    lon=point_lon,
                    cot_xml=cot_xml,
                    metadata={
                        "target_type": target_type,
                        "target": poi,
                        "distance_m": poi.get("distance_m"),
                    },
                )
            )

    payload = TakCotPayload(
        replace_existing=True,
        collection_uid=collection_uid,
        summary=(
            f"Generated {len(items)} TAK item(s) from local {target_type} query "
            f"within {radius_m:.0f} m."
        ),
        algorithm=(
            "osm_nearest_feature_direct_route"
            if route_requested
            else "osm_nearest_feature_points"
        ),
        items=items,
    )
    payload.package = _tak_cot_file_package(payload)
    return payload


def _response_text_with_tak_cot_summary(text: str, tak_cot: TakCotPayload) -> str:
    if tak_cot.items:
        return f"{text}\n\nTAK CoT: {tak_cot.summary}"
    return text


def _normalize_for_match(text: str) -> str:
    expanded = text.lower()
    for canonical, aliases in KEYWORD_EXPANSIONS.items():
        for alias in aliases:
            expanded = re.sub(rf"\b{re.escape(alias)}\b", canonical, expanded)
    return re.sub(r"[^a-z0-9]+", " ", expanded).strip()


def _tokens_for_match(text: str) -> list[str]:
    return [token for token in _normalize_for_match(text).split() if token]


def _token_matches(candidate: str, target: str) -> bool:
    if candidate == target:
        return True
    if len(candidate) >= 4 and len(target) >= 4:
        if candidate.startswith(target) or target.startswith(candidate):
            return True
        return SequenceMatcher(None, candidate, target).ratio() >= 0.82
    return False


def _phrase_matches(text_tokens: list[str], term_tokens: list[str]) -> bool:
    if not term_tokens:
        return False
    if len(term_tokens) == 1:
        return any(_token_matches(token, term_tokens[0]) for token in text_tokens)
    if len(text_tokens) < len(term_tokens):
        return False
    for index in range(0, len(text_tokens) - len(term_tokens) + 1):
        window = text_tokens[index : index + len(term_tokens)]
        if all(_token_matches(token, term) for token, term in zip(window, term_tokens)):
            return True
    return False


def _text_has_any(text: str, terms: tuple[str, ...]) -> bool:
    normalized_text = _normalize_for_match(text)
    text_tokens = normalized_text.split()
    for term in terms:
        expanded_terms = (term, *KEYWORD_EXPANSIONS.get(term, ()))
        for expanded_term in expanded_terms:
            normalized_term = _normalize_for_match(expanded_term)
            if not normalized_term:
                continue
            if f" {normalized_term} " in f" {normalized_text} ":
                return True
            if _phrase_matches(text_tokens, normalized_term.split()):
                return True
    return False


def _infer_is_us_context(prompt_text: str, map_context: MapContext | None) -> bool:
    if _text_has_any(prompt_text, US_CONTEXT_TERMS):
        return True
    bounds = None
    if map_context and (map_context.location_confirmed or map_context.selected_area):
        bounds = map_context.selected_area or map_context.view_bounds
    if bounds and bounds.center_lat is not None and bounds.center_lon is not None:
        return 18.0 <= bounds.center_lat <= 72.0 and -170.0 <= bounds.center_lon <= -50.0
    return False


def _infer_mission_focus(prompt_text: str) -> str:
    scores: dict[str, int] = {}
    for focus, keywords in FOCUS_KEYWORDS:
        score = sum(1 for keyword in keywords if _text_has_any(prompt_text, (keyword,)))
        if score:
            scores[focus] = score
    if not scores:
        return "mission-data-package"
    return max(scores.items(), key=lambda item: item[1])[0]


def _append_unique(source_ids: list[str], *new_source_ids: str) -> None:
    for source_id in new_source_ids:
        if source_id in SOURCE_BY_ID and source_id not in source_ids:
            source_ids.append(source_id)


def _sanitize_package_slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:60] or "mission-package"


def _infer_source_recommendation(
    mission_text: str, map_context: MapContext | None
) -> SourceRecommendationResponse:
    prompt_text = mission_text.strip().lower()
    mission_focus = _infer_mission_focus(prompt_text)

    required_ids: list[str] = []
    optional_ids: list[str] = []
    questions: list[str] = []
    rationale: list[str] = []

    rationale.append(
        "Jetson demo file selection is fixed to root-staged analytical data: "
        "OSM vectors under /WINTAK Imagery and DTED terrain under /DTED. "
        "Do not select any source outside that allowlist for agentic answers "
        "or TAK actions."
    )

    needs_routing = _text_has_any(
        prompt_text,
        (
            "route",
            "routing",
            "patrol",
            "walk",
            "foot",
            "trail",
            "road",
            "evac",
            "exfil",
            "nearest",
            "avoid",
        ),
    )
    needs_terrain = needs_routing or _text_has_any(
        prompt_text,
        ("terrain", "slope", "ridge", "mountain", "valley", "steep", "exposed", "viewshed"),
    )
    needs_dted = _text_has_any(prompt_text, ("dted", "dt2", "earth explorer", "earthexplorer"))
    needs_water = _text_has_any(
        prompt_text, ("water", "stream", "river", "spring", "lake", "potable", "hydrate")
    )
    needs_landcover = needs_routing or _text_has_any(
        prompt_text, ("cover", "conceal", "brush", "forest", "canopy", "wetland", "vegetation")
    )
    needs_hazards = _text_has_any(
        prompt_text,
        ("wildfire", "fire", "flood", "storm", "weather", "avalanche", "closure", "hazard"),
    )
    needs_access = _text_has_any(
        prompt_text,
        ("private", "restricted", "public land", "boundary", "parcel", "permission", "access"),
    )
    needs_signal = _text_has_any(
        prompt_text,
        ("signal", "radio", "comms", "communications", "line of sight", "los", "relay"),
    )
    needs_sar = _text_has_any(prompt_text, ("sar", "search", "rescue", "missing", "lost person"))
    needs_current_imagery = _text_has_any(
        prompt_text, ("current", "recent", "latest", "flood", "burn", "changed", "cloud")
    )
    needs_cesium_archive = "cesium" in prompt_text and _text_has_any(
        prompt_text, ("download", "offline", "archive", "export", "jetson", "local")
    )

    if needs_cesium_archive:
        rationale.append(
            "External archive requests are out of scope for this Jetson demo; "
            "use the root-staged OSM and DTED allowlist instead."
        )

    if needs_routing:
        _append_unique(required_ids, "osm_extract")
        rationale.append(
            "OSM from /WINTAK Imagery is required for local routable graph, POI, "
            "waterway, trail, road, and obstacle lookup."
        )

    if needs_terrain:
        _append_unique(required_ids, "dted_earth_explorer")
        rationale.append(
            "DTED from /DTED is the only deterministic terrain source for slope, "
            "exposure, viewshed, and cost-surface work in this Jetson demo."
        )

    if needs_dted:
        _append_unique(required_ids, "dted_earth_explorer")
        rationale.append(
            "DTED was explicitly requested, so the importer uses the root-staged "
            "/DTED folder unless DTED_SOURCE_DIR overrides it."
        )

    if needs_landcover:
        rationale.append(
            "No separate land-cover source is selected for the Jetson demo; covered "
            "movement must be inferred from OSM features plus DTED terrain only."
        )

    if needs_water:
        _append_unique(required_ids, "osm_extract")
        rationale.append(
            "Water-source lookup uses OSM waterway, spring, river, lake, and related "
            "tags from the local WinTAK imagery folder; no external hydrography is selected."
        )

    if needs_sar:
        _append_unique(required_ids, "osm_extract")
        rationale.append(
            "SAR planning uses OSM access/feature data for action and DTED for "
            "terrain constraints; no separate imagery or hazard source is selected."
        )

    if needs_hazards:
        rationale.append(
            "Live hazard feeds are not selected for the offline Jetson demo; hazards "
            "must come from OSM features, DTED terrain, or the operator prompt."
        )

    if needs_access:
        _append_unique(required_ids, "osm_extract")
        rationale.append(
            "Access and barriers are constrained to OSM tags for this Jetson demo; "
            "parcel or managed-land overlays are not selected."
        )

    if needs_signal:
        _append_unique(required_ids, "osm_extract", "dted_earth_explorer")
        if not needs_terrain:
            _append_unique(required_ids, "dted_earth_explorer")
        rationale.append(
            "Signal planning uses DTED-derived viewshed/high-ground checks and OSM "
            "tower/peak/lookout tags only."
        )

    if needs_current_imagery and not needs_water and not needs_hazards:
        rationale.append(
            "Current imagery feeds are not selected. The Jetson agentic path ignores "
            "imagery sources and answers from local OSM vectors plus DTED terrain only."
        )

    if map_context is None or not (map_context.location_confirmed or map_context.selected_area):
        questions.append(
            "Move the map to the mission AO with search, KML/KMZ import, or AO "
            "drawing and confirm that view before final source selection. The "
            "AO decides which local OSM and DTED files are relevant."
        )

    if not required_ids:
        questions.append(
            "Which mission outcome must the database answer first: routing, "
            "water lookup, SAR sectors, signal planning, hazards, or access "
            "control? This decides how OSM and DTED are queried."
        )
        rationale.append(
            "No deterministic analytical layer was identified yet, so the "
            "package stays in preview mode."
        )

    if needs_routing and not _text_has_any(
        prompt_text, ("foot", "vehicle", "atv", "convoy", "boat", "drone")
    ):
        questions.append(
            "Should movement be optimized for foot, vehicle, ATV, boat, "
            "drone, or mixed movement? This determines whether OSM roads "
            "alone are enough or whether trail/off-road friction layers are "
            "required."
        )
    if needs_water:
        questions.append(
            "Is the operator asking for mapped water features only, or confidence "
            "that the point is usable? The demo can map OSM water features, but "
            "potability/current flow must remain a caveat."
        )
    if needs_hazards:
        questions.append(
            "Which hazards should the operator avoid if they are not present in "
            "OSM or visible from DTED-derived terrain? The demo will treat those "
            "as operator-stated constraints."
        )
    if needs_signal:
        questions.append(
            "What antenna height and radio role should viewshed or relay "
            "analysis assume? The demo can use OSM tower/peak candidates and "
            "DTED-derived line-of-sight only."
        )
    if needs_access:
        questions.append(
            "Should the route avoid access restrictions that appear in OSM tags, "
            "or only support terrain movement? The demo does not add parcel or "
            "managed-land overlays."
        )
    if map_context is None or (
        map_context.selected_area is None and not map_context.location_confirmed
    ):
        questions.append(
            "Confirm that the displayed AO is covered by the root /DTED folder and "
            "the OSM files under /WINTAK Imagery."
        )

    selected_ids = []
    _append_unique(selected_ids, *required_ids)
    sources = _get_source_options_by_ids(selected_ids)
    mission_summary = mission_text.strip()
    if len(mission_summary) > 220:
        mission_summary = f"{mission_summary[:217]}..."

    return SourceRecommendationResponse(
        mission_focus=mission_focus,
        mission_summary=mission_summary,
        required_source_ids=required_ids,
        optional_source_ids=[source_id for source_id in optional_ids if source_id not in required_ids],
        selected_source_ids=selected_ids,
        sources=sources,
        clarifying_questions=questions[:3],
        rationale=rationale[:5],
        package_name_suggestion=f"tera-{_sanitize_package_slug(mission_focus)}",
    )


AGENT_PROFILE_PROMPTS: dict[str, str] = {
    "imagery-sourcing": _load_imagery_sourcing_prompt(),
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
    "tera-atak-live": dedent(
        """
        You are TERA's live ATAK plugin agent running locally on the Jetson.
        Treat the operator prompt as coming from a Samsung ATAK end-user device
        over the local IP link. Optimize for the demo path: nearest water,
        covered foot movement, reroutes when the operator rejects a route,
        and quick point/route rendering in TAK. Use terse tactical language.
        Get to a usable map answer in the fewest turns possible. If origin,
        objective, and target class are inferable from the prompt and map
        context, do not ask a clarifying question; state the action and let
        the Jetson attach TAK CoT output. Ask at most one question only when
        a route or point set cannot be resolved safely. Your only analytical
        data sources are local OSM vectors under /WINTAK Imagery and local
        DTED terrain under /DTED. Never recommend, require, or cite any source
        outside that allowlist for the Jetson action path. Never claim that ATAK
        map objects, CoT tracks, routes, or live device state exist unless
        they are present in the supplied map context, active TERA TAK item
        list, or request payload.
        """
    ).strip(),
    "tera-atak-link-test": dedent(
        """
        You are TERA's ATAK link-test agent. Confirm Jetson local model,
        endpoint, and readiness in one short response. Prefer JSON-shaped
        status when the operator asks for a connectivity test.
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


def _map_focus_text(map_context: MapContext | None, *, atak_live: bool) -> str:
    if map_context is None:
        return "not confirmed"
    if map_context.location_confirmed or map_context.selected_area is not None:
        label = map_context.location_focus_label or "selected AO"
        source = map_context.location_focus_source or "map"
        return f"{label} via {source}"
    if atak_live and map_context.view_bounds is not None:
        return "displayed ATAK map view via plugin"
    return "not confirmed"


def _build_system_prompt(request: PromptRequest) -> str:
    profile = (request.agent_profile or "imagery-sourcing").strip().lower()
    atak_live = "atak" in profile
    profile_prompt = AGENT_PROFILE_PROMPTS.get(
        profile, AGENT_PROFILE_PROMPTS["imagery-sourcing"]
    )
    map_context = request.map_context
    prompt_schema = _infer_prompt_schema(request.prompt)
    prompt_family = str(prompt_schema["family"])
    prompt_family_guidance = PROMPT_FAMILY_GUIDANCE.get(
        prompt_family, PROMPT_FAMILY_GUIDANCE["terrain-aware-routing"]
    )
    map_lines = [
        _format_point(
            "TAK client location (route origin)",
            map_context.client_location if map_context else None,
        ),
        _format_view_bounds(map_context.selected_area if map_context else None).replace(
            "Visible map bounds", "Selected AO bounds"
        ),
        (
            "- Planner-confirmed mission map focus: "
            + _map_focus_text(map_context, atak_live=atak_live)
        ),
        _format_point("Displayed map center", map_context.camera if map_context else None),
        _format_view_bounds(map_context.view_bounds if map_context else None).replace(
            "Visible map bounds",
            "Displayed ATAK map bounds",
        ),
        f"- Imagery source: {(map_context.imagery_source if map_context else None) or 'unknown'}",
        f"- Terrain source: {(map_context.terrain_source if map_context else None) or 'unknown'}",
        (
            "- Deterministic Jetson sources: OSM vectors from /WINTAK Imagery "
            "and DTED terrain from /DTED; NAIP/OSM imagery is display-only."
        ),
        f"- Active TERA TAK items on map: {_active_tak_item_count(map_context) if map_context else 0}",
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
            f"Current source package context:\n{_format_source_context(request.source_context)}",
            f"Available data source catalog:\n{_format_source_catalog_brief()}",
            "\n".join(
                [
                    "Rules:",
                    "- Keep the answer concise and operational.",
                    "- Mention visible terrain relationships before recommendations.",
                    (
                        "- For imagery-sourcing requests, separate display streams from "
                        "analysis/download datasets and explain required, optional, and "
                        "not-needed sources."
                    ),
                    (
                        "- Do not recommend the full catalog. Optimize for the smallest "
                        "package that enables the mission and explain what would be missing "
                        "if a source is omitted."
                    ),
                    (
                        "- Drive source planning to mission scope in the fewest useful turns: "
                        "combine missing AO, objective, movement mode, time horizon, and "
                        "constraints into one ranked scope pass when possible."
                    ),
                    (
                        "- If the planner-confirmed mission map focus is not confirmed, "
                        "tell the planner to move the map with location search, import a "
                        "KML/KMZ overlay, or draw an AO before final source confirmation."
                    ),
                    (
                        "- Ask no more than three clarifying questions, and only ask "
                        "questions that would materially change the data package."
                    ),
                    (
                        "- Use a Socratic sourcing dialogue for imagery-sourcing: "
                        "reflect the mission read, ask ranked questions that broaden "
                        "or limit the package, and state what source decision each "
                        "answer controls."
                    ),
                    (
                        "- Do not present a final manifest-style answer until the "
                        "planner has confirmed mission scope and source families."
                    ),
                    (
                        "- In ATAK live mode, be decisive: if the prompt names a target "
                        "class and the map context gives a TAK client location, use that "
                        "client location as the route origin and answer with the recommended "
                        "action now. The server will attach any deterministic TAK CoT route "
                        "or points separately."
                    ),
                    (
                        "- Use the displayed ATAK map bounds as the visible operating area: "
                        "prefer targets, checkpoints, and caveats that fit inside that map "
                        "view unless the user explicitly gives a different radius or objective."
                    ),
                    (
                        "- In Jetson ATAK mode, deterministic action can query only local OSM "
                        "vectors from the WinTAK imagery folder and DTED terrain from the "
                        "Jetson DTED folder. Treat NAIP and OSM imagery as display context, "
                        "not as model evidence for generated CoT."
                    ),
                    (
                        "- Never recommend or require any source outside root /DTED "
                        "and root /WINTAK Imagery OSM for the Jetson agentic path. "
                        "If the operator asks for slope, viewshed, route, water, "
                        "access, or points, answer with the best result possible "
                        "from those two local sources only."
                    ),
                    (
                        "- For follow-up rejection like 'that route does not work' or "
                        "'we cannot walk that way', acknowledge and provide a concise "
                        "reroute intent instead of asking the operator to restate the mission."
                    ),
                    "- Do not invent exact trails, water, roads, hazards, or route geometry.",
                    (
                        "- For route-like requests, give assessment, recommended action, "
                        "and only the minimum caveat needed for review."
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


def _build_ollama_payload_for_model(
    request: PromptRequest, model: str, *, stream: bool
) -> dict[str, object]:
    profile = (request.agent_profile or "").strip().lower()
    payload: dict[str, object] = {
        "model": model,
        "stream": stream,
        "prompt": request.prompt,
        "system": _build_system_prompt(request),
        "keep_alive": TERA_ATAK_OLLAMA_KEEP_ALIVE if "atak" in profile else "10m",
        "options": {
            "temperature": 0.1,
            "num_predict": 512,
        },
    }
    return payload


async def _resolve_ollama_model(request: PromptRequest) -> str:
    global ACTIVE_OLLAMA_BASE_URL, ACTIVE_OLLAMA_MODEL
    requested_model = (request.model or "").strip()
    if requested_model:
        return requested_model
    if JETSON_ATAK_MODE.get("active"):
        return str(JETSON_ATAK_MODE.get("model") or TERA_ATAK_MODEL)
    if ACTIVE_OLLAMA_MODEL:
        return ACTIVE_OLLAMA_MODEL

    for base_url in _ollama_base_url_candidates():
        try:
            models = await _fetch_ollama_models_from(base_url)
        except httpx.HTTPError:
            continue
        default_model = _select_ollama_default_model(models)
        ACTIVE_OLLAMA_BASE_URL = base_url
        ACTIVE_OLLAMA_MODEL = default_model
        return default_model

    return OLLAMA_MODEL


async def _build_ollama_payload(
    request: PromptRequest, *, stream: bool
) -> tuple[str, dict[str, object]]:
    model = await _resolve_ollama_model(request)
    return model, _build_ollama_payload_for_model(request, model, stream=stream)


def _request_llm_provider(request: PromptRequest) -> str:
    provider = (request.llm_provider or "auto").strip().lower()
    if provider in {"auto", "default", "primary"}:
        return "auto"
    if provider in {"claude", "anthropic"}:
        return "claude"
    if provider in {"ollama", "local", "llama"}:
        return "ollama"
    return "auto"


def _provider_sequence(request: PromptRequest) -> list[str]:
    provider = _request_llm_provider(request)
    if JETSON_ATAK_MODE.get("active") and provider in {"auto", "ollama"}:
        return ["ollama"]
    if provider == "ollama":
        return ["ollama"]
    return ["claude", "ollama"]


def _default_provider() -> str:
    return "auto" if os.getenv("ANTHROPIC_API_KEY", "").strip() else "ollama"


def _anthropic_api_key(request: PromptRequest) -> str:
    return (request.cloud_api_key or os.getenv("ANTHROPIC_API_KEY", "")).strip()


def _failure_message(provider: str, exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        detail = str(exc.detail)
    else:
        detail = str(exc)
    return f"{provider}: {detail}"


def _score_claude_model_for_default(model: str) -> int:
    normalized = model.lower()
    score = 0
    if model == CLAUDE_MODEL:
        score += 700
    if "sonnet-4" in normalized:
        score += 600
    elif "opus-4-1" in normalized:
        score += 450
    elif "opus-4" in normalized:
        score += 400
    elif "3-7-sonnet" in normalized:
        score += 300
    elif "3-5-sonnet" in normalized:
        score += 220
    elif "3-5-haiku" in normalized:
        score += 160
    elif "haiku" in normalized:
        score += 100
    if normalized.endswith("-latest"):
        score -= 50
    return score


def _normalize_claude_model(model: str | None) -> str:
    candidate = (model or CLAUDE_MODEL).strip()
    if not candidate:
        return CLAUDE_MODEL
    compact = re.sub(r"[\s_]+", "-", candidate.lower())
    compact = compact.replace("sonnet-4.6", "sonnet-4-6")
    compact = compact.replace("opus-4.7", "opus-4-7")
    return CLAUDE_MODEL_ALIASES.get(compact, CLAUDE_MODEL_ALIASES.get(candidate.lower(), candidate))


def _preferred_claude_model(request: PromptRequest) -> str:
    if request.cloud_model:
        return request.cloud_model
    if _request_llm_provider(request) == "claude" and request.model:
        return request.model
    return CLAUDE_MODEL


def _claude_model_candidates(preferred_model: str | None) -> list[str]:
    candidates = [
        _normalize_claude_model(preferred_model),
        *CLAUDE_MODEL_FALLBACKS,
    ]
    deduped: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return deduped


async def _fetch_anthropic_model_ids(api_key: str) -> list[str]:
    global ACTIVE_CLAUDE_MODELS
    if ACTIVE_CLAUDE_MODELS is not None:
        return ACTIVE_CLAUDE_MODELS

    timeout = httpx.Timeout(8.0, connect=3.0)
    headers = {
        "anthropic-version": ANTHROPIC_VERSION,
        "x-api-key": api_key,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(ANTHROPIC_MODELS_URL, headers=headers)
        response.raise_for_status()
    data = response.json()
    models = [
        str(model.get("id", "")).strip()
        for model in data.get("data", [])
        if isinstance(model, dict) and str(model.get("id", "")).strip()
    ]
    ACTIVE_CLAUDE_MODELS = models
    return models


async def _claude_model_candidates_for_key(
    preferred_model: str | None, api_key: str
) -> list[str]:
    candidates = _claude_model_candidates(preferred_model)
    try:
        discovered = await _fetch_anthropic_model_ids(api_key)
    except httpx.HTTPError as exc:
        log.warning("claude_model_discovery_unavailable", error=str(exc))
        discovered = []

    for model in sorted(
        discovered,
        key=lambda candidate: (_score_claude_model_for_default(candidate), candidate),
        reverse=True,
    ):
        if model and model not in candidates:
            candidates.append(model)
    return candidates


def _build_claude_payload_for_model(
    request: PromptRequest, model: str
) -> dict[str, object]:
    payload: dict[str, object] = {
        "model": model,
        "max_tokens": 900,
        "temperature": 0.1,
        "system": _build_system_prompt(request),
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": request.prompt,
                    }
                ],
            }
        ],
    }
    return payload


def _build_claude_payload(request: PromptRequest) -> tuple[str, dict[str, object]]:
    model = _normalize_claude_model(_preferred_claude_model(request))
    return model, _build_claude_payload_for_model(request, model)


def _extract_claude_response_text(data: dict[str, object]) -> str:
    content = data.get("content")
    if not isinstance(content, list):
        return ""

    chunks: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            chunks.append(str(block.get("text", "")))
    return "\n".join(chunk for chunk in chunks if chunk).strip()


async def _post_claude_message(request: PromptRequest) -> PromptResponse:
    api_key = _anthropic_api_key(request)
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=(
                "Claude API key required. Set ANTHROPIC_API_KEY on the Jetson "
                "or add a key for this browser session."
            ),
        )

    requested_model = _normalize_claude_model(_preferred_claude_model(request))
    timeout = httpx.Timeout(REQUEST_TIMEOUT_S, connect=10.0)
    headers = {
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
        "x-api-key": api_key,
    }
    model_errors: list[str] = []

    for model in await _claude_model_candidates_for_key(requested_model, api_key):
        payload = _build_claude_payload_for_model(request, model)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    ANTHROPIC_API_URL, headers=headers, json=payload
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500]
            log.error(
                "claude_http_error",
                status_code=exc.response.status_code,
                body=body,
                model=model,
            )
            if exc.response.status_code in {401, 403}:
                detail = (
                    f"Claude API rejected the key or account access for {model}. "
                    "Check the key in Model Provider or set ANTHROPIC_API_KEY on the server."
                )
                raise HTTPException(status_code=502, detail=detail) from exc
            if exc.response.status_code == 400 and "model" in body.lower():
                model_errors.append(f"{model}: {body}")
                continue
            detail = f"Claude API returned {exc.response.status_code}: {body}"
            raise HTTPException(status_code=502, detail=detail) from exc
        except httpx.HTTPError as exc:
            log.error("claude_connection_error", error=str(exc), model=model)
            raise HTTPException(
                status_code=502,
                detail=(
                    "Could not reach Claude API. Check internet connectivity, "
                    "proxy/firewall settings, and the Anthropic API endpoint."
                ),
            ) from exc

        text = _extract_claude_response_text(response.json())
        if not text:
            raise HTTPException(status_code=502, detail="Claude returned an empty response.")
        return PromptResponse(model=model, response=text, provider="claude")

    detail = (
        "Claude API rejected every configured model candidate. "
        + " | ".join(model_errors)
    )
    raise HTTPException(status_code=502, detail=detail)


async def _post_ollama_message(request: PromptRequest) -> PromptResponse:
    global ACTIVE_OLLAMA_BASE_URL, ACTIVE_OLLAMA_MODEL
    model, payload = await _build_ollama_payload(request, stream=False)

    timeout = httpx.Timeout(REQUEST_TIMEOUT_S, connect=10.0)

    errors: list[str] = []
    for base_url in _ollama_base_url_candidates():
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(f"{base_url}/api/generate", json=payload)
                response.raise_for_status()
            ACTIVE_OLLAMA_BASE_URL = base_url
            ACTIVE_OLLAMA_MODEL = model
            break
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500]
            errors.append(f"{base_url} returned {exc.response.status_code}: {body}")
            log.error(
                "ollama_http_error",
                status_code=exc.response.status_code,
                body=body,
                ollama_base_url=base_url,
                model=model,
            )
        except httpx.HTTPError as exc:
            errors.append(f"{base_url} unreachable: {exc}")
            log.error(
                "ollama_connection_error",
                error=str(exc),
                ollama_base_url=base_url,
                model=model,
            )
    else:
        raise HTTPException(
            status_code=502,
            detail="Could not reach a local Ollama host. " + " | ".join(errors),
        )

    data = response.json()
    text = str(data.get("response", "")).strip()
    if not text:
        raise HTTPException(status_code=502, detail="Ollama returned an empty response.")

    return PromptResponse(model=model, response=text, provider="ollama")


async def _post_prompt_with_fallback(request: PromptRequest) -> PromptResponse:
    fallbacks: list[str] = []
    for provider in _provider_sequence(request):
        try:
            if provider == "claude":
                result = await _post_claude_message(request)
            else:
                result = await _post_ollama_message(request)
        except HTTPException as exc:
            fallbacks.append(_failure_message(provider, exc))
            continue
        result.fallbacks = fallbacks
        return result

    detail = " | ".join(fallbacks) if fallbacks else "No model providers were configured."
    raise HTTPException(status_code=502, detail=f"All model providers failed. {detail}")


def _sse_event(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _ollama_base_url_candidates() -> list[str]:
    candidates = [
        url.strip().rstrip("/")
        for url in (
            ACTIVE_OLLAMA_BASE_URL,
            OLLAMA_BASE_URL,
            "http://127.0.0.1:11434",
            "http://localhost:11434",
            "http://host.docker.internal:11434",
        )
        if url and url.strip()
    ]
    deduped: list[str] = []
    for url in candidates:
        if url not in deduped:
            deduped.append(url)
    return deduped


async def _fetch_ollama_models_from(base_url: str) -> list[str]:
    timeout = httpx.Timeout(6.0, connect=2.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(f"{base_url}/api/tags")
        response.raise_for_status()
    data = response.json()
    return [
        str(model.get("name", "")).strip()
        for model in data.get("models", [])
        if str(model.get("name", "")).strip()
    ]


def _start_local_ollama_runtime() -> str | None:
    attempts: list[str] = []
    if shutil.which("systemctl"):
        commands = (
            ["systemctl", "--user", "start", "ollama"],
            ["sudo", "-n", "systemctl", "start", "ollama"],
            ["systemctl", "start", "ollama"],
        )
        for command in commands:
            try:
                completed = subprocess.run(
                    command,
                    timeout=12,
                    check=False,
                    capture_output=True,
                    text=True,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                attempts.append(f"{' '.join(command)} failed: {exc}")
                continue
            if completed.returncode == 0:
                return f"started Ollama via {' '.join(command)}"
            stderr = (completed.stderr or completed.stdout or "").strip()
            if stderr:
                attempts.append(f"{' '.join(command)}: {stderr[:180]}")

    ollama_bin = shutil.which("ollama")
    if ollama_bin:
        log_path = _runtime_dir() / "ollama-serve.log"
        env = os.environ.copy()
        env.setdefault("OLLAMA_HOST", "0.0.0.0:11434")
        with log_path.open("ab") as output:
            process = subprocess.Popen(
                [ollama_bin, "serve"],
                stdout=output,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=str(BASE_DIR.parent),
            )
        return f"started Ollama serve with pid {process.pid}"

    if attempts:
        return "Ollama start attempted but did not succeed: " + " | ".join(attempts[:2])
    return "Ollama executable/systemd service not found in this runtime."


async def _wait_for_ollama(base_url: str, *, attempts: int = 20) -> list[str] | None:
    for _ in range(attempts):
        try:
            return await _fetch_ollama_models_from(base_url)
        except httpx.HTTPError:
            await asyncio.sleep(0.5)
    return None


async def _pull_ollama_model(base_url: str, model: str) -> str:
    timeout = httpx.Timeout(900.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{base_url}/api/pull",
            json={"name": model, "stream": False},
        )
        response.raise_for_status()
    return f"Pulled Ollama model {model}."


async def _warm_ollama_atak_model(base_url: str, model: str, agent_profile: str) -> str:
    warm_request = PromptRequest(
        prompt=f'Readiness check. Reply exactly: "{TERA_ATAK_READY_MESSAGE}"',
        model=model,
        llm_provider="ollama",
        agent_profile=agent_profile,
    )
    payload = _build_ollama_payload_for_model(warm_request, model, stream=False)
    payload["keep_alive"] = TERA_ATAK_OLLAMA_KEEP_ALIVE
    options = dict(payload.get("options") or {})
    options["num_predict"] = 24
    payload["options"] = options

    timeout = httpx.Timeout(TERA_ATAK_WARMUP_TIMEOUT_S, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{base_url}/api/generate", json=payload)
        response.raise_for_status()
    warm_text = str(response.json().get("response", "")).strip()
    if not warm_text:
        raise RuntimeError(f"Ollama warmup returned an empty response for {model}.")
    return f"Warmed {model} with TERA ATAK profile; keep_alive={TERA_ATAK_OLLAMA_KEEP_ALIVE}."


async def _prepare_ollama_for_atak(model: str, agent_profile: str) -> dict[str, object]:
    details: list[str] = []
    selected_base_url: str | None = None
    models: list[str] | None = None

    for base_url in _ollama_base_url_candidates():
        try:
            models = await _fetch_ollama_models_from(base_url)
            selected_base_url = base_url
            details.append(f"Ollama reachable at {base_url}.")
            break
        except httpx.HTTPError as exc:
            details.append(f"{base_url} unavailable: {exc}")

    if selected_base_url is None:
        start_detail = _start_local_ollama_runtime()
        if start_detail:
            details.append(start_detail)
        for base_url in _ollama_base_url_candidates():
            models = await _wait_for_ollama(base_url)
            if models is not None:
                selected_base_url = base_url
                details.append(f"Ollama became reachable at {base_url}.")
                break

    if selected_base_url is None or models is None:
        return {
            "ready": False,
            "base_url": None,
            "detail": " ".join(details[-4:]) or "Ollama is not reachable.",
        }

    if not _ollama_model_is_available(models, model):
        try:
            details.append(await _pull_ollama_model(selected_base_url, model))
            models = await _fetch_ollama_models_from(selected_base_url)
        except httpx.HTTPError as exc:
            details.append(f"Could not pull {model}: {exc}")
            return {
                "ready": False,
                "base_url": selected_base_url,
                "detail": " ".join(details[-4:]),
            }

    if not _ollama_model_is_available(models, model):
        details.append(f"{model} still not listed by Ollama after pull.")
        return {
            "ready": False,
            "base_url": selected_base_url,
            "detail": " ".join(details[-4:]),
        }

    try:
        details.append(await _warm_ollama_atak_model(selected_base_url, model, agent_profile))
    except (RuntimeError, httpx.HTTPError) as exc:
        details.append(f"Ollama warmup failed for {model}: {exc}")
        return {
            "ready": False,
            "base_url": selected_base_url,
            "detail": " ".join(details[-4:]),
        }

    return {
        "ready": True,
        "base_url": selected_base_url,
        "detail": " ".join(details[-4:]),
    }


def _score_ollama_model_for_default(model: str, configured_model: str) -> int:
    normalized = model.lower()
    score = 0
    if model == configured_model:
        score += 500
    if "gemma" in normalized:
        score += 300
    if "gemma4" in normalized or "gemma-4" in normalized:
        score += 80
    elif "gemma3" in normalized or "gemma-3" in normalized:
        score += 60
    elif "gemma2" in normalized or "gemma-2" in normalized:
        score += 20
    if "e4b" in normalized:
        score += 50
    if "/gemma" in normalized or normalized.startswith("hf.co/"):
        score -= 20
    return score


def _select_ollama_default_model(models: list[str]) -> str:
    if not models:
        return OLLAMA_MODEL
    if OLLAMA_MODEL in models:
        return OLLAMA_MODEL
    return max(
        models,
        key=lambda model: (_score_ollama_model_for_default(model, OLLAMA_MODEL), -len(model)),
    )


def _clean_location_query(query: str) -> str:
    cleaned = re.sub(r"\s+", " ", query.strip())
    previous = None
    while cleaned and cleaned != previous:
        previous = cleaned
        cleaned = LOCATION_INTENT_PREFIX_RE.sub("", cleaned).strip()
    return cleaned


def _coordinate_location_suggestion(query: str) -> LocationSuggestion | None:
    for pattern in GOOGLE_MAPS_COORD_PATTERNS:
        match = pattern.search(query)
        if not match:
            continue
        lat = _safe_float(match.group("lat"), default=float("nan"))
        lon = _safe_float(match.group("lon"), default=float("nan"))
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return LocationSuggestion(
                name=f"Coordinates {lat:.5f}, {lon:.5f}",
                detail="Parsed from Google Maps link or coordinate query.",
                lat=lat,
                lon=lon,
                height_m=12000,
                source="coordinate-query",
                score=1000,
            )

    numbers = re.findall(r"[+-]?\d+(?:\.\d+)?", query)
    if len(numbers) < 2 or "http" in query.lower():
        return None
    lat = _safe_float(numbers[0], default=float("nan"))
    lon = _safe_float(numbers[1], default=float("nan"))
    if abs(lat) > 90 and abs(lon) <= 90:
        lat, lon = lon, lat
    upper = query.upper()
    if re.search(r"\d(?:\.\d+)?\s*S\b", upper):
        lat = -abs(lat)
    elif re.search(r"\d(?:\.\d+)?\s*N\b", upper):
        lat = abs(lat)
    if re.search(r"\d(?:\.\d+)?\s*W\b", upper) or " W" in upper:
        lon = -abs(lon)
    elif re.search(r"\d(?:\.\d+)?\s*E\b", upper) or " E" in upper:
        lon = abs(lon)
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return LocationSuggestion(
            name=f"Coordinates {lat:.5f}, {lon:.5f}",
            detail="Parsed decimal latitude/longitude.",
            lat=lat,
            lon=lon,
            height_m=12000,
            source="coordinate-query",
            score=1000,
        )
    return None


def _distance_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    radius_km = 6371.0088
    lat1 = math.radians(lat_a)
    lat2 = math.radians(lat_b)
    delta_lat = math.radians(lat_b - lat_a)
    delta_lon = math.radians(lon_b - lon_a)
    sin_lat = math.sin(delta_lat / 2)
    sin_lon = math.sin(delta_lon / 2)
    a = sin_lat * sin_lat + math.cos(lat1) * math.cos(lat2) * sin_lon * sin_lon
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _safe_float(value: object, default: float = 0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isfinite(number):
        return number
    return default


def _score_local_location(query: str, item: dict[str, object]) -> int:
    cleaned_query = _clean_location_query(query)
    query_tokens = _tokens_for_match(cleaned_query)
    if not query_tokens:
        return 0
    haystack = " ".join(
        [
            str(item.get("name", "")),
            str(item.get("detail", "")),
            " ".join(str(alias) for alias in item.get("aliases", ())),
        ]
    )
    haystack_tokens = _tokens_for_match(haystack)
    score = 0
    for query_token in query_tokens:
        if any(_token_matches(token, query_token) for token in haystack_tokens):
            score += 20
    normalized_query = _normalize_for_match(cleaned_query)
    normalized_name = _normalize_for_match(str(item.get("name", "")))
    normalized_aliases = [
        _normalize_for_match(str(alias)) for alias in item.get("aliases", ())
    ]
    if normalized_name.startswith(normalized_query):
        score += 60
    elif normalized_query in normalized_name:
        score += 40
    for alias in normalized_aliases:
        if alias == normalized_query:
            score += 130
        elif alias.startswith(normalized_query):
            score += 65
        elif normalized_query in alias:
            score += 45
    return score


def _score_online_location(
    query: str,
    suggestion: LocationSuggestion,
    *,
    center_lat: float | None = None,
    center_lon: float | None = None,
    importance: float = 0,
    category: str = "",
    place_type: str = "",
) -> float:
    item = {
        "name": suggestion.name,
        "detail": suggestion.detail,
        "aliases": (),
    }
    score = float(_score_local_location(query, item))
    score += max(0, min(1, importance)) * 65

    category_type = f"{category}/{place_type}".lower()
    if any(token in category_type for token in ("city", "town", "village", "hamlet")):
        score += 8
    if any(token in category_type for token in ("national_park", "protected_area", "park")):
        score += 24
    if any(token in category_type for token in ("mountain", "peak", "natural", "water")):
        score += 18
    if "administrative" in category_type:
        score -= 8

    if center_lat is not None and center_lon is not None:
        distance = _distance_km(center_lat, center_lon, suggestion.lat, suggestion.lon)
        score += max(0, 10 - min(distance / 500, 10))

    return round(score, 3)


def _google_location_bias(
    *,
    center_lat: float | None = None,
    center_lon: float | None = None,
    west: float | None = None,
    south: float | None = None,
    east: float | None = None,
    north: float | None = None,
) -> dict[str, object] | None:
    if None not in (west, south, east, north):
        return {
            "rectangle": {
                "low": {
                    "latitude": min(float(south), float(north)),
                    "longitude": min(float(west), float(east)),
                },
                "high": {
                    "latitude": max(float(south), float(north)),
                    "longitude": max(float(west), float(east)),
                },
            }
        }
    if center_lat is not None and center_lon is not None:
        return {
            "circle": {
                "center": {
                    "latitude": center_lat,
                    "longitude": center_lon,
                },
                "radius": 50000.0,
            }
        }
    return None


def _google_text_value(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("text") or "").strip()
    return str(value or "").strip()


def _google_prediction_text(prediction: dict[str, object]) -> str:
    direct_text = _google_text_value(prediction.get("text"))
    if direct_text:
        return direct_text
    structured = prediction.get("structuredFormat")
    if not isinstance(structured, dict):
        return ""
    main_text = _google_text_value(structured.get("mainText"))
    secondary_text = _google_text_value(structured.get("secondaryText"))
    return ", ".join(part for part in (main_text, secondary_text) if part)


def _google_place_details_url(place_name: str) -> str:
    place_path = place_name.strip().strip("/")
    if not place_path:
        return ""
    base_url = GOOGLE_PLACE_DETAILS_URL_BASE.rstrip("/")
    if place_path.startswith("places/"):
        return f"{base_url}/{place_path}"
    return f"{base_url}/places/{place_path}"


async def _google_place_details_suggestion(
    query: str,
    place_name: str,
    *,
    client: httpx.AsyncClient,
    prediction_text: str = "",
    rank: int = 0,
    center_lat: float | None = None,
    center_lon: float | None = None,
) -> tuple[LocationSuggestion | None, str | None]:
    url = _google_place_details_url(place_name)
    if not url:
        return None, None

    try:
        response = await client.get(
            url,
            headers={
                "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
                "X-Goog-FieldMask": (
                    "id,displayName,formattedAddress,location,"
                    "googleMapsUri,primaryType,types"
                ),
            },
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:300]
        return None, (
            f"Google Maps Place Details returned {exc.response.status_code}: {body}"
        )
    except httpx.HTTPError as exc:
        return None, f"Google Maps Place Details unavailable: {exc}"

    place = response.json()
    if not isinstance(place, dict):
        return None, "Google Maps Place Details returned an unexpected payload."
    location = place.get("location")
    if not isinstance(location, dict):
        return None, None
    place_lat = _safe_float(location.get("latitude"), default=float("nan"))
    place_lon = _safe_float(location.get("longitude"), default=float("nan"))
    if not (-90 <= place_lat <= 90 and -180 <= place_lon <= 180):
        return None, None

    display_name = place.get("displayName")
    name = _google_text_value(display_name) or prediction_text or query
    formatted_address = str(place.get("formattedAddress") or "").strip()
    google_maps_uri = str(place.get("googleMapsUri") or "").strip()
    primary_type = str(place.get("primaryType") or "place").strip()
    detail_parts = [
        part for part in [primary_type, formatted_address, google_maps_uri] if part
    ]
    suggestion = LocationSuggestion(
        name=name,
        detail="Google Maps - " + " | ".join(detail_parts),
        lat=place_lat,
        lon=place_lon,
        height_m=12000,
        source="google-places",
        score=900 - (rank * 12),
    )
    suggestion.score += _score_online_location(
        query,
        suggestion,
        center_lat=center_lat,
        center_lon=center_lon,
        category="google",
        place_type=primary_type,
    )
    return suggestion, None


async def _google_places_location_suggestions(
    query: str,
    *,
    center_lat: float | None = None,
    center_lon: float | None = None,
    west: float | None = None,
    south: float | None = None,
    east: float | None = None,
    north: float | None = None,
    limit: int = 8,
    client: httpx.AsyncClient | None = None,
) -> tuple[list[LocationSuggestion], str | None]:
    if not GOOGLE_MAPS_API_KEY:
        return [], "Google Maps Places search disabled; set GOOGLE_MAPS_API_KEY."

    payload: dict[str, object] = {
        "textQuery": query,
        "pageSize": max(1, min(limit, 20)),
        "languageCode": "en",
    }
    location_bias = _google_location_bias(
        center_lat=center_lat,
        center_lon=center_lon,
        west=west,
        south=south,
        east=east,
        north=north,
    )
    if location_bias:
        payload["locationBias"] = location_bias

    try:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,"
                "places.location,places.googleMapsUri,places.primaryType"
            ),
        }
        if client is None:
            timeout = httpx.Timeout(LOCATION_SEARCH_TIMEOUT_S, connect=2.0)
            async with httpx.AsyncClient(timeout=timeout) as owned_client:
                response = await owned_client.post(
                    GOOGLE_PLACES_TEXT_SEARCH_URL,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
        else:
            response = await client.post(
                GOOGLE_PLACES_TEXT_SEARCH_URL,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:300]
        return [], f"Google Maps Places search returned {exc.response.status_code}: {body}"
    except httpx.HTTPError as exc:
        return [], f"Google Maps Places search unavailable: {exc}"

    suggestions: list[LocationSuggestion] = []
    for index, place in enumerate(response.json().get("places", [])):
        if not isinstance(place, dict):
            continue
        location = place.get("location")
        if not isinstance(location, dict):
            continue
        place_lat = _safe_float(location.get("latitude"), default=float("nan"))
        place_lon = _safe_float(location.get("longitude"), default=float("nan"))
        if not (-90 <= place_lat <= 90 and -180 <= place_lon <= 180):
            continue
        display_name = place.get("displayName")
        if isinstance(display_name, dict):
            name = str(display_name.get("text") or "").strip()
        else:
            name = ""
        formatted_address = str(place.get("formattedAddress") or "").strip()
        google_maps_uri = str(place.get("googleMapsUri") or "").strip()
        primary_type = str(place.get("primaryType") or "place").strip()
        detail_parts = [
            part for part in [primary_type, formatted_address, google_maps_uri] if part
        ]
        suggestion = LocationSuggestion(
            name=name or formatted_address or query,
            detail="Google Maps - " + " | ".join(detail_parts),
            lat=place_lat,
            lon=place_lon,
            height_m=12000,
            source="google-places",
            score=650 - (index * 10),
        )
        suggestion.score += _score_online_location(
            query,
            suggestion,
            center_lat=center_lat,
            center_lon=center_lon,
            category="google",
            place_type=primary_type,
        )
        suggestions.append(suggestion)

    return suggestions, None


async def _google_places_autocomplete_suggestions(
    query: str,
    *,
    center_lat: float | None = None,
    center_lon: float | None = None,
    west: float | None = None,
    south: float | None = None,
    east: float | None = None,
    north: float | None = None,
) -> tuple[list[LocationSuggestion], str | None]:
    if not GOOGLE_MAPS_API_KEY:
        return [], "Google Maps Places autocomplete disabled; set GOOGLE_MAPS_API_KEY."

    payload: dict[str, object] = {
        "input": query,
        "includeQueryPredictions": True,
        "languageCode": "en",
    }
    location_bias = _google_location_bias(
        center_lat=center_lat,
        center_lon=center_lon,
        west=west,
        south=south,
        east=east,
        north=north,
    )
    if location_bias:
        payload["locationBias"] = location_bias

    suggestions: list[LocationSuggestion] = []
    detail_parts: list[str] = []
    prediction_texts: list[str] = []
    timeout = httpx.Timeout(LOCATION_SEARCH_TIMEOUT_S, connect=2.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                GOOGLE_PLACES_AUTOCOMPLETE_URL,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
                    "X-Goog-FieldMask": (
                        "suggestions.placePrediction.place,"
                        "suggestions.placePrediction.placeId,"
                        "suggestions.placePrediction.text.text,"
                        "suggestions.placePrediction.structuredFormat.mainText.text,"
                        "suggestions.placePrediction.structuredFormat.secondaryText.text,"
                        "suggestions.queryPrediction.text.text"
                    ),
                },
            )
            response.raise_for_status()
            for index, raw_suggestion in enumerate(
                response.json().get("suggestions", [])
            ):
                if not isinstance(raw_suggestion, dict):
                    continue
                place_prediction = raw_suggestion.get("placePrediction")
                if isinstance(place_prediction, dict):
                    prediction_text = _google_prediction_text(place_prediction)
                    place_name = str(
                        place_prediction.get("place")
                        or place_prediction.get("placeId")
                        or ""
                    ).strip()
                    if place_name:
                        place_suggestion, detail = await _google_place_details_suggestion(
                            query,
                            place_name,
                            client=client,
                            prediction_text=prediction_text,
                            rank=index,
                            center_lat=center_lat,
                            center_lon=center_lon,
                        )
                        if place_suggestion:
                            suggestions.append(place_suggestion)
                            continue
                        if detail:
                            detail_parts.append(detail)
                    if prediction_text:
                        prediction_texts.append(prediction_text)
                    continue

                query_prediction = raw_suggestion.get("queryPrediction")
                if isinstance(query_prediction, dict):
                    query_text = _google_prediction_text(query_prediction)
                    if query_text:
                        prediction_texts.append(query_text)

            for prediction_text in prediction_texts[:3]:
                if len(suggestions) >= 8:
                    break
                text_suggestions, text_detail = (
                    await _google_places_location_suggestions(
                        prediction_text,
                        center_lat=center_lat,
                        center_lon=center_lon,
                        west=west,
                        south=south,
                        east=east,
                        north=north,
                        limit=2,
                        client=client,
                    )
                )
                if text_suggestions:
                    suggestions.extend(text_suggestions)
                elif text_detail:
                    detail_parts.append(text_detail)
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:300]
        return [], (
            f"Google Maps Places autocomplete returned {exc.response.status_code}: {body}"
        )
    except httpx.HTTPError as exc:
        return [], f"Google Maps Places autocomplete unavailable: {exc}"

    return suggestions, " | ".join(detail_parts[:3]) if detail_parts else None


def _local_location_suggestions(query: str) -> list[LocationSuggestion]:
    scored = [
        (_score_local_location(query, item), item)
        for item in LOCAL_LOCATION_GAZETTEER
    ]
    suggestions: list[LocationSuggestion] = []
    for score, item in sorted(scored, key=lambda pair: pair[0], reverse=True):
        if score <= 0:
            continue
        suggestions.append(
            LocationSuggestion(
                name=str(item["name"]),
                detail=str(item.get("detail", "")),
                lat=float(item["lat"]),
                lon=float(item["lon"]),
                height_m=float(item.get("height_m", 12000)),
                source="local-gazetteer",
                score=float(score + 120),
            )
        )
    return suggestions[:8]


@app.get("/")
async def serve_index() -> FileResponse:
    return FileResponse(INDEX_FILE)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "ollama_base_url": OLLAMA_BASE_URL}


@app.get("/api/jetson/atak-agent/status", response_model=JetsonAtakModeResponse)
async def jetson_atak_agent_status() -> JetsonAtakModeResponse:
    return _jetson_atak_response()


@app.get("/api/jetson/atak-agent/mirror", response_model=JetsonAtakModeResponse)
async def jetson_atak_agent_mirror() -> JetsonAtakModeResponse:
    return _jetson_atak_response()


@app.post("/api/jetson/atak-agent/activate", response_model=JetsonAtakModeResponse)
async def activate_jetson_atak_agent(
    activation: JetsonAtakActivateRequest,
    http_request: Request,
) -> JetsonAtakModeResponse:
    global ACTIVE_OLLAMA_BASE_URL, ACTIVE_OLLAMA_MODEL
    model = _normalize_ollama_model_name(activation.model)
    agent_profile = (
        activation.agent_profile or TERA_ATAK_AGENT_PROFILE
    ).strip() or TERA_ATAK_AGENT_PROFILE
    atak_device_url = (activation.atak_device_url or TERA_ATAK_DEVICE_URL).strip() or None
    jetson_ip, plugin_endpoint = _plugin_endpoint_for_request(http_request)

    ACTIVE_OLLAMA_MODEL = model
    JETSON_ATAK_MODE.update(
        {
            "active": True,
            "status": "activating",
            "detail": "Starting and warming local Ollama for TERA ATAK agent mode.",
            "model": model,
            "provider": "ollama",
            "agent_profile": agent_profile,
            "atak_device_url": atak_device_url,
            "ollama_base_url": None,
            "ollama_ready": False,
            "jetson_ip": jetson_ip,
            "plugin_endpoint": plugin_endpoint,
            "activated_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    ollama_ready = await _prepare_ollama_for_atak(model, agent_profile)
    ACTIVE_OLLAMA_BASE_URL = (
        str(ollama_ready["base_url"]) if ollama_ready.get("base_url") else ACTIVE_OLLAMA_BASE_URL
    )

    command_detail = _start_jetson_atak_command(
        model=model,
        agent_profile=agent_profile,
        atak_device_url=atak_device_url,
    )
    details = [str(ollama_ready.get("detail") or "Ollama readiness check complete.")]
    if command_detail:
        details.append(command_detail)
    else:
        details.append(
            "No TERA_ATAK_AGENT_COMMAND configured; this server will handle ATAK-profile "
            "prompt calls directly."
        )
    if plugin_endpoint:
        details.append(f"Samsung ATAK plugin endpoint: {plugin_endpoint}.")
    if atak_device_url:
        details.append(f"ATAK device target configured: {atak_device_url}.")
    else:
        details.append("Waiting for the ATAK plugin to POST prompts to this Jetson.")

    detail = " ".join(details)
    JETSON_ATAK_MODE.update(
        {
            "status": "active" if ollama_ready.get("ready") else "error",
            "detail": detail,
            "ollama_base_url": ollama_ready.get("base_url"),
            "ollama_ready": bool(ollama_ready.get("ready")),
        }
    )
    if ollama_ready.get("ready"):
        _append_atak_mirror_event(
            source="jetson",
            role="assistant",
            text=TERA_ATAK_READY_MESSAGE,
            model=model,
            provider="ollama",
            direction="ready",
        )
    else:
        _append_atak_mirror_event(
            source="jetson",
            role="system",
            text=(
                f"Local TERA ATAK agent not ready on Ollama {model}. "
                "Hold traffic and retry ATAK Local activation."
            ),
            model=model,
            provider="ollama",
            direction="mode-switch",
        )
    return _jetson_atak_response(detail)


@app.get("/api/config", response_model=RuntimeConfigResponse)
async def runtime_config() -> RuntimeConfigResponse:
    return RuntimeConfigResponse(
        cesium_ion_token=CESIUM_ION_TOKEN,
        esri_token_configured=ESRI_TOKEN_CONFIGURED,
        default_model=OLLAMA_MODEL,
        default_provider=_default_provider(),
        claude_default_model=_normalize_claude_model(CLAUDE_MODEL),
        anthropic_api_key_configured=bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),
        default_lat=DEFAULT_LAT,
        default_lon=DEFAULT_LON,
        default_height_m=DEFAULT_HEIGHT_M,
    )


@app.get("/api/models", response_model=ModelsResponse)
async def list_ollama_models() -> ModelsResponse:
    global ACTIVE_OLLAMA_BASE_URL, ACTIVE_OLLAMA_MODEL
    errors: list[str] = []
    for base_url in _ollama_base_url_candidates():
        try:
            models = await _fetch_ollama_models_from(base_url)
            default_model = _select_ollama_default_model(models)
            ACTIVE_OLLAMA_BASE_URL = base_url
            ACTIVE_OLLAMA_MODEL = default_model
            return ModelsResponse(
                default_model=default_model,
                models=models,
                online=True,
                base_url=base_url,
                detail=(
                    f"Auto-detected installed Gemma model {default_model}."
                    if default_model != OLLAMA_MODEL
                    else None
                ),
            )
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300]
            errors.append(f"{base_url} returned {exc.response.status_code}: {body}")
        except httpx.HTTPError as exc:
            errors.append(f"{base_url} unreachable: {exc}")

    detail = " | ".join(errors) if errors else "No Ollama base URLs were configured."
    log.warning("ollama_models_unavailable", detail=detail)
    return ModelsResponse(
        default_model=OLLAMA_MODEL,
        models=[],
        online=False,
        base_url=_ollama_base_url_candidates()[0],
        detail=f"Local model unavailable. Deterministic source planner is active. {detail}",
    )


@app.get("/api/location-search", response_model=LocationSearchResponse)
async def search_locations(
    q: str = Query(min_length=1, max_length=200),
    lat: float | None = None,
    lon: float | None = None,
    west: float | None = None,
    south: float | None = None,
    east: float | None = None,
    north: float | None = None,
) -> LocationSearchResponse:
    query = _clean_location_query(q)
    if not query:
        return LocationSearchResponse(
            query=query,
            suggestions=[],
            online=False,
            detail="Enter a mission location, coordinates, or a Google Maps link.",
        )

    suggestions = _local_location_suggestions(query)
    coordinate_suggestion = _coordinate_location_suggestion(query)
    if coordinate_suggestion:
        suggestions.insert(0, coordinate_suggestion)
    online = False
    detail_parts: list[str] = []

    if GOOGLE_MAPS_API_KEY:
        autocomplete_suggestions, autocomplete_detail = (
            await _google_places_autocomplete_suggestions(
                query,
                center_lat=lat,
                center_lon=lon,
                west=west,
                south=south,
                east=east,
                north=north,
            )
        )
        if autocomplete_suggestions:
            online = True
            suggestions.extend(autocomplete_suggestions)
        elif autocomplete_detail:
            detail_parts.append(autocomplete_detail)

        text_search_suggestions, text_search_detail = await _google_places_location_suggestions(
            query,
            center_lat=lat,
            center_lon=lon,
            west=west,
            south=south,
            east=east,
            north=north,
            limit=8,
        )
        if text_search_suggestions:
            online = True
            suggestions.extend(text_search_suggestions)
        elif text_search_detail:
            detail_parts.append(text_search_detail)
    else:
        detail_parts.append(
            "Google Maps Places disabled; set GOOGLE_MAPS_API_KEY for Google-grade autocomplete."
        )

    should_query_nominatim = len(query) >= 2 or not query.isdigit()
    if should_query_nominatim:
        try:
            params: dict[str, object] = {
                "q": query,
                "format": "jsonv2",
                "limit": 10,
                "addressdetails": 1,
                "extratags": 1,
                "namedetails": 1,
                "dedupe": 1,
            }
            if len(query) <= 2 and None not in (west, south, east, north):
                params["viewbox"] = f"{west},{north},{east},{south}"

            timeout = httpx.Timeout(LOCATION_SEARCH_TIMEOUT_S, connect=2.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    LOCATION_SEARCH_URL,
                    params=params,
                    headers={
                        "Accept-Language": "en",
                        "User-Agent": "TERA Source Planner local web app; optional online geocode",
                    },
                )
                response.raise_for_status()
            online = True
            for item in response.json():
                item_lat = item.get("lat")
                item_lon = item.get("lon")
                if item_lat is None or item_lon is None:
                    continue
                display_name = str(item.get("display_name") or item.get("name") or query)
                category = str(item.get("category") or "online geocoder")
                place_type = str(item.get("type") or "place")
                suggestion = LocationSuggestion(
                    name=display_name.split(",")[0],
                    detail=f"{category}/{place_type} - {display_name}",
                    lat=float(item_lat),
                    lon=float(item_lon),
                    height_m=12000,
                    source="online-geocoder",
                )
                suggestion.score = _score_online_location(
                    query,
                    suggestion,
                    center_lat=lat if lat is not None else None,
                    center_lon=lon if lon is not None else None,
                    importance=_safe_float(item.get("importance")),
                    category=category,
                    place_type=place_type,
                )
                suggestions.append(suggestion)
        except (httpx.HTTPError, ValueError) as exc:
            detail_parts.append(f"Nominatim location lookup unavailable: {exc}")
    else:
        detail_parts.append(
            "Numeric location searches need more context unless Google Maps Places is configured."
        )

    deduped: list[LocationSuggestion] = []
    seen: set[tuple[int, int, str]] = set()
    for suggestion in suggestions:
        key = (
            round(suggestion.lat * 1000),
            round(suggestion.lon * 1000),
            suggestion.name.lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(suggestion)
    deduped.sort(key=lambda suggestion: suggestion.score, reverse=True)

    return LocationSearchResponse(
        query=query,
        suggestions=deduped[:8],
        online=online,
        detail=" | ".join(detail_parts) if detail_parts else None,
    )


@app.get("/api/data-sources", response_model=SourceCatalogResponse)
async def list_data_sources() -> SourceCatalogResponse:
    return SourceCatalogResponse(
        primary_streams=PRIMARY_STREAM_SOURCE_IDS,
        sources=SOURCE_CATALOG,
    )


@app.post("/api/source-package/recommend", response_model=SourceRecommendationResponse)
async def recommend_source_package(
    request: SourceRecommendationRequest,
) -> SourceRecommendationResponse:
    return _infer_source_recommendation(request.mission_text, request.map_context)


@app.get("/api/storage", response_model=StorageInfoResponse)
async def get_storage_info() -> StorageInfoResponse:
    return _storage_info()


def _build_package_manifest(
    *,
    package_id: str,
    package_name: str,
    request: DownloadPlanRequest,
    sources: list[SourceOption],
) -> dict[str, object]:
    selected_ids = [source.id for source in sources]
    bounds = _manifest_bounds_from_context(request.map_context)
    download_operations = _build_source_download_operations(
        package_id=package_id,
        sources=sources,
        bounds=bounds,
    )
    jetson_query_contracts = _build_jetson_query_contracts(
        package_id=package_id,
        sources=sources,
    )
    return {
        "package_id": package_id,
        "package_name": package_name,
        "mission_focus": request.mission_focus,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "aoi": _format_manifest_bounds(request.map_context),
        "selected_source_ids": selected_ids,
        "sources": [
            {
                "id": source.id,
                "name": source.name,
                "provider": source.provider,
                "category": source.category,
                "purpose": source.purpose,
                "stream_status": source.stream_status,
                "download_status": source.download_status,
                "stream_layer": source.stream_layer,
                "analysis_role": source.analysis_role,
                "derived_layers": source.derived_layers,
                "source_url": source.source_url,
                "license_or_terms": source.license_or_terms,
                "download_methods": [
                    method.model_dump(exclude_none=True) for method in source.download_methods
                ],
                "jetson_query_formats": [
                    query_format.model_dump(exclude_none=True)
                    for query_format in source.jetson_query_formats
                ],
                "notes": source.notes,
            }
            for source in sources
        ],
        "download_operations": download_operations,
        "jetson_query_contracts": jetson_query_contracts,
        "deterministic_algorithms": algorithm_catalog(),
        "server_ingest_plan": {
            "store_raw_sources": [
                source.id
                for source in sources
                if source.download_status
                in {
                    "download-required",
                    "cache-feed",
                    "export-tiles-with-account",
                }
                or source.download_methods
            ],
            "cache_display_tiles": [
                source.id
                for source in sources
                if source.download_status in {"cache-tiles", "export-tiles-with-account"}
                or any(method.id.endswith("_tile_cache") for method in source.download_methods)
                or source.id == "cesium_ion_archive"
            ],
            "generate_derived_layers": sorted(
                {
                    derived_layer
                    for source in sources
                    for derived_layer in source.derived_layers
                }
            ),
            "load_vector_indexes": [
                source.id
                for source in sources
                if source.category in {"vector", "hydrography", "boundaries-access", "communications"}
            ],
            "load_raster_indexes": [
                source.id
                for source in sources
                if source.category
                in {
                    "terrain",
                    "land-cover",
                    "imagery-analysis",
                    "hazards",
                    "terrain-display",
                    "imagery-terrain-archive",
                }
            ],
            "jetson_queryable_artifacts": [
                contract["local_path"] for contract in jetson_query_contracts
            ],
        },
        "offline_metadata_required": [
            "source_dataset_id",
            "source_version_or_acquired_at",
            "license_or_usage_constraint",
            "aoi_bbox",
            "native_resolution",
            "processing_steps",
            "sha256",
        ],
    }


def _download_plan_warnings(
    request: DownloadPlanRequest, sources: list[SourceOption]
) -> list[str]:
    warnings: list[str] = []
    known_ids = set(SOURCE_BY_ID)
    unknown_ids = [source_id for source_id in request.source_ids if source_id not in known_ids]
    if unknown_ids:
        warnings.append(f"Unknown source ids ignored: {', '.join(unknown_ids)}")
    if not sources:
        warnings.append("No sources selected; manifest has no server ingest work.")
    if request.map_context is None or not (
        request.map_context.location_confirmed or request.map_context.selected_area
    ):
        warnings.append(
            "Mission map focus is not confirmed; use location search, KML/KMZ import, "
            "or AO drawing before treating bounds as final."
        )
    if request.map_context is None or (
        request.map_context.selected_area is None and request.map_context.view_bounds is None
    ):
        warnings.append("No AO bounds were provided; downloads must be clipped before ingest.")
    if not any(source.id == "osm_extract" for source in sources):
        warnings.append("OSM extract is not selected, so server-side routable graph work is blocked.")
    elif not _env_path("TERA_WINTAK_IMAGERY_DIR"):
        warnings.append(
            "TERA_WINTAK_IMAGERY_DIR is not configured; OSM lookup expects staged files "
            "under /WINTAK Imagery on the Jetson."
        )
    elif not _jetson_local_sources_only() and shutil.which("osmium") is None:
        warnings.append(
            "OSM Geofabrik PBF will download, but osmium is not installed; AO clipping "
            "will be marked pending and the regional PBF will be registered."
        )
    if not any(source.category == "terrain" for source in sources):
        warnings.append("No analysis DEM is selected; slope, hydrology, and viewshed queries are blocked.")
    if any(source.id == "naip" for source in sources):
        warnings.append(
            "NAIP AWS prefixes can be large. The manifest caps downloads with NAIP_MAX_FILES "
            "and the Jetson storage check runs before execution."
        )
        if not _env_path("NAIP_EARTHEXPLORER_DIR"):
            warnings.append(
                "NAIP_EARTHEXPLORER_DIR is not configured; display imagery expects "
                "NAIP files under /WINTAK Imagery on the Jetson."
            )
    if any(source.id == "dted_earth_explorer" for source in sources):
        if not _env_path("DTED_SOURCE_DIR"):
            warnings.append(
                "DTED_SOURCE_DIR is not configured; EarthExplorer DTED import is skipped. "
                "The Jetson demo expects DTED files under /DTED."
            )
        elif shutil.which("gdal_translate") is None:
            warnings.append(
                "DTED files will be imported, but gdal_translate is not installed; "
                "raw DTED will be registered without GeoTIFF conversion."
            )
    if any(source.id in {"esri_world_imagery", "esri_world_elevation"} for source in sources):
        if not ESRI_TOKEN_CONFIGURED:
            warnings.append(
                "Esri export operations require ESRI_ARCGIS_TOKEN at download time; "
                "the manifest uses an environment placeholder and does not store secrets."
            )
    if any(source.id == "cesium_ion_archive" for source in sources):
        has_archive_id = bool(_get_cesium_archive_id())
        has_asset_ids = bool(
            (
                os.getenv("CESIUM_ION_ASSET_IDS")
                or os.getenv("CESIUM_ASSET_IDS")
                or os.getenv("CESIUM_ION_ASSET_ID")
                or ""
            ).strip()
        )
        if not _get_cesium_token():
            warnings.append(
                "Cesium archive downloads require CESIUM_ION_TOKEN on the Jetson."
            )
        if not (has_archive_id or has_asset_ids):
            warnings.append(
                "Cesium archive source selected, but no CESIUM_ION_ARCHIVE_ID or "
                "CESIUM_ION_ASSET_IDS is configured; no Cesium download operation "
                "will be created."
            )
        else:
            warnings.append(
                "Cesium downloads use ion archive/export APIs only. The planner will "
                "not scrape World Imagery or World Terrain stream tiles."
            )
    if any(source.stream_status.startswith("streamable") for source in sources):
        warnings.append(
            "Streamable layers still need cached tiles or analytical companions for disconnected use."
        )
    if any(source.id == "esri_world_imagery" for source in sources):
        warnings.append(
            "Esri World Imagery must be exported through the export-enabled service "
            "for offline use; do not scrape individual streaming tiles."
        )
    return warnings


@app.post("/api/source-package/plan", response_model=DownloadPlanResponse)
async def plan_source_package(request: DownloadPlanRequest) -> DownloadPlanResponse:
    sources = _get_source_options_by_ids(request.source_ids)
    package_id = uuid4().hex[:12]
    package_name = (
        request.package_name.strip()
        if request.package_name and request.package_name.strip()
        else f"tera-{request.mission_focus.strip().lower().replace(' ', '-')}-{package_id}"
    )
    manifest = _build_package_manifest(
        package_id=package_id,
        package_name=package_name,
        request=request,
        sources=sources,
    )
    PACKAGE_MANIFESTS[package_id] = manifest
    estimated_bytes = _estimate_manifest_bytes(manifest)
    storage = _storage_info(package_id)
    storage_warning = _storage_warning(estimated_bytes, storage)
    _persist_package_manifest(package_id, manifest)
    _save_package_status(package_id, _initial_package_status(package_id, manifest))
    return DownloadPlanResponse(
        package_id=package_id,
        package_name=package_name,
        mission_focus=request.mission_focus,
        sources=sources,
        manifest=manifest,
        warnings=_download_plan_warnings(request, sources),
        download_url=f"/api/source-package/{package_id}/download",
        execute_url=f"/api/source-package/{package_id}/execute",
        status_url=f"/api/source-package/{package_id}/status",
        artifacts_url=f"/api/source-package/{package_id}/artifacts",
        estimated_bytes=estimated_bytes,
        storage_fit=storage_warning is None,
        storage=storage,
        storage_warning=storage_warning,
    )


@app.get("/api/source-package/{package_id}/download")
async def download_source_manifest(package_id: str) -> StreamingResponse:
    manifest = _load_package_manifest(package_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Source package manifest not found.")

    payload = json.dumps(manifest, indent=2).encode("utf-8")
    package_name = str(manifest.get("package_name", package_id))
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "-", package_name).strip("-") or package_id
    return StreamingResponse(
        iter([payload]),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}.json"',
            "Cache-Control": "no-store",
        },
    )


@app.post("/api/source-package/{package_id}/execute", response_model=PackageExecuteResponse)
async def execute_source_package(package_id: str) -> PackageExecuteResponse:
    package_id = _safe_package_id(package_id)
    manifest = _load_package_manifest(package_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Source package manifest not found.")

    estimated_bytes = _estimate_manifest_bytes(manifest)
    storage = _storage_info(package_id)
    storage_warning = _storage_warning(estimated_bytes, storage)
    if storage_warning is not None:
        raise HTTPException(status_code=507, detail=storage_warning)

    existing_task = PACKAGE_TASKS.get(package_id)
    if existing_task is not None and not existing_task.done():
        status = _load_package_status(package_id)
        return PackageExecuteResponse(
            package_id=package_id,
            state=str(status.get("state", "running")),
            status_url=f"/api/source-package/{package_id}/status",
            artifacts_url=f"/api/source-package/{package_id}/artifacts",
            storage=storage,
            message="Package download is already running on the Jetson.",
        )

    status = _load_package_status(package_id)
    if status.get("state") == "succeeded":
        return PackageExecuteResponse(
            package_id=package_id,
            state="succeeded",
            status_url=f"/api/source-package/{package_id}/status",
            artifacts_url=f"/api/source-package/{package_id}/artifacts",
            storage=storage,
            message="Package is already downloaded on the Jetson.",
        )

    task = asyncio.create_task(_execute_package_job(package_id, manifest))
    PACKAGE_TASKS[package_id] = task
    status["state"] = "queued"
    status["message"] = "Package download queued on the Jetson."
    _save_package_status(package_id, status)
    return PackageExecuteResponse(
        package_id=package_id,
        state="queued",
        status_url=f"/api/source-package/{package_id}/status",
        artifacts_url=f"/api/source-package/{package_id}/artifacts",
        storage=storage,
        message="Package download queued on the Jetson.",
    )


@app.get("/api/source-package/{package_id}/status")
async def get_source_package_status(package_id: str) -> dict[str, object]:
    package_id = _safe_package_id(package_id)
    status = _load_package_status(package_id)
    status["storage"] = _storage_info(package_id).model_dump()
    return status


@app.get("/api/source-package/{package_id}/artifacts")
async def get_source_package_artifacts(package_id: str) -> dict[str, object]:
    package_id = _safe_package_id(package_id)
    if _load_package_manifest(package_id) is None:
        raise HTTPException(status_code=404, detail="Source package manifest not found.")
    registry = _load_artifact_registry(package_id)
    registry["storage"] = _storage_info(package_id).model_dump()
    return registry


@app.get("/api/source-package/{package_id}/query/imagery")
async def query_package_imagery(package_id: str) -> dict[str, object]:
    package_id = _safe_package_id(package_id)
    if _load_package_manifest(package_id) is None:
        raise HTTPException(status_code=404, detail="Source package manifest not found.")
    artifacts = _registry_artifacts_by_prefix(
        package_id,
        source_ids={"naip", "sentinel_2", "usgs_imagery_only", "nrl_naip_conus"},
    )
    indexes: list[dict[str, object]] = []
    for artifact in artifacts:
        if str(artifact.get("artifact_type") or "").endswith("_index"):
            index = _read_json(_artifact_file(package_id, artifact))
            if index:
                indexes.append(index)
    return {
        "package_id": package_id,
        "artifacts": artifacts,
        "indexes": indexes,
        "query_interfaces": [
            "GET /api/source-package/{package_id}/query/imagery",
            "GET /api/source-package/{package_id}/query/imagery/files/{relative_path}",
        ],
        "storage": _storage_info(package_id).model_dump(),
    }


@app.get("/api/source-package/{package_id}/query/imagery/files/{relative_path:path}")
async def get_package_imagery_file(package_id: str, relative_path: str) -> FileResponse:
    return _package_file_response(package_id, relative_path, allowed_roots=("imagery", "tiles"))


@app.get("/api/source-package/{package_id}/query/osm")
async def query_package_osm(package_id: str) -> dict[str, object]:
    package_id = _safe_package_id(package_id)
    if _load_package_manifest(package_id) is None:
        raise HTTPException(status_code=404, detail="Source package manifest not found.")
    artifacts = _registry_artifacts_by_prefix(package_id, source_ids={"osm_extract"})
    indexes: list[dict[str, object]] = []
    for artifact in artifacts:
        if str(artifact.get("artifact_type") or "").endswith("_index"):
            index = _read_json(_artifact_file(package_id, artifact))
            if index:
                indexes.append(index)
    return {
        "package_id": package_id,
        "artifacts": artifacts,
        "indexes": indexes,
        "query_interfaces": [
            "osmium tags-filter",
            "pyosmium scan",
            "valhalla_build_tiles",
            "GET /api/source-package/{package_id}/query/osm/files/{relative_path}",
        ],
        "storage": _storage_info(package_id).model_dump(),
    }


@app.get("/api/source-package/{package_id}/query/osm/files/{relative_path:path}")
async def get_package_osm_file(package_id: str, relative_path: str) -> FileResponse:
    return _package_file_response(package_id, relative_path, allowed_roots=("vectors/osm",))


@app.get("/api/source-package/{package_id}/query/cesium")
async def query_package_cesium(package_id: str) -> dict[str, object]:
    package_id = _safe_package_id(package_id)
    if _load_package_manifest(package_id) is None:
        raise HTTPException(status_code=404, detail="Source package manifest not found.")
    index_path = _package_dir(package_id) / "cesium" / "archive" / "cesium_archive_index.json"
    index = _read_json(index_path)
    if index is None:
        raise HTTPException(status_code=404, detail="Cesium archive index not found for this package.")
    registry = _load_artifact_registry(package_id)
    artifacts = [
        artifact
        for artifact in registry.get("artifacts", [])
        if isinstance(artifact, dict)
        and str(artifact.get("artifact_type") or "").startswith("cesium_")
    ]
    return {
        "package_id": package_id,
        "index": index,
        "artifacts": artifacts,
        "storage": _storage_info(package_id).model_dump(),
    }


@app.get("/api/source-package/{package_id}/query/cesium/files/{relative_path:path}")
async def get_package_cesium_file(package_id: str, relative_path: str) -> FileResponse:
    return _package_file_response(package_id, relative_path, allowed_roots=("cesium",))


@app.post("/api/source-package/{package_id}/query/terrain")
async def query_package_terrain(
    package_id: str,
    request: TerrainQueryRequest,
) -> dict[str, object]:
    package_id = _safe_package_id(package_id)
    grid, bbox, cell_size, artifact = _load_package_terrain_grid(
        package_id,
        max_cells=request.max_cells,
    )
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    if request.query_type == "sample":
        if request.lat is None or request.lon is None:
            raise HTTPException(status_code=422, detail="lat and lon are required for sample queries.")
        row, col = _coord_to_cell(request.lat, request.lon, bbox, rows, cols)
        return {
            "package_id": package_id,
            "query_type": "sample",
            "artifact": artifact.get("relative_path"),
            "lat": request.lat,
            "lon": request.lon,
            "row": row,
            "col": col,
            "elevation_m": grid[row][col],
            "bbox": bbox,
            "cell_size_m": cell_size,
        }
    if request.query_type == "window":
        window_bbox = request.bbox
        if window_bbox is None:
            raise HTTPException(status_code=422, detail="bbox is required for window queries.")
        north_west = _coord_to_cell(window_bbox.north, window_bbox.west, bbox, rows, cols)
        south_east = _coord_to_cell(window_bbox.south, window_bbox.east, bbox, rows, cols)
        row_min, row_max = sorted((north_west[0], south_east[0]))
        col_min, col_max = sorted((north_west[1], south_east[1]))
        window = [row[col_min : col_max + 1] for row in grid[row_min : row_max + 1]]
        cell_count = len(window) * (len(window[0]) if window else 0)
        if cell_count > request.max_cells:
            raise HTTPException(status_code=413, detail="Terrain window exceeds max_cells.")
        return {
            "package_id": package_id,
            "query_type": "window",
            "artifact": artifact.get("relative_path"),
            "bbox": window_bbox.model_dump(),
            "row_range": [row_min, row_max],
            "col_range": [col_min, col_max],
            "elevation_grid": window,
            "cell_size_m": cell_size,
        }

    values = [
        float(value)
        for row in grid
        for value in row
        if isinstance(value, (int, float)) and math.isfinite(float(value))
    ]
    return {
        "package_id": package_id,
        "query_type": "summary",
        "artifact": artifact.get("relative_path"),
        "bbox": bbox,
        "rows": rows,
        "cols": cols,
        "cell_size_m": cell_size,
        "min_elevation_m": min(values) if values else None,
        "max_elevation_m": max(values) if values else None,
        "mean_elevation_m": sum(values) / len(values) if values else None,
    }


@app.get("/api/source-package/{package_id}/query/terrain/files/{relative_path:path}")
async def get_package_terrain_file(package_id: str, relative_path: str) -> FileResponse:
    return _package_file_response(package_id, relative_path, allowed_roots=("rasters", "samples"))


@app.post("/api/source-package/{package_id}/algorithm")
async def run_package_algorithm(
    package_id: str,
    request: AlgorithmRequest,
) -> dict[str, object]:
    package_id = _safe_package_id(package_id)
    if _load_package_manifest(package_id) is None:
        raise HTTPException(status_code=404, detail="Source package manifest not found.")
    return _run_algorithm(package_id, request)


@app.post("/api/source-package/{package_id}/route")
async def create_package_route(
    package_id: str,
    request: PackageRouteRequest,
) -> dict[str, object]:
    package_id = _safe_package_id(package_id)
    if _load_package_manifest(package_id) is None:
        raise HTTPException(status_code=404, detail="Source package manifest not found.")
    return _build_route_from_package(package_id, request)


@app.post("/api/source-package/{package_id}/cot")
async def create_package_cot(
    package_id: str,
    request: PackageCotRequest,
) -> dict[str, object]:
    package_id = _safe_package_id(package_id)
    route_artifact = _load_route_artifact(package_id, request.route_id) if request.route_id else None
    route = request.route or (route_artifact or {}).get("route")
    if not isinstance(route, dict):
        raise HTTPException(status_code=422, detail="route or route_id is required.")
    route_id = request.route_id or str(route.get("properties", {}).get("route_id") or f"TERA-{uuid4().hex[:10]}")
    rationale = request.rationale
    if route_artifact and isinstance(route_artifact.get("rationale"), str):
        rationale = str(route_artifact["rationale"])
    coordinates = route.get("geometry", {}).get("coordinates", [])
    if not coordinates:
        raise HTTPException(status_code=422, detail="Route geometry must contain coordinates.")

    events: list[dict[str, object]] = []
    cot_type_code = "b-m-r" if request.cot_type == "route" else "a-f-G-U-C"
    event_coords = [coordinates[-1]] if request.cot_type == "route" else coordinates
    for index, coordinate in enumerate(event_coords):
        lon = float(coordinate[0])
        lat = float(coordinate[1])
        uid = route_id if request.cot_type == "route" else f"{route_id}-track-{index:03d}"
        route_properties = route.get("properties")
        route_title_value = (
            route_properties.get("route_id") if isinstance(route_properties, dict) else None
        )
        route_title = str(route_title_value or route_id)
        cot_xml = _build_cot_xml(
            uid=uid,
            cot_type=cot_type_code,
            lat=lat,
            lon=lon,
            route=route,
            title=route_title or route_id,
            remarks=rationale,
        )
        signed_xml, signed = _sign_cot_xml(
            uid=uid,
            lat=lat,
            lon=lon,
            route=route,
            rationale=rationale,
            mission_type=request.mission_type,
            cot_xml=cot_xml,
        )
        cot_path = _cot_dir(package_id) / f"{_safe_package_id(uid)}.cot.xml"
        cot_path.parent.mkdir(parents=True, exist_ok=True)
        cot_path.write_text(signed_xml, encoding="utf-8")
        events.append(
            {
                "uid": uid,
                "cot_type": cot_type_code,
                "path": str(cot_path),
                "relative_path": cot_path.relative_to(_package_dir(package_id)).as_posix(),
                "signed": True,
                "signature_scheme": signed.get("algorithm"),
                "key_id": signed.get("key_id"),
                "cot_xml": signed_xml,
            }
        )

    response = {
        "package_id": package_id,
        "route_id": route_id,
        "route_hash": _route_hash(route),
        "cot_type": request.cot_type,
        "approval_state": "provisional",
        "atak_display": "Suggested Route - Needs Review",
        "events": events,
    }
    _write_json(_cot_dir(package_id) / f"{_safe_package_id(route_id)}-{request.cot_type}.json", response)
    return response


@app.post("/api/prompt", response_model=PromptResponse)
async def prompt_ollama(request: PromptRequest) -> PromptResponse:
    request = _coerce_atak_prompt_request(request)
    mirror = _request_is_atak_mirror_candidate(request)
    mirror_query_context = _atak_monitor_query_context(request) if mirror else {}
    mirror_client_location = _atak_monitor_client_location(request.map_context)
    mirror_view_bounds = _atak_monitor_view_bounds(request.map_context)
    if mirror:
        _append_atak_mirror_event(
            source=_mirror_source_for_request(request),
            role="operator",
            text=request.prompt,
            model=request.model or str(JETSON_ATAK_MODE.get("model") or TERA_ATAK_MODEL),
            provider=_request_llm_provider(request),
            direction="inbound",
            client_location=mirror_client_location,
            view_bounds=mirror_view_bounds,
            query_context=mirror_query_context,
        )
    try:
        result = await _post_prompt_with_fallback(request)
    except HTTPException as exc:
        if mirror:
            _append_atak_mirror_event(
                source="tera-agent",
                role="assistant",
                text=f"ERROR: {exc.detail}",
                model=request.model or str(JETSON_ATAK_MODE.get("model") or TERA_ATAK_MODEL),
                provider=_request_llm_provider(request),
                direction="error",
                client_location=mirror_client_location,
                view_bounds=mirror_view_bounds,
                query_context=mirror_query_context,
            )
        raise
    result.tak_cot = _build_tak_cot_payload(request, result.response)
    if mirror:
        outbound_text = _response_text_with_tak_cot_summary(
            result.response,
            result.tak_cot,
        )
        _append_atak_mirror_event(
            source="tera-agent",
            role="assistant",
            text=outbound_text,
            model=result.model,
            provider=result.provider,
            direction="outbound",
            client_location=mirror_client_location,
            view_bounds=mirror_view_bounds,
            query_context=mirror_query_context,
            tak_cot_summary=_tak_cot_monitor_summary(result.tak_cot),
        )
    return result


@app.post("/api/prompt/stream")
async def prompt_ollama_stream(request: PromptRequest) -> StreamingResponse:
    request = _coerce_atak_prompt_request(request)
    mirror = _request_is_atak_mirror_candidate(request)
    mirror_query_context = _atak_monitor_query_context(request) if mirror else {}
    mirror_client_location = _atak_monitor_client_location(request.map_context)
    mirror_view_bounds = _atak_monitor_view_bounds(request.map_context)
    if mirror:
        _append_atak_mirror_event(
            source=_mirror_source_for_request(request),
            role="operator",
            text=request.prompt,
            model=request.model or str(JETSON_ATAK_MODE.get("model") or TERA_ATAK_MODEL),
            provider=_request_llm_provider(request),
            direction="inbound",
            client_location=mirror_client_location,
            view_bounds=mirror_view_bounds,
            query_context=mirror_query_context,
        )

    async def event_stream():
        global ACTIVE_OLLAMA_BASE_URL, ACTIVE_OLLAMA_MODEL
        failures: list[str] = []
        sequence = _provider_sequence(request)
        for provider in sequence:
            if provider == "claude":
                model, _payload = _build_claude_payload(request)
                yield _sse_event({"type": "start", "model": model, "provider": "claude"})
                yield _sse_event(
                    {
                        "type": "status",
                        "detail": "Waiting for Claude API response",
                        "model": model,
                        "provider": "claude",
                    }
                )
                try:
                    result = await _post_claude_message(request)
                except HTTPException as exc:
                    failure = _failure_message("claude", exc)
                    failures.append(failure)
                    if "ollama" in sequence:
                        yield _sse_event(
                            {
                                "type": "fallback",
                                "detail": "Claude unavailable; trying local Ollama fallback.",
                                "reason": failure,
                                "provider": "claude",
                            }
                        )
                        continue
                    if mirror:
                        _append_atak_mirror_event(
                            source="tera-agent",
                            role="assistant",
                            text=f"ERROR: {exc.detail}",
                            model=model,
                            provider="claude",
                            direction="error",
                            client_location=mirror_client_location,
                            view_bounds=mirror_view_bounds,
                            query_context=mirror_query_context,
                        )
                    yield _sse_event(
                        {
                            "type": "error",
                            "detail": str(exc.detail),
                            "model": model,
                            "provider": "claude",
                        }
                    )
                    return
                yield _sse_event(
                    {
                        "type": "token",
                        "text": result.response,
                        "model": result.model,
                        "provider": "claude",
                    }
                )
                result.tak_cot = _build_tak_cot_payload(request, result.response)
                if mirror:
                    _append_atak_mirror_event(
                        source="tera-agent",
                        role="assistant",
                        text=_response_text_with_tak_cot_summary(
                            result.response,
                            result.tak_cot,
                        ),
                        model=result.model,
                        provider="claude",
                        direction="outbound",
                        client_location=mirror_client_location,
                        view_bounds=mirror_view_bounds,
                        query_context=mirror_query_context,
                        tak_cot_summary=_tak_cot_monitor_summary(result.tak_cot),
                    )
                yield _sse_event(
                    {
                        "type": "done",
                        "model": result.model,
                        "provider": "claude",
                        "fallbacks": failures,
                        "tak_cot": result.tak_cot.model_dump(),
                    }
                )
                return

            model, payload = await _build_ollama_payload(request, stream=True)
            timeout = httpx.Timeout(REQUEST_TIMEOUT_S, connect=10.0)
            yield _sse_event({"type": "start", "model": model, "provider": "ollama"})
            yield _sse_event(
                {
                    "type": "status",
                    "detail": "Waiting for local model tokens",
                    "model": model,
                    "provider": "ollama",
                }
            )
            errors: list[str] = []
            for base_url in _ollama_base_url_candidates():
                streamed_text = ""
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        async with client.stream(
                            "POST", f"{base_url}/api/generate", json=payload
                        ) as response:
                            if response.status_code >= 400:
                                body = (await response.aread()).decode(
                                    "utf-8", errors="replace"
                                )[:500]
                                errors.append(
                                    f"{base_url} returned {response.status_code}: {body}"
                                )
                                log.error(
                                    "ollama_stream_http_error",
                                    status_code=response.status_code,
                                    body=body,
                                    ollama_base_url=base_url,
                                    model=model,
                                )
                                continue

                            ACTIVE_OLLAMA_BASE_URL = base_url
                            ACTIVE_OLLAMA_MODEL = model
                            async for line in response.aiter_lines():
                                if not line:
                                    continue
                                try:
                                    chunk = json.loads(line)
                                except json.JSONDecodeError:
                                    continue

                                text = str(chunk.get("response", ""))
                                if text:
                                    streamed_text += text
                                    yield _sse_event(
                                        {
                                            "type": "token",
                                            "text": text,
                                            "model": model,
                                            "provider": "ollama",
                                        }
                                    )

                                if chunk.get("done"):
                                    tak_cot = _build_tak_cot_payload(
                                        request,
                                        streamed_text,
                                    )
                                    if mirror:
                                        _append_atak_mirror_event(
                                            source="tera-agent",
                                            role="assistant",
                                            text=_response_text_with_tak_cot_summary(
                                                streamed_text,
                                                tak_cot,
                                            ),
                                            model=model,
                                            provider="ollama",
                                            direction="outbound",
                                            client_location=mirror_client_location,
                                            view_bounds=mirror_view_bounds,
                                            query_context=mirror_query_context,
                                            tak_cot_summary=_tak_cot_monitor_summary(tak_cot),
                                        )
                                    yield _sse_event(
                                        {
                                            "type": "done",
                                            "model": model,
                                            "provider": "ollama",
                                            "fallbacks": failures,
                                            "tak_cot": tak_cot.model_dump(),
                                        }
                                    )
                                    return
                except httpx.HTTPError as exc:
                    errors.append(f"{base_url} unreachable: {exc}")
                    log.error(
                        "ollama_stream_connection_error",
                        error=str(exc),
                        ollama_base_url=base_url,
                        model=model,
                    )
            failures.append("ollama: " + " | ".join(errors))
            if mirror:
                _append_atak_mirror_event(
                    source="tera-agent",
                    role="assistant",
                    text="ERROR: All model providers failed. " + " | ".join(failures),
                    model=model,
                    provider="ollama",
                    direction="error",
                    client_location=mirror_client_location,
                    view_bounds=mirror_view_bounds,
                    query_context=mirror_query_context,
                )
            yield _sse_event(
                {
                    "type": "error",
                    "detail": "All model providers failed. " + " | ".join(failures),
                    "model": model,
                    "provider": "ollama",
                    "fallbacks": failures,
                }
            )
            return

        yield _sse_event(
            {
                "type": "error",
                "detail": "No model providers were configured.",
                "fallbacks": failures,
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
