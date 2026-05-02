const MISSION_DEFAULT_SOURCE_IDS = {
  "terrain-routing": [
    "esri_world_imagery",
    "cesium_world_terrain",
    "osm_basemap",
    "osm_extract",
    "usgs_3dep",
    "nlcd",
    "pad_us",
  ],
  "water-access": [
    "esri_world_imagery",
    "osm_basemap",
    "osm_extract",
    "usgs_3dep",
    "usgs_3dhp",
    "nhdplus_hr",
    "nwis",
    "sentinel_2",
  ],
  "sar-planning": [
    "esri_world_imagery",
    "cesium_world_terrain",
    "osm_basemap",
    "osm_extract",
    "usgs_3dep",
    "nlcd",
    "usgs_3dhp",
    "naip",
    "noaa_alerts",
    "pad_us",
    "blm_usfs_nps",
  ],
  evacuation: [
    "esri_world_imagery",
    "osm_basemap",
    "osm_extract",
    "usgs_3dep",
    "nlcd",
    "noaa_alerts",
    "fema_flood",
    "pad_us",
    "blm_usfs_nps",
  ],
  "signal-planning": [
    "esri_world_imagery",
    "cesium_world_terrain",
    "osm_basemap",
    "osm_extract",
    "usgs_3dep",
    "fcc_towers",
    "osm_towers",
    "viewshed_surfaces",
  ],
  "hazard-routing": [
    "esri_world_imagery",
    "osm_basemap",
    "osm_extract",
    "usgs_3dep",
    "noaa_alerts",
    "nasa_firms",
    "fema_flood",
    "sentinel_1_sar",
  ],
  "access-control": [
    "esri_world_imagery",
    "osm_basemap",
    "osm_extract",
    "pad_us",
    "blm_usfs_nps",
    "parcels_boundaries",
  ],
  "imagery-preview": [
    "esri_world_imagery",
    "cesium_world_terrain",
    "osm_basemap",
    "sentinel_2",
    "landsat_collection_2",
    "naip",
  ],
};

const state = {
  config: null,
  viewer: null,
  clickHandler: null,
  resizeObserver: null,
  selectedPoint: null,
  markerEntity: null,
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
  selectedSourceIds: new Set(),
  packagePlan: null,
};

const els = {
  tokenChip: document.getElementById("tokenChip"),
  ollamaChip: document.getElementById("ollamaChip"),
  settingsToggleBtn: document.getElementById("settingsToggleBtn"),
  settingsMenu: document.getElementById("settingsMenu"),
  agentProfileSelect: document.getElementById("agentProfileSelect"),
  imagerySelect: document.getElementById("imagerySelect"),
  terrainSelect: document.getElementById("terrainSelect"),
  resetViewBtn: document.getElementById("resetViewBtn"),
  panelToggleBtn: document.getElementById("panelToggleBtn"),
  panelResizer: document.getElementById("panelResizer"),
  workspaceShell: document.querySelector(".workspace-shell"),
  agentPanel: document.getElementById("agentPanel"),
  mapStage: document.querySelector(".map-stage"),
  previewStatus: document.getElementById("previewStatus"),
  promptForm: document.getElementById("promptForm"),
  promptInput: document.getElementById("promptInput"),
  modelSelect: document.getElementById("modelSelect"),
  systemInput: document.getElementById("systemInput"),
  includeMapPoint: document.getElementById("includeMapPoint"),
  submitBtn: document.getElementById("submitBtn"),
  clearChatBtn: document.getElementById("clearChatBtn"),
  requestStatus: document.getElementById("requestStatus"),
  modelsStatus: document.getElementById("modelsStatus"),
  modelsList: document.getElementById("modelsList"),
  selectedPoint: document.getElementById("selectedPoint"),
  cameraPosition: document.getElementById("cameraPosition"),
  imageryStatus: document.getElementById("imageryStatus"),
  terrainStatus: document.getElementById("terrainStatus"),
  chatLog: document.getElementById("chatLog"),
  chatMeta: document.getElementById("chatMeta"),
  mapHint: document.getElementById("mapHint"),
  sourceCount: document.getElementById("sourceCount"),
  sourceList: document.getElementById("sourceList"),
  missionFocusSelect: document.getElementById("missionFocusSelect"),
  packageNameInput: document.getElementById("packageNameInput"),
  selectRecommendedBtn: document.getElementById("selectRecommendedBtn"),
  streamSelectedBtn: document.getElementById("streamSelectedBtn"),
  buildPackageBtn: document.getElementById("buildPackageBtn"),
  packageStatus: document.getElementById("packageStatus"),
  packageManifest: document.getElementById("packageManifest"),
  downloadManifestLink: document.getElementById("downloadManifestLink"),
};

