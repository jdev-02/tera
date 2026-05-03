from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
from uuid import uuid4

import httpx
import structlog
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

log = structlog.get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent
PROMPT_DIR = BASE_DIR.parent / "prompts" / "local_model_prompts"
IMAGERY_SOURCING_PROMPT_FILE = (
    PROMPT_DIR / "imagery_sourcing_local_model_system_prompt.md"
)
INDEX_FILE = BASE_DIR / "static" / "index.html"
STATIC_DIR = BASE_DIR / "static"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:2b")
REQUEST_TIMEOUT_S = float(os.getenv("REQUEST_TIMEOUT_S", "120"))
CESIUM_ION_TOKEN = os.getenv("CESIUM_ION_TOKEN", "")
DEFAULT_LAT = float(os.getenv("DEFAULT_LAT", "37.7749"))
DEFAULT_LON = float(os.getenv("DEFAULT_LON", "-122.4194"))
DEFAULT_HEIGHT_M = float(os.getenv("DEFAULT_HEIGHT_M", "14000"))

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
    agent_profile: str | None = Field(default="imagery-sourcing", max_length=80)
    map_context: "MapContext | None" = None
    source_context: SourceContext | None = None


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
    selected_area: ViewBounds | None = None
    camera: MapPoint | None = None
    view_bounds: ViewBounds | None = None
    imagery_source: str | None = Field(default=None, max_length=200)
    terrain_source: str | None = Field(default=None, max_length=200)


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


class DownloadPlanResponse(BaseModel):
    package_id: str
    package_name: str
    mission_focus: str
    sources: list[SourceOption]
    manifest: dict[str, object]
    warnings: list[str]
    download_url: str


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


