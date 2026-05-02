"""Tests for the LLM registry, profile gating, and the two client impls."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from agent import llm
from agent.schemas import Completion, ToolCall


@pytest.fixture(autouse=True)
def _reset_registry() -> Iterator[None]:
    llm.reset_registry()
    yield
    llm.reset_registry()


def test_invalid_profile_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERA_DEVICE_PROFILE", "totally-invalid")
    with pytest.raises(RuntimeError, match="Invalid TERA_DEVICE_PROFILE"):
        llm.LLMRegistry()


def test_austere_never_constructs_frontier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defense in depth: austere profile must NEVER instantiate FrontierClient."""
    monkeypatch.setenv("TERA_DEVICE_PROFILE", "austere")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-be-used")
    with (
        patch("agent.llm.OllamaClient") as mock_ollama,
        patch("agent.llm.FrontierClient") as mock_frontier,
    ):
        mock_ollama.return_value = MagicMock(name="local")
        registry = llm.LLMRegistry()
        assert registry.profile == "austere"
        assert registry.default_mode == "local"
        assert registry.allowed_modes == frozenset({"local"})
        # The critical assertion: even with OPENAI_API_KEY set, austere never
        # touches FrontierClient. The key never enters memory.
        mock_frontier.assert_not_called()


def test_austere_rejects_frontier_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERA_DEVICE_PROFILE", "austere")
    with patch("agent.llm.OllamaClient") as mock_ollama:
        mock_ollama.return_value = MagicMock(name="local")
        registry = llm.LLMRegistry()
        with pytest.raises(PermissionError, match="not allowed"):
            registry.get("frontier")


def test_garrison_allows_both_local_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERA_DEVICE_PROFILE", "garrison")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with (
        patch("agent.llm.OllamaClient") as mock_ollama,
        patch("agent.llm.FrontierClient") as mock_frontier,
    ):
        local = MagicMock(name="local")
        frontier = MagicMock(name="frontier")
        mock_ollama.return_value = local
        mock_frontier.return_value = frontier
        registry = llm.LLMRegistry()
        assert registry.allowed_modes == frozenset({"local", "frontier"})
        assert registry.default_mode == "local"
        assert registry.get("local") is local
        assert registry.get("frontier") is frontier
        assert registry.get("auto") is local


def test_sar_defaults_to_frontier(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERA_DEVICE_PROFILE", "sar")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with (
        patch("agent.llm.OllamaClient") as mock_ollama,
        patch("agent.llm.FrontierClient") as mock_frontier,
    ):
        local = MagicMock(name="local")
        frontier = MagicMock(name="frontier")
        mock_ollama.return_value = local
        mock_frontier.return_value = frontier
        registry = llm.LLMRegistry()
        assert registry.default_mode == "frontier"
        assert registry.get("auto") is frontier


def test_garrison_without_api_key_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """If frontier is allowed but OPENAI_API_KEY is missing, frontier requests
    must fail with a clear RuntimeError, not silently route to local."""
    monkeypatch.setenv("TERA_DEVICE_PROFILE", "garrison")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with patch("agent.llm.OllamaClient") as mock_ollama:
        mock_ollama.return_value = MagicMock(name="local")
        registry = llm.LLMRegistry()
        # local works
        assert registry.get("local") is not None
        # frontier is allowed by profile but the client failed to initialize
        with pytest.raises(RuntimeError, match="did not initialize"):
            registry.get("frontier")


def test_ollama_rejects_non_loopback_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """OllamaClient must refuse a non-loopback host -- defense in depth."""
    monkeypatch.setenv("OLLAMA_HOST", "http://example.com:11434")
    with pytest.raises(RuntimeError, match="loopback"):
        llm.OllamaClient()


def test_ollama_accepts_loopback_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    for host in (
        "http://127.0.0.1:11434",
        "http://localhost:11434",
        "http://[::1]:11434",
    ):
        monkeypatch.setenv("OLLAMA_HOST", host)
        # Just construct it; we mock the actual client lib below.
        with patch("agent.llm.OllamaLib"):
            client = llm.OllamaClient()
            assert client.host == host


def test_frontier_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        llm.FrontierClient()


def test_completion_text_path() -> None:
    c = Completion(text="ok", finish_reason="stop", model="test")
    assert c.text == "ok"
    assert c.tool_call is None


def test_completion_tool_call_path() -> None:
    c = Completion(
        tool_call=ToolCall(name="find_pois", args_json='{"type": "freshwater"}'),
        finish_reason="tool_call",
        model="test",
    )
    assert c.text is None
    assert c.tool_call is not None
    assert c.tool_call.name == "find_pois"


def test_get_registry_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERA_DEVICE_PROFILE", "austere")
    with patch("agent.llm.OllamaClient") as mock_ollama:
        mock_ollama.return_value = MagicMock(name="local")
        a = llm.get_registry()
        b = llm.get_registry()
        assert a is b
