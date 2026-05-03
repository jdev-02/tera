const state = {
  config: null,
  viewer: null,
  clickHandler: null,
  resizeObserver: null,
  selectedArea: null,
  areaEntity: null,
  areaHandleEntities: [],
  areaSelectActive: false,
  areaDrawing: false,
  areaResizeHandle: null,
  areaResizeAnchorPoint: null,
  areaStartPoint: null,
  cameraText: "",
  chatCount: 0,
  imageryMode: "ion-satellite",
  terrainMode: "cesium-world",
  mapMode: "2d",
  panelWidth: 520,
  panelCollapsed: false,
  dragState: null,
  handlersBound: false,
  dataSources: [],
  primarySourceIds: [],
  sourceCatalogFallback: false,
  sourceCatalogMessage: "",
  sourcePlannerFallback: false,
  sourcePlannerMessage: "",
  overlayDataSource: null,
  overlayFileName: "",
  overlayFeatureCount: 0,
  locationSearchMatches: [],
  locationSearchDetail: "",
  activeLocationSearchIndex: -1,
  mapFocusLabel: "",
  mapFocusSource: "",
  mapLocationConfirmed: false,
  locationSearchTimer: null,
  locationSearchRequestId: 0,
  cesiumIonTokenAvailable: false,
  localModelAvailable: false,
  localModelDetail: "",
  serverClaudeKeyAvailable: false,
  llmProvider: sessionStorage.getItem("teraLlmProvider") || "auto",
  claudeApiKey: sessionStorage.getItem("teraClaudeApiKey") || "",
  atakAgentActive: false,
  atakMirrorTimer: null,
  selectedSourceIds: new Set(),
  packagePlan: null,
  packageStatusTimer: null,
  jetsonStorage: null,
  sourceInference: null,
  sourceConfirmed: false,
  workflowStageIndex: 0,
  lastMissionText: "",
};

const els = {
  tokenChip: document.getElementById("tokenChip"),
  settingsToggleBtn: document.getElementById("settingsToggleBtn"),
  settingsMenu: document.getElementById("settingsMenu"),
  modelProviderBtn: document.getElementById("modelProviderBtn"),
  modelProviderMenu: document.getElementById("modelProviderMenu"),
  providerStatus: document.getElementById("providerStatus"),
  providerSelect: document.getElementById("providerSelect"),
  topModelSelect: document.getElementById("topModelSelect"),
  claudeModelSelect: document.getElementById("claudeModelSelect"),
  claudeApiKeyInput: document.getElementById("claudeApiKeyInput"),
  providerLocalModelRow: document.getElementById("providerLocalModelRow"),
  providerClaudeModelRow: document.getElementById("providerClaudeModelRow"),
  providerClaudeKeyRow: document.getElementById("providerClaudeKeyRow"),
  saveProviderBtn: document.getElementById("saveProviderBtn"),
  clearClaudeKeyBtn: document.getElementById("clearClaudeKeyBtn"),
  agentProfileSelect: document.getElementById("agentProfileSelect"),
  imagerySelect: document.getElementById("imagerySelect"),
  terrainSelect: document.getElementById("terrainSelect"),
  resetViewBtn: document.getElementById("resetViewBtn"),
  importOverlayBtn: document.getElementById("importOverlayBtn"),
  overlayFileInput: document.getElementById("overlayFileInput"),
  atakAgentBtn: document.getElementById("atakAgentBtn"),
  atakMirrorPanel: document.getElementById("atakMirrorPanel"),
  atakMirrorStatus: document.getElementById("atakMirrorStatus"),
  atakMirrorLog: document.getElementById("atakMirrorLog"),
  atakMirrorRefreshBtn: document.getElementById("atakMirrorRefreshBtn"),
  panelToggleBtn: document.getElementById("panelToggleBtn"),
  panelResizer: document.getElementById("panelResizer"),
  workspaceShell: document.querySelector(".workspace-shell"),
  agentPanel: document.getElementById("agentPanel"),
  sourcePanel: document.getElementById("sourcePanel"),
  mapStage: document.querySelector(".map-stage"),
  mapResetViewBtn: document.getElementById("mapResetViewBtn"),
  mapModeToggleBtn: document.getElementById("mapModeToggleBtn"),
  locationSearchPanel: document.getElementById("locationSearchPanel"),
  locationSearchForm: document.getElementById("locationSearchForm"),
  locationSearchInput: document.getElementById("locationSearchInput"),
  locationSearchSuggestions: document.getElementById("locationSearchSuggestions"),
  centerGridValue: document.getElementById("centerGridValue"),
  centerGridLatLon: document.getElementById("centerGridLatLon"),
  compassRose: document.getElementById("compassRose"),
  compassHeading: document.getElementById("compassHeading"),
  tiltNeedle: document.getElementById("tiltNeedle"),
  tiltValue: document.getElementById("tiltValue"),
  promptForm: document.getElementById("promptForm"),
  promptInput: document.getElementById("promptInput"),
  modelSelect: document.getElementById("modelSelect"),
  systemInput: document.getElementById("systemInput"),
  includeMapContext: document.getElementById("includeMapContext"),
  submitBtn: document.getElementById("submitBtn"),
  clearChatBtn: document.getElementById("clearChatBtn"),
  requestStatus: document.getElementById("requestStatus"),
  modelsStatus: document.getElementById("modelsStatus"),
  modelsList: document.getElementById("modelsList"),
  selectedArea: document.getElementById("selectedArea"),
  cameraPosition: document.getElementById("cameraPosition"),
  imageryStatus: document.getElementById("imageryStatus"),
  terrainStatus: document.getElementById("terrainStatus"),
  chatLog: document.getElementById("chatLog"),
  chatMeta: document.getElementById("chatMeta"),
  sourceCount: document.getElementById("sourceCount"),
  workflowEmpty: document.getElementById("workflowEmpty"),
  workflowCarousel: document.getElementById("workflowCarousel"),
  workflowPrevBtn: document.getElementById("workflowPrevBtn"),
  workflowNextBtn: document.getElementById("workflowNextBtn"),
  workflowStageLabel: document.getElementById("workflowStageLabel"),
  workflowStageMeta: document.getElementById("workflowStageMeta"),
  workflowDots: document.getElementById("workflowDots"),
  workflowSlides: Array.from(document.querySelectorAll("[data-workflow-slide]")),
  sourceList: document.getElementById("sourceList"),
  packageModeChip: document.getElementById("packageModeChip"),
  inferredMission: document.getElementById("inferredMission"),
  packageNameInput: document.getElementById("packageNameInput"),
  confirmSourcesBtn: document.getElementById("confirmSourcesBtn"),
  aoLockedNotice: document.getElementById("aoLockedNotice"),
  areaControlSurface: document.getElementById("areaControlSurface"),
  drawAreaBtn: document.getElementById("drawAreaBtn"),
  clearAreaBtn: document.getElementById("clearAreaBtn"),
  streamSelectedBtn: document.getElementById("streamSelectedBtn"),
  buildPackageBtn: document.getElementById("buildPackageBtn"),
  packageStatus: document.getElementById("packageStatus"),
  packageManifest: document.getElementById("packageManifest"),
  downloadManifestLink: document.getElementById("downloadManifestLink"),
  jetsonStorageCard: document.getElementById("jetsonStorageCard"),
  storageRoot: document.getElementById("storageRoot"),
  storageFitChip: document.getElementById("storageFitChip"),
  storageMeterUsed: document.getElementById("storageMeterUsed"),
  storageMeterReserve: document.getElementById("storageMeterReserve"),
  storageFree: document.getElementById("storageFree"),
  storageUsable: document.getElementById("storageUsable"),
  storageReserve: document.getElementById("storageReserve"),
  storageEstimate: document.getElementById("storageEstimate"),
  packageExecutionActions: document.getElementById("packageExecutionActions"),
  downloadToJetsonBtn: document.getElementById("downloadToJetsonBtn"),
  refreshPackageStatusBtn: document.getElementById("refreshPackageStatusBtn"),
  packageExecutionStatus: document.getElementById("packageExecutionStatus"),
  packageArtifacts: document.getElementById("packageArtifacts"),
};

window.__TERA_SOURCE_STATE = state;
window.__LLM_DEV_STATE = state;

const WORKFLOW_STAGES = [
  {
    key: "mission",
    label: "Mission",
    meta: "Review extracted mission",
  },
  {
    key: "sources",
    label: "Sources",
    meta: "Confirm database inputs",
  },
  {
    key: "area",
    label: "AO",
    meta: "Set package coverage",
  },
];

const IMAGERY_FALLBACKS = {
  esri: {
    url: "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    credit: "Esri World Imagery",
    label: "Esri World Imagery",
  },
  "usgs-imagery": {
    url: "https://basemap.nationalmap.gov/ArcGIS/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}",
    credit: "USGS The National Map",
    label: "USGS Imagery Only",
  },
  osm: {
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    credit: "OpenStreetMap contributors",
    label: "OpenStreetMap",
  },
};

const FALLBACK_PRIMARY_STREAM_SOURCE_IDS = [
  "cesium_world_imagery",
  "usgs_imagery_only",
  "cesium_world_terrain",
  "osm_basemap",
];

const LOCATION_INTENT_PREFIX_PATTERN = /^(go to|goto|navigate to|take me to|move map to|move to|search for|find|show me|zoom to|center on|focus on)\s+/i;

const LOCATION_GAZETTEER = [
  {
    name: "San Francisco, CA",
    detail: "City center and Bay Area mission staging reference",
    lat: 37.7749,
    lon: -122.4194,
    heightM: 14000,
    aliases: ["sf", "san fran", "bay area"],
  },
  {
    name: "Presidio of San Francisco, CA",
    detail: "Urban-coastal terrain, trails, batteries, and shoreline access",
    lat: 37.7989,
    lon: -122.4662,
    heightM: 4500,
    aliases: ["presidio", "crissy field"],
  },
  {
    name: "Golden Gate Bridge, CA",
    detail: "Bridge, shoreline, ridge, and urban approach terrain",
    lat: 37.8199,
    lon: -122.4783,
    heightM: 4500,
    aliases: ["golden gate", "ggb"],
  },
  {
    name: "Treasure Island, CA",
    detail: "Bay island, bridge access, and maritime-adjacent infrastructure",
    lat: 37.8230,
    lon: -122.3708,
    heightM: 5000,
    aliases: ["yerba buena island", "treasure island sf"],
  },
  {
    name: "Oakland, CA",
    detail: "Urban port, hills, freeway, rail, and shoreline terrain",
    lat: 37.8044,
    lon: -122.2712,
    heightM: 12000,
    aliases: ["oakland hills", "port of oakland"],
  },
  {
    name: "Mount Tamalpais, CA",
    detail: "Coastal mountain terrain, ridges, trails, and signal high ground",
    lat: 37.9235,
    lon: -122.5965,
    heightM: 9000,
    aliases: ["mt tam", "mount tam"],
  },
  {
    name: "Yosemite Valley, CA",
    detail: "Steep granitic valley, trails, water, cliffs, and SAR terrain",
    lat: 37.7456,
    lon: -119.5936,
    heightM: 9000,
    aliases: ["yosemite", "yosemite national park"],
  },
  {
    name: "Lake Tahoe, CA/NV",
    detail: "Mountain lake, ridges, winter hazards, trails, and evacuation routes",
    lat: 39.0968,
    lon: -120.0324,
    heightM: 18000,
    aliases: ["tahoe", "south lake tahoe"],
  },
  {
    name: "Cascade Range, WA/OR/BC",
    detail: "Pacific Northwest mountain range, national forests, volcanoes, SAR and terrain-routing context",
    lat: 45.6500,
    lon: -121.7000,
    heightM: 26000,
    aliases: ["cascades", "the cascades", "cascade mountains", "cascade range", "pnw cascades"],
  },
  {
    name: "North Cascades National Park, WA",
    detail: "High alpine terrain, glaciers, steep valleys, trails, and SAR access constraints",
    lat: 48.7718,
    lon: -121.2985,
    heightM: 22000,
    aliases: ["north cascades", "north cascades np", "noca"],
  },
  {
    name: "Olympic National Park, WA",
    detail: "Dense forest, mountains, river valleys, coastline, and SAR mission terrain",
    lat: 47.8021,
    lon: -123.6044,
    heightM: 22000,
    aliases: ["olympic", "olympic peninsula", "olympics"],
  },
  {
    name: "Mount Rainier National Park, WA",
    detail: "Volcanic alpine terrain, glaciers, roads, trails, and high-risk weather",
    lat: 46.8523,
    lon: -121.7603,
    heightM: 20000,
    aliases: ["rainier", "mount rainier", "mt rainier"],
  },
  {
    name: "Joshua Tree National Park, CA",
    detail: "Desert terrain, trails, dry washes, roads, climbing areas, and water scarcity",
    lat: 33.8734,
    lon: -115.9010,
    heightM: 18000,
    aliases: ["joshua tree", "joshua tree np", "jtnp", "joshu tree", "joshua"],
  },
  {
    name: "Fort Hunter Liggett, CA",
    detail: "Training area with rural roads, ridges, valleys, and access control",
    lat: 35.9730,
    lon: -121.2400,
    heightM: 18000,
    aliases: ["hunter liggett", "fhl"],
  },
  {
    name: "Fort Irwin / National Training Center, CA",
    detail: "Desert maneuver terrain, dry washes, roads, and range constraints",
    lat: 35.2627,
    lon: -116.6848,
    heightM: 26000,
    aliases: ["fort irwin", "ntc", "national training center"],
  },
  {
    name: "Camp Pendleton, CA",
    detail: "Coastal military terrain, roads, hills, and beach approaches",
    lat: 33.3178,
    lon: -117.3205,
    heightM: 17000,
    aliases: ["pendleton", "mcb camp pendleton"],
  },
  {
    name: "Yakima Training Center, WA",
    detail: "High-desert training terrain, ranges, roads, and ridgelines",
    lat: 46.6847,
    lon: -120.4531,
    heightM: 25000,
    aliases: ["yakima", "ytc"],
  },
  {
    name: "White Sands Missile Range, NM",
    detail: "Desert range terrain, restricted areas, roads, and dry lakebeds",
    lat: 32.3825,
    lon: -106.4795,
    heightM: 26000,
    aliases: ["white sands", "wsmr"],
  },
  {
    name: "Fort Liberty, NC",
    detail: "Installation and pine forest movement terrain",
    lat: 35.1415,
    lon: -79.0060,
    heightM: 16000,
    aliases: ["fort bragg", "liberty"],
  },
  {
    name: "Fort Moore, GA",
    detail: "Installation terrain, river corridors, roads, and training areas",
    lat: 32.3668,
    lon: -84.9693,
    heightM: 16000,
    aliases: ["fort benning", "moore"],
  },
  {
    name: "Fort Carson, CO",
    detail: "Front Range installation, foothills, roads, and mountain approaches",
    lat: 38.7375,
    lon: -104.7889,
    heightM: 18000,
    aliases: ["carson", "colorado springs"],
  },
  {
    name: "Joint Base Lewis-McChord, WA",
    detail: "Installation, forest, prairie, airfield, and road access context",
    lat: 47.1079,
    lon: -122.5769,
    heightM: 16000,
    aliases: ["jblm", "fort lewis", "mcchord"],
  },
  {
    name: "Washington, DC",
    detail: "Capital region urban infrastructure, waterways, and access constraints",
    lat: 38.9072,
    lon: -77.0369,
    heightM: 12000,
    aliases: ["dc", "district of columbia"],
  },
  {
    name: "Honolulu, HI",
    detail: "Island urban, volcanic ridges, coastline, and evacuation context",
    lat: 21.3099,
    lon: -157.8581,
    heightM: 13000,
    aliases: ["oahu", "pearl harbor"],
  },
  {
    name: "Anchorage, AK",
    detail: "Arctic/subarctic urban, mountain, river, and coastal terrain",
    lat: 61.2181,
    lon: -149.9003,
    heightM: 22000,
    aliases: ["alaska", "anchorage bowl"],
  },
];

const LOCATION_SEARCH_LIMIT = 6;
const LOCATION_SOURCE_PRIORITY = {
  "coordinate-query": 500,
  "google-places": 260,
  gazetteer: 180,
  "local-gazetteer": 180,
  "online-geocoder": 0,
};
const UTM_LATITUDE_BANDS = "CDEFGHJKLMNPQRSTUVWXX";
const MGRS_COLUMN_LETTER_SETS = ["ABCDEFGH", "JKLMNPQR", "STUVWXYZ"];
const MGRS_ROW_LETTER_SETS = ["ABCDEFGHJKLMNPQRSTUV", "FGHJKLMNPQRSTUVABCDE"];
const KEYWORD_EXPANSIONS = {
  route: ["routing", "navigate", "navigation", "path", "corridor", "approach"],
  patrol: ["movement", "move", "walk", "team", "operator"],
  water: ["hydration", "hydrate", "stream", "river", "spring", "creek", "wash", "well", "source", "watter"],
  terrain: ["terain", "topography", "elevation", "ground", "landform"],
  slope: ["steep", "grade", "incline", "cliff", "exposed", "exposure"],
  cover: ["concealment", "conceal", "canopy", "shade", "vegetation", "brush"],
  hazard: ["hazzard", "risk", "danger", "closure", "blocked", "unsafe"],
  signal: ["comms", "communications", "radio", "relay", "antenna", "line of sight", "los"],
  imagery: ["image", "satellite", "satelite", "aerial", "visual", "photo"],
  sar: ["search", "rescue", "missing", "lost", "hasty"],
  access: ["private", "restricted", "boundary", "parcel", "permission", "legal"],
};

