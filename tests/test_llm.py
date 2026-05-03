"""Tests for the multi-provider LLM registry, profile gating, and structured
output adapters."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from agent import llm
from agent.schemas import Completion, Message, ToolCall


@pytest.fixture(autouse=True)
def _reset_registry() -> Iterator[None]:
    llm.reset_registry()
    yield
    llm.reset_registry()


# ---------------------------------------------------------------------------
# Profile gating
# ---------------------------------------------------------------------------


def test_invalid_profile_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERA_DEVICE_PROFILE", "totally-invalid")
    with pytest.raises(RuntimeError, match="Invalid TERA_DEVICE_PROFILE"):
        llm.LLMRegistry()


def test_austere_never_constructs_frontier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defense in depth: austere profile must NEVER instantiate any frontier client."""
    monkeypatch.setenv("TERA_DEVICE_PROFILE", "austere")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-be-used")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-not-be-used")
    with (
        patch("agent.llm.OllamaClient") as mock_ollama,
        patch("agent.llm.OpenAIClient") as mock_openai,
        patch("agent.llm.AnthropicClient") as mock_anthropic,
    ):
        mock_ollama.return_value = MagicMock(name="local")
        registry = llm.LLMRegistry()
        assert registry.profile == "austere"
        assert registry.allowed_modes == frozenset({"local"})
        mock_openai.assert_not_called()
        mock_anthropic.assert_not_called()


def test_austere_rejects_frontier_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERA_DEVICE_PROFILE", "austere")
    with patch("agent.llm.OllamaClient") as mock_ollama:
        mock_ollama.return_value = MagicMock(name="local")
        registry = llm.LLMRegistry()
        with pytest.raises(PermissionError, match="not allowed"):
            registry.get("frontier")


def test_garrison_default_local_frontier_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERA_DEVICE_PROFILE", "garrison")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with (
        patch("agent.llm.OllamaClient") as mock_ollama,
        patch("agent.llm.OpenAIClient") as mock_openai,
    ):
        local = MagicMock(name="local")
        frontier = MagicMock(name="openai")
        mock_ollama.return_value = local
        mock_openai.return_value = frontier
        registry = llm.LLMRegistry()
        assert registry.allowed_modes == frozenset({"local", "frontier"})
        assert registry.default_mode == "local"
        assert registry.get("frontier") is frontier
        assert registry.get("auto") is local


def test_sar_defaults_frontier(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERA_DEVICE_PROFILE", "sar")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with (
        patch("agent.llm.OllamaClient") as mock_ollama,
        patch("agent.llm.OpenAIClient") as mock_openai,
    ):
        local = MagicMock(name="local")
        frontier = MagicMock(name="openai")
        mock_ollama.return_value = local
        mock_openai.return_value = frontier
        registry = llm.LLMRegistry()
        assert registry.default_mode == "frontier"
        assert registry.get("auto") is frontier


# ---------------------------------------------------------------------------
# Frontier provider selection
# ---------------------------------------------------------------------------


def test_frontier_provider_anthropic_when_preferred(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERA_DEVICE_PROFILE", "garrison")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    monkeypatch.setenv("TERA_FRONTIER_PROVIDER", "anthropic")
    with (
        patch("agent.llm.OllamaClient") as mock_ollama,
        patch("agent.llm.AnthropicClient") as mock_anthropic,
        patch("agent.llm.OpenAIClient") as mock_openai,
    ):
        mock_ollama.return_value = MagicMock(name="local")
        anthropic_inst = MagicMock(name="anthropic")
        mock_anthropic.return_value = anthropic_inst
        registry = llm.LLMRegistry()
        # Anthropic was constructed; OpenAI was NOT (preference honored).
        mock_anthropic.assert_called_once()
        mock_openai.assert_not_called()
        assert registry.get("frontier") is anthropic_inst


def test_frontier_provider_falls_back_to_other_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pref openai but only Anthropic key present -> AnthropicClient is used."""
    monkeypatch.setenv("TERA_DEVICE_PROFILE", "garrison")
    monkeypatch.setenv("TERA_FRONTIER_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    with (
        patch("agent.llm.OllamaClient") as mock_ollama,
        patch("agent.llm.AnthropicClient") as mock_anthropic,
        patch("agent.llm.OpenAIClient") as mock_openai,
    ):
        mock_ollama.return_value = MagicMock(name="local")
        anthropic_inst = MagicMock(name="anthropic")
        mock_anthropic.return_value = anthropic_inst
        llm.LLMRegistry()
        mock_openai.assert_not_called()
        mock_anthropic.assert_called_once()


def test_frontier_no_keys_means_no_frontier(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERA_DEVICE_PROFILE", "garrison")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("agent.llm.OllamaClient") as mock_ollama:
        mock_ollama.return_value = MagicMock(name="local")
        registry = llm.LLMRegistry()
        with pytest.raises(RuntimeError, match="did not initialize"):
            registry.get("frontier")


# ---------------------------------------------------------------------------
# Loopback enforcement
# ---------------------------------------------------------------------------


def test_ollama_rejects_non_loopback_host(monkeypatch: pytest.MonkeyPatch) -> None:
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
        with patch("agent.llm.OllamaLib"):
            client = llm.OllamaClient()
            assert client.host == host


def test_openai_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        llm.OpenAIClient()


def test_anthropic_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        llm.AnthropicClient()


# ---------------------------------------------------------------------------
# Schema completion
# ---------------------------------------------------------------------------


def test_openai_complete_structured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content='{"a": 1}'))]
    with patch("agent.llm.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.create.return_value = fake_response
        client = llm.OpenAIClient()
        result = client.complete_structured(
            messages=[Message(role="user", content="x")],
            schema={"type": "object"},
        )
    assert result == {"a": 1}


def test_anthropic_complete_structured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    block = MagicMock()
    block.type = "tool_use"
    block.input = {"a": 1}
    fake_response = MagicMock(content=[block])
    with patch("agent.llm.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value.messages.create.return_value = fake_response
        client = llm.AnthropicClient()
        result = client.complete_structured(
            messages=[Message(role="user", content="x")],
            schema={"type": "object"},
        )
    assert result == {"a": 1}


def test_ollama_complete_structured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    fake_response = {"message": {"content": '{"a": 1}'}}
    with patch("agent.llm.OllamaLib") as mock_ollama_cls:
        mock_ollama_cls.return_value.chat.return_value = fake_response
        client = llm.OllamaClient()
        result = client.complete_structured(
            messages=[Message(role="user", content="x")],
            schema={"type": "object"},
        )
    assert client.model == "gemma3:4b"
    assert result == {"a": 1}


# ---------------------------------------------------------------------------
# Completion shape sanity
# ---------------------------------------------------------------------------


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
    assert c.tool_call is not None
    assert c.tool_call.name == "find_pois"


def test_get_registry_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERA_DEVICE_PROFILE", "austere")
    with patch("agent.llm.OllamaClient") as mock_ollama:
        mock_ollama.return_value = MagicMock(name="local")
        a = llm.get_registry()
        b = llm.get_registry()
        assert a is b
