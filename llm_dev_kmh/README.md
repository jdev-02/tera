# LLM Dev KMH Workspace

Map-centric local LLM workspace kept entirely inside `llm_dev_kmh`.

## What it does

- serves a Cesium-based map view with imagery and terrain streaming
- exposes an operator sidebar tailored for TERA map and source-planning workflows
- lists locally installed Ollama models
- sends prompt requests to local Ollama via `/api/prompt`
- lets the operator draw and resize an AO rectangle for source package coverage

## Run it directly

1. Start Ollama on the host machine and confirm the model is available.
2. Set environment variables as needed.
3. Start the app with Uvicorn from an environment that has the requirements installed.

Example on Windows PowerShell:

```powershell
$env:OLLAMA_BASE_URL="http://127.0.0.1:11434"
$env:OLLAMA_MODEL="gemma4:e4b"
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

- `OLLAMA_BASE_URL`: defaults to `http://host.docker.internal:11434`
- `OLLAMA_MODEL`: default model exposed in the UI
- `REQUEST_TIMEOUT_S`: prompt timeout in seconds, default `120`
- `CESIUM_ION_TOKEN`: required for Cesium World Terrain and Cesium satellite imagery
- `DEFAULT_LAT`: initial camera latitude, default `37.7749`
- `DEFAULT_LON`: initial camera longitude, default `-122.4194`
- `DEFAULT_HEIGHT_M`: initial camera height in meters, default `14000`

## Notes

- Without `CESIUM_ION_TOKEN`, the workspace falls back to OpenStreetMap imagery and ellipsoid terrain.
- On Docker Desktop, `host.docker.internal` should resolve automatically.
- On Linux, `extra_hosts` maps `host.docker.internal` to the Docker host gateway.
- If Ollama is running somewhere else on your LAN, set `OLLAMA_BASE_URL` to that reachable address before starting the container.
