# AGENT KICKOFF — Ben (P4) — atak / routing / data

> You are an AI coding agent (Codex / Cursor / Claude Code / Copilot). Ben is your human partner. He's a USMC Combat Engineer, CS student, and went to Marine Corps Mountain Warfare School — he is the team's operator-side SME and Presenter A on stage. This file is your operating contract for the next 24 hours. Execute the INSTRUCTIONS section below in order, then begin work.

---

## INSTRUCTIONS (execute in this exact order)

### Step 1 — Read these files in order (do not skip)

1. `AGENTS.md` (repo root)
2. `.agents/00-team.md`
3. `.agents/10-architecture.md`
4. `.agents/22-atak.md` (Ben's lane — your primary playbook)
5. `team.yml`
6. `docs/PRD.md` — read §1, §6 (scenarios, Ben authors), §7.2 (ATAK + routing rows), §11 (route quality SME rating), §12 (Ben is Presenter A)
7. `docs/contracts/agent_routing.schema.json` (co-owned with Jon)
8. `docs/contracts/cot_signed.md` (co-owned with Satriyo)

### Step 2 — Confirm context to Ben

Output a numbered list of 5 constraints you took away. Wait for Ben to confirm or correct.

### Step 3 — Find Ben's open issues

Run this command in the terminal:

```bash
gh issue list --label "lane:atak" --label "lane:routing" --label "lane:data" --json number,title,labels --limit 30
```

If empty, ask Satriyo to run `bash scripts/seed-issues.sh`. Otherwise, find the highest-priority unassigned issue. Read the body via `gh issue view <number>`.

### Step 4 — Comfort confirmation (REQUIRED — do not skip)

Ask Ben this exact question, with the issue title filled in:

> "The next issue is **#N — \<title>**. Have you done this kind of work before?
> A) confident — I want you to generate code, I'll review.
> B) need-walkthrough — explain the design and library APIs first, then generate.
> C) never-done — walk me through the official docs for ~10 min before any code."

Wait for his answer. Do not generate code before he answers.

### Step 5 — Begin work based on his answer

Same pattern as Jon's prompt: A → generate; B → design first; C → docs walkthrough first.

After code lands, run `make ci`. Fix failures; do not bypass.

### Step 6 — When Ben gives operator-side input, treat it as authoritative

Ben is the SME for "what makes a good tactical route." When you generate cost-model logic, ATAK overlays, or scenario phrasing, **always verify with Ben that a Marine would actually want this** before assuming OSM tags or DEM math is enough.

Examples:
- You: "I'll penalize edges with slope > 30°."
- Better: "A Marine on foot can usually handle up to 35° slope with effort. Should I cap at 35° and add a separate `extreme` tier above that?" → wait for Ben's answer.

When Ben rates a generated route 2/5, generate a one-line "what's wrong" summary. Use it to tune the cost model.

---

## CONSTRAINTS (NEVER violate, no exceptions)

| # | Rule |
|---|---|
| 1 | NEVER log the operator's location to files outside `data/runtime/`. |
| 2 | NEVER push directly to `main`. |
| 3 | NEVER edit files outside `atak/`, `routing/`, `data/`. |
| 4 | NEVER bypass `make ci`. |
| 5 | NEVER call ATAK across the network in Phase 3. Loopback / USB / BLE only. The "no outbound packets" claim depends on this. |
| 6 | NEVER call `*.cesium.com` at runtime in Phase 3. Cesium tiles are pre-cached in `data/cache/cesium/` while online; Phase 3 reads from cache only. |
| 7 | NEVER skip Step 4 (comfort confirmation). |
| 8 | NEVER write code without a GitHub issue. |

## OWNED DIRECTORIES (you may edit)

- `/atak/` — CoT bridge (Android EUD + WinTAK), CoT XML construction, multicast emit/listen
- `/routing/` — Valhalla client + custom cost model (slope, prominence, cover)
- `/data/` — OSM PBF clipping, DEM tiles, Cesium tile cache, AOI manifest, hash verification

## FORBIDDEN DIRECTORIES (do not edit)

- `/agent/`, `/ontology/`, `/voice/`, `/eval/`, `/figma/` — Jon (P1)
- `/hardware/`, `/deploy/`, `/models/`, `/mesh/` — Kyle (P3)
- `/security/`, `/crypto/`, `/infra/`, `.github/`, `.agents/` — Satriyo (P2)
- `Makefile`, `lefthook.yml`, `pyproject.toml` — Satriyo
- `docs/contracts/agent_routing.schema.json` — co-owned with Jon (changes need both signoffs)
- `docs/contracts/cot_signed.md` — co-owned with Satriyo

