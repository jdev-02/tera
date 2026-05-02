from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

from llm_dev_kmh import app as kmh_app


class _FakeStreamContext:
    def __init__(self, response: object) -> None:
        self.response = response

    async def __aenter__(self) -> object:
        return self.response

    async def __aexit__(self, *_exc_info: object) -> None:
        return None


class _FakeAsyncClient:
    response: object

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        return None

    def stream(self, *_args: object, **_kwargs: Any) -> _FakeStreamContext:
        return _FakeStreamContext(self.response)


class _TokenResponse:
    status_code = 200

    async def aiter_lines(self) -> AsyncIterator[str]:
        yield json.dumps({"response": "Hello ", "done": False})
        yield json.dumps({"response": "operator.", "done": False})
        yield json.dumps({"done": True})


class _ErrorResponse:
    status_code = 404

    async def aread(self) -> bytes:
        return b'{"error":"model missing"}'


async def _collect_stream(response: object) -> str:
    body_iterator = response.body_iterator
    chunks: list[str] = []
    async for chunk in body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
    return "".join(chunks)


@pytest.mark.asyncio
async def test_prompt_stream_yields_sse_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeAsyncClient.response = _TokenResponse()
    monkeypatch.setattr(kmh_app.httpx, "AsyncClient", _FakeAsyncClient)

    response = await kmh_app.prompt_ollama_stream(
        kmh_app.PromptRequest(prompt="What can you do?", model="gemma4:e4b")
    )

    body = await _collect_stream(response)

    assert '"type": "start"' in body
    assert '"type": "status"' in body
    assert '"text": "Hello "' in body
    assert '"text": "operator."' in body
    assert '"type": "done"' in body


@pytest.mark.asyncio
async def test_prompt_stream_reports_ollama_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeAsyncClient.response = _ErrorResponse()
    monkeypatch.setattr(kmh_app.httpx, "AsyncClient", _FakeAsyncClient)

    response = await kmh_app.prompt_ollama_stream(
        kmh_app.PromptRequest(prompt="What can you do?", model="missing")
    )

    body = await _collect_stream(response)

    assert '"type": "error"' in body
    assert "model missing" in body
