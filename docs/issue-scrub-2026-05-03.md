# Issue ↔ Code Reconciliation Scrub — 2026-05-03

> **Author:** automated reconciliation pass for Jon (team lead).
> **Repo state:** `main` synced to `origin/main`, last merged PR #93 (Piper voice metadata JSONs).
> **Methodology:** every open issue (32 total) cross-checked against on-`main` code, recent merged PRs (#49–#93), and the two open PRs (#92 already merged at scan time, #93 already merged). When an acceptance criterion was ambiguous, scrub erred toward LEAVE OPEN / PARTIAL — judges may inspect the tracker.

## Summary

- **Total open issues scanned:** 32
- **Recommended CLOSE:** 1
- **Recommended PARTIAL (scope down or split):** 9
- **Recommended LEAVE OPEN (with context refresh):** 21
- **Recommended DUPLICATE / STALE:** 1

> Note: zero issues are recommended for hard-CLOSE except #17. The hackathon is mid-flight; almost everything has *some* downstream work that materially advances it but few issues are *fully* satisfied. Use the PARTIAL bucket aggressively to prune scope rather than closing.

---

## CLOSE candidates (fully shipped)

### #17 — [P0] [agent] Wire ollama (Gemma) as Phase 3 LLM
**Evidence:**
- `agent/llm.py` (lines 304–396) — full `OllamaClient` with loopback enforcement, native `format=<schema>` structured output, tool-call shim. `OLLAMA_MODEL` env var switches model (gemma2:2b → gemma3:4b without code change).
- `agent/llm.py` `LLMRegistry` (lines 426–493) + `PROFILE_ALLOWED` / `PROFILE_DEFAULT` (lines 49–59) — `TERA_PHASE` / `TERA_DEVICE_PROFILE` flips orchestrator without code change. austere = local-only by construction; frontier client never built.
- `agent/orchestrator.py` `plan()` (line 284–307) — calls `client.complete_structured(...)` with the RouteQuery schema. Tool calling is sandboxed: LLM emits JSON only, deterministic dispatch follows.
- PR #73 (`feat: add chat interface for TERA using local Ollama model`), PR #85 (Kyle's Source Planner UI + `llm_dev_kmh/tera_gemma/chat_tera_gemma.py` proof), PR #86 (`atak/scripts/run_jetson_gemma_server.sh` end-to-end Jetson smoke-test).
- `tests/test_llm.py`, `tests/test_llm_dev_stream.py` — provider tests.

**Suggested close comment:**
```
Closing — Ollama is fully wired as the Phase-3 LLM. agent/llm.py:OllamaClient
uses native ollama format=<schema> for structured output, loopback-enforced,
profile-gated via TERA_DEVICE_PROFILE. PR #73 added the chat interface, #85
shipped Kyle's Source Planner driving Gemma 3 4B end-to-end, #86 added the
Jetson smoke-test scripts. The runtime "start it on the Jetson with
OLLAMA_MODEL=gemma3:4b" task lives separately at #82.
```

---

## PARTIAL candidates (scope down or split)

### #79 — [P0] [atak] Wire format alignment: TeraPlanClient → /plan PlanRequest schema
**Done:**
- ATAK plugin (`atak/plugin/.../TeraPlanClient.java` lines 135–146) now POSTs to `/api/prompt` with `{prompt, model:"gemma3:4b", llm_provider:"ollama", agent_profile, map_context}`.
- That endpoint (`llm_dev_kmh/app.py` line 7555 `/api/prompt`) is what the Jetson actually serves today via PR #86's `run_jetson_gemma_server.sh`.
- `TERAPlugin.java` voice path uses Android's native `SpeechRecognizer` so transcribed prompt is in the payload as `prompt`.

**Remaining:**
- The plugin no longer talks to `agent.app:/plan` at all. It talks to `llm_dev_kmh.app:/api/prompt`. The original wire-format work (mapping `lat/lon` → `current` for `agent.schemas.PlanRequest`) is moot until/unless `agent.app` is re-introduced into the Jetson loop.
- If `/plan` is the demo target, plugin payload must be reshaped (`current: {lat, lon}` nested, `source: "operator_text"|"operator_voice"`).
- `current` location is still hard-coded to `null` (`buildPromptPayload` passes `null` for `mapContext`).

**Suggested rewritten body:**
```markdown
**Lane:** atak · **Owners:** Ben (plugin) + Jon (schema) · **Phase:** P3 · **Priority:** P0

## Why (revised post #85, #86, #90)

The plugin now talks to `llm_dev_kmh.app:/api/prompt`, not `agent.app:/plan`.
Two paths forward; pick at 0500 sync:

**A) Plumb /plan through llm_dev_kmh** (preferred for hero demo)
- Add a `/plan` proxy in `llm_dev_kmh/app.py` that calls `agent.orchestrator.plan`
  internally, so the existing security pipeline + ML-DSA signature still run.
- Plugin keeps current /api/prompt shape but agent_profile="tera-routing"
  triggers the proxy.

**B) Plugin sends /plan directly**
- Update `TeraPlanClient.buildPromptPayload` to nest lat/lon under `current`
  and use source: "operator_text" | "operator_voice".
- Plug current location from `MapView.getMapView().getSelfMarker().getPoint()`.
- `TERAPlugin.buildEndpoint` defaults to `/api/prompt` — change to `/plan` or
  make path configurable.

## Acceptance criteria
- [ ] Plugin can drive a real /plan call (either via proxy or direct).
- [ ] Operator's current location appears in server logs (`plan_request prompt_len=N source=operator_text`).
- [ ] Server logs show `llm_emitted_route_query objective=...`.
- [ ] Plugin receives valid PlanResponse with `route`, `waypoints`, `signature`.

Refs PRD §7.2 API surface row, §13 contract co-ownership rule.
Supersedes the original /api/prompt → /plan rename framing.
```

---

### #20 — [P1] [data] Pre-cache Cesium imagery + terrain tiles for both AOIs
**Done:**
- PR #85 (`feat(planner): Source Planner UI`) shipped a comprehensive Cesium download stack inside `llm_dev_kmh/app.py`: archive REST endpoints (`CESIUM_ION_ARCHIVES_URL`, `CESIUM_ION_ARCHIVE_DOWNLOAD_URL`), `/api/source-package/{id}/execute`, `/api/source-package/{id}/query/cesium` for offline serve.
- `llm_dev_kmh/static/index.html` loads `cesium.com/.../widgets.css` 1.124.
- Token gating via `/api/config` exposes `cesium_ion_token` to the client.

**Remaining:**
- `data/scripts/cache_cesium.sh` does not exist.
- `data/aois.yml` does not exist on `main` (lives on Ben's `ben/valhalla-local-sf` branch — see #83).
- `data/cache/cesium/` is not pre-populated, no hash-verification step against `data/manifest.sha256`.
- For Phase 3 (WiFi-off) the planner must serve from a baked-in cache; today the Cesium widget loads from cesium.com CDN at runtime.

**Suggested rewritten body:**
```markdown
**Owner:** Ben (P4) · Pair: Kyle (P3, planner integration)
**Why:** Phase 3 runs WiFi-off. PR #85 shipped the Cesium archive download
infra inside the Source Planner. Need to convert that into a deterministic
pre-bake step against the demo AOIs.

**Acceptance:**
- [ ] `data/aois.yml` lands on main (depends on #83).
- [ ] `data/scripts/cache_cesium.sh` invokes the existing
      `/api/source-package/{id}/execute` flow against each AOI and writes the
      archive zip + extracted tileset under `data/cache/cesium/<aoi>/`.
- [ ] Hashes recorded in `data/manifest.sha256`; `make data-verify` passes.
- [ ] Source Planner served on the Jetson works WiFi-off against the
      cached tileset (verify with `infra/jetson_firewall.sh enable`).

**Defer:** if Sat 1500 progress behind, drop Cesium tiles; SRTM/OSM only.
```

---

### #19 — [P1] [agent] CesiumJS 3D globe frontend (Phase 1 web visualization)
**Done:**
- PR #85 shipped `llm_dev_kmh/` — a much larger Cesium-based "Source Planner" UI: globe, 3D terrain, KML/KMZ import, ATAK agent toggle, model provider switch (Claude → local Ollama), full source-package planner. This *exceeds* the original Phase 1 scope.

**Remaining:**
- `agent/static/index.html` does not exist — the original Phase 1 demo path (click point → POST /plan → render polyline draped on terrain) is not built.
- `agent/app.py` has no `/config` endpoint scoped to `CESIUM_ION_TOKEN` (that's in `llm_dev_kmh/app.py:/api/config` instead).
- The Source Planner does *source planning*, not *click-to-route*. If we want a click-to-route Cesium demo, that's still pending — though the demo construct now leans on the ATAK plugin polyline (#80), not Cesium-on-laptop, so this may be moot.

**Suggested rewritten body:**
```markdown
**Owner:** Jon (P1) + Kyle (P3)
**Status post #85:** the Source Planner UI superseded the original "click point
on globe -> POST /plan" Phase 1 demo. Two scopes left to consider:

(a) Source Planner is the Phase 1 demo — no further work. Close this issue.
(b) We still want a click-to-route Cesium frontend that drives /plan — keep
    open as a stretch.

Decision to be made by Jon at Sun 0700 go/no-go. Until then, leave open with
the understanding that the hero demo path is plugin-on-ATAK (#80), not
laptop-Cesium.
```

---

### #28 — [P0] [docs] 1-minute YouTube demo video uploaded
**Done:**
- PR #87 added `docs/demo-recording-plan.md` — canonical recording index + pitch-day fallback rules.
- PR #89 consolidated `docs/demo-clips/` (gitignored) + workflow.
- 7 component clips already captured (S1–S5 security, B1 ATAK, J1 voice severity test).
- `scripts/demo_voice.py` `--severity-demo` flag (PR #76, #78) ships pitch-mode capture for J2.

**Remaining:**
- The actual 1-minute submission video is not yet recorded.
- Not yet edited.
- Not yet uploaded unlisted to YouTube.
- Submission-form link not posted.
- README link not added.

**Suggested rewritten body:**
```markdown
**Owner:** P3 (capture) + P4 (script). Coordinator: Jon.
**Acceptance:** Sun 1100-1200 window — capture, edit, upload, link.

Recording infrastructure is ready (PR #87, #89, #76, #78). 7 component clips
live in docs/demo-clips/. The 1-minute pitch cut still needs to:
- [ ] Sun 1100 — record 1-minute pitch from PRD §12 5-minute structure.
- [ ] Sun 1145 — edit (likely just titlecard + score-bar).
- [ ] Sun 1200 — upload to YouTube unlisted.
- [ ] Sun 1200 — paste URL into hackathon submission form.
- [ ] Sun 1200 — add link to README §Demo + docs/SUBMISSION_NOTES.md.

**Source:** TASKS.md #25.
```

---

### #27 — [P2] [mesh] Inject-reject-accept demo script for laptop
**Done:**
- `security/cot_inject_demo.py` (172 lines) ships the inject-reject-accept construct: unsigned CoT rejected, tampered CoT rejected, properly-signed CoT accepted. Standalone Python, no ATAK or network required.
- Demo clip S1 already captured (`docs/demo-clips/2254-security-cot-inject-demo.mp4`).
- `make inject-demo` Make target (per `docs/demo-recording-plan.md`).

**Remaining:**
- Acceptance says "Two-device side-by-side" — current demo is single-device. mesh injection over the wire (laptop A pretending to be adversary, laptop B running bridge) is not built.
- `mesh/inject_demo.py` (vs current path `security/cot_inject_demo.py`) does not exist.

**Suggested rewritten body:**
```markdown
**Owner:** P3 (impl), Pair: P2 (signer)

**Done so far:** single-device construct shipped via `security/cot_inject_demo.py`
+ recording S1 (`docs/demo-clips/2254-security-cot-inject-demo.mp4`). This is
already adequate for the §12 pitch beat 3:00-3:30.

**Optional stretch (this issue):** two-device side-by-side over the multicast
wire. Requires `mesh/inject_demo.py` + a second laptop running the verifier.
Defer to post-pitch unless Sun 0700 stretch decision is GO.

**Acceptance:** unchanged (two-device demo).
```

---

### #24 — [P1] [eval] 20-prompt regression eval set
**Done:**
- `eval/prompts.yml` has 23 entries (more than 20): 3 PRD hero scenarios + 17 variations + 3 adversarial. Expected RouteQuery goldens for all.
- `eval/runner.py` ships mock-mode (validates each `expected_query` against the live RouteQuery JSON Schema, fails CI < 90%).
- Adversarial entries (`adversarial_ignore_instructions`, `adversarial_request_to_sign`) flag pipeline-block expectations.

**Remaining:**
- `runner.py` line 96: `live` mode (`TERA_EVAL_LIVE=1`) prints `"ERROR: TERA_EVAL_LIVE=1 not yet implemented"` and falls back to mock-mode. So the LLM is not actually exercised.
- Acceptance says "golden tool calls + golden route bboxes" — bbox checks are not present (depends on real Valhalla, see #83).
- `make eval` target exists but only runs mock-mode.

**Suggested rewritten body:**
```markdown
**Owner:** Jon (P1)
**Status:** `eval/prompts.yml` (23 entries) + `eval/runner.py` mock-mode shipped
and CI-gated at 90%. Live-mode + bbox golden checks still pending.

**Remaining acceptance:**
- [ ] Implement TERA_EVAL_LIVE=1 path in `eval/runner.py` (call orchestrator
      with mocked tool dispatch; assert structured_query matches golden modulo
      defaulted fields).
- [ ] Add golden route bboxes per entry (depends on #83 — real Valhalla on main).
- [ ] Wire `make eval-live` into the Sat 1400 dev-time + Sun 0900 demo dry-run
      benchmarks per the runner.py docstring intent.

Mock-mode is sufficient for CI today; live-mode lights up the LLM grounding
test once Ben's routing branch is on main.
```

---

### #22 — [P0] [infra] Egress firewall: default-deny outbound for Phase 3
**Done:**
- `infra/jetson_firewall.sh` (71 lines) ships `enable` / `disable` / `status` modes. Drops outbound to non-loopback non-mesh; default-deny on OUTPUT chain. Mesh subnet allowlisted via `MESH_SUBNET` env.
- `infra/firewall_dev.ps1` (PR #71) blocks port 8000 from WiFi on Windows demo day.
- Verification path documented (`iptables -L OUTPUT -v --line-numbers`).

**Remaining:**
- Acceptance: "TERA_PHASE=3 activates iptables ruleset" — currently fully manual (`sudo bash infra/jetson_firewall.sh enable`). No `TERA_PHASE`-triggered automation.
- Acceptance: "Verified by tcpdump showing zero packets" — `infra/tcpdump_demo.sh` exists but isn't bundled into a `make verify-egress` style command that proves zero outbound under the firewall.

**Suggested rewritten body:**
```markdown
**Owner:** Satriyo (P2) — already assigned.

**Remaining acceptance:**
- [ ] Auto-trigger: tera-agent.service (or a new `tera-firewall@phase3.service`)
      runs `infra/jetson_firewall.sh enable` when `TERA_PHASE=3` is set in
      systemd Environment=.
- [ ] Combine `infra/jetson_firewall.sh enable` + `infra/tcpdump_demo.sh` into
      a single `make verify-egress` target that captures 30s of tcpdump under
      lockdown and asserts zero non-loopback outbound.
- [ ] Document in docs/PHASE3_RUNBOOK.md (lives in #56 too).

The script-level lockdown construct is already proven; remaining work is
trigger + verification automation.
```

---

### #16 — [P0] [models] Pull + verify Gemma + Whisper-tiny
**Done:**
- Gemma is pulled out-of-band by `atak/scripts/run_jetson_gemma_server.sh` (`ollama pull ${MODEL}` step, model defaults to `gemma3:4b`).
- 4 Piper voices committed under `models/piper/` (PRs #84, #93). PR #93 added `.onnx.json` metadata for all four.
- `agent/llm.py` `OllamaClient` validates loopback host (defense in depth).

**Remaining:**
- `make models-pull` Make target does not exist.
- `models/manifest.sha256` does not exist — no SHA-256 verification against pinned hashes for any model.
- `make models-bench` does not exist; no per-token latency measurement is captured anywhere.
- Whisper-tiny is not pulled or wired anywhere on `main`. Voice-IN today is Android's native `SpeechRecognizer` (TERAPlugin.toggleVoiceInput), not Whisper.
- Closely related to #57 (model supply-chain integrity).

**Suggested rewritten body:**
```markdown
**Owner:** Kyle (P3)
**Remaining acceptance:**
- [ ] `make models-pull` invokes `ollama pull ${OLLAMA_MODEL:-gemma3:4b}` and
      downloads any Whisper artifacts we actually decide to use.
- [ ] `models/manifest.sha256` pins all model files (the 4 Piper .onnx are on
      disk and easy to hash today; Gemma's blobs live under ~/.ollama).
- [ ] `make models-bench` runs `crypto/sign_bench.py`-style timing loop
      against the LLM (single-token latency + 50-token latency) and prints
      pass/fail vs PRD §11.2 targets.
- [ ] Decision: do we ship Whisper-tiny at all for Phase 3, or is the Android
      SpeechRecognizer path sufficient? See #18 dependency.

Note this issue overlaps with #57 (model supply-chain integrity). Consider
folding manifest+hash-verify work there; keep this issue scoped to pull+bench.
```

---

### #14 — [P1] [deploy] systemd unit for agent + bridge on Jetson
**Done:**
- PR #88 shipped `deploy/systemd/tera-planner.service`, `tera-planner-update.service`, and `tera-planner-update.timer`. `Restart=always`, `RestartSec=3`, `NoNewPrivileges=true`, journald via stdout.
- `deploy/scripts/run_tera_planner.sh`, `install_jetson_autoupdate.sh`, `jetson_update_and_restart.sh` complete the auto-update story.
- PR #92 added `deploy/scripts/jetson_compose_refresh.sh`.

**Remaining:**
- `tera-planner.service` runs `llm_dev_kmh.app` (Source Planner UI), not `agent.app` (the FastAPI orchestrator).
- `tera-bridge.service` does not exist — depends on `atak/bridge.py` landing first (#13/#83).
- If we want both `agent.app` *and* the planner running on the Jetson concurrently, need to allocate ports + decide which is "the agent service".

**Suggested rewritten body:**
```markdown
**Owner:** Kyle (P3)
**Done:** systemd framework + auto-update infra (PR #88, #92) for the planner.

**Remaining acceptance:**
- [ ] Decide: is `tera-planner.service` the canonical agent service, or do we
      add `tera-agent.service` for `agent.app:app` on a separate port?
- [ ] If the latter: clone tera-planner.service to tera-agent.service,
      ExecStart=`uvicorn agent.app:app --port 8000`, Environment=
      `TERA_PHASE=3 OLLAMA_MODEL=gemma3:4b TERA_DEVICE_PROFILE=austere` (mirrors #82).
- [ ] Add tera-bridge.service once #13/#83 lands the bridge code.

Tracker: #82 covers the runtime smoke-test for the agent service once it has
a unit file.
```

---

### #1 — [P0] [docs] Codename + AO + hero scenario locked in ADR-002
**Done:**
- `docs/adrs/2026-05-02-002-kickoff-vote.md` exists with the tabular structure called out in the acceptance.
- Codename = "TERA" (`TacticalEdgeRouteAgent` in plugin package, "TERA" everywhere in PRD/README) — implicit lock.
- Hero scenario locked via PR #64 (`docs/demo-scenarios/sar-olympic.md`).
- Cesium decision implied by PR #85 (Cesium UI shipped → kepler.gl out, Leaflet out).
- Ollama vs llama.cpp implicitly decided by `agent/llm.py:OllamaClient` shipping (Ollama).

**Remaining:**
- ADR-002 cells literally read "TBD" / "deferred" — the file exists structurally but does not record the decisions that have de-facto happened.

**Suggested rewritten body:**
```markdown
**Owner:** Jon (P1)
**Status:** ADR-002 file exists but decision cells are still "TBD". The
decisions themselves have happened de facto via downstream code (TERA codename
in plugin/PRD/README, sar-olympic.md hero scenario PR #64, Cesium via Source
Planner PR #85, Ollama via agent/llm.py).

**Remaining work:** five-minute editorial pass to fill in ADR-002 cells with
what's actually been shipped. No code change.

**Acceptance:** unchanged.
```

---

## LEAVE OPEN (with context refresh)

### #83 — [P0] [routing] Merge ben/valhalla-local-sf — Valhalla + OSM/DEM scripts + KML emit
**Status note:** Still entirely valid. Verified that `data/extracts/`, `data/dem/`, and `data/scripts/` are empty on `main`; `routing/` only has `__init__.py`; `atak/bridge.py`, `atak/cot.py`, `atak/__init__.py` do not exist. Branch `ben/valhalla-local-sf` (945 lines, 16 files) has not been opened as a PR yet. **This is the umbrella for #7, #8, #9, and prerequisite for #13/#23.** Highest-leverage merge available — should be the first thing Sunday morning.

### #82 — [P0] [deploy] Start TERA agent on Jetson with OLLAMA_MODEL=gemma3:4b
**Status note:** `agent/llm.py:OllamaClient` defaults to `gemma2:2b` (line 327) — without `OLLAMA_MODEL=gemma3:4b` override it will try to pull a model the Jetson doesn't have. PR #88's `tera-planner.service` runs `llm_dev_kmh.app`, not `agent.app`. The runtime smoke-test (curl `/health` returning `{"phase":"3","profile":"austere"}`) has not been demonstrated. Still a P0 blocker for the demo loop. Consider pairing with #14 to ship a `tera-agent.service` unit at the same time.

### #81 — [P1] [atak] Verify ML-DSA signature on /plan response before rendering
**Status note:** Plugin currently does not call `/plan` at all (calls `llm_dev_kmh:/api/prompt` per #79). Verification can't happen until the plugin sees a `Signature` block. `agent/orchestrator._sign_response` (orchestrator.py line 184–239) already signs server-side. `security/cot_inject_demo.py` already proves the inject-reject construct end-to-end without the plugin — the §12 pitch beat 3:00-3:30 is covered. Defer per the issue's own defer condition (Sun 0700 go/no-go).

### #80 — [P0] [atak] Render route_geojson as polyline on ATAK MapView
**Status note:** Plugin (`TERAPlugin.java` line 160–195) appends agent response as text to chat scroll only — no MapItem polyline. Hard-blocks on #79 (need a real PlanResponse with `route.geometry.coordinates` to render). Hero demo claim ("ATAK draws a blue line down a draw...") is currently unmet.

### #70 — [P2] [docs] ADR: production encrypted tunnel architecture
**Status note:** No file at `docs/adrs/2026-05-03-NNN-production-encrypted-tunnel.md`. Lowest priority of the encrypted-tunnel stretch issues; defer per the issue's own defer condition. Pure docs, can be written during Sun 1300-1410 finalist deliberations if needed.

### #69 — [P2] [atak] Android-side PQC sidecar for ML-KEM session decrypt
**Status note:** `atak/sidecar/` does not exist. Stretch issue with explicit defer condition (Sun 0700 GO/NO-GO on Phase 3 + mesh stretch). Recommend NO-GO unless Phase 3 USB tether path is proven solid by Sat night.

### #68 — [P2] [crypto] ML-KEM-768 session encryption
**Status note:** `crypto/kem_session.py`, `crypto/aead.py`, `docs/contracts/pqc_session.md` do not exist. Hard prerequisite is #69 (Android sidecar). Same defer-condition logic.

### #57 — [P1] [security] Model supply-chain integrity — checksum + signed bundles
**Status note:** No `models/MANIFEST.yml`. PR #93 committed Piper `.onnx.json` metadata but did not add SHA pins. `make verify-models` does not exist. The pickle/torch.load audit (the second prong) has not been done. Critical given that PR #93 just expanded our external-model dependency surface to 4 Piper voices.

### #56 — [P1] [infra] Jetson Orin Nano storage + RAM budget
**Status note:** No `make budget` target. No `docs/PHASE3_RUNBOOK.md`. PR #92 (`jetson_compose_refresh.sh`) and #88 (systemd units) are deploy-related but don't measure footprint. The working-set inventory table in the issue body is still the only source of truth and has not been measured. Recommend Kyle owns a 30-min measurement pass on the Jetson during the integration smoke-test.

### #45 — [P2] [voice] Mission-context situational narration
**Status note:** Partial credit not enough to flag PARTIAL — the issue is specifically about the *narrative* layer ("Based on your need for CASEVAC..."), and `agent/orchestrator._build_rationale` (orchestrator.py line 160–176) is still the generic template ("Routed to X, distance Y, ETA Z..."). The vocabulary infrastructure exists (`voice/glossary.py` knows CASEVAC/HLZ/golden hour with definitions; `voice/profiles.py` auto-elevates voice mode on severity cues per PR #63), but the per-mission_type rationale templates that *string mission rationale together* are not present. Stretch only.

### #38 — [P2] [routing] priority_grid tool (currently stubbed)
**Status note:** `agent/orchestrator._dispatch_tools` (orchestrator.py line 109–119) still returns "Objective priority_search_area is not yet supported by the MVP pipeline." Eval set has two entries (`sar_priority_area`, `sar_with_team_lead`) that exercise this objective; both expect `destination_type: none`. Stretch.

### #37 — [P2] [agent] Operator-approval workflow
**Status note:** `agent/orchestrator._run_security_pipeline` (line 374–409) still hard-codes `operator_approved=True, policy_valid=True`. Comment in code already points to this issue ("operator-approval flow"). Stretch.

### #36 — [P2] [contracts] Add PlanRequest.mode field
**Status note:** `agent/schemas.PlanRequest` has no `mode` field. `agent/orchestrator.plan(req, mode="auto", ...)` takes `mode` as a function arg only. `agent/app.py:plan_endpoint` does not surface `mode` to the request body or query params. Stretch; touches the public contract so needs Ben + Jon signoff.

### #35 — [P2] [ci] Tighten mypy on crypto/ + security/ post-MVP
**Status note:** `pyproject.toml` likely still has `ignore_errors = true` for `crypto.*` and `security.*` (the issue body cites this). `Makefile` `lint` target only runs mypy on `agent routing crypto` (line 55), not `security` — so even where `crypto.*` is allowed, the gate doesn't include `security`. Post-hackathon cleanup. Don't touch during the demo window.

### #23 — [P1] [routing] Slope + ridgeline-prominence cost extension
**Status note:** No real Valhalla on `main` (`routing/__init__.py` only). Hard prerequisite is #83. Cannot start until Ben's branch lands.

### #18 — [P1] [voice] Whisper-tiny push-to-talk endpoint (voice IN)
**Status note:** No `/plan/voice` endpoint in `agent/app.py`. Whisper isn't wired anywhere. Plugin uses Android `SpeechRecognizer` instead (TERAPlugin.toggleVoiceInput, line 288–381). For the hero demo, Android SpeechRecognizer may be sufficient — recommend a Sun 0700 decision: ship Whisper or formally adopt SpeechRecognizer and rewrite this issue's scope.

### #13 — [P0] [atak] Signed CoT bridge over multicast
**Status note:** No `atak/bridge.py` on `main`. `crypto.cot_signer.sign_cot` exists; `agent/orchestrator._sign_response` calls it. But CoT XML emission + multicast delivery doesn't exist. Ben's `ben/valhalla-local-sf` branch has a 22-line `atak/bridge.py` (likely just stub) — won't fully satisfy this issue even when merged. Realistically blocked on a follow-up to #83.

### #11 — [P0] [hardware] Jetson Orin Nano bring-up complete
**Status note:** Significant Jetson tooling has shipped: PR #85 (`llm_dev_kmh/tera_gemma/chat_tera_gemma.py` proves Gemma 3 4B runs on the Jetson), #86 (link-test scripts + Ollama serve helper), #88 (systemd auto-update), #92 (compose refresh). However, `make jetson-prepare` Make target does not exist, and "make ci passes on the Jetson" cannot be verified from main without Jetson access. Recommend Kyle confirms the bring-up state during Sun 0700 sync; don't auto-close.

### #9 — [P1] [atak] Emit KML route file from /plan response
**Status note:** No KML emitter on `main`. Ben's branch has `atak/cot.py` (147 lines, "plan_to_kml + write_plan_kml") per #83 — will satisfy this when the branch merges. Hard-prerequisite on #83.

### #8 — [P0] [data] Clip OSM PBF + DEM tiles for SF + austere AO
**Status note:** `data/extracts/` and `data/dem/` are empty. Ben's branch has the clip scripts + manifest per #83. Merge of #83 closes this immediately. Consider marking as DUPLICATE of #83 once the umbrella PR opens.

### #7 — [P0] [routing] Stand up Valhalla locally with SF extract
**Status note:** `routing/` is empty (only `__init__.py`). Ben's branch has `routing/valhalla_client.py` (184 lines) per #83. Merge of #83 closes this immediately. Consider marking as DUPLICATE of #83 once the umbrella PR opens.

---

## DUPLICATE / STALE

### (none recommended for hard duplicate today)

The natural duplicate candidates — #7, #8, #9 vs the umbrella #83 — are arguably *better tracked separately* until #83 actually opens as a PR. Once that PR is open and CI green, close #7/#8/#9 in the same merge with `Closes #7, #8, #9` in the PR body and skip the dup-marking step. **Net DUPLICATE/STALE for this scrub: 1 (informally — see treatment of #7/#8/#9 above as soft duplicates of #83).**

---

## Suggested batch commands (for Jon)

```bash
# === Close fully-shipped (1) ===
gh issue close 17 --comment "Closing — Ollama is fully wired as the Phase-3 LLM. agent/llm.py:OllamaClient uses native ollama format=<schema> for structured output, loopback-enforced, profile-gated via TERA_DEVICE_PROFILE. PR #73 added the chat interface, #85 shipped Kyle's Source Planner driving Gemma 3 4B end-to-end, #86 added the Jetson smoke-test scripts. The runtime smoke-test on the actual Jetson lives separately at #82."

# === Edit partially-done — scope down (9) ===
# Save each suggested rewritten body to /tmp/issue-NN-body.md first, then:
gh issue edit 79 --body-file /tmp/issue-79-body.md   # /plan vs /api/prompt pivot
gh issue edit 20 --body-file /tmp/issue-20-body.md   # Cesium pre-cache: scope to AOI bake step
gh issue edit 19 --body-file /tmp/issue-19-body.md   # 3D globe: ack Source Planner; click-to-route optional
gh issue edit 28 --body-file /tmp/issue-28-body.md   # YouTube video: tighten to Sun 1100-1200 acceptance
gh issue edit 27 --body-file /tmp/issue-27-body.md   # mesh inject-reject: ack S1 capture; two-device stretch
gh issue edit 24 --body-file /tmp/issue-24-body.md   # eval: ack mock-mode shipped; live-mode + bbox open
gh issue edit 22 --body-file /tmp/issue-22-body.md   # firewall: ack script; auto-trigger + tcpdump verify open
gh issue edit 16 --body-file /tmp/issue-16-body.md   # models: ack Gemma+Piper; manifest+bench+Whisper open
gh issue edit 14 --body-file /tmp/issue-14-body.md   # systemd: ack planner.service; agent.service + bridge open
gh issue edit  1 --body-file /tmp/issue-1-body.md    # ADR-002: editorial pass to fill in TBD cells

# === Soft-duplicate hint (no edit needed; will close together with #83 PR) ===
# When opening the PR for ben/valhalla-local-sf, include in the body:
#   Closes #83
#   Closes #7
#   Closes #8
#   Closes #9
# That prunes 4 issues with one merge.

# === Leave open (21) ===
# No action. Status notes above are for the next standup, not the issue tracker.
```

### Where to dump the rewritten bodies before running `gh issue edit`

```bash
# A one-liner to populate /tmp/issue-*-body.md from the markdown blocks above —
# easiest path is to manually copy each "Suggested rewritten body:" block in
# this report into the corresponding /tmp/issue-NN-body.md file. The blocks
# are already pure markdown ready to paste; no transformation needed.
```

---

## Notes for Jon

1. **#83 is the highest-leverage merge available.** Merging Ben's `ben/valhalla-local-sf` (945 lines, 16 files) effectively closes #7, #8, #9 in one shot and unblocks #13, #20, #23. Treat it as the Sunday-0500 anchor.
2. **Two divergent contracts on the Jetson today** — `agent.app:/plan` (the original, signed, security-pipeline path) vs `llm_dev_kmh.app:/api/prompt` (Kyle's planner, used by the ATAK plugin). The hero-demo wiring is currently the latter. Decide at Sun 0700 which is "the demo path"; #79, #80, #81, #82, #14 all depend on this.
3. **Defer-condition issues** (#68, #69, #70, #45, #38, #37, #36) — all stretch with explicit defer logic in their bodies. Don't feel obligated to touch them during the demo window.
4. **Voice/audio infrastructure is in good shape.** PRs #49 (Piper TTS + glossary), #63 (profiles + radio FX + bakeoff), #66 (per-request voice profile), #76/#78 (severity demo + pitch mode), #84/#93 (voice models on disk). The remaining voice work is mostly demo capture (#28) and the mission-narration stretch (#45).
5. **Security lane is hackathon-ready.** `crypto/`, `security/pipeline.py`, `security/cot_inject_demo.py`, `crypto/sign_bench.py`, ADR-003 (two-signature approval), and 5 captured demo clips (S1–S5). Satriyo has covered the §12 pitch beat 3:00-3:30 without the plugin needing to verify (#81).

---

*End of scrub. — generated 2026-05-03 against `main` @ origin/main, post-#93.*

---

## Post-scrub deltas (appended 2026-05-03 after security-posture pass)

Single-line notes for issues that have changed status since the scrub above. Body of the scrub is unchanged.

- **#57** — closed by **#100** (`models/MANIFEST.yml` + `security/model_integrity.py` + `make model-integrity` wired into `make ci`). No longer LEAVE OPEN.
- **#81** — closed by **#97** (`agent/orchestrator.verify_plan_response` + `/plan/verify` endpoint, fail-closed render gate, ML-DSA-65 verify with payload→response binding). No longer PARTIAL/LEAVE OPEN.
- **#105** — closed by the same merge (post-#97 follow-up): wires `crypto.cot_signer.load_trust_list` into `verify_plan_response`, returns `Untrusted key_id - REJECTED` for unknown keys (`agent/orchestrator.py:420–438`), and adds a FastAPI lifespan hook that auto-bootstraps the device's own key into the trust list at process start (`agent/app.py:42–60`). Three new tests on main (`tests/test_orchestrator.py:626 / :654 / :679`). Closes the trust-list-at-`/plan/verify` gap that an earlier draft of `docs/security/posture.md` had flagged as a known asymmetry — that asymmetry no longer exists; see the rewritten `docs/security/posture.md` §5.1 for the post-#105 framing of the (intentional) self-attestation trust model.
- **#79** — closed by **#102** (`fix(atak): wire TeraPlanClient to /plan with PlanRequest schema`). The plugin now POSTs to `/plan` with the correct `PlanRequest` shape; was PARTIAL in scrub.
- **#27** — single-device construct adequately covered by **S1** clip + `security/cot_inject_demo.py`. The two-device mesh stretch remains open per the issue's own defer condition; status note unchanged.
- **#28** — recording infrastructure has expanded one slot (S6 model-integrity clip added to `docs/demo-recording-plan.md`); the 1-minute submission cut still pending per the original status note.