window.__TERA_SOURCE_STATE = state;
window.__LLM_DEV_STATE = state;

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

function setChip(node, text, tone = "") {
  node.textContent = text;
  node.className = `chip${tone ? ` ${tone}` : ""}`;
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `${response.status} ${response.statusText}`);
  }
  return data;
}

function appendMessage(role, body, meta = "") {
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
  els.chatLog.scrollTop = els.chatLog.scrollHeight;
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

function getSelectedSources() {
  return state.dataSources.filter((source) => state.selectedSourceIds.has(source.id));
}

function formatSourceStatus(source) {
  const stream = source.stream_status.replace(/-/g, " ");
  const download = source.download_status.replace(/-/g, " ");
  return `${stream} / ${download}`;
}

function updateSourceCount() {
  const selectedCount = state.selectedSourceIds.size;
  const total = state.dataSources.length;
  els.sourceCount.textContent = `${selectedCount} selected of ${total} sources`;
  els.buildPackageBtn.disabled = selectedCount === 0;
  els.streamSelectedBtn.disabled = selectedCount === 0;
}

function renderSourceList() {
  els.sourceList.replaceChildren();

  if (!state.dataSources.length) {
    const empty = document.createElement("div");
    empty.className = "source-empty";
    empty.textContent = "No source catalog loaded.";
    els.sourceList.appendChild(empty);
    updateSourceCount();
    return;
  }

  for (const source of state.dataSources) {
    const article = document.createElement("article");
    article.className = "source-item";
    article.dataset.selected = String(state.selectedSourceIds.has(source.id));

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
      article.dataset.selected = String(checkbox.checked);
      hidePackageOutput();
      updateSourceCount();
    });

    const title = document.createElement("span");
    title.className = "source-title";
    title.textContent = source.name;

    const category = document.createElement("span");
    category.className = "source-category";
    category.textContent = source.category;

    header.append(checkbox, title, category);

    const purpose = document.createElement("p");
    purpose.className = "source-purpose";
    purpose.textContent = source.purpose;

    const meta = document.createElement("div");
    meta.className = "source-meta";

    const provider = document.createElement("span");
    provider.textContent = source.provider;

    const status = document.createElement("span");
    status.textContent = formatSourceStatus(source);

    meta.append(provider, status);
    article.append(header, purpose, meta);
    els.sourceList.appendChild(article);
  }

  updateSourceCount();
}

function selectRecommendedSources() {
  const missionFocus = els.missionFocusSelect.value;
  const defaults = MISSION_DEFAULT_SOURCE_IDS[missionFocus] || state.primarySourceIds;
  state.selectedSourceIds = new Set(defaults);
  state.packagePlan = null;
  hidePackageOutput();
  renderSourceList();
  els.packageStatus.textContent = `Recommended sources selected for ${missionFocus}.`;
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
    selectRecommendedSources();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    state.dataSources = [];
    els.packageStatus.textContent = `Source catalog failed: ${message}`;
    renderSourceList();
  }
}

