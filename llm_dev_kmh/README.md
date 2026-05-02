# LLM Dev KMH MVP

Small containerized web app for sending prompts from another device on your local network to an Ollama instance running on the host machine.

## What it does

- serves a minimal web UI on port `8080`
- accepts prompt requests at `/api/prompt`
- forwards requests to Ollama's `/api/generate`
- is configurable with `OLLAMA_BASE_URL` and `OLLAMA_MODEL`

## Run it

1. Start Ollama on the host machine and confirm the model is available.
2. From this directory, build and run the container:

```bash
docker compose up --build
```

3. From another device on the same network, open:

```text
http://YOUR-HOST-IP:8080
```

## Environment variables

- `OLLAMA_BASE_URL`: defaults to `http://host.docker.internal:11434`
- `OLLAMA_MODEL`: defaults to `gemma2:2b`
- `REQUEST_TIMEOUT_S`: defaults to `120`

## Notes

- On Docker Desktop, `host.docker.internal` should resolve automatically.
- On Linux, `extra_hosts` maps `host.docker.internal` to the Docker host gateway.
- If Ollama is running somewhere else on your LAN, set `OLLAMA_BASE_URL` to that reachable address before starting the container.