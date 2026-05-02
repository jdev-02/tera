#!/usr/bin/env bash
# seed-issues.sh -- Bulk-create GitHub Issues from TASKS.md.
# Run from the repo root after `gh repo create` and `git push`.
# Requires: gh (authed), jq.
#
# Usage:
#   bash scripts/seed-issues.sh [--dry-run]
#
# Idempotency: skips issues whose titles already exist (matched exactly).

set -euo pipefail

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=1
fi

if ! command -v gh >/dev/null; then
    echo "ERROR: gh CLI not installed."
    exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
    echo "ERROR: gh not authenticated. Run 'gh auth login' first."
    exit 1
fi

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
echo "[seed-issues] target repo: $REPO"
echo "[seed-issues] dry-run: $DRY_RUN"

# Lane and priority labels we want to exist.
LABELS=(
    "lane:agent|0e8a16|Agent / orchestrator (P1)"
    "lane:ontology|0e8a16|Ontology (P1)"
    "lane:eval|0e8a16|Eval / regression (P1)"
    "lane:voice|0e8a16|Voice / Whisper (P1)"
    "lane:atak|1d76db|ATAK / CoT bridge (P4)"
    "lane:routing|1d76db|Routing engine (P4)"
    "lane:data|1d76db|OSM / DEM data (P4)"
    "lane:hardware|fbca04|Hardware / Jetson (P3)"
    "lane:deploy|fbca04|Deploy / systemd (P3)"
    "lane:models|fbca04|Models (P3)"
    "lane:mesh|fbca04|Mesh / stretch (P3)"
    "lane:security|d93f0b|Security / threat model (P2)"
    "lane:crypto|d93f0b|Crypto / PQC (P2)"
    "lane:infra|d93f0b|Infra / hardening (P2)"
    "lane:ci|d93f0b|CI / CD (P2)"
    "lane:docs|c5def5|Docs / cross-cutting"
    "phase:P1|c2e0c6|Phase 1: web MVP"
    "phase:P2|c2e0c6|Phase 2: edge + frontier"
    "phase:P3|c2e0c6|Phase 3: fully local HERO"
    "phase:stretch|c2e0c6|Stretch: mesh + PQC reject"
    "priority:P0|b60205|Blocker / critical path"
    "priority:P1|d93f0b|High"
    "priority:P2|fbca04|Medium / stretch"
)

echo "[seed-issues] ensuring labels exist..."
for spec in "${LABELS[@]}"; do
    IFS='|' read -r name color desc <<< "$spec"
    if [[ $DRY_RUN -eq 1 ]]; then
        echo "  [dry-run] would create label: $name"
    else
        gh label create "$name" --color "$color" --description "$desc" --force >/dev/null 2>&1 || true
    fi
done
echo "[seed-issues] labels ready."

# Issues. Format: TITLE|LABELS_CSV|BODY (body is multi-line via printf).
create_issue() {
    local title="$1"
    local labels="$2"
    local body="$3"

    if gh issue list --search "in:title \"$title\"" --json title -q '.[].title' | grep -Fxq "$title"; then
        echo "  [skip] already exists: $title"
        return
    fi

    if [[ $DRY_RUN -eq 1 ]]; then
        echo "  [dry-run] would create: $title  [labels: $labels]"
        return
    fi

    gh issue create --title "$title" --body "$body" --label "$labels" >/dev/null
    echo "  [ok]   created: $title"
}

echo "[seed-issues] creating issues..."

create_issue "[docs] Codename + AO + hero scenario locked in ADR-002" \
    "lane:docs,priority:P0" \
    "**Owner:** P1 (Jon)