const FALLBACK_SOURCE_CATALOG = [
  {
    id: "esri_world_imagery",
    name: "Esri World Imagery",
    provider: "Esri ArcGIS Online",
    category: "imagery",
    purpose: "Optional licensed imagery stream when an Esri account is available.",
    stream_status: "streamable",
    download_status: "export-tiles-with-account",
    stream_layer: "esri",
  },
  {
    id: "cesium_world_imagery",
    name: "Cesium World Imagery",
    provider: "Cesium ion",
    category: "imagery",
    purpose: "Token-backed imagery preview stream using the available Cesium token.",
    stream_status: "streamable-with-token",
    download_status: "stream-only-no-offline-copy",
    stream_layer: "ion-satellite",
  },
  {
    id: "cesium_ion_archive",
    name: "Cesium ion Offline Archive",
    provider: "Cesium ion",
    category: "imagery-terrain-archive",
    purpose: "Licensed Cesium ion archive or AO clip downloaded to the Jetson for local preview and metadata queries.",
    stream_status: "not-streamed",
    download_status: "download-required",
  },
  {
    id: "usgs_imagery_only",
    name: "USGS Imagery Only",
    provider: "USGS The National Map",
    category: "imagery",
    purpose: "Free U.S. imagery tile stream and AO tile cache for offline visual context.",
    stream_status: "streamable",
    download_status: "cache-tiles",
    stream_layer: "usgs-imagery",
  },
  {
    id: "nrl_naip_conus",
    name: "NRL NAIP (CONUS)",
    provider: "NRL / USDA NAIP",
    category: "imagery",
    purpose: "Free CONUS NAIP tile stream from the WinTAK imagery source folder for high-detail visual review.",
    stream_status: "streamable",
    download_status: "cache-tiles",
  },
  {
    id: "esri_world_elevation",
    name: "Esri World Elevation Terrain",
    provider: "Esri ArcGIS Online / Living Atlas",
    category: "terrain",
    purpose: "Primary queryable terrain source for DEM export, slope, hydrology, cost surfaces, and viewshed.",
    stream_status: "queryable-online",
    download_status: "download-required",
  },
  {
    id: "cesium_world_terrain",
    name: "Cesium World Terrain",
    provider: "Cesium ion",
    category: "terrain-display",
    purpose: "Streamable 3D terrain preview for landform awareness.",
    stream_status: "streamable-with-token",
    download_status: "stream-only-no-offline-copy",
    stream_layer: "cesium-world",
  },
  {
    id: "osm_basemap",
    name: "OpenStreetMap Basemap",
    provider: "OpenStreetMap contributors",
    category: "basemap",
    purpose: "Streamable orientation map for roads, trails, and place names.",
    stream_status: "streamable",
    download_status: "manifest-only",
    stream_layer: "osm",
  },
  {
    id: "osm_extract",
    name: "OpenStreetMap PBF Extract",
    provider: "OpenStreetMap / regional extract",
    category: "vector",
    purpose: "Local server extract for roads, trails, waterways, buildings, POIs, and barriers.",
    stream_status: "not-streamed",
    download_status: "download-required",
  },
  {
    id: "usgs_3dep",
    name: "USGS 3DEP DEM",
    provider: "USGS",
    category: "terrain",
    purpose: "U.S. elevation dataset for slope, hydrology, viewshed, and cost surfaces.",
    stream_status: "not-streamed",
    download_status: "download-required",
  },
  {
    id: "copernicus_dem",
    name: "Copernicus DEM GLO-30 COG",
    provider: "Copernicus",
    category: "terrain",
    purpose: "No-account public S3 COG terrain tiles for slope, viewshed, and terrain-cost analysis.",
    stream_status: "not-streamed",
    download_status: "download-required",
  },
  {
    id: "dted_earth_explorer",
    name: "DTED from USGS EarthExplorer",
    provider: "USGS EarthExplorer",
    category: "terrain",
    purpose: "Operator-staged DTED cells imported to the Jetson and converted to GeoTIFF when GDAL is available.",
    stream_status: "not-streamed",
    download_status: "manual-stage-import",
  },
  {
    id: "nlcd",
    name: "USGS Annual NLCD",
    provider: "USGS",
    category: "land-cover",
    purpose: "U.S. land-cover baseline for surface friction, wetlands, and vegetation context.",
    stream_status: "not-streamed",
    download_status: "download-required",
  },
  {
    id: "esa_worldcover",
    name: "ESA WorldCover",
    provider: "ESA",
    category: "land-cover",
    purpose: "Global land-cover baseline for off-road friction and vegetation screening.",
    stream_status: "not-streamed",
    download_status: "download-required",
  },
  {
    id: "usgs_3dhp",
    name: "USGS 3D Hydrography Program / NHD",
    provider: "USGS",
    category: "hydrography",
    purpose: "U.S. hydrography for streams, rivers, water bodies, and crossing context.",
    stream_status: "not-streamed",
    download_status: "download-required",
  },
  {
    id: "hydrosheds",
    name: "HydroSHEDS / HydroRIVERS / HydroLAKES",
    provider: "HydroSHEDS",
    category: "hydrography",
    purpose: "Global hydrography baseline for water-source and drainage queries.",
    stream_status: "not-streamed",
    download_status: "download-required",
  },
  {
    id: "nwis",
    name: "USGS NWIS",
    provider: "USGS",
    category: "water-observation",
    purpose: "Cached observations for stream gauge and water-availability confidence.",
    stream_status: "not-streamed",
    download_status: "cache-feed",
  },
  {
    id: "sentinel_2",
    name: "Sentinel-2 Multispectral",
    provider: "ESA Copernicus / Element 84 Earth Search",
    category: "imagery-analysis",
    purpose: "Free downloadable COG imagery for offline visual context, vegetation, water, burn, and surface-condition indices.",
    stream_status: "not-streamed",
    download_status: "download-required",
  },
  {
    id: "naip",
    name: "NAIP Aerial Imagery",
    provider: "USDA",
    category: "imagery-analysis",
    purpose: "High-resolution U.S. aerial imagery for detailed AO review and feature extraction.",
    stream_status: "not-streamed",
    download_status: "download-required",
  },
  {
    id: "sentinel_1_sar",
    name: "Sentinel-1 SAR",
    provider: "ESA Copernicus",
    category: "imagery-analysis",
    purpose: "Radar imagery for cloud/night/flood surface observation.",
    stream_status: "not-streamed",
    download_status: "download-required",
  },
  {
    id: "nasa_firms",
    name: "NASA FIRMS",
    provider: "NASA",
    category: "hazards",
    purpose: "Active fire and hotspot feed for wildfire route risk.",
    stream_status: "not-streamed",
    download_status: "cache-feed",
  },
  {
    id: "noaa_alerts",
    name: "NOAA / NWS Alerts",
    provider: "NOAA",
    category: "hazards",
    purpose: "Weather watches, warnings, and advisories for package-time hazards.",
    stream_status: "not-streamed",
    download_status: "cache-feed",
  },
  {
    id: "fema_flood",
    name: "FEMA Flood Products",
    provider: "FEMA",
    category: "hazards",
    purpose: "U.S. floodplain and flood hazard context for route risk.",
    stream_status: "not-streamed",
    download_status: "download-required",
  },
  {
    id: "pad_us",
    name: "PAD-US Protected Areas",
    provider: "USGS",
    category: "boundaries-access",
    purpose: "U.S. protected-area and management boundaries for access constraints.",
    stream_status: "not-streamed",
    download_status: "download-required",
  },
  {
    id: "parcels_boundaries",
    name: "Parcels / Local Boundaries",
    provider: "County or local GIS",
    category: "boundaries-access",
    purpose: "Ownership and parcel boundaries for restricted or private-land movement.",
    stream_status: "not-streamed",
    download_status: "download-required",
  },
  {
    id: "viewshed_surfaces",
    name: "DEM-Derived Viewshed Surfaces",
    provider: "Derived from package DEM",
    category: "derived",
    purpose: "Line-of-sight products for communications, signaling, and observation planning.",
    stream_status: "derived",
    download_status: "derived-after-ingest",
  },
  {
    id: "fcc_towers",
    name: "FCC Antenna / Tower Data",
    provider: "FCC",
    category: "communications",
    purpose: "Tower locations for communications planning context.",
    stream_status: "not-streamed",
    download_status: "download-required",
  },
  {
    id: "osm_towers",
    name: "OSM Towers, Peaks, Lookouts",
    provider: "OpenStreetMap",
    category: "communications",
    purpose: "Mapped towers, peaks, masts, lookouts, and high-ground candidates.",
    stream_status: "not-streamed",
    download_status: "derived-from-osm",
  },
];

const CHAT_AUTOSCROLL_THRESHOLD_PX = 80;

function setChip(node, text, tone = "") {
  node.textContent = text;
  node.className = `chip${tone ? ` ${tone}` : ""}`;
}

function setModelProviderButton(text, tone = "") {
  els.modelProviderBtn.textContent = text;
  els.modelProviderBtn.className = `chip chip-button${tone ? ` ${tone}` : ""}`;
}

function setAtakAgentButton(text, tone = "") {
  els.atakAgentBtn.textContent = text;
  els.atakAgentBtn.className = `chip chip-button${tone ? ` ${tone}` : ""}`;
}

function getErrorMessage(error) {
  return error instanceof Error ? error.message : String(error);
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `${response.status} ${response.statusText}`);
  }
  return data;
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  const units = ["B", "KB", "MB", "GB", "TB"];
  let scaled = Math.max(0, bytes);
  let index = 0;
  while (scaled >= 1024 && index < units.length - 1) {
    scaled /= 1024;
    index += 1;
  }
  const precision = index <= 1 ? 0 : 1;
  return `${scaled.toFixed(precision)} ${units[index]}`;
}

function renderJetsonStorage(storage = state.jetsonStorage, estimateBytes = null, storageFit = true, warning = "") {
  if (!storage) {
    els.storageRoot.textContent = "Jetson storage unavailable";
    setChip(els.storageFitChip, "Unknown", "warn");
    return;
  }
  state.jetsonStorage = storage;
  const total = Number(storage.total_bytes || 0);
  const used = Number(storage.used_bytes || 0);
  const reserved = Number(storage.reserved_bytes || 0);
  const free = Number(storage.free_bytes || 0);
  const usable = Number(storage.usable_bytes || 0);
  const estimate = Number(estimateBytes || 0);
  const usedPct = total > 0 ? Math.min(100, (used / total) * 100) : 0;
  const reservePct = total > 0 ? Math.min(100, (reserved / total) * 100) : 0;

  els.storageRoot.textContent = storage.package_root || "Jetson package root";
  els.storageFree.textContent = formatBytes(free);
  els.storageUsable.textContent = formatBytes(usable);
  els.storageReserve.textContent = formatBytes(reserved);
  els.storageEstimate.textContent = estimate ? formatBytes(estimate) : "--";
  els.storageMeterUsed.style.width = `${usedPct}%`;
  els.storageMeterReserve.style.left = `${Math.max(0, 100 - reservePct)}%`;
  els.storageMeterReserve.style.width = `${reservePct}%`;

  if (estimate && !storageFit) {
    setChip(els.storageFitChip, "No room", "bad");
    els.storageRoot.textContent = warning || "Package estimate exceeds Jetson usable storage";
  } else if (estimate) {
    setChip(els.storageFitChip, "Fits", "good");
  } else {
    setChip(els.storageFitChip, "Ready", usable > 0 ? "good" : "warn");
  }
}

async function loadJetsonStorage() {
  try {
    const storage = await fetchJson("/api/storage");
    renderJetsonStorage(storage);
    return storage;
  } catch (error) {
    els.storageRoot.textContent = getErrorMessage(error);
    setChip(els.storageFitChip, "Storage error", "bad");
    return null;
  }
}

function normalizeSearchText(value) {
  return value.trim().toLowerCase().replace(/[^a-z0-9.+-]+/g, " ").replace(/\s+/g, " ");
}

function getMatchTokens(value) {
  return normalizeSearchText(value).split(" ").filter(Boolean);
}

function editDistance(a, b) {
  const left = a || "";
  const right = b || "";
  if (!left.length) {
    return right.length;
  }
  if (!right.length) {
    return left.length;
  }

  const previous = Array.from({ length: right.length + 1 }, (_, index) => index);
  const current = Array.from({ length: right.length + 1 }, () => 0);
  for (let i = 1; i <= left.length; i += 1) {
    current[0] = i;
    for (let j = 1; j <= right.length; j += 1) {
      const cost = left[i - 1] === right[j - 1] ? 0 : 1;
      current[j] = Math.min(
        current[j - 1] + 1,
        previous[j] + 1,
        previous[j - 1] + cost,
      );
    }
    for (let j = 0; j <= right.length; j += 1) {
      previous[j] = current[j];
    }
  }
  return previous[right.length];
}

function tokenLooksLike(token, target) {
  if (token === target) {
    return true;
  }
  if (token.length < 4 || target.length < 4) {
    return false;
  }
  if (token.startsWith(target) || target.startsWith(token)) {
    return true;
  }
  const distance = editDistance(token, target);
  return distance <= Math.max(1, Math.floor(Math.max(token.length, target.length) * 0.28));
}

function cleanLocationSearchQuery(query) {
  let cleaned = query.trim().replace(/\s+/g, " ");
  let previous = "";
  while (cleaned && cleaned !== previous) {
    previous = cleaned;
    cleaned = cleaned.replace(LOCATION_INTENT_PREFIX_PATTERN, "").trim();
  }
  return cleaned;
}

function parseGoogleMapsCoordinateQuery(query) {
  const patterns = [
    /!3d([+-]?\d+(?:\.\d+)?)!4d([+-]?\d+(?:\.\d+)?)/i,
    /@([+-]?\d+(?:\.\d+)?),([+-]?\d+(?:\.\d+)?)/i,
    /[?&](?:q|ll|center)=([+-]?\d+(?:\.\d+)?),([+-]?\d+(?:\.\d+)?)/i,
  ];
  for (const pattern of patterns) {
    const match = query.match(pattern);
    if (!match) {
      continue;
    }
    const lat = Number(match[1]);
    const lon = Number(match[2]);
    if (Number.isFinite(lat) && Number.isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180) {
      return {
        name: `Coordinates ${lat.toFixed(5)}, ${lon.toFixed(5)}`,
        detail: "Parsed from Google Maps link or coordinate query",
        lat,
        lon,
        heightM: 12000,
        source: "coordinate-query",
        score: LOCATION_SOURCE_PRIORITY["coordinate-query"],
      };
    }
  }
  return null;
}

function parseCoordinateQuery(query) {
  const trimmed = cleanLocationSearchQuery(query);
  if (!trimmed) {
    return null;
  }

  const googleMapsCoordinate = parseGoogleMapsCoordinateQuery(trimmed);
  if (googleMapsCoordinate) {
    return googleMapsCoordinate;
  }

  if (/^https?:\/\//i.test(trimmed)) {
    return null;
  }

  const numbers = trimmed.match(/[+-]?\d+(?:\.\d+)?/g);
  if (!numbers || numbers.length < 2) {
    return null;
  }

  let lat = Number(numbers[0]);
  let lon = Number(numbers[1]);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
    return null;
  }

  if (Math.abs(lat) > 90 && Math.abs(lon) <= 90) {
    [lat, lon] = [lon, lat];
  }

  const upper = trimmed.toUpperCase();
  if (/\d(?:\.\d+)?\s*S\b/.test(upper)) {
    lat = -Math.abs(lat);
  } else if (/\d(?:\.\d+)?\s*N\b/.test(upper)) {
    lat = Math.abs(lat);
  }
  if (/\d(?:\.\d+)?\s*W\b/.test(upper) || upper.includes(" W")) {
    lon = -Math.abs(lon);
  } else if (/\d(?:\.\d+)?\s*E\b/.test(upper) || upper.includes(" E")) {
    lon = Math.abs(lon);
  }

  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) {
    return null;
  }

  return {
    name: `Coordinates ${lat.toFixed(5)}, ${lon.toFixed(5)}`,
    detail: "Parsed decimal latitude/longitude",
    lat,
    lon,
    heightM: 12000,
    source: "coordinate-query",
  };
}

function scoreLocationCandidate(candidate, query) {
  const normalizedQuery = normalizeSearchText(cleanLocationSearchQuery(query));
  if (!normalizedQuery) {
    return 0;
  }

  const name = normalizeSearchText(candidate.name);
  const detail = normalizeSearchText(candidate.detail || "");
  const aliases = (candidate.aliases || []).map((alias) => normalizeSearchText(alias));
  let score = 0;

  if (name === normalizedQuery) {
    score += 120;
  } else if (name.startsWith(normalizedQuery)) {
    score += 95;
  } else if (name.includes(normalizedQuery)) {
    score += 70;
  }

  for (const alias of aliases) {
    if (alias === normalizedQuery) {
      score += 145;
    } else if (alias.startsWith(normalizedQuery)) {
      score += 85;
    } else if (alias.includes(normalizedQuery)) {
      score += 60;
    }
  }

  const haystackTokens = getMatchTokens(`${candidate.name} ${candidate.detail || ""} ${(candidate.aliases || []).join(" ")}`);
  const terms = normalizedQuery.split(" ").filter(Boolean);
  for (const term of terms) {
    if (name.includes(term)) {
      score += 15;
    }
    if (detail.includes(term)) {
      score += 8;
    }
    if (aliases.some((alias) => alias.includes(term))) {
      score += 12;
    }
    if (haystackTokens.some((token) => tokenLooksLike(token, term))) {
      score += 18;
    }
  }

  return score;
}

function getLocationSearchSuggestions(query) {
  const cleanedQuery = cleanLocationSearchQuery(query);
  const coordinate = parseCoordinateQuery(cleanedQuery);
  const scored = LOCATION_GAZETTEER
    .map((candidate) => {
      const matchScore = scoreLocationCandidate(candidate, cleanedQuery);
      return {
        ...candidate,
        source: "gazetteer",
        score: matchScore > 0 ? matchScore + LOCATION_SOURCE_PRIORITY.gazetteer : 0,
      };
    })
    .filter((candidate) => candidate.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, LOCATION_SEARCH_LIMIT);

  if (coordinate) {
    return [coordinate, ...scored].slice(0, LOCATION_SEARCH_LIMIT);
  }
  return scored;
}

function normalizeServerLocationSuggestion(suggestion) {
  const serverScore = Number(suggestion.score);
  return {
    name: suggestion.name,
    detail: suggestion.detail || `${Number(suggestion.lat).toFixed(5)}, ${Number(suggestion.lon).toFixed(5)}`,
    lat: Number(suggestion.lat),
    lon: Number(suggestion.lon),
    heightM: Number(suggestion.height_m || suggestion.heightM || 12000),
    source: suggestion.source || "online-geocoder",
    score: Number.isFinite(serverScore) ? serverScore : 0,
  };
}

function scoreMergedLocation(match, query) {
  const providedScore = Number(match.score);
  if (Number.isFinite(providedScore) && providedScore > 0) {
    return providedScore;
  }
  return scoreLocationCandidate(match, query)
    + (LOCATION_SOURCE_PRIORITY[match.source] || 0);
}

