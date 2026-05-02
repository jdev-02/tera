# 21 — Agent / Ontology / Voice / Eval / Figma Lane (P1 — Jon, Navy CWO, AI/ontology + UI/UX)

> Owns: `/agent/`, `/ontology/`, `/voice/`, `/eval/`, `/figma/`. Pairs with Ben (P4) on the agent ↔ routing contract.

## What this lane delivers

1. The FastAPI service exposing `POST /plan`.
2. LLM orchestration: prompt → tool call → tool result → response synthesis.
3. JSON-schema-validated tool-calling layer.
4. Ontology mapping NL terms ("freshwater", "covered route") → OSM tag predicates + cost params.
5. **Multimodal voice path: Whisper-tiny (voice in) + Piper TTS (voice out).** Hands-free for moving operators is core, not stretch.
6. 20-prompt eval set with golden tool calls + golden route bounding boxes.
7. Figma user-journey mockups for the 3 scenarios + UI/UX for the Phase 1 web frontend.

## Entry points (must exist + work)

- `POST /plan` — see `/.agents/10-architecture.md` for contract.
- `POST /plan/voice` — multipart audio in, plan response out (with optional TTS audio out).
- `GET /tts?text=...` — synthesize and stream audio back. Or include audio bytes in the `/plan` response under `audio_b64`.
- `GET /health` — `{"status": "ok", "phase": "1|2|3"}`.
- `make eval` — runs the 20-prompt regression set; fails CI if pass rate < 90%.

## Stack inside this lane

- **FastAPI + uvicorn** for the HTTP service.
- **pydantic v2** for request/response models.
- **`openai`** Python client for Phase 1 (frontier API).
- **`ollama`** Python client for Phase 3 (local Gemma).
- **`faster-whisper`** for Whisper-tiny on the Jetson (CUDA build).
- **`piper-tts`** (or `piper` binary) for offline TTS on Jetson. CPU-only — doesn't fight Gemma for GPU.
- **`jsonschema`** for tool-call argument validation.
- **`pyyaml`** for the ontology file.
- **CesiumJS** (in browser, from CDN) for the Phase 1 web frontend 3D globe. Token via `CESIUM_ION_TOKEN` in `.env` (Kyle provisioned). Phase 3 falls back to cached tiles from `data/cache/cesium/` (Ben pre-caches).

## File layout inside `/agent/`

```
agent/
  __init__.py
  app.py             # FastAPI app, route definitions
  orchestrator.py    # the main prompt-to-response pipeline
  llm.py             # provider abstraction: FrontierClient | OllamaClient
  tools/
    __init__.py
    find_pois.py
    route.py
    terrain_query.py
  schemas.py         # pydantic models for all I/O
  constants.py
```

## File layout inside `/ontology/`

```
ontology/
  ontology.yml       # NL term -> {osm_tags: [...], cost_overrides: {...}}
  loader.py          # validates + loads ontology.yml at startup
```

## File layout inside `/voice/`

```
voice/
  __init__.py
  whisper_client.py  # thin wrapper around faster-whisper (voice in)
  piper_client.py    # thin wrapper around Piper (voice out)
  ptt.py             # push-to-talk endpoint handler
  tts.py             # TTS synthesis + audio streaming
  rationale.py       # converts route response into operator-cadence speech
                     # ("zero-three-zero", "one-two-three-four-five",
                     #  "ETA three-eight minutes" — military number reading)
```

## File layout inside `/eval/`

```
eval/
  demo_prompts.yml   # 5 prompts the presenters memorize
  prompts.yml        # 20-prompt regression set with golden outputs
  runner.py          # invoked by `make eval`
```

## Contracts you OWN (and can change with P4 sign-off)

- `/docs/contracts/agent_routing.schema.json` — the JSON schema for tool-call args and route response. Co-owned with P4.

## Contracts you MUST respect

- The CoT signing format: when your `/plan` response includes a signature, the signature object must match `/docs/contracts/cot_signed.md`. P2 owns the actual signing implementation in `/crypto/`.

## Common gotchas

1. **Frontier vs local LLM swap must be a config flag.** Don't hardcode `openai` imports in `orchestrator.py`. Use `LLMClient` interface.
2. **Tool calls must be validated before invocation.** Use `jsonschema.validate(args, schema)`. A schema-invalid call returns 400 — don't retry.
3. **Whisper model loads at startup, not per-request.** ~2 sec load time is fine; per-request would be unacceptable.
4. **Never log the full prompt** in production logs (may contain location). Log `prompt_len` and a hash.
5. **Ontology file is YAML, not JSON.** Load it once at startup; cache the parsed structure.

## Definition of done for this lane

- `/plan` returns valid response per contract for all 5 demo prompts.
- 20-prompt eval set has ≥ 90% pass rate.
- **Voice in → text → plan path** works on the Jetson under 5 sec end-to-end.
- **Plan → TTS → audio out** works on the Jetson with first-audio < 1 sec, hero rationale audible in 6-10 sec.
- LLM client swap (frontier ↔ local) works via env var with no code change.
- Figma mockups for scenarios A/B/C exist as exported PNGs in `figma/exports/`.
