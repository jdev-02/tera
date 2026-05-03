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
  imageryMode: "esri",
  terrainMode: "cesium-world",
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
  locationSearchMatches: [],
  activeLocationSearchIndex: -1,
  mapFocusLabel: "",
  mapFocusSource: "",
  mapLocationConfirmed: false,
  locationSearchTimer: null,
  locationSearchRequestId: 0,
  localModelAvailable: false,
  localModelDetail: "",
  llmProvider: sessionStorage.getItem("teraLlmProvider") || "ollama",
  claudeApiKey: sessionStorage.getItem("teraClaudeApiKey") || "",
  selectedSourceIds: new Set(),
  packagePlan: null,
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
  panelToggleBtn: document.getElementById("panelToggleBtn"),
  panelResizer: document.getElementById("panelResizer"),
  workspaceShell: document.querySelector(".workspace-shell"),
  agentPanel: document.getElementById("agentPanel"),
  sourcePanel: document.getElementById("sourcePanel"),
  mapStage: document.querySelector(".map-stage"),
  mapResetViewBtn: document.getElementById("mapResetViewBtn"),
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
  clarifyingQuestions: document.getElementById("clarifyingQuestions"),
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
    key: "questions",
    label: "Questions",
    meta: "Broaden or limit scope",
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
  osm: {
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    credit: "OpenStreetMap contributors",
    label: "OpenStreetMap",
  },
};