SOURCE_CATALOG: list[SourceOption] = [
    SourceOption(
        id="esri_world_imagery",
        name="Esri World Imagery",
        provider="Esri ArcGIS Online",
        category="imagery",
        purpose="High-resolution visual basemap for AO inspection and imagery context.",
        useful_for=[
            "visual AO verification",
            "roads and tracks visible in imagery",
            "buildings and clearings",
            "vegetation and water body sanity checks",
        ],
        analysis_role=(
            "Display stream only in this app; cache tiles for offline visualization and "
            "pair with analytical imagery or vector extracts for database queries."
        ),
        stream_status="streamable",
        download_status="manifest-only",
        stream_layer="esri",
        required_for=["imagery-preview"],
        recommended_for=["terrain-routing", "water-access", "sar-planning", "evacuation"],
        derived_layers=["visual_aoi_reference"],
        notes="Do not use the visual tile stream as the sole analytical source.",
    ),
    SourceOption(
        id="cesium_world_imagery",
        name="Cesium World Imagery",
        provider="Cesium ion",
        category="imagery",
        purpose="Token-backed global imagery stream for Cesium preview.",
        useful_for=["3D mission preview", "route visualization backdrop", "AO briefing"],
        analysis_role="Display layer; pre-cache selected tiles for disconnected demos.",
        stream_status="streamable-with-token",
        download_status="cache-via-cesium-pipeline",
        stream_layer="ion-satellite",
        recommended_for=["imagery-preview", "terrain-routing"],
        derived_layers=["cached_imagery_tiles"],
        notes="Phase 3 runtime must read cached tiles rather than calling Cesium online.",
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
        download_status="cache-via-cesium-pipeline",
        stream_layer="cesium-world",
        recommended_for=["terrain-routing", "signal-planning", "imagery-preview"],
        derived_layers=["cached_terrain_tiles"],
        notes="Good for visualization, not a substitute for indexed DEM rasters.",
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
        provider="OpenStreetMap / Geofabrik / regional extract",
        category="vector",
        purpose="Local vector extract for roads, trails, paths, waterways, buildings, POIs, and barriers.",
        useful_for=[
            "routable graph",
            "nearest road or trail",
            "waterway and POI lookup",
            "barrier and bridge/crossing context",
        ],
        analysis_role="Primary local vector dataset for database-backed graph and feature queries.",
        stream_status="not-streamed",
        download_status="download-required",
        required_for=["terrain-routing", "water-access", "evacuation", "sar-planning"],
        recommended_for=["access-control", "signal-planning"],
        derived_layers=["routable_graph", "poi_index", "waterway_index", "barrier_index"],
        notes="Clip tightly to AO and preserve source/version metadata.",
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
        name="Copernicus DEM",
        provider="Copernicus",
        category="terrain",
        purpose="Strong global DEM when U.S. 3DEP is unavailable.",
        useful_for=["global slope", "viewshed", "terrain cost", "AO outside U.S."],
        analysis_role="Primary or fallback analysis DEM for non-U.S. mission areas.",
        stream_status="not-streamed",
        download_status="download-required",
        required_for=["terrain-routing", "signal-planning"],
        recommended_for=["water-access", "sar-planning"],
        derived_layers=["slope_degrees", "roughness", "flow_accumulation", "viewshed_surfaces"],
        notes="Confirm coverage, license, and void handling for the AO before packaging.",
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
        provider="ESA Copernicus",
        category="imagery-analysis",
        purpose="Multispectral imagery for vegetation, water, burn, and surface-condition indices.",
        useful_for=["NDVI", "NDWI", "water detection", "vegetation condition", "recent surface context"],
        analysis_role="Analysis imagery source for derived indices, not just visual backdrop.",
        stream_status="not-streamed",
        download_status="download-required",
        recommended_for=["water-access", "sar-planning", "imagery-preview"],
        derived_layers=["ndvi", "ndwi", "vegetation_condition", "water_detection"],
        notes="Cloud cover and date filtering matter; preserve acquisition timestamp.",
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
        provider="USDA",
        category="imagery-analysis",
        purpose="High-resolution U.S. aerial imagery for detailed visual feature extraction.",
        useful_for=["small roads/tracks", "buildings", "clearings", "agricultural features"],
        analysis_role="Analysis imagery and offline basemap source for U.S. AO detail.",
        stream_status="not-streamed",
        download_status="download-required",
        recommended_for=["imagery-preview", "sar-planning", "evacuation"],
        derived_layers=["high_detail_aerial_reference", "feature_extraction_review"],
        notes="Check acquisition date; may be stale for fast-changing environments.",
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
PRIMARY_STREAM_SOURCE_IDS = ["esri_world_imagery", "cesium_world_terrain", "osm_basemap"]
PACKAGE_MANIFESTS: dict[str, dict[str, object]] = {}

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


def _format_source_catalog_brief() -> str:
    lines = []
    for source in SOURCE_CATALOG:
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
        lines.append(f"- Required sources inferred: {', '.join(required_names)}")
    if source_context.optional_source_ids:
        optional_names = [
            SOURCE_BY_ID[source_id].name
            for source_id in source_context.optional_source_ids
            if source_id in SOURCE_BY_ID
        ]
        lines.append(f"- Optional sources inferred: {', '.join(optional_names)}")
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


def _text_has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _infer_is_us_context(prompt_text: str, map_context: MapContext | None) -> bool:
    if _text_has_any(prompt_text, US_CONTEXT_TERMS):
        return True
    bounds = (map_context.selected_area or map_context.view_bounds) if map_context else None
    if bounds and bounds.center_lat is not None and bounds.center_lon is not None:
        return 18.0 <= bounds.center_lat <= 72.0 and -170.0 <= bounds.center_lon <= -50.0
    return False


def _infer_mission_focus(prompt_text: str) -> str:
    scores: dict[str, int] = {}
    for focus, keywords in FOCUS_KEYWORDS:
        score = sum(1 for keyword in keywords if keyword in prompt_text)
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
    is_us_context = _infer_is_us_context(prompt_text, map_context)
    mission_focus = _infer_mission_focus(prompt_text)

    required_ids: list[str] = []
    optional_ids: list[str] = []
    questions: list[str] = []
    rationale: list[str] = []

    _append_unique(optional_ids, "esri_world_imagery", "osm_basemap")
    rationale.append("Esri imagery and OSM basemap stay as lightweight preview/context layers.")

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

    if needs_routing:
        _append_unique(required_ids, "osm_extract")
        rationale.append("OSM PBF is required for the local routable graph and POI/feature lookup.")

    if needs_terrain:
        _append_unique(required_ids, "usgs_3dep" if is_us_context else "copernicus_dem")
        _append_unique(optional_ids, "cesium_world_terrain")
        rationale.append("An analysis DEM is required for slope, exposure, hydrology, and cost surfaces.")

    if needs_landcover:
        _append_unique(required_ids, "nlcd" if is_us_context else "esa_worldcover")
        rationale.append(
            "Land cover is included only because the mission mentions movement "
            "friction, cover, vegetation, or route quality."
        )

    if needs_water:
        _append_unique(required_ids, "usgs_3dhp" if is_us_context else "hydrosheds")
        if is_us_context:
            _append_unique(optional_ids, "nwis")
        _append_unique(optional_ids, "sentinel_2")
        rationale.append(
            "Hydrography is required for water-source and drainage queries; "
            "imagery/observations are optional confidence boosters."
        )

    if needs_sar:
        _append_unique(required_ids, "osm_extract")
        _append_unique(optional_ids, "naip" if is_us_context else "sentinel_2", "noaa_alerts")
        rationale.append(
            "SAR planning needs access features and often benefits from "
            "high-detail imagery and current alerts."
        )

    if needs_hazards:
        _append_unique(optional_ids, "noaa_alerts")
        if "fire" in prompt_text or "wildfire" in prompt_text:
            _append_unique(required_ids, "nasa_firms")
        if "flood" in prompt_text:
            _append_unique(required_ids, "fema_flood" if is_us_context else "sentinel_1_sar")
        rationale.append(
            "Hazard feeds are included only when the mission says current "
            "hazards affect routing or safety."
        )

    if needs_access:
        _append_unique(required_ids, "pad_us" if is_us_context else "parcels_boundaries")
        if is_us_context:
            _append_unique(optional_ids, "blm_usfs_nps", "parcels_boundaries")
        rationale.append(
            "Access and boundary layers are included only when "
            "legal/restricted movement matters."
        )

    if needs_signal:
        _append_unique(required_ids, "viewshed_surfaces")
        _append_unique(optional_ids, "fcc_towers" if is_us_context else "osm_towers", "osm_towers")
        if not needs_terrain:
            _append_unique(required_ids, "usgs_3dep" if is_us_context else "copernicus_dem")
        rationale.append("Signal planning requires DEM-derived viewsheds plus tower/high-ground candidates.")

    if needs_current_imagery and not needs_water and not needs_hazards:
        _append_unique(optional_ids, "sentinel_2", "landsat_collection_2")
        if is_us_context:
            _append_unique(optional_ids, "naip")
        rationale.append(
            "Current or historical imagery is optional unless the mission "
            "depends on recent conditions."
        )

    if not required_ids:
        questions.append(
            "Which mission outcome must the database answer first: routing, "
            "water lookup, SAR sectors, signal planning, hazards, or access "
            "control? This decides the required source family."
        )
        rationale.append(
            "No deterministic analytical layer was inferred yet, so the "
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
            "Is the operator asking for mapped water features only, or "
            "confidence in current and potable water availability? The "
            "broader answer adds observation or imagery layers beyond "
            "hydrography."
        )
    if needs_hazards:
        questions.append(
            "Which hazards must be current at package time versus treated as "
            "cached baseline risk? Current hazards add live feeds; baseline "
            "risk keeps the package smaller."
        )
    if needs_signal:
        questions.append(
            "What antenna height and radio role should viewshed or relay "
            "analysis assume? This controls whether tower datasets are needed "
            "or a DEM-derived viewshed is sufficient."
        )
    if needs_access:
        questions.append(
            "Should the package enforce legal or restricted access boundaries, "
            "or only support terrain movement? Enforcing access adds parcels, "
            "protected areas, or land-management boundaries."
        )
    if map_context is None or (map_context.selected_area is None and map_context.view_bounds is None):
        questions.append(
            "Is this AO inside the U.S. or outside it? That choice switches "
            "between U.S.-authoritative layers and global open layers."
        )

    selected_ids = []
    preview_ids = [
        source_id
        for source_id in ("esri_world_imagery", "osm_basemap")
        if source_id in optional_ids
    ]
    _append_unique(selected_ids, *required_ids, *preview_ids)
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
    profile = (request.agent_profile or "imagery-sourcing").strip().lower()
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
        _format_view_bounds(map_context.selected_area if map_context else None).replace(
            "Visible map bounds", "Selected AO bounds"
        ),
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


def _build_package_manifest(
    *,
    package_id: str,
    package_name: str,
    request: DownloadPlanRequest,
    sources: list[SourceOption],
) -> dict[str, object]:
    selected_ids = [source.id for source in sources]
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
                "notes": source.notes,
            }
            for source in sources
        ],
        "server_ingest_plan": {
            "store_raw_sources": [
                source.id
                for source in sources
                if source.download_status in {"download-required", "cache-feed"}
            ],
            "cache_display_tiles": [
                source.id
                for source in sources
                if source.download_status == "cache-via-cesium-pipeline"
                or source.stream_status.startswith("streamable")
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
                in {"terrain", "land-cover", "imagery-analysis", "hazards", "terrain-display"}
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
    if request.map_context is None or (
        request.map_context.selected_area is None and request.map_context.view_bounds is None
    ):
        warnings.append("No AO bounds were provided; downloads must be clipped before ingest.")
    if not any(source.id == "osm_extract" for source in sources):
        warnings.append("OSM PBF extract is not selected, so server-side routable graph work is blocked.")
    if not any(source.category == "terrain" for source in sources):
        warnings.append("No analysis DEM is selected; slope, hydrology, and viewshed queries are blocked.")
    if any(source.stream_status.startswith("streamable") for source in sources):
        warnings.append(
            "Streamable layers still need cached tiles or analytical companions for disconnected use."
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
    return DownloadPlanResponse(
        package_id=package_id,
        package_name=package_name,
        mission_focus=request.mission_focus,
        sources=sources,
        manifest=manifest,
        warnings=_download_plan_warnings(request, sources),
        download_url=f"/api/source-package/{package_id}/download",
    )


@app.get("/api/source-package/{package_id}/download")
async def download_source_manifest(package_id: str) -> StreamingResponse:
    manifest = PACKAGE_MANIFESTS.get(package_id)
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
