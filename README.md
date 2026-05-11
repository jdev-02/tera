# TERA -- Offline-first AI Emergency Logistics Coordination Agent

> **By Team TruePoint** -- Naval Postgraduate School Foundation Entrepreneurship Club.

TERA is an offline-first AI coordination platform for disaster response. It helps emergency teams detect active hazards, identify hospitals and shelters, allocate scarce resources, assign vehicles, choose safer routes, explain operational decisions, and keep working when connectivity is degraded.

Originally built as a tactical edge routing prototype, TERA is now extended into a humanitarian disaster response platform powered by Gemini, Gemma, Google Maps, Firebase, and live US disaster APIs. The original ATAK, Jetson, signed CoT, and offline tactical route architecture remains available as a legacy/optional capability.

## Problem

Disaster responders make time-critical logistics decisions with incomplete information. Wildfire perimeters, flood gauges, smoke exposure, road closures, hospital availability, shelter capacity, vehicle status, and inventory all move faster than teams can manually reconcile. During the same window, fraud and misinformation can push fake donation links, fake FEMA portals, unverified shelter instructions, and fraudulent supply requests into the response loop.

## Solution

TERA turns a natural-language emergency objective into an explainable mission plan:

- active hazards and official disaster context
- hospital, shelter, fuel, bridge, and critical infrastructure options
- route candidates and route risk scoring
- deterministic offline resource allocation
- optional Google Maps Routes and Route Optimization when credentials and network are available
- TERA Trust Shield checks for disaster-fraud links, suspicious supply requests, unverified shelter claims, and conflicting field reports
- offline Gemma fallback and Firebase-ready shared state for degraded operations

## Why Offline-first Matters

TERA defaults to cached/sample/local state and deterministic fallbacks. Live APIs are opt-in on the v2 mission endpoint with `use_live_apis=true`. This keeps the legacy zero-outbound tactical demo intact while giving humanitarian teams richer live data when the network allows it.

## Google I/O Hackathon Fit

- **Gemini:** emergency reasoning, tool calling, multimodal explanation, and decision summaries.
- **Gemma:** local/offline fallback reasoning when connectivity drops.
- **Google Maps Routes API:** route generation, ETA, and alternatives.
- **Google Route Optimization API:** vehicle and resource allocation.
- **Firebase:** offline-first shared state for shelters, vehicles, inventory, missions, field reports, and hazard cache.
- **Google Safe Browsing:** phishing and malware URL checks for crisis-related links.

## Architecture v2

Legacy `/plan` remains available for tactical ATAK routing. The humanitarian layer adds:

- `POST /mission/plan` -- emergency logistics mission planning
- `GET /mission/health` -- v2 liveness and offline default status
- `GET /mission/api-status` -- API-key presence without exposing values
- `GET /mission/demo/bay-area-wildfire` -- no-key, no-network wildfire logistics demo
- `POST /trust/check-url` -- crisis-link trust assessment
- `POST /trust/check-message` -- field-message trust assessment
- `POST /trust/check-supply-request` -- supply-request trust assessment
- `GET /trust/api-status` -- Trust Shield API-key presence without exposing values

See [`docs/architecture_v2.md`](docs/architecture_v2.md).

## TERA Trust Shield

During disasters, fraud and misinformation can disrupt response operations. TERA Trust Shield verifies crisis-related links, supply requests, shelter claims, and field reports using Google Safe Browsing, optional threat intelligence providers, official-source matching, and human approval workflows. Suspicious information is isolated from mission planning until approved.

See [`docs/trust_shield.md`](docs/trust_shield.md).

## API Integrations

TERA includes thin adapters for NOAA/NWS, FEMA, HIFLD, NIFC/WFIGS, AirNow, SF511, NASA FIRMS, USGS, NOAA NWPS, National Bridge Inventory, NREL, EONET, ReliefWeb, Google Maps Routes, Google Route Optimization, Firebase status, Google Safe Browsing, VirusTotal, urlscan.io, and RDAP.

See [`docs/api_inventory.md`](docs/api_inventory.md).

## Demo: Bay Area Wildfire Logistics

```bash
make run
curl -s http://localhost:8000/mission/demo/bay-area-wildfire | jq .
```

The demo identifies Shelter North as overloaded and smoke-exposed, selects Shelter West as the safer logistics destination, assigns trucks to verified needs, flags a fake FEMA login link, blocks an unverified supply request from changing dispatch, and explains the decision with offline fallback state.

See [`docs/demo_google_io.md`](docs/demo_google_io.md).

## Quickstart for Development

```bash
git clone https://github.com/jdev-02/tera.git tera && cd tera
make install
lefthook install
cp .env.example .env
make run
make ci
```

Mission demo:

```bash
curl -s http://localhost:8000/mission/demo/bay-area-wildfire | jq .
```

Trust Shield demo:

```bash
curl -s -X POST http://localhost:8000/trust/check-url \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://fema-aid-claim-example.com/login","context":"wildfire relief claim link"}' | jq .
```

Optional live API preflight:

```bash
python scripts/test_live_apis.py
python scripts/test_live_apis.py --submit-urlscan
```

`--submit-urlscan` is explicit because urlscan.io consumes quota and may load the target page.

## Legacy Tactical Mode

The original tactical route agent is preserved:

- `GET /health`
- `POST /plan`
- `POST /plan/approve`
- `POST /plan/verify`
- ML-DSA/Ed25519 fallback signing
- ATAK/CoT render-gate compatibility
- Jetson/Gemma offline deployment path

The tactical docs and contracts remain in [`docs/PRD.md`](docs/PRD.md), [`docs/contracts/agent_routing.schema.json`](docs/contracts/agent_routing.schema.json), and [`docs/contracts/cot_signed.md`](docs/contracts/cot_signed.md).

## Repo Layout

```text
agent/        # legacy /plan plus v2 mission/trust endpoints
integrations/ # Google, US disaster, and Trust Shield adapters
data/         # sample scenarios and fixtures
security/     # threat model, parse-verify, security demos
crypto/       # ML-DSA / ML-KEM signing lane
atak/         # CoT bridge and render gate
routing/      # Valhalla/local routing lane
docs/         # PRD, contracts, v2 architecture, API inventory
```

## License

MIT.
