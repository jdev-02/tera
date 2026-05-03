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
  selectedSourceIds: new Set(),
  packagePlan: null,
  sourceInference: null,
  sourceConfirmed: false,
  workflowStageIndex: 0,
  lastMissionText: "",
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
  sourcePanel: document.getElementById("sourcePanel"),
  mapStage: document.querySelector(".map-stage"),
  mapResetViewBtn: document.getElementById("mapResetViewBtn"),
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
      ? "No additional Socratic question was inferred. Review the working sources or describe a constraint in chat."
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
  const stream = source.stream_status.replace(/-/g, " ");
  const download = source.download_status.replace(/-/g, " ");
  return `${stream} / ${download}`;
}

function updateSourceCount() {
  const selectedCount = state.selectedSourceIds.size;
  const total = state.dataSources.length;
  if (!hasMissionInference()) {
    els.sourceCount.textContent = total
      ? "Awaiting mission description"
      : "Source catalog not loaded";
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
    empty.textContent = "No source catalog loaded.";
    els.sourceList.appendChild(empty);
    updateSourceCount();
    return;
  }

  const visibleSources = getSelectedSources();
  if (!visibleSources.length) {
    const empty = document.createElement("div");
    empty.className = "source-empty";
    empty.textContent = "Send a mission description in chat. TERA will infer a compact source list here.";
    els.sourceList.appendChild(empty);
    updateSourceCount();
    return;
  }

  for (const source of visibleSources) {
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
      state.sourceConfirmed = false;
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
    state.selectedSourceIds = new Set();
    renderSourceList();
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
    : `${sourceNames.length} sources inferred from chat for ${inference?.mission_focus || "mission-data-package"}`;

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
  els.packageStatus.textContent = "No sources selected yet. Send a mission description to infer the needed package.";
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
    "Source planner ready. Describe the mission in chat. I will work through the source package as a short question-driven dialogue.",
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

function makeMapContextAppendix() {
  if (!els.includeMapContext.checked) {
    return "";
  }

  const lines = [];
  if (state.selectedArea) {
    lines.push(
      `Selected AO west ${state.selectedArea.west.toFixed(6)}, south ${state.selectedArea.south.toFixed(6)}, east ${state.selectedArea.east.toFixed(6)}, north ${state.selectedArea.north.toFixed(6)}.`,
    );
  }
  if (!lines.length) {
    return "";
  }
  return `\n\nAO context:\n${lines.join("\n")}`;
}

async function inferSourcesFromMission(missionText, mapContext) {
  els.packageStatus.textContent = "Inferring compact source package from mission text...";
  setChip(els.packageModeChip, "Inferring", "warn");

  const data = await fetchJson("/api/source-package/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      mission_text: missionText,
      map_context: mapContext,
    }),
  });

  state.sourceInference = data;
  state.lastMissionText = missionText;
  state.selectedSourceIds = new Set(data.selected_source_ids || []);
  state.sourceConfirmed = false;
  state.workflowStageIndex = data.clarifying_questions?.length ? 1 : 2;
  state.packagePlan = null;
  hidePackageOutput();

  if (!els.packageNameInput.value.trim() && data.package_name_suggestion) {
    els.packageNameInput.value = data.package_name_suggestion;
  }

  els.inferredMission.textContent = data.mission_summary || missionText;
  setChip(els.packageModeChip, data.mission_focus || "Inferred", "good");
  renderSourceList();

  const questionText = data.clarifying_questions?.length
    ? ` Next questions: ${data.clarifying_questions.join(" ")}`
    : "";
  els.packageStatus.textContent = `Drafted ${state.selectedSourceIds.size} working sources. Answer the dialogue questions to broaden or narrow the package.${questionText}`;
  updateWorkflowPanel();
  return data;
}

async function buildSourcePackage() {
  if (!state.sourceConfirmed) {
    els.packageStatus.textContent = "Confirm the inferred source list before building the manifest.";
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
  const finalPrompt = `${prompt}${makeMapContextAppendix()}`;
  const mapContext = els.includeMapContext.checked ? buildMapContext() : null;
  els.requestStatus.textContent = "Inferring source package...";
  try {
    await inferSourcesFromMission(prompt, mapContext);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    els.packageStatus.textContent = `Source inference failed: ${message}`;
    setChip(els.packageModeChip, "Inference failed", "bad");
  }
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
  updateSelectedArea();
  hidePackageOutput();
}

function setAreaSelectMode(active) {
  if (active && !state.sourceConfirmed) {
    els.packageStatus.textContent = "Confirm the inferred source list before drawing AO coverage.";
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
  updateSelectedArea();

  if (!state.handlersBound) {
    els.promptForm.addEventListener("submit", submitPrompt);
    els.promptInput.addEventListener("keydown", onPromptInputKeyDown);
    els.clearChatBtn.addEventListener("click", clearChat);
    els.resetViewBtn.addEventListener("click", resetView);
    els.mapResetViewBtn.addEventListener("click", resetView);
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
