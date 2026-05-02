# TASKS.md — Seed Issues for the GitHub Project Board

> 25 medium-granularity issues. Each lands on the GitHub Project board (Doing / Blocked / Done) via `scripts/seed-issues.sh`.
> Each issue has: title, body (with Acceptance Criteria + File Pointers), labels (lane + priority + phase).
> Pull from this board, never from this file directly. Branch per issue. PR per branch. AGENTS.md §4.

## How to use this file

1. At kickoff, after `gh repo create`, run `bash scripts/seed-issues.sh` from the repo root.
2. Issues become live GitHub Issues with labels.
3. The GitHub Project board (3 columns: Doing / Blocked / Done) auto-includes them.
4. WIP cap: 2 issues "Doing" per person at any time.
5. When you finish, close the issue from the merged PR (`Closes #NN` in PR description).

---

## DAY-0 (Hour 0:00 - 0:30, full-team kickoff blocking)

### #1 [docs] Codename + AO + hero scenario locked in ADR-002
- **Lane:** cross-cutting · **Owner:** P1 (Jon) · **Priority:** P0
- **Acceptance:** `/docs/adrs/2026-05-02-002-kickoff-vote.md` exists with: codename, austere AO, hero scenario, OSM extract size, ollama vs llama.cpp, Palantir/Danti/kepler.gl decisions.
- **Files:** `/docs/adrs/`

### #2 [infra] Repo public on GitHub with branch protection + CODEOWNERS active
- **Lane:** security/infra · **Owner:** P2 (Satriyo) · **Priority:** P0
- **Acceptance:** Repo is public, `main` is protected (require PR, require CI pass, empty bypass list), `CODEOWNERS` is enforced on PR review, all 4 teammates have write access.
- **Files:** GitHub settings, `CODEOWNERS`

### #3 [ci] AI PR review enabled; lefthook installed on each dev machine
- **Lane:** security/infra · **Owner:** P2 · **Priority:** P0
- **Acceptance:** Each teammate has `lefthook install` run; AI PR review action posts on every PR; one test PR exercises the full gate.
- **Files:** `lefthook.yml`, `.github/workflows/ci.yml`

---

## P1 — Web MVP path (target: Sat 1800)

### #4 [agent] Wire frontier LLM client behind LLMClient interface
- **Lane:** agent · **Owner:** P1 (Jon) · **Priority:** P0 · **Phase:** P1
- **Acceptance:** `agent/llm.py` defines `LLMClient` Protocol with `FrontierClient` (OpenAI/Anthropic) and `OllamaClient` impls. Selected via `TERA_PHASE` env var.
- **Files:** `agent/llm.py`, `agent/orchestrator.py`

### #5 [agent] Implement /plan orchestrator with tool-calling loop
- **Lane:** agent · **Owner:** P1 · **Priority:** P0 · **Phase:** P1
- **Acceptance:** `/plan` accepts a prompt, invokes the LLM with tool schemas from `/docs/contracts/agent_routing.schema.json`, validates returned tool args, dispatches to a stub tool, returns valid `PlanResponse`.
- **Files:** `agent/orchestrator.py`, `agent/schemas.py`, `agent/tools/__init__.py`

### #6 [ontology] Author ontology.yml v1 (water, cover, slope, road, trail)
- **Lane:** ontology · **Owner:** P1 · **Priority:** P0 · **Phase:** P1
- **Acceptance:** `ontology/ontology.yml` covers freshwater, covered route, ridgeline, vehicle-passable; loader validates schema at startup.
- **Files:** `ontology/ontology.yml`, `ontology/loader.py`

### #7 [routing] Stand up Valhalla locally with SF extract
- **Lane:** routing · **Owner:** P4 · **Priority:** P0 · **Phase:** P1
- **Acceptance:** `routing/valhalla_client.py` can compute a foot route between two SF coords using locally-built tiles. `make valhalla-build` documented in `data/scripts/`.
- **Files:** `routing/valhalla_client.py`, `data/scripts/clip_osm.sh`