## PRIORITY ISSUES (highest → lowest)

| # | Title | Phase | Priority |
|---|---|---|---|
| #8 | Clip OSM PBF + DEM tiles for SF + austere AO | P1 | P0 |
| #7 | Stand up Valhalla locally with SF extract | P1 | P0 |
| #9 | Emit KML from /plan response (Phase 1 fallback) | P1 | P1 |
| #13 | Signed CoT bridge over multicast (paired with Satriyo) | P2 | P0 |
| #28 | Pre-cache Cesium imagery + terrain for both AOIs | P2 | P1 |
| #20 | Slope + ridgeline-prominence cost extension | P3 | P1 |
| #25 | 1-minute YouTube demo video (Ben scripts, Kyle captures) | submit | P0 |

## STACK

- **Valhalla** (Docker for tile build, native binary on Jetson for runtime). Custom-cost lua scripts.
- **`osmium`** CLI for OSM PBF clipping/filtering
- **`gdal`** for DEM tile mosaicking
- **`shapely` + `geojson`** for geometry handling in Python
- **`pytak`** for CoT XML (or hand-rolled `lxml` — pytak has dependency baggage; pick at kickoff)
- **`lxml`** for CoT XML signing wrapper (signature wrapper provided by Satriyo's `crypto/`)
- **Cesium Ion REST API** for pre-caching imagery + terrain (token from `.env` `CESIUM_ION_TOKEN`, Kyle provisioned)

## LANE-SPECIFIC GOTCHAS

1. **CoT timestamps** are ISO-8601 UTC, not local time. ATAK silently drops malformed timestamps.
2. **ATAK multicast group default:** 239.2.3.1:6969. Some venue networks block multicast; test on the Jetson's local interface (`lo`), not the venue WiFi.
3. **Valhalla custom costs** are computed at TILE-BUILD time via per-edge CSV, not at routing time. Per-request slope calc is too slow. Pre-compute slope and prominence rasters from DEM, snap edges to raster cells, write cost CSV, build Valhalla tiles.
4. **DO NOT call ATAK across the network in Phase 3.** Loopback / USB / BLE only.
5. **Cesium pre-cache** must complete BEFORE WiFi off in dry-runs. Use `data/scripts/cache_cesium.sh` (which you'll write in #28). Cached tiles in `data/cache/cesium/`.
6. **Operator-cadence TTS rationale** (your collab with Jon, issue #26): you provide the phrasing patterns. Examples:
   - Bearings: "zero-three-zero", not "30 degrees"
   - Grids: digit-by-digit, "one-two-three-four-five, six-seven-eight-nine-zero", not "twelve thousand three hundred forty-five"
   - Distances: "two-point-one kilometers" or "two-thousand-one-hundred meters"
   - ETA: "ETA three-eight minutes" or "estimated time three-eight"
   - Direction: "northeast" not "045 degrees"

## DEFINITION OF DONE

1. `make ci` passes locally.
2. PR has summary + test plan.
3. CI passes on GitHub.
4. AI PR review HIGH findings addressed.
5. If the change touches a contract: paired reviewer (Jon for routing schema, Satriyo for CoT signing) approved.
6. After merge: the route renders in ATAK from `/plan` in under 5s.

---

## HUMAN NOTES (Ben — secondary)

You are Ben (P4 — USMC Combat Engineer, CS student, Marine Corps Mountain Warfare School). Your operator credibility is the spine of the pitch.

Your lane: ATAK bridge, Valhalla routing, OSM/DEM data pipeline, Cesium tile pre-caching, scenario authoring, SME route quality scoring.

Note: Figma reassigned to Jon at kickoff review. You write scenario scripts in operator vocabulary; Jon mocks them in Figma based on your scripts.

You are Presenter A on stage — lead narrator. The Mountain Warfare credibility is what makes the hook land in the first 30 seconds (PRD §12.1).

Pair with Jon on the agent ↔ routing JSON contract (Sat 1500 freeze) AND on the operator-cadence TTS rationale phrasing (Sat 1500 checkpoint).

Pair with Satriyo on the CoT signing format (in `docs/contracts/cot_signed.md`).

When in doubt: prefer the version of a feature you can demonstrate physically on stage in 30 seconds.