**Acceptance:** \`/docs/adrs/2026-05-02-002-kickoff-vote.md\` exists with: codename, austere AO, hero scenario, OSM extract size, ollama vs llama.cpp, Palantir/Danti/kepler.gl decisions.
**Files:** \`/docs/adrs/\`
**Source:** TASKS.md #1"

create_issue "[infra] Repo public on GitHub with branch protection + CODEOWNERS active" \
    "lane:infra,priority:P0" \
    "**Owner:** P2 (Satriyo)
**Acceptance:** Repo public, \`main\` protected (require PR, CI pass, empty bypass list), CODEOWNERS enforced, all 4 teammates have write access.
**Source:** TASKS.md #2"

create_issue "[ci] AI PR review enabled; lefthook installed on each dev machine" \
    "lane:ci,priority:P0" \
    "**Owner:** P2
**Acceptance:** Every teammate has \`lefthook install\` run; AI PR review action posts on every PR; one test PR exercises the full gate.
**Source:** TASKS.md #3"

create_issue "[agent] Wire frontier LLM client behind LLMClient interface" \
    "lane:agent,phase:P1,priority:P0" \
    "**Owner:** P1
**Acceptance:** \`agent/llm.py\` defines \`LLMClient\` Protocol; \`FrontierClient\` and \`OllamaClient\` impls; selected via \`WAYFINDER_PHASE\`.
**Files:** \`agent/llm.py\`, \`agent/orchestrator.py\`
**Source:** TASKS.md #4"

create_issue "[agent] Implement /plan orchestrator with tool-calling loop" \
    "lane:agent,phase:P1,priority:P0" \
    "**Owner:** P1
**Acceptance:** \`/plan\` accepts a prompt, invokes LLM with tool schemas from \`/docs/contracts/agent_routing.schema.json\`, validates returned tool args, dispatches to a stub tool, returns valid PlanResponse.
**Source:** TASKS.md #5"

create_issue "[ontology] Author ontology.yml v1 (water, cover, slope, road, trail)" \
    "lane:ontology,phase:P1,priority:P0" \
    "**Owner:** P1
**Acceptance:** \`ontology/ontology.yml\` covers freshwater, covered route, ridgeline, vehicle-passable; loader validates schema at startup.
**Source:** TASKS.md #6"

create_issue "[routing] Stand up Valhalla locally with SF extract" \
    "lane:routing,phase:P1,priority:P0" \
    "**Owner:** P4
**Acceptance:** \`routing/valhalla_client.py\` computes a foot route between two SF coords using locally-built tiles. \`make valhalla-build\` documented.
**Source:** TASKS.md #7"

create_issue "[data] Clip OSM PBF + DEM tiles for SF + austere AO" \
    "lane:data,phase:P1,priority:P0" \
    "**Owner:** P4
**Acceptance:** \`data/extracts/sf.osm.pbf\` + \`data/dem/sf.tif\` + same for austere AO. \`make data-verify\` passes against \`data/manifest.sha256\`.
**Source:** TASKS.md #8"

create_issue "[atak] Emit KML route file from /plan response (Phase 1 fallback)" \
    "lane:atak,phase:P1,priority:P1" \
    "**Owner:** P4
**Acceptance:** Given a PlanResponse, write a KML file importable into ATAK. Phase 1 fallback before signed CoT lands.
**Source:** TASKS.md #9"

create_issue "[agent] Web frontend (Leaflet or kepler.gl) showing routes" \
    "lane:agent,phase:P1,priority:P1" \
    "**Owner:** P1
**Acceptance:** Static page served by FastAPI; click on map -> POST /plan -> render returned route. Leaflet first; kepler.gl only if time permits.
**Source:** TASKS.md #10"

create_issue "[hardware] Jetson Orin Nano bring-up complete" \
    "lane:hardware,phase:P2,priority:P0" \
    "**Owner:** P3
**Acceptance:** JetPack flashed, Python 3.11 + venv working, \`make jetson-prepare\` idempotent, \`make ci\` passes on the Jetson.
**Source:** TASKS.md #11"

create_issue "[crypto] ML-DSA-65 signer + verifier library" \
    "lane:crypto,phase:P2,priority:P0" \
    "**Owner:** P2
**Acceptance:** \`crypto/signer.py\` exposes Signer/Verifier; sign+verify roundtrip < 5ms (\`make sign-bench\`); unit tests in \`tests/test_signer.py\`.
**Source:** TASKS.md #12"

create_issue "[atak] Signed CoT bridge over multicast" \
    "lane:atak,phase:P2,priority:P0" \
    "**Owner:** P4 (impl), Pair: P2 (signer)
**Acceptance:** \`bridge.py\` ingests PlanResponse, builds CoT XML per \`/docs/contracts/cot_signed.md\`, signs via Signer, emits to multicast. ATAK draws the line.
**Source:** TASKS.md #13"

create_issue "[deploy] systemd unit for agent + bridge on Jetson" \
    "lane:deploy,phase:P2,priority:P1" \
    "**Owner:** P3
**Acceptance:** \`wayfinder-agent.service\` + \`wayfinder-bridge.service\` start on boot, restart on failure, log to journald.
**Source:** TASKS.md #14"

create_issue "[security] tcpdump demo capture + audit log scroll" \
    "lane:security,phase:P2,priority:P1" \
    "**Owner:** P2
**Acceptance:** \`make tcpdump-demo\` opens window showing zero outbound during /plan; audit log scrolls structured prompt/tool/sign events.
**Source:** TASKS.md #15"

create_issue "[models] Pull + verify Gemma + Whisper-tiny" \
    "lane:models,phase:P3,priority:P0" \
    "**Owner:** P3
**Acceptance:** \`make models-pull\` pulls Gemma 2B + Whisper-tiny; SHA-256 verified against \`models/manifest.sha256\`. \`make models-bench\` reports per-token latency on Jetson.
**Source:** TASKS.md #16"

create_issue "[agent] Wire ollama (Gemma) as Phase 3 LLM" \
    "lane:agent,phase:P3,priority:P0" \
    "**Owner:** P1
**Acceptance:** \`OllamaClient\` works against local ollama; \`WAYFINDER_PHASE=3\` flips orchestrator without code change. Tool-calling via structured-output prompting.
**Source:** TASKS.md #17"

create_issue "[voice] Whisper-tiny push-to-talk endpoint (voice IN)" \
    "lane:voice,phase:P3,priority:P1" \
    "**Owner:** Jon (P1)
**Acceptance:** \`POST /plan/voice\` accepts WAV/Opus, transcribes via Whisper-tiny, calls orchestrator, returns plan. End-to-end < 5s on Jetson.
**Source:** TASKS.md #18"

create_issue "[agent] CesiumJS 3D globe frontend (Phase 1 web visualization)" \
    "lane:agent,phase:P1,priority:P1" \
    "**Owner:** Jon (P1)
**Why:** Kyle provisioned a Cesium Ion token. 3D globe with real terrain >> 2D Leaflet for Phase 1 demo wow.
**Acceptance:**
- agent/static/index.html loads CesiumJS, reads CESIUM_ION_TOKEN via server-side /config endpoint.
- Click point on globe -> POST /plan -> render route as polyline draped on terrain.
- Camera fly-to on route generation; 3D terrain visible.
**Files:** agent/static/index.html, agent/static/wayfinder.js, agent/app.py (/config endpoint scoped to CESIUM_ION_TOKEN).
**Decision point Sat 1400:** fall back to Leaflet if CesiumJS too heavy.
**Source:** TASKS.md #27"

create_issue "[data] Pre-cache Cesium imagery + terrain tiles for both AOIs" \
    "lane:data,phase:P2,priority:P1" \
    "**Owner:** Ben (P4)
**Why:** Phase 3 runs WiFi-off. Cesium is online-only at runtime. Pre-cache demo AO tiles before going offline.
**Acceptance:**
- data/scripts/cache_cesium.sh downloads imagery + terrain tiles via Cesium Ion REST API.
- Cached tiles in data/cache/cesium/, hash-verified.
- In Phase 3, frontend serves from cache; no calls to *.cesium.com.
**Files:** data/scripts/cache_cesium.sh, data/aois.yml, data/cache/cesium/.gitkeep.
**Defer:** if Sat 1500 progress behind, drop Cesium tiles; SRTM/OSM only.
**Source:** TASKS.md #28"

create_issue "[voice] Piper TTS voice-out -- speak rationale + waypoints (voice OUT)" \
    "lane:voice,phase:P3,priority:P0" \
    "**Owner:** Jon (P1)
**Why:** Operators climbing or hands-on with another task cannot read an ATAK screen. Hands-free output is the whole reason the system exists when the operator is moving (PRD section 4).
**Acceptance:**
- \`voice/piper_client.py\` synthesizes audio via Piper (CPU-only, doesn't fight Gemma for GPU).
- \`voice/rationale.py\` formats route response into operator cadence (\"zero-three-zero\", \"ETA three-eight minutes\", grid-by-digit).
- /plan response includes optional audio_b64 when ?tts=true, OR GET /tts?text=... streaming endpoint.
- First-audio latency < 1s on Jetson; hero rationale audio is 6-10s long.
- Demo dry-run Sat 2200: speak hero rationale through a real headset.
**Files:** \`voice/piper_client.py\`, \`voice/rationale.py\`, \`voice/tts.py\`, \`agent/app.py\`
**Source:** TASKS.md #26"

create_issue "[infra] Egress firewall: default-deny outbound for Phase 3" \
    "lane:infra,phase:P3,priority:P0" \
    "**Owner:** P2
**Acceptance:** \`WAYFINDER_PHASE=3\` activates iptables ruleset dropping all outbound except loopback + multicast. Verified by tcpdump showing zero packets.
**Source:** TASKS.md #19"

create_issue "[routing] Slope + ridgeline-prominence cost extension" \
    "lane:routing,phase:P3,priority:P1" \
    "**Owner:** P4
**Acceptance:** Valhalla custom-cost reads pre-computed slope + prominence rasters; \"covered foot\" profile uses both; verifiable on Scenario B.
**Source:** TASKS.md #20"

create_issue "[eval] 20-prompt regression eval set" \
    "lane:eval,phase:P3,priority:P1" \
    "**Owner:** P1
**Acceptance:** \`eval/prompts.yml\` has 20 prompts with golden tool calls + golden route bboxes. \`make eval\` reports pass rate; CI fails if < 90%.
**Source:** TASKS.md #21"

create_issue "[security] Intrinsic parsing-verification layer (Jon's paper)" \
    "lane:security,phase:P3,priority:P1" \
    "**Owner:** P2
**Acceptance:** \`security/parse_verify.py\` validates OSM tags, tool-call args, CoT structure against grammars; rejects anomalies; tests cover 5 primary attack vectors.
**Source:** TASKS.md #22"

create_issue "[mesh] WiFi-Direct or BLE substrate for phone+laptop+Nano" \
    "lane:mesh,phase:stretch,priority:P2" \
    "**Owner:** P3
**Acceptance:** All three devices visible on one mesh; CoT multicast works between Jetson and Android EUD.
**Source:** TASKS.md #23"

create_issue "[mesh] Inject-reject-accept demo script for laptop" \
    "lane:mesh,phase:stretch,priority:P2" \
    "**Owner:** P3 (impl), Pair: P2 (signer)
**Acceptance:** \`mesh/inject_demo.py\` sends unsigned CoT; bridge rejects. Then signed CoT; bridge accepts. Two-device side-by-side.
**Source:** TASKS.md #24"

create_issue "[docs] 1-minute YouTube demo video uploaded" \
    "lane:docs,priority:P0" \
    "**Owner:** P3 (capture) + P4 (script)
**Acceptance:** Video captured by Sun 1100, edited by 1145, uploaded unlisted to YouTube by 1200, link in submission form + README.
**Source:** TASKS.md #25"

echo "[seed-issues] done."
echo ""
echo "Next: open the GitHub Project board, ensure these issues are added,"
echo "configure the 3 columns (Doing / Blocked / Done), and set the WIP cap."
