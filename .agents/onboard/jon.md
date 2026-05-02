# AGENT KICKOFF — Jon (P1) — agent / ontology / voice / eval / figma

> You are an AI coding agent (Codex / Cursor / Claude Code / Copilot). Jon is your human partner. This file is your operating contract for the next 24 hours. Execute the INSTRUCTIONS section below in order, then begin work.

---

## INSTRUCTIONS (execute in this exact order)

### Step 1 — Read these files in order (do not skip)

1. `AGENTS.md` (repo root)
2. `.agents/00-team.md`
3. `.agents/10-architecture.md`
4. `.agents/21-agent.md` (Jon's lane — your primary playbook)
5. `team.yml`
6. `docs/PRD.md` — read §1, §4, §6, §7, §11, §13, §16
7. `docs/contracts/agent_routing.schema.json`
8. `docs/contracts/cot_signed.md` (read-only — Jon doesn't own it but his code consumes it)

### Step 2 — Confirm context to the human

Output a **numbered list of 5 constraints** you took away from the reading. Wait for Jon to confirm or correct. Do not proceed to Step 3 until he confirms.

### Step 3 — Find Jon's open issues

Run this command in the terminal:

```bash
gh issue list --label "lane:agent" --label "lane:ontology" --label "lane:voice" --label "lane:eval" --json number,title,labels --limit 30
```

If the output is empty, tell Jon: "issue board not seeded yet — ask Satriyo (P2) to run `bash scripts/seed-issues.sh`."

If the output has issues, identify the highest-priority unassigned issue (look for `priority:P0` first, then `priority:P1`). Read the issue body via `gh issue view <number>`.

### Step 4 — Comfort confirmation (REQUIRED — do not skip)

Ask Jon this exact question, with the issue title filled in:

> "The next issue is **#N — \<title>**. Have you done this kind of work before?
> A) confident — I want you to generate code, I'll review.
> B) need-walkthrough — explain the design and library APIs first, then generate.
> C) never-done — walk me through the official docs for ~10 min before any code."

Wait for his answer. Do not generate code before he answers.

### Step 5 — Begin work based on his answer

- **A (confident):** generate code that satisfies the issue's acceptance criteria. Small PR. Commit message must be conventional: `feat(<scope>): <description>`. Branch: `jon/<short-desc>`.
- **B (need-walkthrough):** describe the design first (APIs, file layout, data flow). Wait for Jon's confirmation. Then generate.
- **C (never-done):** find the library's official docs (Cursor / Codex web search OK), summarize the relevant 3-5 sections, paste links, then ask if Jon's ready to proceed.

After code lands, run `make ci` (you must run this; do not assume it passes). If it fails, fix the failure before the PR. Do not bypass.

---

## CONSTRAINTS (NEVER violate, no exceptions)

| # | Rule |
|---|---|
| 1 | NEVER commit `.env`, API keys, model weights, private keys, or `crypto/keys/*.priv`. `gitleaks` runs pre-commit and will block; do not work around it. |
| 2 | NEVER push directly to `main`. Branch protection has empty bypass list. |
| 3 | NEVER edit files outside `agent/`, `ontology/`, `voice/`, `eval/`, `figma/`. Other directories are owned by other people (CODEOWNERS enforces). |
| 4 | NEVER bypass `make ci`. If it fails, fix the failure or fix the CI; do not skip. |
| 5 | NEVER call any URL that is not localhost or the configured frontier API in code that runs in Phase 3. The Phase 3 demo runs with WiFi physically off. |
| 6 | NEVER let the LLM call a tool without JSON-schema validation against `docs/contracts/agent_routing.schema.json`. |
| 7 | NEVER write code without a corresponding GitHub issue. Pull from the board. |
| 8 | NEVER skip Step 4 (comfort confirmation). Always ask before non-trivial code. |

## OWNED DIRECTORIES (you may edit)

- `/agent/` — FastAPI orchestrator, LLM client, tool dispatch
- `/ontology/` — NL → OSM tag mapping (YAML + loader)
- `/voice/` — Whisper-tiny (in) + Piper TTS (out)
- `/eval/` — 20-prompt regression set
- `/figma/` — UI/UX mockup exports

## FORBIDDEN DIRECTORIES (do not edit)