function mergeLocationSuggestions(primaryMatches, incomingMatches, query = "") {
  const merged = [];
  const seen = new Set();
  for (const match of [...primaryMatches, ...incomingMatches]) {
    if (!Number.isFinite(match.lat) || !Number.isFinite(match.lon)) {
      continue;
    }
    const key = `${Math.round(match.lat * 1000)}:${Math.round(match.lon * 1000)}:${match.name.toLowerCase()}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    merged.push({
      ...match,
      score: scoreMergedLocation(match, query),
    });
  }
  return merged
    .sort((a, b) => {
      const scoreDelta = scoreMergedLocation(b, query) - scoreMergedLocation(a, query);
      if (scoreDelta !== 0) {
        return scoreDelta;
      }
      return (LOCATION_SOURCE_PRIORITY[b.source] || 0) - (LOCATION_SOURCE_PRIORITY[a.source] || 0);
    })
    .slice(0, LOCATION_SEARCH_LIMIT);
}

function buildLocationSearchUrl(query) {
  const params = new URLSearchParams({ q: cleanLocationSearchQuery(query) });
  const center = getMapCenterPoint();
  if (center) {
    params.set("lat", center.lat.toFixed(6));
    params.set("lon", center.lon.toFixed(6));
  }

  const bounds = buildMapContext().view_bounds;
  if (bounds) {
    params.set("west", bounds.west.toFixed(6));
    params.set("south", bounds.south.toFixed(6));
    params.set("east", bounds.east.toFixed(6));
    params.set("north", bounds.north.toFixed(6));
  }
  return `/api/location-search?${params.toString()}`;
}

function googleMapsSearchUrl(query) {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(cleanLocationSearchQuery(query))}`;
}

async function fetchLocationSearchSuggestions(query) {
  const cleanedQuery = cleanLocationSearchQuery(query);
  if (cleanedQuery.length < 1) {
    return { suggestions: [], detail: "" };
  }
  const data = await fetchJson(buildLocationSearchUrl(cleanedQuery));
  return {
    suggestions: Array.isArray(data.suggestions)
      ? data.suggestions.map(normalizeServerLocationSuggestion)
      : [],
    detail: data.detail || "",
    online: Boolean(data.online),
  };
}

async function refreshOnlineLocationSuggestions(query, requestId, localMatches) {
  try {
    const cleanedQuery = cleanLocationSearchQuery(query);
    const result = await fetchLocationSearchSuggestions(cleanedQuery);
    if (requestId !== state.locationSearchRequestId) {
      return;
    }
    state.locationSearchDetail = result.detail || "";
    const serverMatches = result.suggestions || [];
    state.locationSearchMatches = mergeLocationSuggestions(localMatches, serverMatches, cleanedQuery);
    if (state.locationSearchMatches.length) {
      renderLocationSearchSuggestions();
    } else {
      renderLocationSearchEmpty(cleanedQuery, state.locationSearchDetail);
    }
  } catch (_error) {
    if (requestId === state.locationSearchRequestId && !state.locationSearchMatches.length) {
      state.locationSearchDetail = getErrorMessage(_error);
      renderLocationSearchEmpty(query, state.locationSearchDetail);
    }
  }
}

function setLocationSearchOpen(open) {
  els.locationSearchSuggestions.classList.toggle("hidden", !open);
  if (!open) {
    state.activeLocationSearchIndex = -1;
  }
}

function setActiveLocationSuggestion(index) {
  const maxIndex = state.locationSearchMatches.length - 1;
  state.activeLocationSearchIndex = maxIndex < 0 ? -1 : clampNumber(index, 0, maxIndex);
  const options = els.locationSearchSuggestions.querySelectorAll("[data-location-index]");
  options.forEach((option) => {
    const isActive = Number(option.dataset.locationIndex) === state.activeLocationSearchIndex;
    option.classList.toggle("active", isActive);
    option.setAttribute("aria-selected", String(isActive));
  });
}

function renderLocationSearchStatus(message, query = "") {
  els.locationSearchSuggestions.replaceChildren();
  const status = document.createElement("div");
  status.className = "location-suggestion-status";
  const text = document.createElement("span");
  text.textContent = message;
  status.appendChild(text);
  const cleanedQuery = cleanLocationSearchQuery(query);
  if (cleanedQuery) {
    const externalLink = document.createElement("a");
    externalLink.className = "location-suggestion-external";
    externalLink.href = googleMapsSearchUrl(cleanedQuery);
    externalLink.target = "_blank";
    externalLink.rel = "noreferrer";
    externalLink.textContent = "Open Google Maps search";
    status.appendChild(externalLink);
  }
  els.locationSearchSuggestions.appendChild(status);
  setLocationSearchOpen(true);
}

function renderLocationSearchLoading(query) {
  const cleanedQuery = cleanLocationSearchQuery(query);
  renderLocationSearchStatus(`Searching ${cleanedQuery}...`, cleanedQuery);
}

function renderLocationSearchEmpty(query, detail = "") {
  const cleanedQuery = cleanLocationSearchQuery(query);
  const detailText = detail ? ` ${detail}` : "";
  renderLocationSearchStatus(
    cleanedQuery
      ? `No in-map coordinate match for "${cleanedQuery}".${detailText}`
      : "Enter a mission location, coordinates, or KML/KMZ overlay.",
    cleanedQuery,
  );
}

function renderLocationSearchSuggestions() {
  els.locationSearchSuggestions.replaceChildren();
  if (!state.locationSearchMatches.length) {
    setLocationSearchOpen(false);
    return;
  }

  state.locationSearchMatches.forEach((match, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "location-suggestion";
    button.dataset.locationIndex = String(index);
    button.setAttribute("role", "option");
    button.setAttribute("aria-selected", "false");

    const name = document.createElement("span");
    name.className = "location-suggestion-name";
    name.textContent = match.name;
    const detail = document.createElement("span");
    detail.className = "location-suggestion-detail";
    detail.textContent = match.detail || `${match.lat.toFixed(5)}, ${match.lon.toFixed(5)}`;
    button.append(name, detail);

    button.addEventListener("pointerenter", () => setActiveLocationSuggestion(index));
    button.addEventListener("click", () => {
      state.activeLocationSearchIndex = index;
      flyToLocationSuggestion(match);
    });

    els.locationSearchSuggestions.appendChild(button);
  });

  setLocationSearchOpen(true);
  setActiveLocationSuggestion(0);
}

function markMapLocationFocused(label, source) {
  state.mapFocusLabel = label || "";
  state.mapFocusSource = source || "";
  state.mapLocationConfirmed = Boolean(label);
}

function clearMapLocationFocus() {
  markMapLocationFocused("", "");
}

function flyToLocationSuggestion(suggestion) {
  if (!state.viewer) {
    els.requestStatus.textContent = "Location search unavailable until the map is ready.";
    return;
  }

  const heightM = suggestion.heightM || Math.max(state.config?.default_height_m || 12000, 9000);
  markMapLocationFocused(suggestion.name, suggestion.source || "location-search");
  state.viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(suggestion.lon, suggestion.lat, heightM),
    duration: 1.1,
    complete: updateCameraText,
  });
  els.locationSearchInput.value = suggestion.name;
  els.requestStatus.textContent = `Map focused: ${suggestion.name}`;
  setLocationSearchOpen(false);
}

async function commitLocationSearch() {
  const query = cleanLocationSearchQuery(els.locationSearchInput.value);
  window.clearTimeout(state.locationSearchTimer);
  state.locationSearchRequestId += 1;
  state.locationSearchDetail = "";

  const coordinate = parseCoordinateQuery(query);
  if (coordinate) {
    flyToLocationSuggestion(coordinate);
    return;
  }

  if (query.length < 1) {
    renderLocationSearchEmpty(query);
    return;
  }

  const localMatches = getLocationSearchSuggestions(query);
  const selectedBeforeFetch = state.activeLocationSearchIndex >= 0
    ? state.locationSearchMatches[state.activeLocationSearchIndex]
    : null;
  if (localMatches.length) {
    state.locationSearchMatches = localMatches;
    renderLocationSearchSuggestions();
  } else {
    renderLocationSearchLoading(query);
  }

  let serverMatches = [];
  try {
    const result = await fetchLocationSearchSuggestions(query);
    serverMatches = result.suggestions || [];
    state.locationSearchDetail = result.detail || "";
  } catch (error) {
    serverMatches = [];
    state.locationSearchDetail = getErrorMessage(error);
  }

  const matches = mergeLocationSuggestions(localMatches, serverMatches, query);
  state.locationSearchMatches = matches;
  const selectedKey = selectedBeforeFetch
    ? `${Math.round(selectedBeforeFetch.lat * 1000)}:${Math.round(selectedBeforeFetch.lon * 1000)}:${selectedBeforeFetch.name.toLowerCase()}`
    : "";
  const suggestion = selectedKey
    ? matches.find((match) => (
      `${Math.round(match.lat * 1000)}:${Math.round(match.lon * 1000)}:${match.name.toLowerCase()}`
    ) === selectedKey) || selectedBeforeFetch
    : matches[0];

  if (!suggestion) {
    els.requestStatus.textContent = "Location not resolved. Try a more specific place, coordinates, or KML/KMZ.";
    renderLocationSearchEmpty(query, state.locationSearchDetail);
    return;
  }

  if (matches.length) {
    renderLocationSearchSuggestions();
  }
  flyToLocationSuggestion(suggestion);
}

function onLocationSearchInput() {
  const query = cleanLocationSearchQuery(els.locationSearchInput.value);
  window.clearTimeout(state.locationSearchTimer);
  state.locationSearchRequestId += 1;
  state.locationSearchDetail = "";
  if (query.length < 1) {
    state.locationSearchMatches = [];
    setLocationSearchOpen(false);
    return;
  }
  const localMatches = getLocationSearchSuggestions(query);
  state.locationSearchMatches = localMatches;
  if (localMatches.length) {
    renderLocationSearchSuggestions();
  } else {
    renderLocationSearchLoading(query);
  }
  const requestId = state.locationSearchRequestId;
  state.locationSearchTimer = window.setTimeout(() => {
    void refreshOnlineLocationSuggestions(query, requestId, localMatches);
  }, 180);
}

function onLocationSearchKeyDown(event) {
  if (event.key === "Escape") {
    setLocationSearchOpen(false);
    return;
  }
  if (event.key === "Enter") {
    event.preventDefault();
    void commitLocationSearch();
    return;
  }
  if (!state.locationSearchMatches.length) {
    return;
  }
  if (event.key === "ArrowDown") {
    event.preventDefault();
    const nextIndex = state.activeLocationSearchIndex + 1;
    setActiveLocationSuggestion(nextIndex > state.locationSearchMatches.length - 1 ? 0 : nextIndex);
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    const nextIndex = state.activeLocationSearchIndex - 1;
    setActiveLocationSuggestion(nextIndex < 0 ? state.locationSearchMatches.length - 1 : nextIndex);
  }
}

function onLocationSearchSubmit(event) {
  event.preventDefault();
  void commitLocationSearch();
}

function getMapCenterPoint() {
  if (!state.viewer) {
    return null;
  }

  const rectangle = state.viewer.camera.computeViewRectangle(state.viewer.scene.globe.ellipsoid);
  if (rectangle) {
    const west = Cesium.Math.toDegrees(rectangle.west);
    const east = Cesium.Math.toDegrees(rectangle.east);
    const south = Cesium.Math.toDegrees(rectangle.south);
    const north = Cesium.Math.toDegrees(rectangle.north);
    const centerLon = west <= east ? (west + east) / 2 : ((west + east + 360) / 2) % 360;
    return {
      lat: clampNumber((south + north) / 2, -89.9999, 89.9999),
      lon: centerLon > 180 ? centerLon - 360 : centerLon,
    };
  }

  const cartographic = state.viewer.camera.positionCartographic;
  return {
    lat: Cesium.Math.toDegrees(cartographic.latitude),
    lon: Cesium.Math.toDegrees(cartographic.longitude),
  };
}

function getUtmZone(lat, lon) {
  let zone = Math.floor((lon + 180) / 6) + 1;
  zone = clampNumber(zone, 1, 60);
  if (lat >= 56 && lat < 64 && lon >= 3 && lon < 12) {
    zone = 32;
  }
  if (lat >= 72 && lat < 84) {
    if (lon >= 0 && lon < 9) {
      zone = 31;
    } else if (lon >= 9 && lon < 21) {
      zone = 33;
    } else if (lon >= 21 && lon < 33) {
      zone = 35;
    } else if (lon >= 33 && lon < 42) {
      zone = 37;
    }
  }
  return zone;
}

function getUtmLatitudeBand(lat) {
  if (lat >= 84) {
    return "X";
  }
  if (lat < -80) {
    return "C";
  }
  const index = clampNumber(Math.floor((lat + 80) / 8), 0, UTM_LATITUDE_BANDS.length - 1);
  return UTM_LATITUDE_BANDS[index];
}

function latLonToUtm(lat, lon) {
  const a = 6378137.0;
  const f = 1 / 298.257223563;
  const k0 = 0.9996;
  const eSq = f * (2 - f);
  const ePrimeSq = eSq / (1 - eSq);
  const zone = getUtmZone(lat, lon);
  const lonOrigin = (zone - 1) * 6 - 180 + 3;
  const latRad = Cesium.Math.toRadians(lat);
  const lonRad = Cesium.Math.toRadians(lon);
  const lonOriginRad = Cesium.Math.toRadians(lonOrigin);
  const sinLat = Math.sin(latRad);
  const cosLat = Math.cos(latRad);
  const tanLat = Math.tan(latRad);
  const n = a / Math.sqrt(1 - eSq * sinLat * sinLat);
  const t = tanLat * tanLat;
  const c = ePrimeSq * cosLat * cosLat;
  const aa = cosLat * (lonRad - lonOriginRad);
  const m = a * (
    (1 - eSq / 4 - (3 * eSq * eSq) / 64 - (5 * eSq * eSq * eSq) / 256) * latRad
    - ((3 * eSq) / 8 + (3 * eSq * eSq) / 32 + (45 * eSq * eSq * eSq) / 1024) * Math.sin(2 * latRad)
    + ((15 * eSq * eSq) / 256 + (45 * eSq * eSq * eSq) / 1024) * Math.sin(4 * latRad)
    - ((35 * eSq * eSq * eSq) / 3072) * Math.sin(6 * latRad)
  );

  let easting = k0 * n * (
    aa
    + ((1 - t + c) * aa ** 3) / 6
    + ((5 - 18 * t + t * t + 72 * c - 58 * ePrimeSq) * aa ** 5) / 120
  ) + 500000.0;
  let northing = k0 * (
    m
    + n * tanLat * (
      (aa * aa) / 2
      + ((5 - t + 9 * c + 4 * c * c) * aa ** 4) / 24
      + ((61 - 58 * t + t * t + 600 * c - 330 * ePrimeSq) * aa ** 6) / 720
    )
  );

  if (lat < 0) {
    northing += 10000000.0;
  }

  easting = Math.round(easting);
  northing = Math.round(northing);
  return {
    zone,
    band: getUtmLatitudeBand(lat),
    easting,
    northing,
  };
}

function utmToMgrs(utm) {
  const columnSet = MGRS_COLUMN_LETTER_SETS[(utm.zone - 1) % MGRS_COLUMN_LETTER_SETS.length];
  const rowSet = MGRS_ROW_LETTER_SETS[(utm.zone - 1) % MGRS_ROW_LETTER_SETS.length];
  const columnIndex = clampNumber(Math.floor(utm.easting / 100000) - 1, 0, columnSet.length - 1);
  const rowIndex = Math.floor(utm.northing / 100000) % rowSet.length;
  const square = `${columnSet[columnIndex]}${rowSet[rowIndex]}`;
  const easting = (utm.easting % 100000).toString().padStart(5, "0");
  const northing = (utm.northing % 100000).toString().padStart(5, "0");
  return `${utm.zone}${utm.band} ${square} ${easting} ${northing}`;
}

function latLonToMgrs(lat, lon) {
  if (lat < -80 || lat >= 84) {
    return "MGRS unavailable";
  }
  return utmToMgrs(latLonToUtm(lat, lon));
}

function updateCenterGrid() {
  const center = getMapCenterPoint();
  if (!center) {
    els.centerGridValue.textContent = "--";
    els.centerGridLatLon.textContent = "--";
    return;
  }

  els.centerGridValue.textContent = `MGRS ${latLonToMgrs(center.lat, center.lon)}`;
  els.centerGridLatLon.textContent = `${center.lat.toFixed(5)}, ${center.lon.toFixed(5)}`;
}

function isChatPinnedToBottom() {
  const distanceFromBottom = els.chatLog.scrollHeight
    - els.chatLog.scrollTop
    - els.chatLog.clientHeight;
  return distanceFromBottom <= CHAT_AUTOSCROLL_THRESHOLD_PX;
}

function scrollChatToBottom() {
  els.chatLog.scrollTop = els.chatLog.scrollHeight;
}

function maybeScrollChatToBottom(shouldScroll = isChatPinnedToBottom()) {
  if (shouldScroll) {
    scrollChatToBottom();
  }
}

function appendMessage(role, body, meta = "") {
  const shouldFollowNewMessage = isChatPinnedToBottom();
  const article = document.createElement("article");
  article.className = `chat-message ${role === "user" ? "user-message" : "assistant-message"}`;

  const roleNode = document.createElement("div");
  roleNode.className = "message-role";
  roleNode.textContent = role;

  const bodyNode = document.createElement("div");
  bodyNode.className = "message-body";
  if (role === "assistant") {
    bodyNode.classList.add("markdown-body");
  }
  renderMessageBody(bodyNode, body, role === "assistant");

  article.append(roleNode, bodyNode);
  if (meta) {
    const metaNode = document.createElement("div");
    metaNode.className = "message-meta";
    metaNode.textContent = meta;
    article.append(metaNode);
  }

  els.chatLog.appendChild(article);
  state.chatCount += 1;
  els.chatMeta.textContent = `${state.chatCount} messages`;
  maybeScrollChatToBottom(shouldFollowNewMessage);
  return {
    article,
    bodyNode,
    metaNode: article.querySelector(".message-meta"),
  };
}

function isMarkdownBlockStart(line) {
  return /^```/.test(line)
    || /^(#{1,4})\s+/.test(line)
    || /^(\d+)\.\s+/.test(line)
    || /^[-*]\s+/.test(line)
    || /^(-{3,}|\*{3,})$/.test(line.trim());
}

function appendInlineMarkdown(parent, text) {
  const tokenPattern = /(`[^`]+`|\*\*[\s\S]+?\*\*|\*[^*\n]+\*|\[[^\]]+\]\((https?:\/\/[^)\s]+)\))/g;
  let lastIndex = 0;

  for (const match of text.matchAll(tokenPattern)) {
    if (match.index > lastIndex) {
      parent.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
    }

    const token = match[0];
    if (token.startsWith("`")) {
      const code = document.createElement("code");
      code.textContent = token.slice(1, -1);
      parent.appendChild(code);
    } else if (token.startsWith("**")) {
      const strong = document.createElement("strong");
      appendInlineMarkdown(strong, token.slice(2, -2));
      parent.appendChild(strong);
    } else if (token.startsWith("*")) {
      const emphasis = document.createElement("em");
      appendInlineMarkdown(emphasis, token.slice(1, -1));
      parent.appendChild(emphasis);
    } else {
      const linkMatch = token.match(/^\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)$/);
      if (linkMatch) {
        const anchor = document.createElement("a");
        anchor.href = linkMatch[2];
        anchor.target = "_blank";
        anchor.rel = "noopener noreferrer";
        anchor.textContent = linkMatch[1];
        parent.appendChild(anchor);
      } else {
        parent.appendChild(document.createTextNode(token));
      }
    }

    lastIndex = match.index + token.length;
  }

  if (lastIndex < text.length) {
    parent.appendChild(document.createTextNode(text.slice(lastIndex)));
  }
}

function appendParagraph(container, lines) {
  const paragraph = document.createElement("p");
  appendInlineMarkdown(paragraph, lines.map((line) => line.trim()).join(" "));
  container.appendChild(paragraph);
}

function appendList(container, lines, ordered) {
  const list = document.createElement(ordered ? "ol" : "ul");
  const itemPattern = ordered ? /^\d+\.\s+(.*)$/ : /^[-*]\s+(.*)$/;

  for (const line of lines) {
    const item = document.createElement("li");
    appendInlineMarkdown(item, line.match(itemPattern)?.[1] || line.trim());
    list.appendChild(item);
  }

  container.appendChild(list);
}

function renderMarkdown(container, markdown) {
  container.replaceChildren();
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed) {
      index += 1;
      continue;
    }

    if (trimmed.startsWith("```")) {
      const codeLines = [];
      index += 1;
      while (index < lines.length && !lines[index].trim().startsWith("```")) {
        codeLines.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) {
        index += 1;
      }

      const pre = document.createElement("pre");
      const code = document.createElement("code");
      code.textContent = codeLines.join("\n");
      pre.appendChild(code);
      container.appendChild(pre);
      continue;
    }

    if (/^(-{3,}|\*{3,})$/.test(trimmed)) {
      container.appendChild(document.createElement("hr"));
      index += 1;
      continue;
    }

    const heading = trimmed.match(/^(#{1,4})\s+(.*)$/);
    if (heading) {
      const headingLevel = Math.min(heading[1].length + 2, 6);
      const headingNode = document.createElement(`h${headingLevel}`);
      appendInlineMarkdown(headingNode, heading[2]);
      container.appendChild(headingNode);
      index += 1;
      continue;
    }

    if (/^\d+\.\s+/.test(trimmed)) {
      const listLines = [];
      while (index < lines.length && /^\d+\.\s+/.test(lines[index].trim())) {
        listLines.push(lines[index].trim());
        index += 1;
      }
      appendList(container, listLines, true);
      continue;
    }

    if (/^[-*]\s+/.test(trimmed)) {
      const listLines = [];
      while (index < lines.length && /^[-*]\s+/.test(lines[index].trim())) {
        listLines.push(lines[index].trim());
        index += 1;
      }
      appendList(container, listLines, false);
      continue;
    }

    const paragraphLines = [];
    while (
      index < lines.length
      && lines[index].trim()
      && !isMarkdownBlockStart(lines[index].trim())
    ) {
      paragraphLines.push(lines[index]);
      index += 1;
    }
    appendParagraph(container, paragraphLines);
  }
}

