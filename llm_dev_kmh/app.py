from __future__ import annotations

import os
from pathlib import Path

import httpx
import structlog
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

log = structlog.get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "static" / "index.html"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:2b")
REQUEST_TIMEOUT_S = float(os.getenv("REQUEST_TIMEOUT_S", "120"))

app = FastAPI(title="LLM Dev KMH MVP", version="0.1.0")


class PromptRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)
    system: str | None = Field(default=None, max_length=4000)
    model: str | None = Field(default=None, max_length=200)


class PromptResponse(BaseModel):
    model: str
    response: str


class ModelsResponse(BaseModel):
    default_model: str
    models: list[str]


@app.get("/")
async def serve_index() -> FileResponse:
    return FileResponse(INDEX_FILE)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "ollama_base_url": OLLAMA_BASE_URL}


@app.get("/api/models", response_model=ModelsResponse)
async def list_ollama_models() -> ModelsResponse:
    timeout = httpx.Timeout(30.0, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500]
        log.error(
            "ollama_tags_http_error",
            status_code=exc.response.status_code,
            body=body,
            ollama_base_url=OLLAMA_BASE_URL,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Could not list models: Ollama returned {exc.response.status_code}: {body}",
        ) from exc
    except httpx.HTTPError as exc:
        log.error("ollama_tags_connection_error", error=str(exc), ollama_base_url=OLLAMA_BASE_URL)
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not reach Ollama to list models. Confirm it is running and that "
                f"OLLAMA_BASE_URL={OLLAMA_BASE_URL} is reachable."
            ),
        ) from exc

    data = response.json()
    models = [
        str(model.get("name", "")).strip()
        for model in data.get("models", [])
        if str(model.get("name", "")).strip()
    ]
    return ModelsResponse(default_model=OLLAMA_MODEL, models=models)


@app.post("/api/prompt", response_model=PromptResponse)
async def prompt_ollama(request: PromptRequest) -> PromptResponse:
    model = request.model or OLLAMA_MODEL
    payload = {
        "model": model,
        "stream": False,
        "prompt": request.prompt,
    }
    if request.system:
        payload["system"] = request.system

    timeout = httpx.Timeout(REQUEST_TIMEOUT_S, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500]
        log.error(
            "ollama_http_error",
            status_code=exc.response.status_code,
            body=body,
            ollama_base_url=OLLAMA_BASE_URL,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Ollama returned {exc.response.status_code}: {body}",
        ) from exc
    except httpx.HTTPError as exc:
        log.error("ollama_connection_error", error=str(exc), ollama_base_url=OLLAMA_BASE_URL)
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not reach Ollama. Confirm it is running and that "
                f"OLLAMA_BASE_URL={OLLAMA_BASE_URL} is reachable from the container."
            ),
        ) from exc

    data = response.json()
    text = str(data.get("response", "")).strip()
    if not text:
        raise HTTPException(status_code=502, detail="Ollama returned an empty response.")

    return PromptResponse(model=model, response=text)