function buildMapContext() {
  const context = {
    imagery_source: els.imageryStatus.textContent || null,
    terrain_source: els.terrainStatus.textContent || null,
  };

  if (state.selectedPoint) {
    context.selected_point = {
      lat: state.selectedPoint.lat,
      lon: state.selectedPoint.lon,
      height_m: state.selectedPoint.heightM,
    };
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
  const packageSummary = state.packagePlan
    ? `${state.packagePlan.package_name}: ${sourceNames.length} sources, manifest ${state.packagePlan.package_id}`
    : `${sourceNames.length} selected sources for ${els.missionFocusSelect.value}`;

  return {
    mission_focus: els.missionFocusSelect.value,
    selected_source_ids: selectedSources.map((source) => source.id),
    selected_source_names: sourceNames,
    package_summary: packageSummary,
  };
}

function clearChat() {
  els.chatLog.innerHTML = "";
  state.chatCount = 0;
  appendMessage(
    "assistant",
    "Source planner ready. Select mission focus and data sources, then ask what the server database needs for the mission.",
  );
}

function applyPanelState() {
  document.body.classList.toggle("panel-collapsed", state.panelCollapsed);
  els.panelToggleBtn.textContent = state.panelCollapsed ? "Expand Planner" : "Collapse Planner";
  els.panelToggleBtn.setAttribute("aria-expanded", String(!state.panelCollapsed));
  if (!state.panelCollapsed) {
    els.workspaceShell.style.setProperty("--panel-width", `${state.panelWidth}px`);
  }
  requestAnimationFrame(() => {
    if (state.viewer) {
      state.viewer.resize();
      state.viewer.scene.requestRender();
    }
  });
}

function clampPanelWidth(width) {
  const maxWidth = Math.max(380, Math.min(window.innerWidth * 0.5, 720));
  return Math.min(Math.max(width, 380), maxWidth);
}

function formatPoint(lat, lon, height = null) {
  const base = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
  if (height === null || Number.isNaN(height)) {
    return base;
  }
  return `${base} | ${height.toFixed(0)} m`;
}

function updateSelectedPoint() {
  if (!state.selectedPoint) {
    els.selectedPoint.textContent = "No point selected";
    return;
  }
  els.selectedPoint.textContent = formatPoint(
    state.selectedPoint.lat,
    state.selectedPoint.lon,
    state.selectedPoint.heightM,
  );
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
}

async function loadRuntimeConfig() {
  state.config = await fetchJson("/api/config");
  const hasToken = Boolean(state.config.cesium_ion_token);
  setChip(els.tokenChip, hasToken ? "Cesium token detected" : "Cesium token missing", hasToken ? "good" : "warn");
  setChip(els.ollamaChip, `Default model: ${state.config.default_model}`, "good");
  state.imageryMode = "esri";
  state.terrainMode = hasToken ? "cesium-world" : "ellipsoid";
  els.imagerySelect.value = state.imageryMode;
  els.terrainSelect.value = state.terrainMode;
}

async function loadModels() {
  els.modelsStatus.textContent = "Checking Ollama...";
  try {
    const data = await fetchJson("/api/models");
    els.modelsList.innerHTML = "";
    els.modelSelect.innerHTML = "";

    if (!Array.isArray(data.models) || data.models.length === 0) {
      const option = document.createElement("option");
      option.value = data.default_model;
      option.textContent = `${data.default_model} (default)`;
      els.modelSelect.appendChild(option);

      const item = document.createElement("li");
      item.textContent = "No installed models reported by Ollama.";
      els.modelsList.appendChild(item);
      els.modelsStatus.textContent = `Default model: ${data.default_model}`;
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
  } catch (error) {
    els.modelSelect.innerHTML = "<option value=''>Could not load models</option>";
    els.modelsList.innerHTML = "";
    const item = document.createElement("li");
    item.textContent = error instanceof Error ? error.message : String(error);
    els.modelsList.appendChild(item);
    els.modelsStatus.textContent = "Model lookup failed";
    setChip(els.ollamaChip, "Ollama lookup failed", "bad");
  }
}

function makeSelectedPointContext() {
  if (!els.includeMapPoint.checked || !state.selectedPoint) {
    return "";
  }
  return `\n\nAO context:\nSelected point latitude ${state.selectedPoint.lat.toFixed(6)}, longitude ${state.selectedPoint.lon.toFixed(6)}, terrain height ${state.selectedPoint.heightM.toFixed(1)} meters.`;
}

async function buildSourcePackage() {
  const selectedSources = getSelectedSources();
  const body = {
    source_ids: selectedSources.map((source) => source.id),
    mission_focus: els.missionFocusSelect.value,
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
  els.requestStatus.textContent = "Connecting to local model...";

  const prompt = els.promptInput.value.trim();
  if (!prompt) {
    els.submitBtn.disabled = false;
    els.requestStatus.textContent = "Idle";
    return;
  }
  const system = els.systemInput.value.trim();
  const model = els.modelSelect.value.trim();
  const agentProfile = els.agentProfileSelect.value;
  const finalPrompt = `${prompt}${makeSelectedPointContext()}`;
  const mapContext = els.includeMapPoint.checked ? buildMapContext() : null;
  const sourceContext = buildSourceContext();

  appendMessage(
    "user",
    finalPrompt,
    [
      model ? `model: ${model}` : "default model",
      `profile: ${agentProfile}`,
      `focus: ${sourceContext.mission_focus}`,
      `${sourceContext.selected_source_ids.length} sources`,
    ].join(" | "),
  );

  let activeAssistantMessage = null;

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
        setMessageBody(assistantMessage, streamedText);
        els.chatLog.scrollTop = els.chatLog.scrollHeight;
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
      throw new Error("The local model returned an empty streamed response.");
    }

    els.requestStatus.textContent = `Completed with ${resolvedModel}`;
    els.promptInput.value = "";
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (activeAssistantMessage) {
      setMessageBody(activeAssistantMessage, message);
      ensureMessageMeta(activeAssistantMessage, "request failed");
    } else {
      appendMessage("assistant", message, "request failed");
    }
    els.requestStatus.textContent = "Request failed";
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

function setMarker(point) {
  if (!state.viewer) {
    return;
  }
  if (state.markerEntity) {
    state.viewer.entities.remove(state.markerEntity);
  }
  state.markerEntity = state.viewer.entities.add({
    position: Cesium.Cartesian3.fromDegrees(point.lon, point.lat, point.heightM + 12),
    point: {
      pixelSize: 12,
      color: Cesium.Color.fromCssColorString("#d6b06d"),
      outlineColor: Cesium.Color.fromCssColorString("#111820"),
      outlineWidth: 2,
    },
  });
}

function wireMapInteraction() {
  if (state.clickHandler) {
    state.clickHandler.destroy();
    state.clickHandler = null;
  }
  const handler = new Cesium.ScreenSpaceEventHandler(state.viewer.scene.canvas);
  state.clickHandler = handler;
  handler.setInputAction((movement) => {
    const cartesian = state.viewer.scene.pickPosition(movement.position)
      || state.viewer.camera.pickEllipsoid(movement.position, state.viewer.scene.globe.ellipsoid);
    if (!cartesian) {
      return;
    }
    const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
    state.selectedPoint = {
      lat: Cesium.Math.toDegrees(cartographic.latitude),
      lon: Cesium.Math.toDegrees(cartographic.longitude),
      heightM: cartographic.height,
    };
    setMarker(state.selectedPoint);
    updateSelectedPoint();
    els.mapHint.textContent = "AO point pinned. Manifest and advisor prompts can include this context.";
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

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
  els.previewStatus.textContent = `${imagery.label} with ${terrain.label.replace("Terrain: ", "")}`;
  installResizeHandling();
  state.viewer.resize();
  state.viewer.scene.requestRender();
  wireMapInteraction();
  updateSelectedPoint();
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
  });
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
  if (els.settingsMenu.classList.contains("hidden")) {
    return;
  }
  if (els.settingsMenu.contains(event.target) || els.settingsToggleBtn.contains(event.target)) {
    return;
  }
  setSettingsMenuOpen(false);
}

function onResizerPointerDown(event) {
  if (state.panelCollapsed) {
    return;
  }
  state.dragState = {
    startX: event.clientX,
    startWidth: state.panelWidth,
  };
  els.panelResizer.classList.add("is-dragging");
  window.addEventListener("pointermove", onResizerPointerMove);
  window.addEventListener("pointerup", onResizerPointerUp, { once: true });
}

function onResizerPointerMove(event) {
  if (!state.dragState) {
    return;
  }
  const delta = state.dragState.startX - event.clientX;
  state.panelWidth = clampPanelWidth(state.dragState.startWidth + delta);
  els.workspaceShell.style.setProperty("--panel-width", `${state.panelWidth}px`);
  if (state.viewer) {
    state.viewer.resize();
    state.viewer.scene.requestRender();
  }
}

function onResizerPointerUp() {
  state.dragState = null;
  els.panelResizer.classList.remove("is-dragging");
  window.removeEventListener("pointermove", onResizerPointerMove);
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

  if (!state.handlersBound) {
    els.promptForm.addEventListener("submit", submitPrompt);
    els.promptInput.addEventListener("keydown", onPromptInputKeyDown);
    els.clearChatBtn.addEventListener("click", clearChat);
    els.resetViewBtn.addEventListener("click", resetView);
    els.panelToggleBtn.addEventListener("click", togglePanel);
    els.settingsToggleBtn.addEventListener("click", toggleSettingsMenu);
    els.panelResizer.addEventListener("pointerdown", onResizerPointerDown);
    els.selectRecommendedBtn.addEventListener("click", selectRecommendedSources);
    els.streamSelectedBtn.addEventListener("click", streamSelectedSources);
    els.buildPackageBtn.addEventListener("click", buildSourcePackage);
    els.missionFocusSelect.addEventListener("change", selectRecommendedSources);
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