function renderMessageBody(bodyNode, body, useMarkdown) {
  bodyNode.removeAttribute("aria-label");
  if (useMarkdown) {
    renderMarkdown(bodyNode, body);
    return;
  }
  bodyNode.textContent = body;
}

function ensureMessageMeta(messageRef, meta) {
  if (messageRef.metaNode) {
    messageRef.metaNode.textContent = meta;
    return;
  }
  const metaNode = document.createElement("div");
  metaNode.className = "message-meta";
  metaNode.textContent = meta;
  messageRef.article.append(metaNode);
  messageRef.metaNode = metaNode;
}

function setMessagePending(messageRef, label = "Agent is thinking") {
  messageRef.article.classList.add("is-pending");
  messageRef.bodyNode.textContent = "";
  messageRef.bodyNode.setAttribute("aria-label", label);

  const indicator = document.createElement("span");
  indicator.className = "typing-indicator";
  indicator.setAttribute("aria-hidden", "true");
  for (let i = 0; i < 3; i += 1) {
    indicator.appendChild(document.createElement("span"));
  }
  messageRef.bodyNode.appendChild(indicator);
}

function setMessageBody(messageRef, text) {
  messageRef.article.classList.remove("is-pending");
  renderMessageBody(
    messageRef.bodyNode,
    text,
    messageRef.article.classList.contains("assistant-message"),
  );
}

async function readEventStream(response, onEvent) {
  if (!response.body) {
    throw new Error("Streaming response body is not available in this browser.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

    let boundaryIndex = buffer.indexOf("\n\n");
    while (boundaryIndex >= 0) {
      const rawEvent = buffer.slice(0, boundaryIndex).trim();
      buffer = buffer.slice(boundaryIndex + 2);
      if (rawEvent) {
        const dataLine = rawEvent
          .split("\n")
          .map((line) => line.trim())
          .find((line) => line.startsWith("data:"));
        if (dataLine) {
          onEvent(JSON.parse(dataLine.slice(5).trim()));
        }
      }
      boundaryIndex = buffer.indexOf("\n\n");
    }

    if (done) {
      const finalEvent = buffer.trim();
      if (finalEvent) {
        const dataLine = finalEvent
          .split("\n")
          .map((line) => line.trim())
          .find((line) => line.startsWith("data:"));
        if (dataLine) {
          onEvent(JSON.parse(dataLine.slice(5).trim()));
        }
      }
      break;
    }
  }
}

function setSettingsMenuOpen(open) {
  els.settingsMenu.classList.toggle("hidden", !open);
  els.settingsToggleBtn.setAttribute("aria-expanded", String(open));
}

function setModelProviderMenuOpen(open) {
  els.modelProviderMenu.classList.toggle("hidden", !open);
  els.modelProviderBtn.setAttribute("aria-expanded", String(open));
}

function syncModelSelects(sourceSelect, targetSelect) {
  const selectedValue = sourceSelect.value;
  targetSelect.innerHTML = "";
  Array.from(sourceSelect.options).forEach((option) => {
    const clone = option.cloneNode(true);
    clone.selected = option.value === selectedValue;
    targetSelect.appendChild(clone);
  });
}

function hasClaudeProviderCredential() {
  return Boolean(state.claudeApiKey || state.serverClaudeKeyAvailable);
}

function applyProviderVisibility() {
  const isClaude = state.llmProvider === "claude";
  const isAuto = state.llmProvider === "auto";
  const hasClaudeKey = hasClaudeProviderCredential();
  els.providerSelect.value = state.llmProvider;
  els.providerLocalModelRow.classList.toggle("hidden", isClaude);
  els.providerClaudeModelRow.classList.toggle("hidden", !(isClaude || isAuto));
  els.providerClaudeKeyRow.classList.toggle("hidden", !(isClaude || isAuto));
  if (state.claudeApiKey) {
    els.claudeApiKeyInput.value = state.claudeApiKey;
  }
  if (isAuto) {
    const localLabel = els.modelSelect.value || els.topModelSelect.value || state.config?.default_model || "local model";
    const tone = hasClaudeKey || state.localModelAvailable ? "good" : "warn";
    setModelProviderButton(hasClaudeKey ? "Auto: Claude primary" : "Auto: local fallback", tone);
    if (hasClaudeKey && state.localModelAvailable) {
      els.providerStatus.textContent = `Claude primary; local fallback: ${localLabel}`;
    } else if (hasClaudeKey) {
      els.providerStatus.textContent = "Claude primary; local model unavailable";
    } else if (state.localModelAvailable) {
      els.providerStatus.textContent = `Claude key missing; using local fallback: ${localLabel}`;
    } else {
      els.providerStatus.textContent = "Claude key and local model unavailable; deterministic planner remains active";
    }
  } else if (isClaude) {
    setModelProviderButton(`Claude: ${els.claudeModelSelect.value}`, hasClaudeKey ? "good" : "warn");
    els.providerStatus.textContent = state.claudeApiKey
      ? "Claude API key loaded for this browser session"
      : state.serverClaudeKeyAvailable
        ? "Server ANTHROPIC_API_KEY will be used"
        : "Claude key required";
  } else {
    const label = els.modelSelect.value || els.topModelSelect.value || state.config?.default_model || "local model";
    const tone = state.localModelAvailable ? "good" : "warn";
    setModelProviderButton(state.localModelAvailable ? `Local: ${label}` : "Local model offline; rules active", tone);
    els.providerStatus.textContent = state.localModelAvailable
      ? `Using detected local model: ${label}`
      : "Local model offline; deterministic planner remains active";
  }
}

function applyProviderSelection() {
  state.llmProvider = els.providerSelect.value;
  state.claudeApiKey = els.claudeApiKeyInput.value.trim();
  if (state.llmProvider === "claude" && !hasClaudeProviderCredential()) {
    applyProviderVisibility();
    els.providerStatus.textContent = "Claude API key required here or ANTHROPIC_API_KEY on the server";
    setModelProviderMenuOpen(true);
    els.claudeApiKeyInput.focus();
    return;
  }

  sessionStorage.setItem("teraLlmProvider", state.llmProvider);
  if (state.claudeApiKey) {
    sessionStorage.setItem("teraClaudeApiKey", state.claudeApiKey);
  } else {
    sessionStorage.removeItem("teraClaudeApiKey");
  }

  if (state.llmProvider === "ollama" || state.llmProvider === "auto") {
    els.modelSelect.value = els.topModelSelect.value;
  }
  applyProviderVisibility();
  setModelProviderMenuOpen(false);
}

function clearClaudeKey() {
  state.claudeApiKey = "";
  els.claudeApiKeyInput.value = "";
  sessionStorage.removeItem("teraClaudeApiKey");
  applyProviderVisibility();
}

function hasMissionInference() {
  return Boolean(state.sourceInference);
}

function renderWorkflowDots() {
  els.workflowDots.replaceChildren();
  WORKFLOW_STAGES.forEach((stage, index) => {
    const dot = document.createElement("span");
    dot.className = "workflow-dot";
    dot.dataset.active = String(index === state.workflowStageIndex);
    dot.title = stage.label;
    els.workflowDots.appendChild(dot);
  });
}

function ensureClarifyingQuestions(recommendation) {
  if (!recommendation) {
    return [];
  }
  if (Array.isArray(recommendation.clarifying_questions) && recommendation.clarifying_questions.length) {
    return recommendation.clarifying_questions;
  }

  const focus = recommendation.mission_focus || "mission-data-package";
  return [
    `Confirm the ${focus} scope in one pass: mission outcome, movement mode, time window, and any must-avoid constraints. This decides whether to add current imagery, hazards, access, or communications layers.`,
  ];
}

function setWorkflowStage(index) {
  state.workflowStageIndex = clampNumber(index, 0, WORKFLOW_STAGES.length - 1);
  updateWorkflowPanel();
}

function updateWorkflowPanel() {
  const hasMission = hasMissionInference();
  const selectedCount = state.selectedSourceIds.size;
  state.workflowStageIndex = clampNumber(state.workflowStageIndex, 0, WORKFLOW_STAGES.length - 1);

  els.sourcePanel.classList.toggle("is-empty", !hasMission);
  els.workflowEmpty.classList.toggle("hidden", hasMission);
  els.workflowCarousel.classList.toggle("hidden", !hasMission);

  if (hasMission) {
    const stage = WORKFLOW_STAGES[state.workflowStageIndex];
    const stageMeta = stage.key === "area" && !state.sourceConfirmed
      ? "Locked until sources are confirmed"
      : stage.meta;
    els.workflowStageLabel.textContent = `${state.workflowStageIndex + 1}/${WORKFLOW_STAGES.length} ${stage.label}`;
    els.workflowStageMeta.textContent = stageMeta;
    for (const slide of els.workflowSlides) {
      slide.classList.toggle("active", slide.dataset.workflowSlide === stage.key);
    }
  }

  els.workflowPrevBtn.disabled = !hasMission || state.workflowStageIndex === 0;
  els.workflowNextBtn.disabled = !hasMission || state.workflowStageIndex === WORKFLOW_STAGES.length - 1;
  els.confirmSourcesBtn.disabled = selectedCount === 0;
  els.confirmSourcesBtn.textContent = state.sourceConfirmed ? "Sources Confirmed" : "Confirm Sources";
  els.confirmSourcesBtn.classList.toggle("confirmed", state.sourceConfirmed);
  els.aoLockedNotice.classList.toggle("hidden", state.sourceConfirmed);
  els.areaControlSurface.classList.toggle("hidden", !state.sourceConfirmed);
  els.drawAreaBtn.disabled = !state.sourceConfirmed;
  els.clearAreaBtn.disabled = !state.sourceConfirmed || !state.selectedArea;
  els.buildPackageBtn.disabled = selectedCount === 0 || !state.sourceConfirmed;
  els.streamSelectedBtn.disabled = selectedCount === 0;

  renderWorkflowDots();
}

function getSelectedSources() {
  return state.dataSources.filter((source) => state.selectedSourceIds.has(source.id));
}

function formatSourceStatus(source) {
  const stream = (source.stream_status || "unknown-stream").replace(/-/g, " ");
  const download = (source.download_status || "unknown-package").replace(/-/g, " ");
  return `${stream} / ${download}`;
}

function textHasAny(text, terms) {
  const normalizedText = normalizeSearchText(text);
  const tokens = getMatchTokens(text);
  return terms.some((term) => {
    const expandedTerms = [term, ...(KEYWORD_EXPANSIONS[term] || [])];
    return expandedTerms.some((expandedTerm) => {
      const normalizedTerm = normalizeSearchText(expandedTerm);
      if (!normalizedTerm) {
        return false;
      }
      if (` ${normalizedText} `.includes(` ${normalizedTerm} `)) {
        return true;
      }
      const termTokens = getMatchTokens(normalizedTerm);
      if (termTokens.length === 1) {
        return tokens.some((token) => tokenLooksLike(token, termTokens[0]));
      }
      return termTokens.every((termToken) => tokens.some((token) => tokenLooksLike(token, termToken)));
    });
  });
}

function findSourceById(sourceId) {
  return state.dataSources.find((source) => source.id === sourceId)
    || FALLBACK_SOURCE_CATALOG.find((source) => source.id === sourceId)
    || null;
}

function appendUniqueSourceIds(sourceIds, ...newSourceIds) {
  for (const sourceId of newSourceIds) {
    if (findSourceById(sourceId) && !sourceIds.includes(sourceId)) {
      sourceIds.push(sourceId);
    }
  }
}

function mergeSourcesIntoCatalog(sources) {
  if (!Array.isArray(sources) || !sources.length) {
    return;
  }

  const sourcesById = new Map(state.dataSources.map((source) => [source.id, source]));
  for (const source of sources) {
    if (source?.id) {
      sourcesById.set(source.id, source);
    }
  }
  state.dataSources = Array.from(sourcesById.values());
}

function useFallbackSourceCatalog(message, updateStatus = true) {
  state.dataSources = FALLBACK_SOURCE_CATALOG.map((source) => ({ ...source }));
  state.primarySourceIds = [...FALLBACK_PRIMARY_STREAM_SOURCE_IDS];
  state.sourceCatalogFallback = true;
  state.sourceCatalogMessage = message;

  if (updateStatus) {
    setChip(els.packageModeChip, "Catalog fallback", "warn");
    els.packageStatus.textContent = `Server source catalog unavailable (${message}). Using the embedded fallback catalog.`;
  }
}

function isUsMissionContext(promptText, mapContext) {
  const usTerms = [
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
  ];
  if (textHasAny(promptText, usTerms)) {
    return true;
  }

  const bounds = mapContext?.selected_area || (mapContext?.location_confirmed ? mapContext?.view_bounds : null);
  const lat = bounds?.center_lat ?? mapContext?.camera?.lat;
  const lon = bounds?.center_lon ?? mapContext?.camera?.lon;
  return Number.isFinite(lat) && Number.isFinite(lon)
    && lat >= 18
    && lat <= 72
    && lon >= -170
    && lon <= -50;
}

function inferClientMissionFocus(promptText) {
  const focusKeywords = [
    ["water-access", ["water", "stream", "river", "spring", "lake", "potable", "hydrate"]],
    ["sar-planning", ["search", "rescue", "sar", "missing", "lost person", "hasty"]],
    ["evacuation", ["evac", "evacuation", "exfil", "casualty", "ambulance", "convoy"]],
    ["signal-planning", ["signal", "radio", "comms", "communications", "line of sight", "relay"]],
    ["hazard-routing", ["wildfire", "fire", "flood", "storm", "avalanche", "hazard", "closure"]],
    ["access-control", ["private", "restricted", "public land", "access", "boundary", "parcel"]],
    ["terrain-routing", ["route", "patrol", "walk", "foot", "trail", "slope", "terrain", "ridge"]],
    ["imagery-preview", ["imagery", "aerial", "satellite", "visual", "inspect", "preview"]],
  ];

  let bestFocus = "mission-data-package";
  let bestScore = 0;
  for (const [focus, keywords] of focusKeywords) {
    const score = keywords.reduce((sum, keyword) => sum + (textHasAny(promptText, [keyword]) ? 1 : 0), 0);
    if (score > bestScore) {
      bestFocus = focus;
      bestScore = score;
    }
  }
  return bestFocus;
}

function sanitizePackageSlug(text) {
  const slug = text.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return (slug || "mission-package").slice(0, 60);
}

function buildClientSourceRecommendation(missionText, mapContext, plannerErrorMessage) {
  if (!state.dataSources.length) {
    useFallbackSourceCatalog(plannerErrorMessage, false);
  }

  const promptText = missionText.trim().toLowerCase();
  const missionFocus = inferClientMissionFocus(promptText);
  const isUsContext = isUsMissionContext(promptText, mapContext);
  const requiredIds = [];
  const optionalIds = [];
  const questions = [];
  const rationale = [`Planner API unavailable: ${plannerErrorMessage}. Using embedded deterministic source rules.`];

  appendUniqueSourceIds(requiredIds, isUsContext ? "naip" : "sentinel_2");
  appendUniqueSourceIds(optionalIds, "cesium_world_imagery", "osm_basemap");
  if (isUsContext) {
    appendUniqueSourceIds(optionalIds, "usgs_imagery_only", "nrl_naip_conus");
  }
  rationale.push("NAIP is the high-detail U.S. imagery default; Sentinel-2 remains the global free imagery fallback and Cesium imagery stays as the token-backed preview stream.");

  const needsRouting = textHasAny(promptText, [
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
  ]);
  const needsTerrain = needsRouting || textHasAny(promptText, [
    "terrain",
    "slope",
    "ridge",
    "mountain",
    "valley",
    "steep",
    "exposed",
    "viewshed",
  ]);
  const needsDted = textHasAny(promptText, ["dted", "dt2", "earth explorer", "earthexplorer"]);
  const needsWater = textHasAny(promptText, ["water", "stream", "river", "spring", "lake", "potable", "hydrate"]);
  const needsLandcover = needsRouting || textHasAny(promptText, [
    "cover",
    "conceal",
    "brush",
    "forest",
    "canopy",
    "wetland",
    "vegetation",
  ]);
  const needsHazards = textHasAny(promptText, [
    "wildfire",
    "fire",
    "flood",
    "storm",
    "weather",
    "avalanche",
    "closure",
    "hazard",
  ]);
  const needsAccess = textHasAny(promptText, [
    "private",
    "restricted",
    "public land",
    "boundary",
    "parcel",
    "permission",
    "access",
  ]);
  const needsSignal = textHasAny(promptText, [
    "signal",
    "radio",
    "comms",
    "communications",
    "line of sight",
    "los",
    "relay",
  ]);
  const needsSar = textHasAny(promptText, ["sar", "search", "rescue", "missing", "lost person"]);
  const needsCurrentImagery = textHasAny(promptText, [
    "current",
    "recent",
    "latest",
    "flood",
    "burn",
    "changed",
    "cloud",
  ]);
  const needsCesiumArchive = promptText.includes("cesium") && textHasAny(promptText, [
    "download",
    "offline",
    "archive",
    "export",
    "jetson",
    "local",
  ]);

  if (needsCesiumArchive) {
    appendUniqueSourceIds(requiredIds, "cesium_ion_archive");
    rationale.push("Cesium offline use is handled through ion archive/export downloads to the Jetson, not by scraping World stream tiles.");
  }
  if (needsRouting) {
    appendUniqueSourceIds(requiredIds, "osm_extract");
    rationale.push("OSM PBF is required for the local routable graph and feature lookup.");
  }
  if (needsTerrain) {
    appendUniqueSourceIds(requiredIds, "copernicus_dem");
    if (isUsContext) {
      appendUniqueSourceIds(optionalIds, "dted_earth_explorer", "usgs_3dep");
    } else {
      appendUniqueSourceIds(optionalIds, "dted_earth_explorer");
    }
    appendUniqueSourceIds(optionalIds, "cesium_world_terrain");
    rationale.push("Copernicus GLO-30 COGs are the no-account terrain default; staged EarthExplorer DTED supplements it when available.");
  }
  if (needsDted) {
    appendUniqueSourceIds(requiredIds, "dted_earth_explorer");
    rationale.push("DTED was explicitly requested, so staged EarthExplorer DTED import is included; set DTED_SOURCE_DIR on the Jetson before executing the package.");
  }
  if (needsLandcover) {
    appendUniqueSourceIds(requiredIds, isUsContext ? "nlcd" : "esa_worldcover");
    rationale.push("Land cover is included because movement friction, cover, vegetation, or route quality matters.");
  }
  if (needsWater) {
    appendUniqueSourceIds(requiredIds, isUsContext ? "usgs_3dhp" : "hydrosheds");
    if (isUsContext) {
      appendUniqueSourceIds(optionalIds, "nwis");
    }
    rationale.push("Hydrography is required for water-source and drainage queries.");
  }
  if (needsSar) {
    appendUniqueSourceIds(requiredIds, "osm_extract");
    appendUniqueSourceIds(optionalIds, isUsContext ? "naip" : "sentinel_2", "noaa_alerts");
    rationale.push("SAR planning needs access features and usually benefits from detailed imagery and current alerts.");
  }
  if (needsHazards) {
    appendUniqueSourceIds(optionalIds, "noaa_alerts");
    if (textHasAny(promptText, ["fire", "wildfire"])) {
      appendUniqueSourceIds(requiredIds, "nasa_firms");
    }
    if (textHasAny(promptText, ["flood"])) {
      appendUniqueSourceIds(requiredIds, isUsContext ? "fema_flood" : "sentinel_1_sar");
    }
    rationale.push("Hazard layers are included only because current or baseline risk affects the mission.");
  }
  if (needsAccess) {
    appendUniqueSourceIds(requiredIds, isUsContext ? "pad_us" : "parcels_boundaries");
    if (isUsContext) {
      appendUniqueSourceIds(optionalIds, "parcels_boundaries");
    }
    rationale.push("Access and boundary layers are included because restricted or legal movement matters.");
  }
  if (needsSignal) {
    appendUniqueSourceIds(requiredIds, "viewshed_surfaces");
    appendUniqueSourceIds(optionalIds, isUsContext ? "fcc_towers" : "osm_towers", "osm_towers");
    if (!needsTerrain) {
      appendUniqueSourceIds(requiredIds, "copernicus_dem");
      if (isUsContext) {
        appendUniqueSourceIds(optionalIds, "dted_earth_explorer", "usgs_3dep");
      }
    }
    rationale.push("Signal planning requires DEM-derived viewsheds plus tower or high-ground candidates.");
  }
  if (needsCurrentImagery && !needsWater && !needsHazards) {
    appendUniqueSourceIds(optionalIds, "landsat_collection_2");
    if (isUsContext) {
      appendUniqueSourceIds(optionalIds, "naip");
    }
    rationale.push("Recent imagery is optional unless recent conditions drive the mission.");
  }

  if (!mapContext?.location_confirmed) {
    questions.push(
      "Move the map to the mission AO with search, KML/KMZ import, or AO drawing and confirm that view before final source selection.",
    );
  }

  if (!requiredIds.length) {
    questions.push(
      "Which mission outcome must the database answer first: routing, water lookup, SAR sectors, signal planning, hazards, or access control?",
    );
    rationale.push("No analytical source family was identified yet, so the package remains in preview mode.");
  }
  if (needsRouting && !textHasAny(promptText, ["foot", "vehicle", "atv", "convoy", "boat", "drone"])) {
    questions.push("Should movement be optimized for foot, vehicle, ATV, boat, drone, or mixed movement?");
  }
  if (needsWater) {
    questions.push("Do you only need mapped water features, or confidence in current and potable water availability?");
  }
  if (needsHazards) {
    questions.push("Which hazards must be current at package time versus treated as cached baseline risk?");
  }
  if (needsSignal) {
    questions.push("What antenna height and radio role should viewshed or relay analysis assume?");
  }
  if (needsAccess) {
    questions.push("Should the package enforce legal or restricted access boundaries, or only support terrain movement?");
  }
  if (!mapContext?.selected_area && !mapContext?.location_confirmed) {
    questions.push("Is this AO inside the U.S. or outside it?");
  }

  const selectedIds = [];
  const previewIds = optionalIds.filter((sourceId) => ["cesium_world_imagery", "usgs_imagery_only", "osm_basemap"].includes(sourceId));
  appendUniqueSourceIds(selectedIds, ...requiredIds, ...previewIds);
  const missionSummary = missionText.length > 220 ? `${missionText.slice(0, 217)}...` : missionText;

  return {
    mission_focus: missionFocus,
    mission_summary: missionSummary,
    required_source_ids: requiredIds,
    optional_source_ids: optionalIds.filter((sourceId) => !requiredIds.includes(sourceId)),
    selected_source_ids: selectedIds,
    sources: selectedIds.map((sourceId) => findSourceById(sourceId)).filter(Boolean),
    clarifying_questions: questions.slice(0, 3),
    rationale: rationale.slice(0, 5),
    package_name_suggestion: `tera-${sanitizePackageSlug(missionFocus)}`,
  };
}

function applySourceRecommendation(data, missionText, mode = "server", statusMessage = "") {
  mergeSourcesIntoCatalog(data.sources);
  data.clarifying_questions = ensureClarifyingQuestions(data);
  state.sourceInference = data;
  state.lastMissionText = missionText;
  state.selectedSourceIds = new Set(data.selected_source_ids || []);
  state.sourceConfirmed = false;
  state.workflowStageIndex = 1;
  state.packagePlan = null;
  state.sourcePlannerFallback = mode === "fallback";
  state.sourcePlannerMessage = statusMessage;
  hidePackageOutput();

  if (!els.packageNameInput.value.trim() && data.package_name_suggestion) {
    els.packageNameInput.value = data.package_name_suggestion;
  }

  els.inferredMission.textContent = data.mission_summary || missionText;
  setChip(
    els.packageModeChip,
    mode === "fallback" ? "Planner fallback" : data.mission_focus || "Planned",
    mode === "fallback" ? "warn" : "good",
  );
  renderSourceList();

  const fallbackText = mode === "fallback"
    ? ` Browser fallback used because the planner API is unavailable (${statusMessage}).`
    : "";
  els.packageStatus.textContent = `Drafted ${state.selectedSourceIds.size} working sources.${fallbackText} Confirm sources when ready.`;
  updateWorkflowPanel();
}

function formatSourceNameList(sourceIds) {
  const names = (sourceIds || []).map((sourceId) => findSourceById(sourceId)?.name || sourceId);
  return names.length ? names.join(", ") : "none";
}

function buildDeterministicAdvisorResponse(recommendation, mapContext) {
  const required = formatSourceNameList(recommendation?.required_source_ids || []);
  const optional = formatSourceNameList(recommendation?.optional_source_ids || []);
  const selected = formatSourceNameList(recommendation?.selected_source_ids || []);
  const rationale = (recommendation?.rationale || [])
    .slice(0, 4)
    .map((item) => `- ${item}`)
    .join("\n") || "- The planner could not infer a stronger source rationale yet.";
  const questions = (recommendation?.clarifying_questions || [])
    .slice(0, 3)
    .map((item, index) => `${index + 1}. ${item}`)
    .join("\n") || "No additional question is required before reviewing the selected source families.";
  const mapFocus = mapContext?.location_confirmed
    ? `Confirmed map focus: **${mapContext.location_focus_label || "selected AO"}**.`
    : "Map focus is not confirmed. Use the search bar, KML/KMZ import, or AO rectangle before finalizing the package.";

  return [
    "### Mission Read",
    recommendation?.mission_summary || "Mission description captured.",
    "",
    "### Working Source Recommendation",
    `- **Required:** ${required}`,
    `- **Optional enhancers:** ${optional}`,
    `- **Currently selected:** ${selected}`,
    "",
    "### Why These Sources",
    rationale,
    "",
    "### Scope Check",
    questions,
    "",
    "### Map Location",
    mapFocus,
  ].join("\n");
}

function updateSourceCount() {
  const selectedCount = state.selectedSourceIds.size;
  const total = state.dataSources.length;
  if (!hasMissionInference()) {
    if (state.sourceCatalogFallback) {
      els.sourceCount.textContent = "Fallback source catalog ready";
    } else {
      els.sourceCount.textContent = total
        ? "Awaiting mission description"
        : "Source catalog unavailable";
    }
  } else {
    els.sourceCount.textContent = selectedCount
      ? `${selectedCount} selected from ${total} available sources`
      : `0 selected from ${total} available sources`;
  }
  updateWorkflowPanel();
}

function renderSourceList() {
  els.sourceList.replaceChildren();

  if (!state.dataSources.length) {
    const empty = document.createElement("div");
    empty.className = "source-empty";
    empty.textContent = "Source catalog unavailable. The browser planner will fall back if the server route is not ready.";
    els.sourceList.appendChild(empty);
    updateSourceCount();
    return;
  }

  const visibleSources = getSelectedSources();
  if (!visibleSources.length) {
    const empty = document.createElement("div");
    empty.className = "source-empty";
    empty.textContent = "Send a mission description in chat. TERA will recommend a compact source list here.";
    els.sourceList.appendChild(empty);
    updateSourceCount();
    return;
  }

  for (const source of visibleSources) {
    const article = document.createElement("article");
    article.className = "source-item compact-source-item source-chip";
    article.dataset.selected = String(state.selectedSourceIds.has(source.id));
    article.title = `${source.category} | ${formatSourceStatus(source)}`;

    const header = document.createElement("label");
    header.className = "source-item-header";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = state.selectedSourceIds.has(source.id);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        state.selectedSourceIds.add(source.id);
      } else {
        state.selectedSourceIds.delete(source.id);
      }
      state.packagePlan = null;
      state.sourceConfirmed = false;
      article.dataset.selected = String(checkbox.checked);
      hidePackageOutput();
      updateSourceCount();
    });

    const title = document.createElement("span");
    title.className = "source-title";
    title.textContent = source.name;

    header.append(checkbox, title);
    article.append(header);
    els.sourceList.appendChild(article);
  }

  updateSourceCount();
}

