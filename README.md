# TERA - Tactical Edge Route Agent

**Team TruePoint** - National Security Hackathon 2026, San Francisco.

TERA turns a TAK operator's plain-language terrain question into local, reviewable map output from a Jetson Orin Nano. The first operating principle is simple: when connectivity is denied, slow, or not worth the risk, the operator still needs a fast answer inside the TAK workflow they already use.

The current repo supports a Jetson-hosted web app, Samsung ATAK plugin traffic monitoring, a local Ollama/Gemma agent path, local OSM and DTED queries, and TAK-ready route/point artifacts. The PRD keeps the larger product direction in view: voice in/out, richer deterministic routing, signed CoT provenance, and a fully offline field workflow.

## Why It Matters

- **Shorter decision loop:** a field user can ask for water, road access, covered movement, no-go areas, LZs, or alternate routes and get a compact response aimed at action on the map.
- **Works where cloud tools do not:** the live Jetson path is built around local data under `/WINTAK Imagery` and `/DTED`, not Google Maps, cloud imagery, or web APIs.
- **Fits existing C2 behavior:** output is shaped for TAK users instead of asking a team to learn a new planning system during a mission.
- **Keeps sensitive intent local:** mission prompts, client position, map bounds, and generated route artifacts stay on the edge device in the offline demo path.
- **Creates accountable artifacts:** the web monitor shows Samsung TAK -> TERA -> Samsung TAK traffic, while generated CoT/KMZ package files give the plugin something concrete to place, update, or replace.

## Current Working Demo

The active Jetson demo path is the `llm_dev_kmh` FastAPI web app served through Docker Compose on port `8080`.

What works today:

- Cesium-based map monitor with a default AO centered on MGRS `11S KC 79790 48252`.
- `ATAK Local` mode that warms Ollama and uses `gemma3:4b` for TAK client prompts.
- Samsung ATAK traffic mirror showing inbound operator prompts and outbound TERA replies.
- Client location and ATAK map bounds passed into the prompt context.
- Local source selection constrained to:
  - `/WINTAK Imagery` for OSM vectors and staged imagery context.
  - `/DTED` for local elevation and terrain analysis.
- Guardrails for prompt injection, external downloads, fabricated geometry, unsigned CoT requests, and out-of-scope RF simulation.
- Operator-facing coordinates normalized to MGRS.
- TAK CoT/KMZ package generation for route and point outputs, with Samsung target handling for `/sdcard/fromTERA` and equivalent internal-storage paths.

What is not claimed as complete in the current path:

- Full voice input/output with Whisper and Piper.
- Full Valhalla custom-cost routing.
- End-to-end PQC-signed ATAK enforcement.
- Mesh transport and unsigned-track rejection as a live multi-device demo.

Those are PRD goals and remain part of the product direction, but this README should not overstate them as the active Jetson web app capability.

## Run The Current Jetson App

On the Jetson:

```bash
cd ~/Documents/tera_folder/tera
BRANCH=khick/jetson-webapp-run-20260503 ./deploy/scripts/jetson_compose_refresh.sh
```

Then open:

```text
http://10.1.63.96:8080
```

If the Jetson is on another address, replace `10.1.63.96` with the current device IP.

## Development Quickstart

```bash
git clone https://github.com/jdev-02/tera.git tera
cd tera
make install
lefthook install
make ci
```

The legacy agent service still runs on port `8000`:

```bash
make run
```

The current Jetson TAK monitor path runs from `llm_dev_kmh`:

```bash
uvicorn llm_dev_kmh.app:app --host 0.0.0.0 --port 8080
```

For Docker Compose:

```bash
docker compose up --build llm-dev-kmh
```

## Read Before Editing

1. [`AGENTS.md`](AGENTS.md) - agent guardrails.
2. [`docs/PRD.md`](docs/PRD.md) - product, architecture, security, and demo plan.
3. [`.agents/10-architecture.md`](.agents/10-architecture.md) - system design summary.
4. [`.agents/2X-<lane>.md`](.agents/) - lane-specific conventions when a lane file exists.
5. [`TASKS.md`](TASKS.md) - seed issues and backlog context.

## Repo Layout

```text
agent/        # Planning API and agent orchestration
ontology/     # Natural-language term to map/query concepts
voice/        # PRD lane for Whisper/Piper voice work
eval/         # Prompt regression and route-quality evaluation
atak/         # ATAK plugin, CoT bridge, device integration
routing/      # Deterministic routing and geospatial algorithms
data/         # Offline source configuration and AO data
hardware/     # Jetson bring-up
deploy/       # Jetson scripts, systemd, Docker refresh
models/       # Local model manifests and pins
mesh/         # Stretch transport work
security/     # Threat model and validation
crypto/       # Signature and PQC work
infra/        # CI, hardening, utility scripts
llm_dev_kmh/  # Current Jetson web app and ATAK/Ollama monitor
docs/         # PRD, contracts, ADRs
```

## Team TruePoint

| Member | Lane | Background | Demo role |
|---|---|---|---|
| Jon (`@jdev-02`) | agent, ontology, voice, eval, figma | Navy CWO, CS + AI | AI and workflow support |
| Satriyo (`@aleens-labs`) | security, crypto, infra, CI | Indonesian Navy, cybersecurity | security and PQC support |
| Kyle (`@khicks1724` / `@kylemhicks`) | hardware, deploy, models, mesh | USMC SIGINT, robotics | Jetson and live demo |
| Ben (`@benschwierking`) | atak, routing, data | USMC Combat Engineer, Mountain Warfare School | route quality and ATAK flow |

Source of truth: [`team.yml`](team.yml) and [`docs/PRD.md`](docs/PRD.md).

## License

MIT.