### #8 [data] Clip OSM PBF + DEM tiles for SF + austere AO
- **Lane:** data · **Owner:** P4 · **Priority:** P0 · **Phase:** P1
- **Acceptance:** `data/extracts/sf.osm.pbf` + `data/dem/sf.tif` + same for austere AO. `make data-verify` passes against `data/manifest.sha256`.
- **Files:** `data/aois.yml`, `data/manifest.sha256`, `data/scripts/`

### #9 [atak] Emit KML route file from /plan response (Phase 1 fallback)
- **Lane:** atak · **Owner:** P4 · **Priority:** P1 · **Phase:** P1
- **Acceptance:** Given a `PlanResponse`, write a KML file that can be imported into ATAK manually. Used as Phase 1 fallback before signed CoT lands.
- **Files:** `atak/cot.py` (KML helper), `atak/bridge.py`

### #10 [agent] kepler.gl or Leaflet web frontend showing routes
- **Lane:** agent · **Owner:** P1 · **Priority:** P1 · **Phase:** P1
- **Acceptance:** Static page served by FastAPI; click on map → posts to `/plan` → renders returned route. Pick Leaflet for speed; upgrade to kepler.gl only if there's time.
- **Files:** `agent/static/index.html`, `agent/app.py`

---

## P2 — Edge w/ frontier (target: Sun 0200)

### #11 [hardware] Jetson Orin Nano bring-up complete
- **Lane:** hardware · **Owner:** P3 · **Priority:** P0 · **Phase:** P2
- **Acceptance:** JetPack flashed, Python 3.11 + venv working, `make jetson-prepare` idempotent, `make ci` passes on the Jetson.
- **Files:** `hardware/scripts/setup.sh`, `hardware/jetpack.md`

### #12 [crypto] ML-DSA-65 signer + verifier library
- **Lane:** crypto · **Owner:** P2 · **Priority:** P0 · **Phase:** P2
- **Acceptance:** `crypto/signer.py` exposes `Signer.load`, `Signer.sign`, `Verifier.from_trust_list`, `Verifier.verify`. Sign + verify roundtrip < 5ms (`make sign-bench`). Unit tests in `tests/test_signer.py`.
- **Files:** `crypto/signer.py`, `crypto/trust.py`, `tests/test_signer.py`

### #13 [atak] Signed CoT bridge over multicast
- **Lane:** atak · **Owner:** P4 (impl) · **Priority:** P0 · **Phase:** P2 · **Pair:** P2 (signer)
- **Acceptance:** `bridge.py` ingests `PlanResponse`, builds CoT XML per `/docs/contracts/cot_signed.md`, signs via P2's `Signer`, emits to multicast. ATAK on Android/WinTAK draws the line.
- **Files:** `atak/bridge.py`, `atak/cot.py`, `atak/multicast.py`

### #14 [deploy] systemd unit for agent + bridge on Jetson
- **Lane:** deploy · **Owner:** P3 · **Priority:** P1 · **Phase:** P2
- **Acceptance:** `tera-agent.service` + `tera-bridge.service` start on boot, restart on failure, log to journald.
- **Files:** `deploy/systemd/`, `deploy/rsync.sh`

### #15 [security] tcpdump capture window for demo + audit log scroll
- **Lane:** security · **Owner:** P2 · **Priority:** P1 · **Phase:** P2
- **Acceptance:** `make tcpdump-demo` opens a window showing zero outbound packets during a `/plan` call. Audit log scrolls in a separate window with structured prompt/tool-call/sign events.
- **Files:** `security/demo_proofs.md`, `infra/tcpdump_demo.sh`

---

## P3 — Fully local HERO (target: Sun 1000)