function hidePackageOutput() {
  els.packageManifest.classList.add("hidden");
  els.packageManifest.textContent = "";
  els.downloadManifestLink.classList.add("hidden");
  els.downloadManifestLink.removeAttribute("href");
  els.packageExecutionActions.classList.add("hidden");
  els.downloadToJetsonBtn.disabled = true;
  els.packageExecutionStatus.classList.add("hidden");
  els.packageExecutionStatus.textContent = "";
  els.packageArtifacts.classList.add("hidden");
  els.packageArtifacts.textContent = "";
  if (state.packageStatusTimer) {
    window.clearInterval(state.packageStatusTimer);
    state.packageStatusTimer = null;
  }
}

async function loadDataSources() {
  try {
    const data = await fetchJson("/api/data-sources");
    state.dataSources = Array.isArray(data.sources) ? data.sources : [];
    state.primarySourceIds = Array.isArray(data.primary_streams) ? data.primary_streams : [];
    state.sourceCatalogFallback = false;
    state.sourceCatalogMessage = "";
    state.selectedSourceIds = new Set();
    if (!state.dataSources.length) {
      throw new Error("empty catalog response");
    }
    renderSourceList();
  } catch (error) {
    const message = getErrorMessage(error);
    useFallbackSourceCatalog(message);
    renderSourceList();
  }
}

function buildMapContext() {
  const context = {
    imagery_source: els.imageryStatus.textContent || null,
    terrain_source: els.terrainStatus.textContent || null,
    location_focus_label: state.mapFocusLabel || null,
    location_focus_source: state.mapFocusSource || null,
    location_confirmed: Boolean(state.mapLocationConfirmed || state.selectedArea),
  };

  if (state.selectedArea) {
    context.selected_area = { ...state.selectedArea };
  }

  if (state.viewer) {
    const camera = state.viewer.camera.positionCartographic;
    context.camera = {
      lat: Cesium.Math.toDegrees(camera.latitude),
      lon: Cesium.Math.toDegrees(camera.longitude),
      height_m: camera.height,
    };

    const rectangle = state.viewer.camera.computeViewRectangle(state.viewer.scene.globe.ellipsoid);
    if (rectangle) {
      const west = Cesium.Math.toDegrees(rectangle.west);
      const south = Cesium.Math.toDegrees(rectangle.south);
      const east = Cesium.Math.toDegrees(rectangle.east);
      const north = Cesium.Math.toDegrees(rectangle.north);
      context.view_bounds = {
        west,
        south,
        east,
        north,
        center_lat: (south + north) / 2,
        center_lon: (west + east) / 2,
      };
    }
  }

  return context;
}

function buildSourceContext() {
  const selectedSources = getSelectedSources();
  const sourceNames = selectedSources.map((source) => source.name);
  const inference = state.sourceInference;
  const packageSummary = state.packagePlan
    ? `${state.packagePlan.package_name}: ${sourceNames.length} sources, manifest ${state.packagePlan.package_id}`
    : `${sourceNames.length} sources planned from chat for ${inference?.mission_focus || "mission-data-package"}`;

  return {
    mission_focus: inference?.mission_focus || "mission-data-package",
    mission_text: state.lastMissionText ? state.lastMissionText.slice(0, 2000) : null,
    selected_source_ids: selectedSources.map((source) => source.id),
    selected_source_names: sourceNames,
    required_source_ids: inference?.required_source_ids || [],
    optional_source_ids: inference?.optional_source_ids || [],
    clarifying_questions: inference?.clarifying_questions || [],
    package_summary: packageSummary,
  };
}

function resetPlannerWorkflow() {
  state.sourceInference = null;
  state.sourceConfirmed = false;
  state.workflowStageIndex = 0;
  state.selectedSourceIds = new Set();
  state.packagePlan = null;
  state.lastMissionText = "";
  state.areaSelectActive = false;
  state.areaDrawing = false;
  state.areaResizeHandle = null;
  state.areaResizeAnchorPoint = null;
  state.selectedArea = null;
  state.areaStartPoint = null;
  setCameraDragEnabled(true);
  if (state.viewer && state.areaEntity) {
    state.viewer.entities.remove(state.areaEntity);
  }
  state.areaEntity = null;
  clearAreaHandles();
  updateSelectedArea();
  els.inferredMission.textContent = "Describe the mission in chat to draft a focused source package.";
  els.packageNameInput.value = "";
  setChip(els.packageModeChip, "Awaiting mission");
  hidePackageOutput();
  renderSourceList();
  els.packageStatus.textContent = "No sources selected yet. Send a mission description to plan the needed package.";
  updateWorkflowPanel();
}

function confirmSources() {
  if (!state.selectedSourceIds.size) {
    els.packageStatus.textContent = "No sources are selected yet.";
    return;
  }
  state.sourceConfirmed = true;
  hidePackageOutput();
  setWorkflowStage(2);
  els.packageStatus.textContent = "Sources confirmed. Draw or adjust the AO rectangle for the data package.";
}

function clearChat() {
  resetPlannerWorkflow();
  els.chatLog.innerHTML = "";
  state.chatCount = 0;
  appendMessage(
    "assistant",
    "Source planner ready. Describe the mission and move the map to the mission area with search, KML/KMZ import, or AO selection. I will keep the source-scope dialogue short.",
  );
}

function applyPanelState() {
  document.body.classList.toggle("panel-collapsed", state.panelCollapsed);
  els.panelToggleBtn.textContent = state.panelCollapsed ? "Expand Planner" : "Collapse Planner";
  els.panelToggleBtn.setAttribute("aria-expanded", String(!state.panelCollapsed));
  if (state.panelCollapsed) {
    els.workspaceShell.style.removeProperty("--panel-width");
  } else {
    els.workspaceShell.style.setProperty("--panel-width", `${state.panelWidth}px`);
  }
  requestAnimationFrame(() => {
    if (state.viewer) {
      state.viewer.resize();
      state.viewer.scene.requestRender();
    }
    requestAnimationFrame(() => {
      if (state.viewer) {
        state.viewer.resize();
        state.viewer.scene.requestRender();
      }
    });
  });
}

function clampPanelWidth(width) {
  const minWidth = 320;
  const maxWidth = Math.max(520, Math.min(window.innerWidth * 0.58, 860));
  return Math.min(Math.max(width, minWidth), maxWidth);
}

function formatPoint(lat, lon, height = null) {
  const base = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
  if (height === null || Number.isNaN(height)) {
    return base;
  }
  return `${base} | ${height.toFixed(0)} m`;
}

function formatBounds(bounds) {
  if (!bounds) {
    return "Camera view will be used until an AO is drawn.";
  }
  const width = Math.abs(bounds.east - bounds.west).toFixed(3);
  const height = Math.abs(bounds.north - bounds.south).toFixed(3);
  return `W ${bounds.west.toFixed(4)} | S ${bounds.south.toFixed(4)} | E ${bounds.east.toFixed(4)} | N ${bounds.north.toFixed(4)} (${width} x ${height} deg)`;
}

