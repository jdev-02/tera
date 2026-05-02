# 10 — Architecture (read after 00-team.md, before any non-trivial change)

> Single source of truth: [`/docs/PRD.md`](../docs/PRD.md) §7 and §8. This file is the agent-friendly summary.

## High-level data flow

```
USER PROMPT (voice or text)
    │
    │  voice path: Whisper-tiny on Jetson (push-to-talk)
    ▼
AGENT ORCHESTRATOR (FastAPI, /plan)
    │
    │  1. parse prompt + ontology lookup
    │  2. construct tool call (JSON schema validated)
    ▼
LOCAL LLM (Gemma via ollama, Phase 3)
    │  returns structured tool call: {find_pois | route | terrain_query}
    ▼
GEOSPATIAL TOOLS
    │  - find_pois(): query local OSM PBF
    │  - route(): call Valhalla with custom cost model
    │  - terrain_query(): DEM-derived slope/prominence
    ▼
ROUTING ENGINE (Valhalla, custom cost from DEM)
    │  returns GeoJSON LineString + waypoints
    ▼
SIGNING LAYER (ML-DSA / Dilithium)
    │  signs each CoT field at emit time
    ▼
ATAK BRIDGE (CoT XML over loopback / mesh)
    │  verifies signatures on ingress
    ▼
ATAK on Android EUD (or WinTAK on laptop)
    └──► Operator sees signed blue line + waypoints
```

## Phased build (PRD §7.3)

| Phase | LLM | Network | Demo state | Target time |
|---|---|---|---|---|
| **P1 — Web MVP** | Frontier API | Online | Web app, click point, see route | Sat 1800 |
| **P2 — Edge w/ frontier** | Frontier API | Online (Jetson WiFi) | Same UX, on the device | Sun 0200 |
| **P3 — Fully local (HERO)** | Gemma local | **WiFi physically off** | Voice → ATAK → signed CoT | Sun 1000 |
| **Stretch — Mesh + PQC reject** | Gemma local | Mesh only | 2-device inject-reject-accept | If go/no-go = GO |

**Critical:** every phase is a complete demo-able product. We never ship "almost working." If P3 doesn't converge by Sun 1000, we demo P2.

## Public contracts (do not change without paired sign-off)

### `POST /plan` (agent orchestrator → caller)

Request:
```json
{
  "prompt": "route me to nearest freshwater within 5km, on foot, covered terrain",
  "current": {"lat": 37.7955, "lon": -122.3937},
  "request_id": "uuid-v4-optional"
}
```

Response (always 200 on success; 400/422 on invalid; 503 on internal error):
```json
{
  "request_id": "uuid-v4",
  "route": { "type": "Feature", "geometry": { "type": "LineString", "coordinates": [...] }, "properties": {} },
  "waypoints": [ { "lat": ..., "lon": ..., "label": "Lobos Creek" } ],
  "rationale": "Selected creek 2.1 km NE; route follows draw to avoid skyline crossing at GR 12345 67890. ETA 38 min on foot at 4 kph.",
  "cost_breakdown": { "distance_m": 2104, "time_s": 2280, "elevation_gain_m": 67 },
  "signature": { "scheme": "ML-DSA-65", "key_id": "...", "value_b64": "...", "signed_at": "ISO-8601" }
}
```

Source of truth for the schema: `/docs/contracts/agent_routing.schema.json`.

### CoT field signing (P2 + P4 contract)

Each emitted CoT message has a custom `<detail><signature>` child:
```xml
<detail>
  <signature scheme="ML-DSA-65" key_id="..." signed_at="..." value_b64="..."/>
</detail>
```

Source of truth: `/docs/contracts/cot_signed.md`.

## Lane → directory map

| Lane | Owner | Directories |
|---|---|---|
| Agent orchestration + ontology + voice + eval | P1 (Jon) | `/agent/`, `/ontology/`, `/voice/`, `/eval/` |
| ATAK + routing + data | P4 | `/atak/`, `/routing/`, `/data/`, `/figma/` |
| Hardware + deploy + models + mesh | P3 | `/hardware/`, `/deploy/`, `/models/`, `/mesh/` |
| Security + crypto + infra + CI | P2 (Satriyo) | `/security/`, `/crypto/`, `/infra/`, `/.github/`, `/.agents/` |

## Threat model summary (PRD §8)

Featured threat: **TAK track injection** (CoT is unauthenticated by default).
Featured mitigation: **ML-DSA-signed CoT**, verified on ingress.

Every CoT message we emit is signed. Every CoT message we ingest is verified. The verifier rejects unsigned or untrusted-key messages. This is the PS4 wow moment in the demo (PRD §12.1, 1:40-2:10 beat).

## What you should NOT build

- Microservices beyond `agent` + `bridge`.
- Custom auth (the device IS the auth boundary).
- Kubernetes / containers for deploy (the Jetson runs systemd or a `tmux` session).
- An admin UI, a settings page, or a dynamic config service.
- Anything that requires outbound network in Phase 3.
