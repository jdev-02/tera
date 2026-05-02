# 22 — ATAK / Routing / Data Lane (P4 — Ben, USMC Combat Engineer, Mountain Warfare School)

> Owns: `/atak/`, `/routing/`, `/data/`. Pairs with Jon (P1) on contract, Satriyo (P2) on CoT signing.
> Note: `/figma/` reassigned to Jon (P1) at kickoff review 2026-05-02 — Jon owns UI/UX end-to-end.

## What this lane delivers

1. **ATAK Bridge** — service that converts agent `/plan` responses into signed CoT messages and emits them to ATAK (Android EUD or WinTAK).
2. **Valhalla setup** — local routing engine with custom cost model.
3. **DEM-derived cost extension** — slope, ridgeline-prominence, cover scoring.
4. **OSM + DEM data pipeline** — clip extracts for SF + austere AO; hash manifests.
5. **SME route quality scoring** — you (Mountain Warfare trained) rate generated routes 1-5 vs. your hand-planned equivalents.
6. **Scenario authoring** — you write the 3 demo scenarios in operator vocabulary; Jon mocks them in Figma based on your scripts.

## Entry points

- `make data-fetch` — clips OSM PBF + downloads DEM tiles for the AOIs in `data/aois.yml`.
- `make data-verify` — checks hashes against `data/manifest.sha256`.
- `make valhalla-build` — builds Valhalla tiles from the clipped extracts.
- `bridge-run` (in `/atak/`) — starts the CoT bridge.

## Stack inside this lane

- **Valhalla** (Docker for build, native binary for runtime on Jetson). Custom-cost lua scripts.
- **`osmium`** CLI for OSM PBF clipping/filtering.
- **`gdal`** for DEM tile mosaicking.
- **`shapely` + `geojson`** Python libs for geometry handling.
- **Cesium Ion REST API** (token via `CESIUM_ION_TOKEN` in `.env`, Kyle provisioned) for pre-caching imagery + terrain tiles for both AOIs. Phase 3 must serve from `data/cache/cesium/` — never call `*.cesium.com` at runtime.
- **`pytak`** Python library for CoT XML construction (or a hand-rolled module — pytak has dependency baggage; evaluate at kickoff).
- **`lxml`** for CoT XML signing wrapper.

## File layout

```
atak/
  __init__.py
  bridge.py          # the main bridge service
  cot.py             # CoT XML construction + parsing
  signer_client.py   # thin client to /crypto/ signer (P2's lib)
  multicast.py       # multicast emit/listen on TAK default group
routing/
  __init__.py
  valhalla_client.py # subprocess or HTTP client to local Valhalla
  costs/
    __init__.py
    slope.py         # DEM-derived slope cost
    prominence.py    # ridgeline-avoidance cost
    cover.py         # landcover-based cover cost
  profiles/
    foot.json
    foot_covered.json
    vehicle_mrap.json
data/
  aois.yml           # AOI definitions: name, bbox, tags
  manifest.sha256    # hashes of every artifact
  README.md          # how to refresh data
  scripts/
    clip_osm.sh
    fetch_dem.sh
```

(Note: `/figma/` is in Jon's lane now. Ben writes scenario scripts; Jon mocks them up.)

## Contracts you OWN (with sign-off)

- `/docs/contracts/cot_signed.md` — co-owned with P2. The CoT XML schema with the signature wrapper.

## Contracts you MUST respect

- `/docs/contracts/agent_routing.schema.json` — the route response shape from P1.
- The signer interface from P2's `/crypto/` library: `sign(payload: bytes) -> Signature`.

## Routing & cost details

- **Valhalla custom costs:** Valhalla supports per-edge cost factors via the `costing_options` API. We override:
  - `slope_factor`: penalty proportional to absolute slope from DEM at edge midpoint.
  - `prominence_factor`: penalty for edges within N meters of a high-prominence ridge cell.
  - `cover_factor`: bonus for edges under high-cover landcover classes.
- **Cost computation:** pre-compute slope and prominence rasters from the DEM, snap edges to raster cells, write a per-edge cost CSV that Valhalla reads at tile-build time. (Doing this at routing time is too slow.)
- **Vehicle profile (Scenario C):** uses Valhalla's `truck` profile with custom `max_grade` and `restricted_bridge_tags` exclusion.

## Common gotchas

1. **DO NOT call ATAK across the network in Phase 3.** Loopback / USB / BLE only.
2. **Multicast group default for ATAK is 239.2.3.1:6969.** Some networks block multicast; test on the Jetson's local interface.
3. **Valhalla tiles are big.** Clip OSM aggressively; only ship the AOI extracts.
4. **CoT timestamps are ISO-8601 UTC, not local.** ATAK silently drops malformed timestamps.
5. **Whatever you do, do not leak the operator's location to logs or files outside `/data/runtime/`.**

## Definition of done for this lane

- `bridge-run` accepts `/plan` responses, signs them via P2's signer, emits CoT, ATAK draws the line.
- `make data-verify` passes for both AOIs.
- All 3 Figma mockups exist as PNG exports in `figma/exports/`.
- Routes for the hero scenario in both AOIs render in ATAK in under 5 sec from `/plan` response.