function clampNumber(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function normalizeDegrees(degrees) {
  return ((degrees % 360) + 360) % 360;
}

function updateSelectedArea() {
  els.selectedArea.textContent = formatBounds(state.selectedArea);
  els.clearAreaBtn.disabled = !state.sourceConfirmed || !state.selectedArea;
  updateWorkflowPanel();
}

function updateMapInstruments() {
  if (!state.viewer) {
    return;
  }
  const camera = state.viewer.camera;
  const headingDeg = normalizeDegrees(Cesium.Math.toDegrees(camera.heading));
  const pitchDeg = Cesium.Math.toDegrees(camera.pitch);
  const tiltDeg = clampNumber(90 + pitchDeg, 0, 90);
  const tiltPercentFromTop = 100 - (tiltDeg / 90) * 100;

  els.compassRose.style.setProperty("--heading-deg", `${headingDeg}deg`);
  els.compassRose.querySelector(".compass-needle").style.transform = `rotate(${headingDeg}deg)`;
  els.compassHeading.textContent = `${Math.round(headingDeg).toString().padStart(3, "0")} deg`;
  els.tiltNeedle.style.top = `calc(${tiltPercentFromTop}% - 1px)`;
  els.tiltValue.textContent = `${Math.round(tiltDeg)} deg tilt`;
}

function updateCameraText() {
  if (!state.viewer) {
    return;
  }
  const cartographic = state.viewer.camera.positionCartographic;
  const lat = Cesium.Math.toDegrees(cartographic.latitude);
  const lon = Cesium.Math.toDegrees(cartographic.longitude);
  const height = cartographic.height;
  state.cameraText = formatPoint(lat, lon, height);
  els.cameraPosition.textContent = state.cameraText;
  updateMapInstruments();
  updateCenterGrid();
}

function updateMapModeControl() {
  if (!els.mapModeToggleBtn) {
    return;
  }
  const is3d = state.mapMode === "3d";
  els.mapModeToggleBtn.textContent = is3d ? "2D View" : "3D View";
  els.mapModeToggleBtn.setAttribute("aria-pressed", String(is3d));
}

function applyMapModeCameraControls() {
  if (!state.viewer) {
    return;
  }
  const controller = state.viewer.scene.screenSpaceCameraController;
  const is3d = state.mapMode === "3d";
  controller.enableTranslate = true;
  controller.enableZoom = true;
  controller.enableRotate = is3d;
  controller.enableTilt = is3d;
  controller.enableLook = is3d;
  controller.enableCollisionDetection = true;
  updateMapModeControl();
}

function setMapMode(mode, { animate = true } = {}) {
  if (!state.viewer) {
    state.mapMode = mode;
    updateMapModeControl();
    return;
  }
  const nextMode = mode === "3d" ? "3d" : "2d";
  state.mapMode = nextMode;
  const duration = animate ? 0.45 : 0;
  if (nextMode === "3d") {
    state.viewer.scene.morphTo3D(duration);
  } else {
    state.viewer.scene.morphTo2D(duration);
  }
  applyMapModeCameraControls();
  state.viewer.scene.requestRender();
}

function toggleMapMode() {
  setMapMode(state.mapMode === "3d" ? "2d" : "3d");
}

function hasCesiumIonToken() {
  return Boolean(state.config?.cesium_ion_token);
}

function updateMapStreamChip(imagery, terrain, requestedModes = {}) {
  const requestedIon = requestedModes.imageryMode === "ion-satellite"
    || requestedModes.terrainMode === "cesium-world";
  const fallbackReason = [imagery?.fallbackReason, terrain?.fallbackReason]
    .filter(Boolean)
    .join("; ");

  if (imagery?.usingIon || terrain?.usingIon) {
    setChip(els.tokenChip, "Cesium ion stream active", "good");
    return;
  }

  if (fallbackReason || (requestedIon && !state.cesiumIonTokenAvailable)) {
    setChip(els.tokenChip, "Map stream active; ion fallback", "warn");
    return;
  }

  const imageryLabel = imagery?.shortLabel || imagery?.label || "imagery";
  setChip(els.tokenChip, `Map stream: ${imageryLabel}`, "good");
}

async function loadRuntimeConfig() {
  state.config = await fetchJson("/api/config");
  state.cesiumIonTokenAvailable = hasCesiumIonToken();
  state.serverClaudeKeyAvailable = Boolean(state.config.anthropic_api_key_configured);
  if (!sessionStorage.getItem("teraLlmProvider")) {
    state.llmProvider = state.config.default_provider || (state.serverClaudeKeyAvailable ? "auto" : "ollama");
  }
  setChip(els.tokenChip, "Map stream checking");
  els.providerSelect.value = state.llmProvider;
  els.claudeModelSelect.value = state.config.claude_default_model || els.claudeModelSelect.value;
  setModelProviderButton(
    state.llmProvider === "auto" ? "Auto: Claude primary" : `Default model: ${state.config.default_model}`,
    state.serverClaudeKeyAvailable ? "good" : "warn",
  );
  state.imageryMode = "esri";
  state.terrainMode = state.cesiumIonTokenAvailable ? "cesium-world" : "ellipsoid";
  els.imagerySelect.value = state.imageryMode;
  els.terrainSelect.value = state.terrainMode;
}

async function loadModels() {
  els.modelsStatus.textContent = "Checking Ollama...";
  try {
    const data = await fetchJson("/api/models");
    state.localModelAvailable = Boolean(data.online);
    state.localModelDetail = data.detail || "";
    els.modelsList.innerHTML = "";
    els.modelSelect.innerHTML = "";

    if (!data.online) {
      const option = document.createElement("option");
      option.value = data.default_model || state.config.default_model;
      option.textContent = `${option.value} (offline)`;
      els.modelSelect.appendChild(option);
      syncModelSelects(els.modelSelect, els.topModelSelect);

      const item = document.createElement("li");
      item.textContent = data.detail || "Local model is not reachable. Deterministic planner remains available.";
      els.modelsList.appendChild(item);
      els.modelsStatus.textContent = "Local model offline; deterministic planner active";
      applyProviderVisibility();
      return data;
    }

    if (!Array.isArray(data.models) || data.models.length === 0) {
      const option = document.createElement("option");
      option.value = data.default_model;
      option.textContent = `${data.default_model} (default)`;
      els.modelSelect.appendChild(option);

      const item = document.createElement("li");
      item.textContent = "No installed models reported by Ollama.";
      els.modelsList.appendChild(item);
      els.modelsStatus.textContent = `Default model: ${data.default_model}`;
      syncModelSelects(els.modelSelect, els.topModelSelect);
      applyProviderVisibility();
      return data;
    }

    for (const model of data.models) {
      const option = document.createElement("option");
      option.value = model;
      option.textContent = model;
      option.selected = model === data.default_model;
      els.modelSelect.appendChild(option);

      const item = document.createElement("li");
      item.textContent = model;
      els.modelsList.appendChild(item);
    }

    if (!data.models.includes(data.default_model)) {
      const option = document.createElement("option");
      option.value = data.default_model;
      option.textContent = `${data.default_model} (default, not installed)`;
      option.selected = true;
      els.modelSelect.appendChild(option);
    }

    els.modelsStatus.textContent = `Detected local model: ${data.default_model}`;
    syncModelSelects(els.modelSelect, els.topModelSelect);
    applyProviderVisibility();
    return data;
  } catch (error) {
    state.localModelAvailable = false;
    state.localModelDetail = error instanceof Error ? error.message : String(error);
    els.modelSelect.innerHTML = "";
    const option = document.createElement("option");
    option.value = state.config?.default_model || "";
    option.textContent = option.value ? `${option.value} (offline)` : "Local model offline";
    els.modelSelect.appendChild(option);
    els.modelsList.innerHTML = "";
    const item = document.createElement("li");
    item.textContent = state.localModelDetail;
    els.modelsList.appendChild(item);
    els.modelsStatus.textContent = "Local model offline; deterministic planner active";
    syncModelSelects(els.modelSelect, els.topModelSelect);
    applyProviderVisibility();
    return null;
  }
}

function ensureLocalModelOption(model) {
  if (!model) {
    return;
  }
  for (const select of [els.modelSelect, els.topModelSelect]) {
    const exists = Array.from(select.options).some((option) => option.value === model);
    if (!exists) {
      const option = document.createElement("option");
      option.value = model;
      option.textContent = `${model} (ATAK local)`;
      select.appendChild(option);
    }
    select.value = model;
  }
}

function renderAtakMirror(events = []) {
  els.atakMirrorLog.innerHTML = "";
  if (!events.length) {
    const empty = document.createElement("div");
    empty.className = "atak-mirror-empty";
    empty.textContent = "No ATAK plugin conversation mirrored yet.";
    els.atakMirrorLog.appendChild(empty);
    return;
  }

  for (const event of events) {
    const item = document.createElement("article");
    item.className = `atak-mirror-event ${event.role === "operator" ? "inbound" : "outbound"}`;

    const header = document.createElement("div");
    header.className = "atak-mirror-event-header";
    const source = document.createElement("span");
    source.textContent = `${event.source || "jetson"} / ${event.role || "event"}`;
    const stamp = document.createElement("time");
    stamp.dateTime = event.timestamp || "";
    stamp.textContent = event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : "";
    header.append(source, stamp);

    const body = document.createElement("div");
    body.className = "atak-mirror-event-body";
    body.textContent = event.text || "";

    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.textContent = [
      event.direction,
      event.provider,
      event.model,
    ].filter(Boolean).join(" | ");

    item.append(header, body);
    if (meta.textContent) {
      item.appendChild(meta);
    }
    els.atakMirrorLog.appendChild(item);
  }
  els.atakMirrorLog.scrollTop = els.atakMirrorLog.scrollHeight;
}

function applyAtakAgentStatus(data) {
  state.atakAgentActive = Boolean(data.active);
  els.atakMirrorPanel.classList.toggle("hidden", !state.atakAgentActive);
  if (state.atakAgentActive) {
    setAtakAgentButton("ATAK Local: active", data.status === "active" ? "good" : "warn");
    els.atakMirrorStatus.textContent = data.detail || `Mirroring ${data.model || "local model"}`;
    renderAtakMirror(data.events || []);
  } else {
    setAtakAgentButton("ATAK Local", "");
  }
}

async function refreshAtakMirror() {
  const data = await fetchJson("/api/jetson/atak-agent/mirror");
  applyAtakAgentStatus(data);
  return data;
}

function startAtakMirrorPolling() {
  if (state.atakMirrorTimer) {
    window.clearInterval(state.atakMirrorTimer);
  }
  state.atakMirrorTimer = window.setInterval(() => {
    refreshAtakMirror().catch((error) => {
      els.atakMirrorStatus.textContent = getErrorMessage(error);
      setAtakAgentButton("ATAK mirror error", "bad");
    });
  }, 2000);
}

async function loadAtakAgentStatus() {
  try {
    const data = await fetchJson("/api/jetson/atak-agent/status");
    applyAtakAgentStatus(data);
    if (data.active) {
      ensureLocalModelOption(data.model);
      startAtakMirrorPolling();
    }
  } catch (error) {
    setAtakAgentButton("ATAK status unknown", "warn");
  }
}

async function activateAtakLocalAgent() {
  els.atakAgentBtn.disabled = true;
  setAtakAgentButton("Switching ATAK...", "warn");
  try {
    const data = await fetchJson("/api/jetson/atak-agent/activate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "gemma3:4b",
        agent_profile: "tera-atak-live",
      }),
    });

    ensureLocalModelOption(data.model || "gemma3:4b");
    state.llmProvider = "ollama";
    sessionStorage.setItem("teraLlmProvider", "ollama");
    els.providerSelect.value = "ollama";
    els.agentProfileSelect.value = data.agent_profile || "tera-atak-live";
    state.localModelAvailable = true;
    els.modelsStatus.textContent = `ATAK local model: ${data.model}`;
    applyProviderVisibility();
    applyAtakAgentStatus(data);
    startAtakMirrorPolling();
  } catch (error) {
    setAtakAgentButton("ATAK switch failed", "bad");
    els.requestStatus.textContent = getErrorMessage(error);
  } finally {
    els.atakAgentBtn.disabled = false;
  }
}

function makeMapContextAppendix() {
  if (!els.includeMapContext.checked) {
    return "";
  }

  const lines = [];
  if (state.mapLocationConfirmed) {
    lines.push(`Mission map focus: ${state.mapFocusLabel} (${state.mapFocusSource}).`);
  } else {
    lines.push("Mission map focus is not confirmed; ask the planner to use map search, KML/KMZ import, or AO drawing before final source confirmation.");
  }
  if (state.selectedArea) {
    lines.push(
      `Selected AO west ${state.selectedArea.west.toFixed(6)}, south ${state.selectedArea.south.toFixed(6)}, east ${state.selectedArea.east.toFixed(6)}, north ${state.selectedArea.north.toFixed(6)}.`,
    );
  }
  return `\n\nAO context:\n${lines.join("\n")}`;
}

async function planSourcesFromMission(missionText, mapContext) {
  els.packageStatus.textContent = "Planning compact source package from mission text...";
  setChip(els.packageModeChip, "Planning", "warn");

  try {
    const data = await fetchJson("/api/source-package/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mission_text: missionText,
        map_context: mapContext,
      }),
    });
    applySourceRecommendation(data, missionText, "server");
    return data;
  } catch (error) {
    const message = getErrorMessage(error);
    const data = buildClientSourceRecommendation(missionText, mapContext, message);
    applySourceRecommendation(data, missionText, "fallback", message);
    return data;
  }
}

async function buildSourcePackage() {
  if (!state.sourceConfirmed) {
    els.packageStatus.textContent = "Confirm the recommended source list before building the manifest.";
    setWorkflowStage(1);
    return;
  }

  const selectedSources = getSelectedSources();
  const body = {
    source_ids: selectedSources.map((source) => source.id),
    mission_focus: state.sourceInference?.mission_focus || "mission-data-package",
    package_name: els.packageNameInput.value.trim() || null,
    map_context: buildMapContext(),
  };

  els.buildPackageBtn.disabled = true;
  els.packageStatus.textContent = "Building manifest...";
  hidePackageOutput();

  try {
    const data = await fetchJson("/api/source-package/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    state.packagePlan = data;
    const warningText = data.warnings?.length ? ` Warnings: ${data.warnings.join(" ")}` : "";
    renderJetsonStorage(data.storage, data.estimated_bytes, data.storage_fit, data.storage_warning);
    const fitText = data.storage_fit ? " Jetson storage check passed." : ` ${data.storage_warning || "Jetson storage check failed."}`;
    els.packageStatus.textContent = `Manifest ${data.package_id} ready with ${data.sources.length} sources.${fitText}${warningText}`;
    els.packageManifest.textContent = JSON.stringify(data.manifest, null, 2);
    els.packageManifest.classList.remove("hidden");
    els.downloadManifestLink.href = data.download_url;
    els.downloadManifestLink.download = `${data.package_name}.json`;
    els.downloadManifestLink.classList.remove("hidden");
    els.packageExecutionActions.classList.remove("hidden");
    els.downloadToJetsonBtn.disabled = !data.storage_fit;
    els.refreshPackageStatusBtn.disabled = false;
  } catch (error) {
    els.packageStatus.textContent = error instanceof Error ? error.message : String(error);
  } finally {
    updateSourceCount();
  }
}

function renderPackageExecutionStatus(status) {
  const rows = [];
  rows.push(["State", status.state || "unknown"]);
  rows.push(["Bytes", formatBytes(status.bytes_written || 0)]);
  rows.push(["Message", status.message || ""]);
  for (const operation of status.operations || []) {
    const label = operation.source_name || operation.id || "source";
    const value = `${operation.state || "planned"} ${operation.bytes_written ? `(${formatBytes(operation.bytes_written)})` : ""}`;
    rows.push([label, value]);
  }
  els.packageExecutionStatus.innerHTML = "";
  for (const [label, value] of rows) {
    const left = document.createElement("span");
    left.textContent = label;
    const right = document.createElement("strong");
    right.textContent = value;
    els.packageExecutionStatus.append(left, right);
  }
  els.packageExecutionStatus.classList.remove("hidden");
  if (status.storage) {
    renderJetsonStorage(status.storage, state.packagePlan?.estimated_bytes, state.packagePlan?.storage_fit, state.packagePlan?.storage_warning);
  }
}

async function refreshPackageArtifacts() {
  if (!state.packagePlan?.artifacts_url) {
    return null;
  }
  const artifacts = await fetchJson(state.packagePlan.artifacts_url);
  els.packageArtifacts.textContent = JSON.stringify(artifacts, null, 2);
  els.packageArtifacts.classList.remove("hidden");
  return artifacts;
}

async function refreshPackageStatus() {
  if (!state.packagePlan?.status_url) {
    return null;
  }
  const status = await fetchJson(state.packagePlan.status_url);
  renderPackageExecutionStatus(status);
  if (status.state === "succeeded" || status.state === "failed") {
    if (state.packageStatusTimer) {
      window.clearInterval(state.packageStatusTimer);
      state.packageStatusTimer = null;
    }
    els.downloadToJetsonBtn.disabled = status.state === "succeeded";
    await refreshPackageArtifacts().catch(() => null);
  }
  return status;
}

async function downloadPackageToJetson() {
  if (!state.packagePlan?.execute_url) {
    els.packageStatus.textContent = "Build the manifest before starting a Jetson download.";
    return;
  }
  els.downloadToJetsonBtn.disabled = true;
  els.packageStatus.textContent = "Starting Jetson download job...";
  try {
    const response = await fetchJson(state.packagePlan.execute_url, { method: "POST" });
    renderPackageExecutionStatus(response);
    els.packageStatus.textContent = response.message || "Jetson download job started.";
    await refreshPackageStatus();
    if (!state.packageStatusTimer) {
      state.packageStatusTimer = window.setInterval(() => {
        refreshPackageStatus().catch((error) => {
          els.packageStatus.textContent = getErrorMessage(error);
        });
      }, 2000);
    }
  } catch (error) {
    els.downloadToJetsonBtn.disabled = false;
    els.packageStatus.textContent = getErrorMessage(error);
  }
}

function providerDisplayName(provider) {
  if (provider === "auto") {
    return "auto provider";
  }
  return provider === "claude" ? "Claude" : "local Ollama";
}

async function resolveLocalModelForFallback() {
  const modelData = await loadModels();
  return (
    els.modelSelect.value.trim()
    || els.topModelSelect.value.trim()
    || modelData?.default_model
    || state.config?.default_model
    || ""
  );
}

async function streamAssistantProvider({
  assistantMessage,
  provider,
  localModel,
  cloudModel,
  finalPrompt,
  system,
  agentProfile,
  mapContext,
  sourceContext,
  metaPrefix = "",
}) {
  const providerLabel = providerDisplayName(provider);
  const baseMeta = metaPrefix ? `${metaPrefix} | ${providerLabel}` : providerLabel;
  let streamedText = "";
  let resolvedModel = provider === "ollama"
    ? localModel || "auto-detect"
    : cloudModel || localModel || "default model";
  let resolvedProvider = provider;
  const selectedLocalModel = localModel || "";
  const selectedCloudModel = cloudModel || "";

  setMessagePending(assistantMessage, `${providerLabel} is thinking`);
  ensureMessageMeta(assistantMessage, `provider: ${baseMeta} | model: ${resolvedModel} | streaming`);
  els.requestStatus.textContent = provider === "claude"
    ? "Streaming Claude response..."
    : provider === "auto"
      ? "Trying Claude, then local model if needed..."
      : "Streaming local Ollama response...";

  const response = await fetch("/api/prompt/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: finalPrompt,
      system: system || null,
      model: provider === "claude" ? null : selectedLocalModel || null,
      llm_provider: provider,
      cloud_model: provider === "ollama" ? null : selectedCloudModel || null,
      cloud_api_key: provider === "ollama" ? null : state.claudeApiKey || null,
      agent_profile: agentProfile,
      map_context: mapContext,
      source_context: sourceContext,
    }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `${response.status} ${response.statusText}`);
  }

  await readEventStream(response, (eventData) => {
    if (eventData.type === "start") {
      resolvedModel = eventData.model || resolvedModel;
      resolvedProvider = eventData.provider || resolvedProvider;
      ensureMessageMeta(assistantMessage, `provider: ${providerDisplayName(resolvedProvider)} | model: ${resolvedModel} | streaming`);
      return;
    }
    if (eventData.type === "token") {
      streamedText += eventData.text || "";
      const shouldFollowStream = isChatPinnedToBottom();
      setMessageBody(assistantMessage, streamedText);
      maybeScrollChatToBottom(shouldFollowStream);
      return;
    }
    if (eventData.type === "status") {
      els.requestStatus.textContent = eventData.detail || `Streaming ${providerLabel} response...`;
      return;
    }
    if (eventData.type === "fallback") {
      const reason = eventData.reason ? ` ${eventData.reason}` : "";
      els.providerStatus.textContent = eventData.detail || "Trying fallback model provider.";
      els.requestStatus.textContent = eventData.detail || "Trying fallback model provider.";
      ensureMessageMeta(assistantMessage, `provider: ${baseMeta} | fallback:${reason}`);
      return;
    }
    if (eventData.type === "error") {
      throw new Error(eventData.detail || `${providerLabel} request failed.`);
    }
    if (eventData.type === "done") {
      resolvedProvider = eventData.provider || resolvedProvider;
      ensureMessageMeta(assistantMessage, `provider: ${providerDisplayName(resolvedProvider)} | model: ${eventData.model || resolvedModel}`);
    }
  });

  if (!streamedText.trim()) {
    throw new Error(provider === "claude"
      ? "Claude returned an empty response."
      : "The local Ollama model returned an empty streamed response.");
  }

  if (resolvedProvider === "ollama") {
    state.localModelAvailable = true;
    state.localModelDetail = "";
    applyProviderVisibility();
  }

  return { provider: resolvedProvider, model: resolvedModel, text: streamedText };
}

