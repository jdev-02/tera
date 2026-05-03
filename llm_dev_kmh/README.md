# TERA Jetson Web App

`llm_dev_kmh` is the current Jetson-facing web app for the TERA demo. It gives the operator a Cesium map, a local model chat surface, and a monitor for Samsung ATAK traffic moving through the Jetson.

The live ATAK path is deliberately narrow: use local Jetson data, answer fast, generate TAK-ready artifacts when there is enough map context, and avoid asking the operator for more data that is not available in the field.

## Current Role

- Serve the map and operator panel on port `8080`.
- Activate local ATAK mode against Ollama, normally `gemma3:4b`.
- Mirror ATAK client prompts and TERA replies in the browser.
- Use the ATAK client location and displayed map bounds as prompt context.
- Query local OSM vectors from `/WINTAK Imagery`.
- Query local DTED terrain from `/DTED`.
- Generate route/point CoT and KMZ/data-package output for the TAK client folder.
- Keep chat coordinates in MGRS for the operator.
- Guardrail prompts that ask for cloud data, fabricated routes, hidden prompts, unsigned CoT, or unsupported RF simulation.

## Data Contract

For the ATAK live demo, TERA should only treat these as analysis sources:

```text
/WINTAK Imagery   OSM vectors and staged visual context
/DTED             local DTED cells for elevation and terrain analysis
```

Cesium, NAIP, OSM basemap tiles, and other imagery streams are useful for web display and planning context. They are not the evidence source for the local TERA agent's terrain answer unless they have been staged into the local Jetson folders above and the code explicitly indexes them.

## Run On The Jetson

```bash
cd ~/Documents/tera_folder/tera
BRANCH=khick/jetson-webapp-run-20260503 ./deploy/scripts/jetson_compose_refresh.sh
```

Then open:

```text
http://10.1.63.96:8080
```

If the Jetson IP changes, use the new address.

## Run Directly

Start Ollama on the host and confirm `gemma3:4b` is available:

```bash
ollama list
```

Run the app:

```bash
uvicorn llm_dev_kmh.app:app --host 0.0.0.0 --port 8080
```

## Run With Docker Compose

From the repo root:

```bash
docker compose up --build llm-dev-kmh
```

## Useful Environment Variables

Local model and ATAK:

- `OLLAMA_BASE_URL`: Ollama endpoint, default `http://127.0.0.1:11434`.
- `OLLAMA_MODEL`: default local model for general local fallback, usually `gemma3:4b`.
- `TERA_ATAK_MODEL`: model used by the `ATAK Local` button, default `gemma3:4b`.
- `TERA_ATAK_DEVICE_URL`: optional ATAK plugin/device URL shown in activation status.
- `TERA_PUBLIC_BASE_URL`: public Jetson URL shown to the Samsung plugin, for example `http://10.1.63.96:8080`.
- `TERA_JETSON_IP`: fallback Jetson IP for ATAK endpoint display.
- `TERA_ATAK_MIRROR_LOG`: JSONL traffic mirror path; defaults under `OFFLINE_PACKAGE_ROOT/runtime/`.

Local data:

- `TERA_WINTAK_IMAGERY_DIR`: defaults to `/WINTAK Imagery` on the Jetson.
- `TERA_OSM_ROOT_DIRS`: OS-path-separated local OSM roots or globs; defaults to the WinTAK imagery folder.
- `DTED_SOURCE_DIR`: defaults to `/DTED` on the Jetson.
- `TERA_JETSON_LOCAL_SOURCES_ONLY`: defaults to `1`; keeps the Jetson path on staged local data.
- `OFFLINE_PACKAGE_ROOT`: package, runtime, route artifact, and CoT/KMZ output root.

Map display:

- `CESIUM_ION_TOKEN`: optional for Cesium imagery/terrain display.
- `DEFAULT_LAT`: initial camera latitude, default for MGRS `11S KC 79790 48252`.
- `DEFAULT_LON`: initial camera longitude, default for MGRS `11S KC 79790 48252`.
- `DEFAULT_HEIGHT_M`: initial camera height in meters, default `14000`.

Cloud/source-planning fallback:

- `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `ANTHROPIC_API_URL`, and `ANTHROPIC_MODELS_URL` support the broader browser source-planning workflow. They are not required for the ATAK live local-agent path.

## Notes

- Pressing `ATAK Local` verifies local Ollama, warms `gemma3:4b`, switches automatic prompt traffic to the local model, and opens the Samsung ATAK monitor.
- Without a Cesium token, the map falls back to open imagery and ellipsoid terrain. That changes the browser display, not the local OSM/DTED constraint for the ATAK agent.
- On Docker Desktop, `host.docker.internal` should resolve automatically. On Linux, the compose file maps it to the Docker host gateway.