const FALLBACK_PRIMARY_STREAM_SOURCE_IDS = [
  "esri_world_imagery",
  "cesium_world_terrain",
  "osm_basemap",
];

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
    purpose: "Streamable visual basemap for AO inspection and imagery context.",
    stream_status: "streamable",
    download_status: "manifest-only",
    stream_layer: "esri",
  },
  {
    id: "cesium_world_terrain",
    name: "Cesium World Terrain",
    provider: "Cesium ion",
    category: "terrain-display",
    purpose: "Streamable 3D terrain preview for landform awareness.",
    stream_status: "streamable-with-token",
    download_status: "cache-via-cesium-pipeline",
    stream_layer: "cesium-world",
  },
  {
    id: "esri_world_elevation",
    name: "Esri World Elevation Terrain",
    provider: "Esri ArcGIS Online / Living Atlas",
    category: "terrain",
    purpose: "Queryable elevation terrain fallback for AO sampling, slope, hillshade, and viewshed preflight.",
    stream_status: "queryable-online",
    download_status: "download-required",
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
    name: "Copernicus DEM",
    provider: "Copernicus",
    category: "terrain",
    purpose: "Global elevation fallback for slope, viewshed, and terrain-cost analysis.",
    stream_status: "not-streamed",
    download_status: "download-required",
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
    provider: "ESA Copernicus",
    category: "imagery-analysis",
    purpose: "Analysis imagery for vegetation, water, burn, and surface-condition indices.",
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

function parseCoordinateQuery(query) {
  const trimmed = query.trim();
  if (!trimmed) {
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
  const normalizedQuery = normalizeSearchText(query);
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
      score += 110;
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
  const coordinate = parseCoordinateQuery(query);
  const scored = LOCATION_GAZETTEER
    .map((candidate) => ({
      ...candidate,
      source: "gazetteer",
      score: scoreLocationCandidate(candidate, query),
    }))
    .filter((candidate) => candidate.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, LOCATION_SEARCH_LIMIT);

  if (coordinate) {
    return [coordinate, ...scored].slice(0, LOCATION_SEARCH_LIMIT);
  }
  return scored;
}

function normalizeServerLocationSuggestion(suggestion) {
  return {
    name: suggestion.name,
    detail: suggestion.detail || `${Number(suggestion.lat).toFixed(5)}, ${Number(suggestion.lon).toFixed(5)}`,
    lat: Number(suggestion.lat),
    lon: Number(suggestion.lon),
    heightM: Number(suggestion.height_m || suggestion.heightM || 12000),
    source: suggestion.source || "online-geocoder",
  };
}

function mergeLocationSuggestions(primaryMatches, incomingMatches) {
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
    merged.push(match);
  }
  return merged.slice(0, LOCATION_SEARCH_LIMIT);
}

async function refreshOnlineLocationSuggestions(query, requestId, localMatches) {
  try {
    const data = await fetchJson(`/api/location-search?q=${encodeURIComponent(query)}`);
    if (requestId !== state.locationSearchRequestId) {
      return;
    }
    const serverMatches = Array.isArray(data.suggestions)
      ? data.suggestions.map(normalizeServerLocationSuggestion)
      : [];
    state.locationSearchMatches = mergeLocationSuggestions(localMatches, serverMatches);
    renderLocationSearchSuggestions();
  } catch (_error) {
    if (requestId === state.locationSearchRequestId && !state.locationSearchMatches.length) {
      setLocationSearchOpen(false);
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
      void commitLocationSearch();
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
  const query = els.locationSearchInput.value.trim();
  let matches = state.locationSearchMatches.length
    ? state.locationSearchMatches
    : getLocationSearchSuggestions(query);
  const index = state.activeLocationSearchIndex >= 0 ? state.activeLocationSearchIndex : 0;
  let suggestion = matches[index] || matches[0];
  if (!suggestion && query.length >= 2) {
    try {
      const data = await fetchJson(`/api/location-search?q=${encodeURIComponent(query)}`);
      const serverMatches = Array.isArray(data.suggestions)
        ? data.suggestions.map(normalizeServerLocationSuggestion)
        : [];
      matches = mergeLocationSuggestions([], serverMatches);
      state.locationSearchMatches = matches;
      suggestion = matches[0];
    } catch (_error) {
      suggestion = null;
    }
  }
  if (!suggestion) {
    els.requestStatus.textContent = "No local match. Paste decimal coordinates or import a KML/KMZ overlay.";
    setLocationSearchOpen(false);
    return;
  }
  flyToLocationSuggestion(suggestion);
}

function onLocationSearchInput() {
  const query = els.locationSearchInput.value.trim();
  window.clearTimeout(state.locationSearchTimer);
  state.locationSearchRequestId += 1;
  if (query.length < 2) {
    state.locationSearchMatches = [];
    setLocationSearchOpen(false);
    return;
  }
  const localMatches = getLocationSearchSuggestions(query);
  state.locationSearchMatches = localMatches;
  renderLocationSearchSuggestions();
  const requestId = state.locationSearchRequestId;
  state.locationSearchTimer = window.setTimeout(() => {
    void refreshOnlineLocationSuggestions(query, requestId, localMatches);
  }, 240);
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

function applyProviderVisibility() {
  const isClaude = state.llmProvider === "claude";
  els.providerSelect.value = state.llmProvider;
  els.providerLocalModelRow.classList.toggle("hidden", isClaude);
  els.providerClaudeModelRow.classList.toggle("hidden", !isClaude);
  els.providerClaudeKeyRow.classList.toggle("hidden", !isClaude);
  if (state.claudeApiKey) {
    els.claudeApiKeyInput.value = state.claudeApiKey;
  }
  if (isClaude) {
    setModelProviderButton(`Claude: ${els.claudeModelSelect.value}`, state.claudeApiKey ? "good" : "warn");
    els.providerStatus.textContent = state.claudeApiKey ? "Claude API key loaded for this session" : "Claude key required";
  } else {
    const label = els.modelSelect.value || els.topModelSelect.value || state.config?.default_model || "local model";
    const tone = state.localModelAvailable ? "good" : "warn";
    setModelProviderButton(state.localModelAvailable ? `Local: ${label}` : "Local model offline; rules active", tone);
    els.providerStatus.textContent = state.localModelAvailable
      ? "Local Ollama available"
      : "Local model offline; deterministic planner remains active";
  }
}

function applyProviderSelection() {
  state.llmProvider = els.providerSelect.value;
  state.claudeApiKey = els.claudeApiKeyInput.value.trim();
  if (state.llmProvider === "claude" && !state.claudeApiKey) {
    applyProviderVisibility();
    els.providerStatus.textContent = "Claude API key required before switching providers";
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

  if (state.llmProvider === "ollama") {
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

function renderClarifyingQuestions() {
  els.clarifyingQuestions.replaceChildren();
  const questions = state.sourceInference?.clarifying_questions || [];

  if (!questions.length) {
    const item = document.createElement("li");
    item.textContent = state.sourceInference
      ? "No additional Socratic question is needed. Review the working sources or describe a constraint in chat."
      : "Socratic source questions will appear after the first mission description.";
    els.clarifyingQuestions.appendChild(item);
    return;
  }

  for (const question of questions) {
    const item = document.createElement("li");
    item.textContent = question;
    els.clarifyingQuestions.appendChild(item);
  }
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

  renderClarifyingQuestions();
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

  appendUniqueSourceIds(optionalIds, "esri_world_imagery", "osm_basemap");
  rationale.push("Esri imagery and OSM basemap stay as lightweight preview/context layers.");

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

  if (needsRouting) {
    appendUniqueSourceIds(requiredIds, "osm_extract");
    rationale.push("OSM PBF is required for the local routable graph and feature lookup.");
  }
  if (needsTerrain) {
    appendUniqueSourceIds(requiredIds, isUsContext ? "usgs_3dep" : "copernicus_dem");
    appendUniqueSourceIds(requiredIds, "esri_world_elevation");
    appendUniqueSourceIds(optionalIds, "cesium_world_terrain");
    rationale.push("Analysis DEM plus queryable Esri terrain fallback is required for slope, exposure, hydrology, and cost surfaces.");
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
    appendUniqueSourceIds(optionalIds, "sentinel_2");
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
      appendUniqueSourceIds(requiredIds, isUsContext ? "usgs_3dep" : "copernicus_dem");
      appendUniqueSourceIds(requiredIds, "esri_world_elevation");
    }
    rationale.push("Signal planning requires DEM-derived viewsheds plus tower or high-ground candidates.");
  }
  if (needsCurrentImagery && !needsWater && !needsHazards) {
    appendUniqueSourceIds(optionalIds, "sentinel_2");
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
  const previewIds = optionalIds.filter((sourceId) => ["esri_world_imagery", "osm_basemap"].includes(sourceId));
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
  els.packageStatus.textContent = `Drafted ${state.selectedSourceIds.size} working sources.${fallbackText} Use Questions to scope, then confirm sources.`;
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
    article.className = "source-item compact-source-item";
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
  setWorkflowStage(3);
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

async function loadRuntimeConfig() {
  state.config = await fetchJson("/api/config");
  const hasToken = Boolean(state.config.cesium_ion_token);
  setChip(els.tokenChip, hasToken ? "Cesium token detected" : "Cesium token missing", hasToken ? "good" : "warn");
  els.claudeModelSelect.value = state.config.claude_default_model || els.claudeModelSelect.value;
  setModelProviderButton(`Default model: ${state.config.default_model}`, "warn");
  state.imageryMode = "esri";
  state.terrainMode = hasToken ? "cesium-world" : "ellipsoid";
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
      return;
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
      return;
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

    els.modelsStatus.textContent = `${data.models.length} model${data.models.length === 1 ? "" : "s"} available`;
    syncModelSelects(els.modelSelect, els.topModelSelect);
    applyProviderVisibility();
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
    setWorkflowStage(2);
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
    els.packageStatus.textContent = `Manifest ${data.package_id} ready with ${data.sources.length} sources.${warningText}`;
    els.packageManifest.textContent = JSON.stringify(data.manifest, null, 2);
    els.packageManifest.classList.remove("hidden");
    els.downloadManifestLink.href = data.download_url;
    els.downloadManifestLink.download = `${data.package_name}.json`;
    els.downloadManifestLink.classList.remove("hidden");
  } catch (error) {
    els.packageStatus.textContent = error instanceof Error ? error.message : String(error);
  } finally {
    updateSourceCount();
  }
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
  const model = provider === "claude"
    ? els.claudeModelSelect.value.trim()
    : els.modelSelect.value.trim();
  els.requestStatus.textContent = provider === "claude"
    ? "Connecting to Claude API..."
    : "Connecting to local model...";
  if (provider === "claude" && !state.claudeApiKey) {
    els.submitBtn.disabled = false;
    els.requestStatus.textContent = "Claude API key required";
    els.providerStatus.textContent = "Enter a Claude API key to use cloud inference";
    setModelProviderMenuOpen(true);
    els.claudeApiKeyInput.focus();
    return;
  }
  const agentProfile = els.agentProfileSelect.value;
  const finalPrompt = `${prompt}${makeMapContextAppendix()}`;
  const mapContext = els.includeMapContext.checked ? buildMapContext() : null;
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
    finalPrompt,
    [
      model ? `model: ${model}` : "default model",
      `provider: ${provider}`,
      `profile: ${agentProfile}`,
      `focus: ${sourceContext.mission_focus}`,
      `${sourceContext.selected_source_ids.length} sources`,
    ].join(" | "),
  );

  let activeAssistantMessage = null;

  if (provider === "ollama" && !state.localModelAvailable) {
    appendMessage(
      "assistant",
      buildDeterministicAdvisorResponse(sourceRecommendation, mapContext),
      "deterministic source advisor | local model offline",
    );
    els.requestStatus.textContent = "Local model offline; deterministic advisor response shown";
    els.promptInput.value = "";
    els.submitBtn.disabled = false;
    return;
  }

  try {
    const assistantMessage = appendMessage(
      "assistant",
      "",
      model ? `model: ${model} | streaming` : "streaming",
    );
    activeAssistantMessage = assistantMessage;
    setMessagePending(assistantMessage);
    const response = await fetch("/api/prompt/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: finalPrompt,
        system: system || null,
        model: model || null,
        llm_provider: provider,
        cloud_model: provider === "claude" ? model : null,
        cloud_api_key: provider === "claude" ? state.claudeApiKey || null : null,
        agent_profile: agentProfile,
        map_context: mapContext,
        source_context: sourceContext,
      }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || `${response.status} ${response.statusText}`);
    }

    let streamedText = "";
    let resolvedModel = model || "default model";

    els.requestStatus.textContent = "Streaming response...";

    await readEventStream(response, (eventData) => {
      if (eventData.type === "start") {
        resolvedModel = eventData.model || resolvedModel;
        ensureMessageMeta(assistantMessage, `model: ${resolvedModel} | streaming`);
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
        els.requestStatus.textContent = eventData.detail || "Streaming response...";
        return;
      }
      if (eventData.type === "error") {
        throw new Error(eventData.detail || "Streaming request failed.");
      }
      if (eventData.type === "done") {
        ensureMessageMeta(assistantMessage, `model: ${eventData.model || resolvedModel}`);
      }
    });

    if (!streamedText.trim()) {
      throw new Error(provider === "claude"
        ? "Claude returned an empty response."
        : "The local model returned an empty streamed response.");
    }

    els.requestStatus.textContent = `Completed with ${resolvedModel}`;
    els.promptInput.value = "";
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (provider === "ollama") {
      state.localModelAvailable = false;
      state.localModelDetail = message;
      applyProviderVisibility();
    } else {
      els.providerStatus.textContent = `Claude request failed: ${message}`;
    }
    const fallbackMeta = provider === "claude"
      ? "deterministic fallback | Claude request failed"
      : "deterministic fallback | local model unavailable";
    if (activeAssistantMessage) {
      setMessageBody(activeAssistantMessage, buildDeterministicAdvisorResponse(sourceRecommendation, mapContext));
      ensureMessageMeta(activeAssistantMessage, fallbackMeta);
    } else {
      appendMessage(
        "assistant",
        buildDeterministicAdvisorResponse(sourceRecommendation, mapContext),
        fallbackMeta,
      );
    }
    els.requestStatus.textContent = provider === "claude"
      ? `Claude request failed; deterministic advisor response shown (${message})`
      : `Local model unavailable; deterministic advisor response shown (${message})`;
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
    };
  }

  if (state.imageryMode === "osm") {
    return {
      provider: makeUrlTemplateImageryProvider(IMAGERY_FALLBACKS.osm),
      label: IMAGERY_FALLBACKS.osm.label,
    };
  }

  if (!state.config.cesium_ion_token) {
    state.imageryMode = "esri";
    els.imagerySelect.value = "esri";
    return {
      provider: makeUrlTemplateImageryProvider(IMAGERY_FALLBACKS.esri),
      label: IMAGERY_FALLBACKS.esri.label,
    };
  }

  try {
    return {
      provider: await Cesium.createWorldImageryAsync({
        style: Cesium.IonWorldImageryStyle.AERIAL,
      }),
      label: "Cesium World Imagery",
    };
  } catch (error) {
    console.warn("Cesium imagery failed; using Esri fallback.", error);
    state.imageryMode = "esri";
    els.imagerySelect.value = "esri";
    return {
      provider: makeUrlTemplateImageryProvider(IMAGERY_FALLBACKS.esri),
      label: IMAGERY_FALLBACKS.esri.label,
    };
  }
}

async function resolveTerrainProvider() {
  if (state.terrainMode === "ellipsoid" || !state.config.cesium_ion_token) {
    if (state.terrainMode !== "ellipsoid" && !state.config.cesium_ion_token) {
      state.terrainMode = "ellipsoid";
      els.terrainSelect.value = "ellipsoid";
    }
    return {
      provider: new Cesium.EllipsoidTerrainProvider(),
      label: "Terrain: Ellipsoid only",
    };
  }
  try {
    return {
      provider: await Cesium.createWorldTerrainAsync(),
      label: "Terrain: Cesium World Terrain",
    };
  } catch (error) {
    console.warn("Cesium terrain failed; using ellipsoid fallback.", error);
    state.terrainMode = "ellipsoid";
    els.terrainSelect.value = "ellipsoid";
    return {
      provider: new Cesium.EllipsoidTerrainProvider(),
      label: "Terrain: Ellipsoid fallback",
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
    setWorkflowStage(2);
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
  controller.enableRotate = enabled;
  controller.enableTranslate = enabled;
  controller.enableTilt = enabled;
  controller.enableLook = enabled;
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
    if (state.mapFocusSource === "kml-kmz-import") {
      clearMapLocationFocus();
    }
  }

  if (state.config.cesium_ion_token) {
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
    sceneModePicker: false,
    selectionIndicator: false,
    terrainProvider: new Cesium.EllipsoidTerrainProvider(),
    timeline: false,
  });
  window.__LLM_DEV_VIEWER = state.viewer;

  const imagery = await resolveImageryProvider();
  state.viewer.imageryLayers.removeAll();
  state.viewer.imageryLayers.addImageryProvider(imagery.provider);

  const terrain = await resolveTerrainProvider();
  state.viewer.terrainProvider = terrain.provider;

  state.viewer.scene.globe.depthTestAgainstTerrain = false;
  state.viewer.scene.screenSpaceCameraController.enableCollisionDetection = true;
  state.viewer.camera.percentageChanged = 0.01;

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

function isSupportedOverlayFile(file) {
  return /\.(kml|kmz)$/i.test(file.name);
}

async function removeCurrentOverlay() {
  if (!state.viewer || !state.overlayDataSource) {
    state.overlayDataSource = null;
    state.overlayFileName = "";
    if (state.mapFocusSource === "kml-kmz-import") {
      clearMapLocationFocus();
    }
    return;
  }

  await state.viewer.dataSources.remove(state.overlayDataSource, true);
  state.overlayDataSource = null;
  state.overlayFileName = "";
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
    const dataSource = await Cesium.KmlDataSource.load(file, {
      camera: state.viewer.scene.camera,
      canvas: state.viewer.scene.canvas,
      clampToGround: true,
      sourceUri: file.name,
    });
    state.overlayDataSource = await state.viewer.dataSources.add(dataSource);
    state.overlayFileName = file.name;
    markMapLocationFocused(file.name, "kml-kmz-import");

    if (state.overlayDataSource.entities.values.length) {
      await state.viewer.flyTo(state.overlayDataSource, { duration: 1.1 });
      updateCameraText();
      els.requestStatus.textContent = `Overlay loaded: ${file.name}`;
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
  if (state.selectedSourceIds.has("esri_world_imagery")) {
    state.imageryMode = "esri";
  } else if (state.selectedSourceIds.has("cesium_world_imagery") && state.config?.cesium_ion_token) {
    state.imageryMode = "ion-satellite";
  } else if (state.selectedSourceIds.has("osm_basemap")) {
    state.imageryMode = "osm";
  }

  state.terrainMode = state.selectedSourceIds.has("cesium_world_terrain")
    && state.config?.cesium_ion_token
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
    els.importOverlayBtn.addEventListener("click", requestOverlayFile);
    els.overlayFileInput.addEventListener("change", onOverlayFileSelected);
    els.locationSearchForm.addEventListener("submit", onLocationSearchSubmit);
    els.locationSearchInput.addEventListener("input", onLocationSearchInput);
    els.locationSearchInput.addEventListener("keydown", onLocationSearchKeyDown);
    els.modelProviderBtn.addEventListener("click", () => {
      setModelProviderMenuOpen(els.modelProviderMenu.classList.contains("hidden"));
    });
    els.providerSelect.addEventListener("change", (event) => {
      state.llmProvider = event.target.value;
      applyProviderVisibility();
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
  await loadDataSources();
  await buildViewer();
}

init().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  setChip(els.tokenChip, "Workspace failed to initialize", "bad");
  appendMessage("assistant", message, "startup error");
  els.requestStatus.textContent = "Startup failed";
});