async function submitPrompt(event) {
  event.preventDefault();
  els.submitBtn.disabled = true;

  const prompt = els.promptInput.value.trim();
  if (!prompt) {
    els.submitBtn.disabled = false;
    els.requestStatus.textContent = "Idle";
    return;
  }
  const system = els.systemInput.value.trim();
  const provider = state.llmProvider;
  const localModel = els.modelSelect.value.trim();
  const cloudModel = els.claudeModelSelect.value.trim();
  els.requestStatus.textContent = provider === "claude"
    ? "Connecting to Claude API..."
    : provider === "auto"
      ? "Connecting with Claude primary and local fallback..."
      : "Connecting to local model...";
  const agentProfile = els.agentProfileSelect.value;
  const finalPrompt = `${prompt}${makeMapContextAppendix()}`;
  const mapContext = els.includeMapContext.checked ? buildMapContext() : null;
  els.promptInput.value = "";
  els.requestStatus.textContent = "Planning source package...";
  try {
    await planSourcesFromMission(prompt, mapContext);
  } catch (error) {
    const message = getErrorMessage(error);
    els.packageStatus.textContent = `Source planner unavailable: ${message}`;
    setChip(els.packageModeChip, "Planner unavailable", "bad");
  }
  const sourceContext = buildSourceContext();
  const sourceRecommendation = state.sourceInference;

  appendMessage(
    "user",
    prompt,
  );

  const assistantMessage = appendMessage(
    "assistant",
    "",
    provider === "auto"
      ? `provider: Auto | Claude: ${cloudModel || "default"} | Local: ${localModel || "auto-detect"} | queued`
      : provider === "claude"
        ? `provider: Claude | model: ${cloudModel || "default"} | queued`
        : `provider: local Ollama | model: ${localModel || "auto-detect"} | queued`,
  );

  try {
    const result = await streamAssistantProvider({
      assistantMessage,
      provider,
      localModel,
      cloudModel,
      finalPrompt,
      system,
      agentProfile,
      mapContext,
      sourceContext,
    });

    if (result) {
      els.requestStatus.textContent = result.provider === "claude"
        ? `Completed with Claude ${result.model}`
        : `Completed with local Ollama ${result.model}`;
      return;
    }
  } catch (error) {
    const message = getErrorMessage(error);
    console.warn("Prompt request failed; deterministic planner response shown.", message);
    state.localModelAvailable = false;
    state.localModelDetail = message;
    applyProviderVisibility();
    setMessageBody(assistantMessage, buildDeterministicAdvisorResponse(sourceRecommendation, mapContext));
    ensureMessageMeta(assistantMessage, "deterministic planner response");
    els.requestStatus.textContent = "Deterministic planner response shown.";
  } finally {
    els.submitBtn.disabled = false;
  }
}

function rememberCamera() {
  if (!state.viewer) {
    return;
  }
  const cartographic = state.viewer.camera.positionCartographic;
  state.lastCamera = {
    lat: Cesium.Math.toDegrees(cartographic.latitude),
    lon: Cesium.Math.toDegrees(cartographic.longitude),
    heightM: cartographic.height,
  };
}

function installResizeHandling() {
  if (state.resizeObserver) {
    state.resizeObserver.disconnect();
  }
  state.resizeObserver = new ResizeObserver(() => {
    if (state.viewer) {
      state.viewer.resize();
      state.viewer.scene.requestRender();
    }
  });
  state.resizeObserver.observe(els.mapStage);
}

function makeUrlTemplateImageryProvider(source) {
  return new Cesium.UrlTemplateImageryProvider({
    url: source.url,
    credit: source.credit,
  });
}

async function resolveImageryProvider() {
  if (state.imageryMode === "esri") {
    return {
      provider: makeUrlTemplateImageryProvider(IMAGERY_FALLBACKS.esri),
      label: IMAGERY_FALLBACKS.esri.label,
      shortLabel: "Esri imagery",
      usingIon: false,
    };
  }

  if (state.imageryMode === "osm") {
    return {
      provider: makeUrlTemplateImageryProvider(IMAGERY_FALLBACKS.osm),
      label: IMAGERY_FALLBACKS.osm.label,
      shortLabel: "OSM basemap",
      usingIon: false,
    };
  }

  if (state.imageryMode === "usgs-imagery") {
    return {
      provider: makeUrlTemplateImageryProvider(IMAGERY_FALLBACKS["usgs-imagery"]),
      label: IMAGERY_FALLBACKS["usgs-imagery"].label,
      shortLabel: "USGS imagery",
      usingIon: false,
    };
  }

  if (!hasCesiumIonToken()) {
    state.imageryMode = "usgs-imagery";
    els.imagerySelect.value = "usgs-imagery";
    return {
      provider: makeUrlTemplateImageryProvider(IMAGERY_FALLBACKS["usgs-imagery"]),
      label: IMAGERY_FALLBACKS["usgs-imagery"].label,
      shortLabel: "USGS imagery",
      usingIon: false,
      fallbackReason: "Cesium ion token is not configured for World Imagery.",
    };
  }

  try {
    return {
      provider: await Cesium.createWorldImageryAsync({
        style: Cesium.IonWorldImageryStyle.AERIAL,
      }),
      label: "Cesium World Imagery",
      shortLabel: "Cesium imagery",
      usingIon: true,
    };
  } catch (error) {
    console.warn("Cesium imagery failed; using USGS imagery fallback.", error);
    state.imageryMode = "usgs-imagery";
    els.imagerySelect.value = "usgs-imagery";
    return {
      provider: makeUrlTemplateImageryProvider(IMAGERY_FALLBACKS["usgs-imagery"]),
      label: IMAGERY_FALLBACKS["usgs-imagery"].label,
      shortLabel: "USGS imagery",
      usingIon: false,
      fallbackReason: "Cesium World Imagery request failed.",
    };
  }
}

async function resolveTerrainProvider() {
  if (state.terrainMode === "ellipsoid" || !hasCesiumIonToken()) {
    const fallbackReason = state.terrainMode !== "ellipsoid" && !hasCesiumIonToken()
      ? "Cesium ion token is not configured for World Terrain."
      : "";
    if (state.terrainMode !== "ellipsoid" && !hasCesiumIonToken()) {
      state.terrainMode = "ellipsoid";
      els.terrainSelect.value = "ellipsoid";
    }
    return {
      provider: new Cesium.EllipsoidTerrainProvider(),
      label: "Terrain: Ellipsoid only",
      shortLabel: "ellipsoid terrain",
      usingIon: false,
      fallbackReason,
    };
  }
  try {
    return {
      provider: await Cesium.createWorldTerrainAsync(),
      label: "Terrain: Cesium World Terrain",
      shortLabel: "Cesium terrain",
      usingIon: true,
    };
  } catch (error) {
    console.warn("Cesium terrain failed; using ellipsoid fallback.", error);
    state.terrainMode = "ellipsoid";
    els.terrainSelect.value = "ellipsoid";
    return {
      provider: new Cesium.EllipsoidTerrainProvider(),
      label: "Terrain: Ellipsoid fallback",
      shortLabel: "ellipsoid terrain",
      usingIon: false,
      fallbackReason: "Cesium World Terrain request failed.",
    };
  }
}

function cssColor(variableName) {
  return getComputedStyle(document.documentElement).getPropertyValue(variableName).trim();
}

function cesiumCssColor(variableName) {
  return Cesium.Color.fromCssColorString(cssColor(variableName));
}

function getCartographicFromScreenPosition(position) {
  if (!state.viewer || !position) {
    return null;
  }
  const cartesian = state.viewer.scene.pickPosition(position)
    || state.viewer.camera.pickEllipsoid(position, state.viewer.scene.globe.ellipsoid);
  if (!cartesian) {
    return null;
  }
  const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
  return {
    lat: Cesium.Math.toDegrees(cartographic.latitude),
    lon: Cesium.Math.toDegrees(cartographic.longitude),
  };
}

function makeBoundsFromPoints(firstPoint, secondPoint) {
  const west = Math.min(firstPoint.lon, secondPoint.lon);
  const east = Math.max(firstPoint.lon, secondPoint.lon);
  const south = Math.min(firstPoint.lat, secondPoint.lat);
  const north = Math.max(firstPoint.lat, secondPoint.lat);
  return {
    west,
    south,
    east,
    north,
    center_lat: (south + north) / 2,
    center_lon: (west + east) / 2,
  };
}

function rectangleFromBounds(bounds) {
  return Cesium.Rectangle.fromDegrees(bounds.west, bounds.south, bounds.east, bounds.north);
}

function getAreaHandleDefinitions(bounds) {
  return [
    { key: "nw", lat: bounds.north, lon: bounds.west },
    { key: "ne", lat: bounds.north, lon: bounds.east },
    { key: "se", lat: bounds.south, lon: bounds.east },
    { key: "sw", lat: bounds.south, lon: bounds.west },
  ];
}

function clearAreaHandles() {
  if (!state.viewer) {
    state.areaHandleEntities = [];
    return;
  }
  for (const entity of state.areaHandleEntities) {
    state.viewer.entities.remove(entity);
  }
  state.areaHandleEntities = [];
}

function updateAreaHandles(bounds) {
  if (!state.viewer || !bounds) {
    return;
  }
  const handles = getAreaHandleDefinitions(bounds);
  for (const handle of handles) {
    const existing = state.areaHandleEntities.find((entity) => entity.areaHandle === handle.key);
    const position = Cesium.Cartesian3.fromDegrees(handle.lon, handle.lat, 0);
    if (existing) {
      existing.position = position;
      continue;
    }
    const entity = state.viewer.entities.add({
      position,
      point: {
        pixelSize: 11,
        color: cesiumCssColor("--color-accent-gold"),
        outlineColor: cesiumCssColor("--color-bg-primary"),
        outlineWidth: 2,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    });
    entity.areaHandle = handle.key;
    state.areaHandleEntities.push(entity);
  }
}

function getPickedAreaHandle(position) {
  if (!state.viewer || !state.selectedArea || !position) {
    return null;
  }
  const picked = state.viewer.scene.pick(position);
  const entity = picked?.id;
  if (!entity) {
    return null;
  }
  const handleEntity = state.areaHandleEntities.find((candidate) => candidate === entity);
  return handleEntity?.areaHandle || null;
}

function getResizeAnchorPoint(handleKey) {
  if (!state.selectedArea) {
    return null;
  }
  const { west, south, east, north } = state.selectedArea;
  const anchors = {
    nw: { lat: south, lon: east },
    ne: { lat: south, lon: west },
    se: { lat: north, lon: west },
    sw: { lat: north, lon: east },
  };
  return anchors[handleKey] || null;
}

function setAreaEntityBounds(bounds) {
  if (!state.viewer || !bounds) {
    return;
  }
  if (!state.areaEntity) {
    state.areaEntity = state.viewer.entities.add({
      rectangle: {
        coordinates: rectangleFromBounds(bounds),
        material: cesiumCssColor("--color-accent-gold").withAlpha(0.18),
        outline: true,
        outlineColor: cesiumCssColor("--color-accent-gold"),
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
      },
    });
    updateAreaHandles(bounds);
    return;
  }
  state.areaEntity.rectangle.coordinates = rectangleFromBounds(bounds);
  updateAreaHandles(bounds);
}

function setSelectedArea(bounds) {
  state.selectedArea = bounds;
  markMapLocationFocused("Drawn AO rectangle", "drawn-aoi");
  setAreaEntityBounds(bounds);
  updateSelectedArea();
  hidePackageOutput();
}

function clearSelectedArea() {
  state.selectedArea = null;
  state.areaStartPoint = null;
  state.areaDrawing = false;
  setCameraDragEnabled(true);
  setAreaSelectMode(false);
  if (state.viewer && state.areaEntity) {
    state.viewer.entities.remove(state.areaEntity);
  }
  state.areaEntity = null;
  clearAreaHandles();
  if (state.mapFocusSource === "drawn-aoi") {
    clearMapLocationFocus();
  }
  updateSelectedArea();
  hidePackageOutput();
}

function setAreaSelectMode(active) {
  if (active && !state.sourceConfirmed) {
    els.packageStatus.textContent = "Confirm the recommended source list before drawing AO coverage.";
    setWorkflowStage(1);
    return;
  }
  state.areaSelectActive = active;
  els.mapStage.classList.toggle("is-drawing-area", active);
  els.drawAreaBtn.textContent = active ? "Drawing AO" : "Draw AO";
  els.drawAreaBtn.setAttribute("aria-pressed", String(active));
}

function setCameraDragEnabled(enabled) {
  if (!state.viewer) {
    return;
  }
  const controller = state.viewer.scene.screenSpaceCameraController;
  controller.enableTranslate = enabled;
  controller.enableZoom = true;
  controller.enableRotate = enabled && state.mapMode === "3d";
  controller.enableTilt = enabled && state.mapMode === "3d";
  controller.enableLook = enabled && state.mapMode === "3d";
}

function finishAreaResize(position) {
  if (!state.areaResizeHandle || !state.areaResizeAnchorPoint) {
    return;
  }
  const point = getCartographicFromScreenPosition(position);
  const handleKey = state.areaResizeHandle;
  state.areaResizeHandle = null;
  state.areaResizeAnchorPoint = null;
  setCameraDragEnabled(true);
  if (!point) {
    return;
  }

  const bounds = makeBoundsFromPoints(state.areaResizeAnchorPoint, point);
  if (Math.abs(bounds.east - bounds.west) < 0.0001 || Math.abs(bounds.north - bounds.south) < 0.0001) {
    if (state.selectedArea) {
      setAreaEntityBounds(state.selectedArea);
    }
    return;
  }

  setSelectedArea(bounds);
}

function finishAreaDrawing(position) {
  if (!state.areaDrawing || !state.areaStartPoint) {
    return;
  }
  const endPoint = getCartographicFromScreenPosition(position);
  state.areaDrawing = false;
  setCameraDragEnabled(true);
  if (!endPoint) {
    setAreaSelectMode(false);
    return;
  }

  const bounds = makeBoundsFromPoints(state.areaStartPoint, endPoint);
  if (Math.abs(bounds.east - bounds.west) < 0.0001 || Math.abs(bounds.north - bounds.south) < 0.0001) {
    if (state.selectedArea) {
      setAreaEntityBounds(state.selectedArea);
    } else if (state.viewer && state.areaEntity) {
      state.viewer.entities.remove(state.areaEntity);
      state.areaEntity = null;
    }
    setAreaSelectMode(false);
    return;
  }

  setAreaSelectMode(false);
  setSelectedArea(bounds);
}

function wireMapInteraction() {
  if (state.clickHandler) {
    state.clickHandler.destroy();
    state.clickHandler = null;
  }
  const handler = new Cesium.ScreenSpaceEventHandler(state.viewer.scene.canvas);
  state.clickHandler = handler;
  handler.setInputAction((movement) => {
    const pickedHandle = getPickedAreaHandle(movement.position);
    if (pickedHandle) {
      state.areaResizeHandle = pickedHandle;
      state.areaResizeAnchorPoint = getResizeAnchorPoint(pickedHandle);
      state.areaDrawing = false;
      setAreaSelectMode(false);
      setCameraDragEnabled(false);
      return;
    }

    if (!state.areaSelectActive) {
      return;
    }
    const point = getCartographicFromScreenPosition(movement.position);
    if (!point) {
      return;
    }
    state.areaStartPoint = point;
    state.areaDrawing = true;
    setCameraDragEnabled(false);
  }, Cesium.ScreenSpaceEventType.LEFT_DOWN);

  handler.setInputAction((movement) => {
    if (state.areaResizeHandle && state.areaResizeAnchorPoint) {
      const point = getCartographicFromScreenPosition(movement.endPosition);
      if (!point) {
        return;
      }
      setAreaEntityBounds(makeBoundsFromPoints(state.areaResizeAnchorPoint, point));
      return;
    }

    if (!state.areaDrawing || !state.areaStartPoint) {
      return;
    }
    const point = getCartographicFromScreenPosition(movement.endPosition);
    if (!point) {
      return;
    }
    setAreaEntityBounds(makeBoundsFromPoints(state.areaStartPoint, point));
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);

  handler.setInputAction((movement) => {
    if (state.areaResizeHandle) {
      finishAreaResize(movement.position);
      return;
    }
    finishAreaDrawing(movement.position);
  }, Cesium.ScreenSpaceEventType.LEFT_UP);

  handler.setInputAction(() => {
    if (state.areaDrawing || state.areaResizeHandle) {
      return;
    }
    setMapMode("3d");
  }, Cesium.ScreenSpaceEventType.MIDDLE_DOWN);

  state.viewer.camera.changed.addEventListener(updateCameraText);
  updateCameraText();
}

async function buildViewer() {
  if (state.viewer) {
    rememberCamera();
    if (state.clickHandler) {
      state.clickHandler.destroy();
      state.clickHandler = null;
    }
    state.viewer.destroy();
    state.areaEntity = null;
    state.areaHandleEntities = [];
    state.overlayDataSource = null;
    state.overlayFileName = "";
    state.overlayFeatureCount = 0;
    if (state.mapFocusSource === "kml-kmz-import") {
      clearMapLocationFocus();
    }
  }

  if (hasCesiumIonToken()) {
    Cesium.Ion.defaultAccessToken = state.config.cesium_ion_token;
  }

  state.viewer = new Cesium.Viewer("cesiumContainer", {
    animation: false,
    baseLayerPicker: false,
    fullscreenButton: false,
    geocoder: false,
    homeButton: false,
    infoBox: false,
    navigationHelpButton: false,
    sceneMode: Cesium.SceneMode.SCENE2D,
    sceneModePicker: false,
    selectionIndicator: false,
    terrainProvider: new Cesium.EllipsoidTerrainProvider(),
    timeline: false,
  });
  window.__LLM_DEV_VIEWER = state.viewer;

  const requestedModes = {
    imageryMode: state.imageryMode,
    terrainMode: state.terrainMode,
  };
  const imagery = await resolveImageryProvider();
  state.viewer.imageryLayers.removeAll();
  state.viewer.imageryLayers.addImageryProvider(imagery.provider);

  const terrain = await resolveTerrainProvider();
  state.viewer.terrainProvider = terrain.provider;
  updateMapStreamChip(imagery, terrain, requestedModes);

  state.viewer.scene.globe.depthTestAgainstTerrain = false;
  applyMapModeCameraControls();
  state.viewer.camera.percentageChanged = 0.01;
  state.viewer.scene.morphComplete.addEventListener(() => {
    applyMapModeCameraControls();
    updateCameraText();
  });

  const target = state.lastCamera || {
    lat: state.config.default_lat,
    lon: state.config.default_lon,
    heightM: state.config.default_height_m,
  };

  state.viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(target.lon, target.lat, target.heightM),
    duration: 0,
  });

  els.imageryStatus.textContent = imagery.label;
  els.terrainStatus.textContent = terrain.label;
  installResizeHandling();
  state.viewer.resize();
  state.viewer.scene.requestRender();
  wireMapInteraction();
  setMapMode(state.mapMode, { animate: false });
  if (state.selectedArea) {
    setAreaEntityBounds(state.selectedArea);
  }
  updateSelectedArea();
  updateMapInstruments();
}

function resetView() {
  if (!state.viewer || !state.config) {
    return;
  }
  state.viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(
      state.config.default_lon,
      state.config.default_lat,
      state.config.default_height_m,
    ),
    duration: 1.1,
    complete: updateCameraText,
  });
  clearMapLocationFocus();
  els.requestStatus.textContent = "Map reset. Search or import the mission location before source confirmation.";
}

function kmlDescendants(root, localName) {
  return Array.from(root.getElementsByTagName("*")).filter((node) => node.localName === localName);
}

function firstKmlDescendant(root, localName) {
  return kmlDescendants(root, localName)[0] || null;
}

function readKmlText(root, localName) {
  const node = firstKmlDescendant(root, localName);
  return node?.textContent?.trim() || "";
}