### #16 [models] Pull + verify Gemma + Whisper-tiny
- **Lane:** models · **Owner:** P3 · **Priority:** P0 · **Phase:** P3
- **Acceptance:** `make models-pull` pulls Gemma 2B (or 3n) + Whisper-tiny; SHA-256 hashes verified against `models/manifest.sha256`. `make models-bench` reports per-token latency on Jetson.
- **Files:** `models/manifest.sha256`, `models/pull.sh`

### #17 [agent] Wire ollama (Gemma) as Phase 3 LLM
- **Lane:** agent · **Owner:** P1 · **Priority:** P0 · **Phase:** P3
- **Acceptance:** `OllamaClient` works against local ollama; `TERA_PHASE=3` flips the orchestrator without code change. Tool-calling works (structured-output prompting if Gemma doesn't natively support tools).
- **Files:** `agent/llm.py`, `agent/orchestrator.py`

### #18 [voice] Whisper-tiny push-to-talk endpoint (voice IN)
- **Lane:** voice · **Owner:** Jon (P1) · **Priority:** P1 · **Phase:** P3
- **Acceptance:** `POST /plan/voice` accepts WAV/Opus, transcribes via Whisper-tiny, calls orchestrator, returns plan. End-to-end < 5s on Jetson.
- **Files:** `voice/whisper_client.py`, `voice/ptt.py`, `agent/app.py`

### #27 [agent] CesiumJS 3D globe frontend (Phase 1 web visualization)
- **Lane:** agent · **Owner:** Jon (P1) · **Priority:** P1 · **Phase:** P1
- **Why:** Kyle provisioned a Cesium Ion token (`NPS SF Hackathon`). 3D globe with real terrain is dramatically more impressive than 2D Leaflet. Phase 1 demo wow factor.
- **Acceptance:**
  - `agent/static/index.html` loads CesiumJS, reads `CESIUM_ION_TOKEN` from a server-side `/config` endpoint (never expose token to client beyond what Cesium SDK requires).
  - User clicks point on globe → POSTs to `/plan` → CesiumJS renders the returned route as a polyline draped on terrain.
  - Camera fly-to on route generation; 3D terrain visible.
- **Files:** `agent/static/index.html`, `agent/static/tera.js`, `agent/app.py` (add `/config` endpoint scoped to `CESIUM_ION_TOKEN`).
- **Dependency:** Cesium Ion token in `.env` (Kyle provisioned).
- **Decision point Sat 1400:** if CesiumJS is too heavy or has integration friction, fall back to Leaflet.

### #28 [data] Pre-cache Cesium imagery + terrain tiles for SF + austere AO
- **Lane:** data · **Owner:** Ben (P4) · **Priority:** P1 · **Phase:** P2
- **Why:** Phase 3 runs WiFi-off. Cesium is online-only at runtime. We must pre-cache the demo AO tiles before going offline.
- **Acceptance:**
  - `data/scripts/cache_cesium.sh` downloads imagery + terrain tiles for both AOI bboxes via Cesium Ion REST API using the token.
  - Cached tiles live in `data/cache/cesium/` and are hash-verified.
  - `data/aois.yml` enumerates AOI bbox + zoom levels needed.
  - In Phase 3, frontend (or local tile server) serves from cache; no calls to `*.cesium.com`.
- **Files:** `data/scripts/cache_cesium.sh`, `data/aois.yml`, `data/cache/cesium/.gitkeep`.
- **Dependency:** Cesium Ion token (Kyle provisioned).
- **Defer:** if Sat 1500 progress is behind, drop Cesium tiles; use SRTM/OSM only. CesiumJS frontend still works with Cesium World Terrain online.

### #26 [voice] Piper TTS voice-out — speak rationale + waypoints (voice OUT)
- **Lane:** voice · **Owner:** Jon (P1) · **Priority:** P0 · **Phase:** P3
- **Why:** Operators climbing, fast-roping, or hands-on with another task cannot read an ATAK screen. Hands-free output is the whole reason the system exists when the operator is moving (PRD §4).
- **Acceptance:**
  - `voice/piper_client.py` synthesizes audio from text via Piper.
  - `voice/rationale.py` formats the route response into operator-cadence speech ("zero-three-zero", "ETA three-eight minutes", grid-by-digit).
  - `/plan` response includes optional `audio_b64` (base64 WAV) when `?tts=true` query param is set, OR a separate `GET /tts?text=...` streaming endpoint.
  - First-audio latency < 1s on Jetson; hero rationale audio is 6-10s long.
  - Demo dry-run on Sat 2200: speak the hero scenario rationale through a real headset.
- **Files:** `voice/piper_client.py`, `voice/rationale.py`, `voice/tts.py`, `agent/app.py`
- **Dependencies:** Piper voice model added to `models/manifest.sha256` (P3 owns the manifest entry; Jon picks the voice).

### #19 [infra] Egress firewall: default-deny outbound for Phase 3
- **Lane:** infra · **Owner:** P2 · **Priority:** P0 · **Phase:** P3
- **Acceptance:** When `TERA_PHASE=3`, `infra/jetson_harden.sh` activates iptables ruleset that drops all outbound except loopback + multicast group. Verified by `make tcpdump-demo` showing zero packets.
- **Files:** `infra/jetson_harden.sh`, `infra/egress.iptables`

### #20 [routing] Slope + ridgeline-prominence cost extension
- **Lane:** routing · **Owner:** P4 · **Priority:** P1 · **Phase:** P3
- **Acceptance:** Valhalla custom-cost lua reads pre-computed slope + prominence rasters; "covered foot" profile uses both; demo-verifiable on Scenario B.
- **Files:** `routing/costs/slope.py`, `routing/costs/prominence.py`, `routing/profiles/foot_covered.json`

### #21 [eval] 20-prompt regression eval set
- **Lane:** eval · **Owner:** P1 · **Priority:** P1 · **Phase:** P3
- **Acceptance:** `eval/prompts.yml` has 20 prompts with golden tool calls + golden route bounding boxes. `make eval` reports pass rate; CI fails if < 90%.
- **Files:** `eval/prompts.yml`, `eval/runner.py`

### #22 [security] Intrinsic parsing-verification layer (Jon's paper)
- **Lane:** security · **Owner:** P2 · **Priority:** P1 · **Phase:** P3
- **Acceptance:** `security/parse_verify.py` validates OSM tag combinations, tool-call args, and CoT structure against grammars. Rejects anomalies before they reach downstream tools. Tests cover the 5 primary attack vectors from Jon's paper.
- **Files:** `security/parse_verify.py`, `tests/test_parse_verify.py`

---

## STRETCH — Mesh + PQC reject (only if Sun 0700 go/no-go = GO)

### #23 [mesh] WiFi-Direct or BLE substrate for phone+laptop+Nano
- **Lane:** mesh · **Owner:** P3 · **Priority:** P2 · **Phase:** stretch
- **Acceptance:** All three devices visible to each other on a single mesh; CoT multicast works between Jetson and Android EUD.
- **Files:** `mesh/network_setup.md`

### #24 [mesh] Inject-reject-accept demo script for laptop
- **Lane:** mesh · **Owner:** P3 (impl) · **Priority:** P2 · **Phase:** stretch · **Pair:** P2 (signer)
- **Acceptance:** `mesh/inject_demo.py` sends an unsigned CoT to the multicast group. Bridge logs rejection. Then a signed CoT is generated; bridge accepts. Two-device side-by-side.
- **Files:** `mesh/inject_demo.py`

---

## SUBMISSION — Sun 1100-1200

### #25 [docs] 1-minute YouTube demo video uploaded
- **Lane:** docs · **Owner:** P3 (capture) + P4 (script) · **Priority:** P0
- **Acceptance:** Video captured by Sun 1100, edited by 1145, uploaded unlisted to YouTube by 1200, link in submission form + README.
- **Files:** `docs/demo_video.md` (script + URL)