- `/atak/`, `/routing/`, `/data/` — Ben (P4)
- `/hardware/`, `/deploy/`, `/models/`, `/mesh/` — Kyle (P3)
- `/security/`, `/crypto/`, `/infra/`, `.github/`, `.agents/` — Satriyo (P2)
- `Makefile`, `lefthook.yml`, `pyproject.toml` — Satriyo

## PRIORITY ISSUES (highest → lowest, fetch live with `gh` in Step 3)

| # | Title | Phase | Priority |
|---|---|---|---|
| #4 | LLMClient interface (frontier + ollama swap via env var) | P1 | P0 |
| #5 | /plan orchestrator with tool-calling loop | P1 | P0 |
| #6 | ontology.yml v1 (water, cover, slope, road, trail) | P1 | P0 |
| #10 | CesiumJS or Leaflet web frontend | P1 | P1 |
| #27 | CesiumJS 3D globe frontend (uses Kyle's Cesium Ion token) | P1 | P1 |
| #17 | Wire ollama (Gemma) as Phase 3 LLM | P3 | P0 |
| #18 | Whisper-tiny push-to-talk (voice IN) | P3 | P1 |
| #26 | Piper TTS voice-out (rationale + waypoints) | P3 | P0 |
| #21 | 20-prompt regression eval set | P3 | P1 |

## STACK (use these libraries, do not introduce others without Jon's OK)

- `fastapi` + `uvicorn` (HTTP)
- `pydantic` v2 (request/response models)
- `openai` (frontier — Phase 1/2 only)
- `ollama` (local Gemma — Phase 3)
- `faster-whisper` (voice in — install via `make install-voice`)
- `piper-tts` (voice out — install via `make install-voice`)
- `jsonschema` (tool-call validation)
- `pyyaml` (ontology)
- `structlog` (logging — never `print()`)
- CesiumJS in browser via CDN; token from `/config` endpoint server-side, never inline in HTML

## LANE-SPECIFIC GOTCHAS

1. The frontier-vs-local LLM swap MUST be a config flag (`WAYFINDER_PHASE`). Do not hardcode `openai` imports in `agent/orchestrator.py`. Use the `LLMClient` Protocol.
2. Tool-call args MUST be `jsonschema.validate()`-d before invocation. A schema-invalid call is a 400-class error; do not retry; do not loosen the schema without paired sign-off from Ben.
3. Whisper model loads ONCE at startup, not per request. Cache the loaded model.
4. Piper runs on CPU only. Do not put it on the same CUDA stream as Gemma; they will fight for memory.
5. NEVER log full prompts (may contain location). Log `prompt_len` and a hash.
6. Ontology file is YAML. Parse once at startup; cache.
7. The Cesium Ion token (in `.env` as `CESIUM_ION_TOKEN`) is consumed via a server-side `/config` endpoint. Do not embed it directly in `agent/static/index.html`.
8. The `rationale` field in the `/plan` response MUST read like an operator wrote it. Never emit "Here is your route." Use the templates in `voice/rationale.py` (which you'll write).

## DEFINITION OF DONE (every change you ship must satisfy this)

1. `make ci` passes locally.
2. PR has a one-line summary and a "test plan" line.
3. Remote CI passes on the PR.
4. AI PR review HIGH findings addressed or explicitly waived.
5. If the change touches a contract: paired reviewer (Ben for routing, Satriyo for crypto) approved.
6. Merged to main; main is still demo-runnable (`make run` works; `make demo` still passes from Sun 0500 onward).

---

## HUMAN NOTES (Jon — secondary; the section above is the agent's contract)

You're Jon (P1 — Navy CWO, AI/ontology, UI/UX). Your background paper on intrinsic parsing-verification went to Satriyo before kickoff (§13.0).

You own: agent orchestrator, ontology, voice in/out (Whisper + Piper), eval, Figma mockups (Ben writes scenario scripts; you mock them up).

Pair with Ben on the agent ↔ routing JSON contract (lock at Sat 1500). Pair with Ben on the operator-cadence TTS phrasing.

Pitch role: floor support (AI questions). Ben presents A, Kyle presents B.

When in doubt: smaller PR. When stuck: paste error into your agent before pinging a teammate.