function parseKmlCoordinateText(text) {
  return String(text || "")
    .trim()
    .split(/\s+/)
    .map((tuple) => tuple.split(",").map((value) => Number.parseFloat(value)))
    .filter(([lon, lat]) => Number.isFinite(lon) && Number.isFinite(lat))
    .map(([lon, lat, height]) => (
      Number.isFinite(height) ? [lon, lat, height] : [lon, lat]
    ));
}

function parseKmlGxCoordinateText(text) {
  return String(text || "")
    .trim()
    .split(/\s+/)
    .map((value) => Number.parseFloat(value))
    .filter((value) => Number.isFinite(value));
}

function closeLinearRing(points) {
  if (points.length < 3) {
    return points;
  }
  const first = points[0];
  const last = points[points.length - 1];
  if (first[0] === last[0] && first[1] === last[1]) {
    return points;
  }
  return [...points, [...first]];
}

function parseKmlPointGeometry(node) {
  const coordinates = parseKmlCoordinateText(readKmlText(node, "coordinates"))[0];
  return coordinates ? { type: "Point", coordinates } : null;
}

function parseKmlLineGeometry(node) {
  const coordinates = parseKmlCoordinateText(readKmlText(node, "coordinates"));
  return coordinates.length >= 2 ? { type: "LineString", coordinates } : null;
}

function parseKmlTrackGeometry(node) {
  const coordinates = kmlDescendants(node, "coord")
    .map((coordNode) => parseKmlGxCoordinateText(coordNode.textContent))
    .filter(([lon, lat]) => Number.isFinite(lon) && Number.isFinite(lat))
    .map(([lon, lat, height]) => (
      Number.isFinite(height) ? [lon, lat, height] : [lon, lat]
    ));
  return coordinates.length >= 2 ? { type: "LineString", coordinates } : null;
}

function parseKmlPolygonGeometry(node) {
  const outerBoundary = firstKmlDescendant(node, "outerBoundaryIs") || node;
  const outerRing = firstKmlDescendant(outerBoundary, "LinearRing");
  const outerCoordinates = closeLinearRing(parseKmlCoordinateText(readKmlText(outerRing || outerBoundary, "coordinates")));
  if (outerCoordinates.length < 4) {
    return null;
  }

  const innerCoordinates = kmlDescendants(node, "innerBoundaryIs")
    .map((innerBoundary) => {
      const innerRing = firstKmlDescendant(innerBoundary, "LinearRing");
      return closeLinearRing(parseKmlCoordinateText(readKmlText(innerRing || innerBoundary, "coordinates")));
    })
    .filter((ring) => ring.length >= 4);

  return { type: "Polygon", coordinates: [outerCoordinates, ...innerCoordinates] };
}

function extractKmlGeometries(root) {
  const geometries = [];
  for (const node of kmlDescendants(root, "Point")) {
    const geometry = parseKmlPointGeometry(node);
    if (geometry) {
      geometries.push(geometry);
    }
  }
  for (const node of kmlDescendants(root, "LineString")) {
    const geometry = parseKmlLineGeometry(node);
    if (geometry) {
      geometries.push(geometry);
    }
  }
  for (const node of kmlDescendants(root, "Track")) {
    const geometry = parseKmlTrackGeometry(node);
    if (geometry) {
      geometries.push(geometry);
    }
  }
  for (const node of kmlDescendants(root, "Polygon")) {
    const geometry = parseKmlPolygonGeometry(node);
    if (geometry) {
      geometries.push(geometry);
    }
  }
  return geometries;
}

function parseKmlToGeoJson(kmlText, sourceName) {
  const xml = new DOMParser().parseFromString(kmlText, "application/xml");
  if (xml.querySelector("parsererror")) {
    throw new Error(`${sourceName} is not valid KML XML.`);
  }

  const placemarks = kmlDescendants(xml, "Placemark");
  const features = [];
  const roots = placemarks.length ? placemarks : [xml.documentElement];

  roots.forEach((root, index) => {
    const name = readKmlText(root, "name") || `${sourceName} feature ${index + 1}`;
    const description = readKmlText(root, "description");
    for (const geometry of extractKmlGeometries(root)) {
      features.push({
        type: "Feature",
        properties: {
          name,
          description,
          source: sourceName,
        },
        geometry,
      });
    }
  });

  return {
    type: "FeatureCollection",
    features,
  };
}

function sortKmlArchiveEntries(a, b) {
  const aName = a.name.toLowerCase();
  const bName = b.name.toLowerCase();
  const aDepth = aName.split("/").length;
  const bDepth = bName.split("/").length;
  if (aDepth !== bDepth) {
    return aDepth - bDepth;
  }
  if (aName.endsWith("doc.kml") && !bName.endsWith("doc.kml")) {
    return -1;
  }
  if (bName.endsWith("doc.kml") && !aName.endsWith("doc.kml")) {
    return 1;
  }
  return aName.localeCompare(bName);
}

async function readOverlayFileText(file) {
  const lowerName = file.name.toLowerCase();
  if (lowerName.endsWith(".kml")) {
    return [{ name: file.name, text: await file.text() }];
  }

  if (!lowerName.endsWith(".kmz")) {
    throw new Error(`Unsupported overlay format: ${file.name}`);
  }
  if (!window.JSZip) {
    throw new Error("KMZ import requires JSZip to finish loading. Try again after the page is ready.");
  }

  const zip = await window.JSZip.loadAsync(await file.arrayBuffer());
  const entries = Object.values(zip.files)
    .filter((entry) => !entry.dir && entry.name.toLowerCase().endsWith(".kml"))
    .sort(sortKmlArchiveEntries);
  if (!entries.length) {
    throw new Error(`No KML document found inside ${file.name}.`);
  }

  const texts = [];
  for (const entry of entries) {
    texts.push({
      name: entry.name,
      text: await entry.async("text"),
    });
  }
  return texts;
}

async function loadParsedOverlayDataSource(file) {
  const entries = await readOverlayFileText(file);
  const features = [];
  for (const entry of entries) {
    const collection = parseKmlToGeoJson(entry.text, entry.name);
    for (const feature of collection.features) {
      features.push({
        ...feature,
        properties: {
          ...(feature.properties || {}),
          package: file.name,
        },
      });
    }
  }
  if (!features.length) {
    throw new Error(`No supported point, line, track, or polygon features were found in ${file.name}.`);
  }

  const dataSource = await Cesium.GeoJsonDataSource.load({
    type: "FeatureCollection",
    features,
  }, {
    clampToGround: true,
    markerColor: cesiumCssColor("--color-accent-gold"),
    stroke: cesiumCssColor("--color-accent-gold"),
    fill: cesiumCssColor("--color-accent-gold").withAlpha(0.2),
    strokeWidth: 3,
  });
  dataSource.name = file.name;
  styleOverlayDataSource(dataSource);
  state.overlayFeatureCount = features.length;
  return dataSource;
}

async function loadNativeOverlayDataSource(file) {
  const dataSource = await Cesium.KmlDataSource.load(file, {
    camera: state.viewer.scene.camera,
    canvas: state.viewer.scene.canvas,
    clampToGround: true,
    sourceUri: file.name,
  });
  state.overlayFeatureCount = dataSource.entities.values.length;
  return dataSource;
}

function styleOverlayDataSource(dataSource) {
  const gold = cesiumCssColor("--color-accent-gold");
  const background = cesiumCssColor("--color-bg-primary");
  const fill = gold.withAlpha(0.22);

  for (const entity of dataSource.entities.values) {
    if (entity.position) {
      entity.billboard = undefined;
      entity.point = new Cesium.PointGraphics({
        pixelSize: 11,
        color: gold,
        outlineColor: background,
        outlineWidth: 2,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      });
    }
    if (entity.polyline) {
      entity.polyline.width = 3;
      entity.polyline.material = gold;
      entity.polyline.depthFailMaterial = gold.withAlpha(0.55);
      entity.polyline.clampToGround = true;
    }
    if (entity.polygon) {
      entity.polygon.material = fill;
      entity.polygon.outline = true;
      entity.polygon.outlineColor = gold;
      entity.polygon.outlineWidth = 2;
      entity.polygon.perPositionHeight = false;
    }
  }
}

function isSupportedOverlayFile(file) {
  return /\.(kml|kmz)$/i.test(file.name);
}

async function removeCurrentOverlay() {
  if (!state.viewer || !state.overlayDataSource) {
    state.overlayDataSource = null;
    state.overlayFileName = "";
    state.overlayFeatureCount = 0;
    if (state.mapFocusSource === "kml-kmz-import") {
      clearMapLocationFocus();
    }
    return;
  }

  await state.viewer.dataSources.remove(state.overlayDataSource, true);
  state.overlayDataSource = null;
  state.overlayFileName = "";
  state.overlayFeatureCount = 0;
  if (state.mapFocusSource === "kml-kmz-import") {
    clearMapLocationFocus();
  }
}

async function importMapOverlay(file) {
  if (!file) {
    return;
  }
  if (!isSupportedOverlayFile(file)) {
    els.requestStatus.textContent = "Overlay import failed: choose a .kml or .kmz file.";
    return;
  }
  if (!state.viewer) {
    els.requestStatus.textContent = "Overlay import unavailable until the map is ready.";
    return;
  }

  els.importOverlayBtn.disabled = true;
  els.requestStatus.textContent = `Loading overlay: ${file.name}`;

  try {
    await removeCurrentOverlay();
    let dataSource;
    try {
      dataSource = await loadParsedOverlayDataSource(file);
    } catch (parseError) {
      console.warn("Parsed KML/KMZ rendering failed; trying Cesium native loader.", parseError);
      dataSource = await loadNativeOverlayDataSource(file);
    }
    state.overlayDataSource = await state.viewer.dataSources.add(dataSource);
    state.overlayFileName = file.name;
    markMapLocationFocused(file.name, "kml-kmz-import");

    if (state.overlayDataSource.entities.values.length) {
      await state.viewer.flyTo(state.overlayDataSource, { duration: 1.1 });
      updateCameraText();
      els.requestStatus.textContent = `Overlay loaded: ${file.name} (${state.overlayFeatureCount} features)`;
    } else {
      els.requestStatus.textContent = `Overlay loaded with no visible features: ${file.name}`;
    }
    state.viewer.scene.requestRender();
  } catch (error) {
    const message = getErrorMessage(error);
    await removeCurrentOverlay();
    els.requestStatus.textContent = `Overlay import failed: ${message}`;
  } finally {
    els.importOverlayBtn.disabled = false;
    els.overlayFileInput.value = "";
  }
}

function requestOverlayFile() {
  els.overlayFileInput.click();
}

function onOverlayFileSelected(event) {
  const [file] = Array.from(event.target.files || []);
  void importMapOverlay(file);
}

function togglePanel() {
  state.panelCollapsed = !state.panelCollapsed;
  applyPanelState();
}

function toggleSettingsMenu() {
  const shouldOpen = els.settingsMenu.classList.contains("hidden");
  setSettingsMenuOpen(shouldOpen);
}

function onDocumentPointerDown(event) {
  if (
    !els.locationSearchSuggestions.classList.contains("hidden")
    && !els.locationSearchPanel.contains(event.target)
  ) {
    setLocationSearchOpen(false);
  }

  if (
    !els.modelProviderMenu.classList.contains("hidden")
    && !els.modelProviderMenu.contains(event.target)
    && !els.modelProviderBtn.contains(event.target)
  ) {
    setModelProviderMenuOpen(false);
  }

  if (!els.settingsMenu.classList.contains("hidden")) {
    if (els.settingsMenu.contains(event.target) || els.settingsToggleBtn.contains(event.target)) {
      return;
    }
    setSettingsMenuOpen(false);
  }
}

function clearDocumentSelection() {
  const selection = window.getSelection?.();
  if (selection && !selection.isCollapsed) {
    selection.removeAllRanges();
  }
}

function onResizerPointerDown(event) {
  if (state.panelCollapsed) {
    return;
  }
  event.preventDefault();
  clearDocumentSelection();
  state.dragState = {
    startX: event.clientX,
    startWidth: state.panelWidth,
    pointerId: event.pointerId,
  };
  document.body.classList.add("is-resizing-panel");
  els.panelResizer.classList.add("is-dragging");
  if (typeof els.panelResizer.setPointerCapture === "function") {
    els.panelResizer.setPointerCapture(event.pointerId);
  }
  window.addEventListener("pointermove", onResizerPointerMove);
  window.addEventListener("pointerup", onResizerPointerUp, { once: true });
  window.addEventListener("pointercancel", onResizerPointerUp, { once: true });
}

function onResizerPointerMove(event) {
  if (!state.dragState) {
    return;
  }
  event.preventDefault();
  clearDocumentSelection();
  const delta = state.dragState.startX - event.clientX;
  state.panelWidth = clampPanelWidth(state.dragState.startWidth + delta);
  els.workspaceShell.style.setProperty("--panel-width", `${state.panelWidth}px`);
  if (state.viewer) {
    state.viewer.resize();
    state.viewer.scene.requestRender();
  }
}

function onResizerPointerUp(event) {
  if (event) {
    event.preventDefault();
  }
  if (
    state.dragState
    && typeof els.panelResizer.releasePointerCapture === "function"
    && els.panelResizer.hasPointerCapture?.(state.dragState.pointerId)
  ) {
    els.panelResizer.releasePointerCapture(state.dragState.pointerId);
  }
  state.dragState = null;
  document.body.classList.remove("is-resizing-panel");
  els.panelResizer.classList.remove("is-dragging");
  window.removeEventListener("pointermove", onResizerPointerMove);
  window.removeEventListener("pointerup", onResizerPointerUp);
  window.removeEventListener("pointercancel", onResizerPointerUp);
  clearDocumentSelection();
}

function onPromptInputKeyDown(event) {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) {
    return;
  }

  event.preventDefault();
  if (els.submitBtn.disabled) {
    return;
  }

  if (typeof els.promptForm.requestSubmit === "function") {
    els.promptForm.requestSubmit();
    return;
  }

  els.submitBtn.click();
}

async function streamSelectedSources() {
  if (state.selectedSourceIds.has("cesium_world_imagery") && hasCesiumIonToken()) {
    state.imageryMode = "ion-satellite";
  } else if (state.selectedSourceIds.has("usgs_imagery_only")) {
    state.imageryMode = "usgs-imagery";
  } else if (state.selectedSourceIds.has("esri_world_imagery")) {
    state.imageryMode = "esri";
  } else if (state.selectedSourceIds.has("osm_basemap")) {
    state.imageryMode = "osm";
  }

  state.terrainMode = state.selectedSourceIds.has("cesium_world_terrain")
    && hasCesiumIonToken()
    ? "cesium-world"
    : "ellipsoid";

  els.imagerySelect.value = state.imageryMode;
  els.terrainSelect.value = state.terrainMode;
  els.packageStatus.textContent = "Updating map stream preview...";
  await buildViewer();
  els.packageStatus.textContent = `Preview streaming ${els.imageryStatus.textContent}.`;
}

async function init() {
  clearChat();
  applyPanelState();
  updateSelectedArea();

  if (!state.handlersBound) {
    els.promptForm.addEventListener("submit", submitPrompt);
    els.promptInput.addEventListener("keydown", onPromptInputKeyDown);
    els.clearChatBtn.addEventListener("click", clearChat);
    els.resetViewBtn.addEventListener("click", resetView);
    els.mapResetViewBtn.addEventListener("click", resetView);
    els.mapModeToggleBtn.addEventListener("click", toggleMapMode);
    els.importOverlayBtn.addEventListener("click", requestOverlayFile);
    els.overlayFileInput.addEventListener("change", onOverlayFileSelected);
    els.atakAgentBtn.addEventListener("click", activateAtakLocalAgent);
    els.atakMirrorRefreshBtn.addEventListener("click", () => {
      refreshAtakMirror().catch((error) => {
        els.atakMirrorStatus.textContent = getErrorMessage(error);
      });
    });
    els.locationSearchForm.addEventListener("submit", onLocationSearchSubmit);
    els.locationSearchInput.addEventListener("input", onLocationSearchInput);
    els.locationSearchInput.addEventListener("keydown", onLocationSearchKeyDown);
    els.modelProviderBtn.addEventListener("click", () => {
      const shouldOpen = els.modelProviderMenu.classList.contains("hidden");
      setModelProviderMenuOpen(shouldOpen);
      if (shouldOpen && (state.llmProvider === "ollama" || state.llmProvider === "auto")) {
        void loadModels();
      }
    });
    els.providerSelect.addEventListener("change", (event) => {
      state.llmProvider = event.target.value;
      applyProviderVisibility();
      if (state.llmProvider === "ollama" || state.llmProvider === "auto") {
        void loadModels();
      }
    });
    els.topModelSelect.addEventListener("change", () => {
      els.modelSelect.value = els.topModelSelect.value;
      applyProviderVisibility();
    });
    els.modelSelect.addEventListener("change", () => {
      els.topModelSelect.value = els.modelSelect.value;
      applyProviderVisibility();
    });
    els.claudeModelSelect.addEventListener("change", applyProviderVisibility);
    els.claudeApiKeyInput.addEventListener("input", () => {
      state.claudeApiKey = els.claudeApiKeyInput.value.trim();
      applyProviderVisibility();
    });
    els.saveProviderBtn.addEventListener("click", applyProviderSelection);
    els.clearClaudeKeyBtn.addEventListener("click", clearClaudeKey);
    els.panelToggleBtn.addEventListener("click", togglePanel);
    els.settingsToggleBtn.addEventListener("click", toggleSettingsMenu);
    els.panelResizer.addEventListener("pointerdown", onResizerPointerDown);
    els.workflowPrevBtn.addEventListener("click", () => {
      setWorkflowStage(state.workflowStageIndex - 1);
    });
    els.workflowNextBtn.addEventListener("click", () => {
      setWorkflowStage(state.workflowStageIndex + 1);
    });
    els.confirmSourcesBtn.addEventListener("click", confirmSources);
    els.drawAreaBtn.addEventListener("click", () => {
      setAreaSelectMode(!state.areaSelectActive);
    });
    els.clearAreaBtn.addEventListener("click", clearSelectedArea);
    els.streamSelectedBtn.addEventListener("click", streamSelectedSources);
    els.buildPackageBtn.addEventListener("click", buildSourcePackage);
    els.downloadToJetsonBtn.addEventListener("click", downloadPackageToJetson);
    els.refreshPackageStatusBtn.addEventListener("click", () => {
      refreshPackageStatus().catch((error) => {
        els.packageStatus.textContent = getErrorMessage(error);
      });
    });
    els.imagerySelect.addEventListener("change", async (event) => {
      state.imageryMode = event.target.value;
      await buildViewer();
    });
    els.terrainSelect.addEventListener("change", async (event) => {
      state.terrainMode = event.target.value;
      await buildViewer();
    });
    window.addEventListener("resize", () => {
      state.panelWidth = clampPanelWidth(state.panelWidth);
      if (!state.panelCollapsed) {
        els.workspaceShell.style.setProperty("--panel-width", `${state.panelWidth}px`);
      }
      if (state.viewer) {
        state.viewer.resize();
        state.viewer.scene.requestRender();
      }
    });
    document.addEventListener("pointerdown", onDocumentPointerDown);
    state.handlersBound = true;
  }

  await loadRuntimeConfig();
  await loadModels();
  await loadAtakAgentStatus();
  await loadDataSources();
  await loadJetsonStorage();
  await buildViewer();
}

init().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  setChip(els.tokenChip, "Workspace failed to initialize", "bad");
  appendMessage("assistant", message, "startup error");
  els.requestStatus.textContent = "Startup failed";
});
