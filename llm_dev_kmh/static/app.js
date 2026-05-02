const state = {
  config: null,
  viewer: null,
  clickHandler: null,
  resizeObserver: null,
  selectedPoint: null,
  markerEntity: null,
  cameraText: "",
  chatCount: 1,
  imageryMode: "ion-satellite",
  terrainMode: "cesium-world",
  panelWidth: 420,
  panelCollapsed: false,
  dragState: null,
  handlersBound: false,
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
};

window.__LLM_DEV_STATE = state;

const IMAGERY_FALLBACKS = {
  esri: {
    url: "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    credit: "Esri World Imagery",
    label: "Esri World Imagery fallback",
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
  bodyNode.textContent = body;

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

function clearChat() {
  els.chatLog.innerHTML = "";
  state.chatCount = 0;
  appendMessage(
    "assistant",
    "Map workspace ready. Choose a model, click a point if you want location context, and send a prompt to your local Ollama host.",
  );
}

function applyPanelState() {
  document.body.classList.toggle("panel-collapsed", state.panelCollapsed);
  els.panelToggleBtn.textContent = state.panelCollapsed ? "Expand Panel" : "Collapse Panel";
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
  const maxWidth = Math.max(320, Math.min(window.innerWidth * 0.46, 620));
  return Math.min(Math.max(width, 320), maxWidth);
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
  state.imageryMode = hasToken ? "ion-satellite" : "osm";
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
  return `\n\nMap context:\nSelected point latitude ${state.selectedPoint.lat.toFixed(6)}, longitude ${state.selectedPoint.lon.toFixed(6)}, terrain height ${state.selectedPoint.heightM.toFixed(1)} meters.`;
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
  const mapContext = buildMapContext();

  appendMessage(
    "user",
    finalPrompt,
    [
      model ? `model: ${model}` : "default model",
      `profile: ${agentProfile}`,
      mapContext.view_bounds ? "view: active" : "view: unavailable",
    ].join(" | "),
  );

  try {
    const assistantMessage = appendMessage("assistant", "", model ? `model: ${model} | streaming` : "streaming");
    const response = await fetch("/api/prompt/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: finalPrompt,
        system: system || null,
        model: model || null,
        agent_profile: agentProfile,
        map_context: mapContext,
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
        assistantMessage.bodyNode.textContent = streamedText;
        els.chatLog.scrollTop = els.chatLog.scrollHeight;
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
    appendMessage("assistant", message, "request failed");
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
  if (state.imageryMode === "osm") {
    return {
      provider: makeUrlTemplateImageryProvider(IMAGERY_FALLBACKS.osm),
      label: IMAGERY_FALLBACKS.osm.label,
    };
  }

  if (!state.config.cesium_ion_token) {
    state.imageryMode = "osm";
    els.imagerySelect.value = "osm";
    return {
      provider: makeUrlTemplateImageryProvider(IMAGERY_FALLBACKS.osm),
      label: IMAGERY_FALLBACKS.osm.label,
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
    console.warn("Cesium imagery failed; using URL-template fallback.", error);
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
      color: Cesium.Color.fromCssColorString("#edb979"),
      outlineColor: Cesium.Color.fromCssColorString("#0b1216"),
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
    els.mapHint.textContent = "Selected point pinned. New prompts can include this location context.";
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

async function init() {
  clearChat();
  applyPanelState();

   if (!state.handlersBound) {
    els.promptForm.addEventListener("submit", submitPrompt);
    els.clearChatBtn.addEventListener("click", clearChat);
    els.resetViewBtn.addEventListener("click", resetView);
    els.panelToggleBtn.addEventListener("click", togglePanel);
    els.settingsToggleBtn.addEventListener("click", toggleSettingsMenu);
    els.panelResizer.addEventListener("pointerdown", onResizerPointerDown);
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
  await buildViewer();
}

init().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  setChip(els.tokenChip, "Workspace failed to initialize", "bad");
  appendMessage("assistant", message, "startup error");
  els.requestStatus.textContent = "Startup failed";
});
