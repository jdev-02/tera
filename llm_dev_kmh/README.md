# LLM Dev KMH Workspace

Map-centric local LLM workspace kept entirely inside `llm_dev_kmh`.

## What it does

- serves a Cesium-based map view with imagery and terrain streaming
- exposes an operator sidebar tailored for TERA map and source-planning workflows
- lists locally installed Ollama models
- sends prompt requests through `/api/prompt` with Claude-first, Ollama-second fallback
- switches into Jetson ATAK local-agent mode with Ollama `gemma3:4b` and a browser mirror of ATAK-profile prompt traffic
- lets the operator draw and resize an AO rectangle for source package coverage

## Run it directly

1. Start Ollama on the host machine and confirm the model is available.
2. Set environment variables as needed. Put `ANTHROPIC_API_KEY` in the repo
   root `.env` when Claude should be the primary provider.
3. Start the app with Uvicorn from an environment that has the requirements installed.

Example on Windows PowerShell:

```powershell
$env:OLLAMA_BASE_URL="http://127.0.0.1:11434"
$env:OLLAMA_MODEL="gemma3:4b"
$env:CLAUDE_MODEL="claude-sonnet-4-6"
$env:CESIUM_ION_TOKEN="YOUR_TOKEN_HERE"
uvicorn llm_dev_kmh.app:app --host 0.0.0.0 --port 8080
```

Then open:

```text
http://YOUR-HOST-IP:8080
```

## Run it in Docker

```bash
docker compose up --build
```

## Environment variables

- `ANTHROPIC_API_KEY`: primary Claude API key loaded from repo root `.env` or environment
- `CLAUDE_MODEL`: primary Claude model, default `claude-sonnet-4-6`
- `ANTHROPIC_API_URL`: Claude Messages endpoint, default `https://api.anthropic.com/v1/messages`
- `ANTHROPIC_MODELS_URL`: Claude model discovery endpoint, default `https://api.anthropic.com/v1/models`
- `OLLAMA_BASE_URL`: defaults to `http://127.0.0.1:11434`
- `OLLAMA_MODEL`: local fallback default, `gemma3:4b`; if unavailable, the app autodetects an installed Ollama model
- `TERA_ATAK_MODEL`: model used by the ATAK Local button, default `gemma3:4b`
- `TERA_ATAK_AGENT_COMMAND`: optional command launched by the ATAK Local button, for example a tmux/systemd wrapper on the Jetson
- `TERA_ATAK_DEVICE_URL`: optional ATAK plugin/device target shown in activation status
- `TERA_ATAK_OLLAMA_KEEP_ALIVE`: Ollama keep-alive used after ATAK activation, default `30m`
- `TERA_ATAK_WARMUP_TIMEOUT_S`: maximum synchronous web warmup wait, default `20`; Jetson compose warmup runs in the background
- `TERA_PUBLIC_BASE_URL`: optional public Jetson web URL shown to the Samsung ATAK plugin, for example `http://10.1.63.96:8080`
- `TERA_JETSON_IP`: optional Jetson IP fallback for ATAK plugin endpoint display
- `TERA_ATAK_MIRROR_LOG`: optional JSONL mirror path; defaults under `OFFLINE_PACKAGE_ROOT/runtime/`
- `REQUEST_TIMEOUT_S`: prompt timeout in seconds, default `120`
- `CESIUM_ION_TOKEN`: required for Cesium World Terrain and Cesium satellite imagery
- `CESIUM_ION_ARCHIVE_ID`: optional completed Cesium ion archive id to download into the Jetson package root.
- `CESIUM_ION_ASSET_IDS`: optional comma-separated ion asset ids for creating a bounded AO clip before downloading it. Use only with assets/licensing that permit archives or clips.
- Cesium World stream data stays stream-only. The Jetson offline package downloads Cesium only through ion archives/exports, then extracts and indexes the local files for query/preview.
- `ESRI_ARCGIS_TOKEN`: optional; used only if the operator explicitly selects Esri export jobs. The default U.S. imagery path uses NAIP, with Sentinel-2 as the global fallback.
- `NAIP_AWS_STATE`, `NAIP_AWS_YEAR`, `NAIP_AWS_RESOLUTION`, `NAIP_AWS_BANDSET`: controls public NAIP AWS prefix downloads; defaults are inferred U.S. state, `2022`, `60cm`, and `rgbir`.
- `NAIP_AWS_BUCKET`: defaults to `naip-analytic`; set to `naip-visualization` for RGB COGs when desired.
- `NAIP_MAX_FILES`: safety cap for NAIP prefix downloads; defaults to `50`.
- `NAIP_EARTHEXPLORER_DIR`: optional folder of EarthExplorer NAIP GeoTIFFs to import instead of relying only on AWS prefix downloads.
- `GEOFABRIK_PBF_URL` or `GEOFABRIK_REGION_SLUG`: optional OSM override; otherwise the app infers a U.S. state extract such as `north-america/us/nevada-latest.osm.pbf`.
- `DTED_SOURCE_DIR`: optional folder of EarthExplorer `.dt0/.dt1/.dt2` files; imported and converted with `gdal_translate` if GDAL is installed.
- `OFFLINE_PACKAGE_ROOT`: Jetson directory where source packages, status files, terrain rasters, route artifacts, and CoT XML are written; defaults to `llm_dev_kmh/offline_packages`
- `PACKAGE_MIN_FREE_GB`: disk space reserve enforced before downloads start; defaults to `10`
- `DEFAULT_LAT`: initial camera latitude, default `37.7749`
- `DEFAULT_LON`: initial camera longitude, default `-122.4194`
- `DEFAULT_HEIGHT_M`: initial camera height in meters, default `14000`

## Notes

- Without `CESIUM_ION_TOKEN`, the workspace falls back to OpenStreetMap imagery and ellipsoid terrain.
- Provider order defaults to Claude first when `ANTHROPIC_API_KEY` is configured, then detected local Ollama, then the deterministic browser planner.
- Pressing `ATAK Local` verifies local Ollama, pulls `gemma3:4b` if needed, warms it with the `tera-atak-live` system profile, forces auto prompt traffic to local Ollama, and opens a mirror panel with the Samsung plugin endpoint.
- On Docker Desktop, `host.docker.internal` should resolve automatically.
- On Linux, `extra_hosts` maps `host.docker.internal` to the Docker host gateway.
- If Ollama is running somewhere else on your LAN, set `OLLAMA_BASE_URL` to that reachable address before starting the container.
