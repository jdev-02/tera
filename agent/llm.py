"""LLM client abstraction with multi-provider frontier + device-profile gating.

Three concrete clients sit behind one Protocol:

  OpenAIClient     -- frontier, uses native response_format=json_schema (strict)
  AnthropicClient  -- frontier, uses native tool-calling for structured output
  OllamaClient     -- local, uses native format=schema (Ollama Dec-2024 feature)

All three implement `complete()` (free-form text) and `complete_structured()`
(returns a dict guaranteed to match a JSON schema).

Why profiles, not just an env var picking one provider:
A frontier API call from a comms-denied environment is an OPSEC failure -- it
emits RF (HTTPS request) that an adversary can geolocate. The `austere` profile
makes this mechanically impossible by never even constructing a frontier client.
The API key never enters memory.

Profiles:
    austere   default; local-only.
    garrison  local default; frontier allowed if operator explicitly chooses.
    sar       frontier default (satellite assumed); can fall back to local.

Frontier provider selection (when allowed by profile):
    TERA_FRONTIER_PROVIDER=openai|anthropic   (default: openai)
    Falls back to whichever API key is present if the chosen provider's key
    is missing.
"""

from __future__ import annotations

import json
import os
from typing import Any, Literal, Protocol, runtime_checkable

import structlog
from anthropic import Anthropic
from ollama import Client as OllamaLib
from openai import OpenAI

from agent.schemas import Completion, Message, ToolCall, ToolDef

log = structlog.get_logger(__name__)

Profile = Literal["austere", "garrison", "sar"]
Mode = Literal["frontier", "local"]
ModeOrAuto = Literal["frontier", "local", "auto"]
FrontierProvider = Literal["openai", "anthropic"]

PROFILE_ALLOWED: dict[Profile, frozenset[Mode]] = {
    "austere": frozenset({"local"}),
    "garrison": frozenset({"local", "frontier"}),
    "sar": frozenset({"local", "frontier"}),
}

PROFILE_DEFAULT: dict[Profile, Mode] = {
    "austere": "local",
    "garrison": "local",
    "sar": "frontier",
}


@runtime_checkable
class LLMClient(Protocol):
    """Provider-agnostic LLM interface. Both methods must be deterministic
    for the same inputs when temperature=0."""

    name: str

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> Completion: ...

    def complete_structured(
        self,
        messages: list[Message],
        schema: dict[str, Any],
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Return a dict guaranteed (by the provider) to match the JSON schema.

        Raises RuntimeError if the provider's structured-output mechanism fails.
        """
        ...


# ---------------------------------------------------------------------------
# OpenAI (frontier)
# ---------------------------------------------------------------------------


class OpenAIClient:
    """OpenAI frontier model. Uses native response_format=json_schema (strict)."""

    name = "openai"

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY required for OpenAIClient")
        self.client = OpenAI(api_key=key)
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def _to_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        return [m.model_dump(exclude_none=True) for m in messages]

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> Completion:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": self._to_messages(messages),
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = [{"type": "function", "function": t.model_dump()} for t in tools]
        resp = self.client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        msg = choice.message
        usage = resp.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0

        if msg.tool_calls:
            tc = msg.tool_calls[0]
            return Completion(
                tool_call=ToolCall(name=tc.function.name, args_json=tc.function.arguments),
                finish_reason="tool_call",
                model=self.model,
                usage_prompt_tokens=prompt_tokens,
                usage_completion_tokens=completion_tokens,
            )
        return Completion(
            text=msg.content,
            finish_reason="stop" if choice.finish_reason == "stop" else "length",
            model=self.model,
            usage_prompt_tokens=prompt_tokens,
            usage_completion_tokens=completion_tokens,
        )

    def complete_structured(
        self,
        messages: list[Message],
        schema: dict[str, Any],
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        # mypy's strict overload typing on OpenAI's create() doesn't play nicely
        # with our generic dict[str, Any] message list; the runtime call is fine.
        resp = self.client.chat.completions.create(  # type: ignore[call-overload]
            model=self.model,
            messages=self._to_messages(messages),
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "RouteQuery",
                    "schema": schema,
                    "strict": True,
                },
            },
        )
        content = resp.choices[0].message.content
        if not content:
            raise RuntimeError("OpenAI returned empty content for structured completion")
        parsed: dict[str, Any] = json.loads(content)
        return parsed


# ---------------------------------------------------------------------------
# Anthropic (frontier)
# ---------------------------------------------------------------------------


class AnthropicClient:
    """Anthropic frontier model. Uses tool-calling for structured output (the
    Anthropic-recommended pattern -- the model emits a single tool call whose
    `input` is the JSON object matching the schema)."""

    name = "anthropic"

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY required for AnthropicClient")
        self.client = Anthropic(api_key=key)
        self.model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")

    def _split_messages(self, messages: list[Message]) -> tuple[str | None, list[dict[str, Any]]]:
        """Anthropic takes `system` separately from `messages`."""
        system: str | None = None
        rest: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "system":
                system = m.content if system is None else system + "\n\n" + m.content
            else:
                rest.append({"role": m.role, "content": m.content})
        return system, rest

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> Completion:
        system, rest = self._split_messages(messages)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": rest,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.parameters or {"type": "object"},
                }
                for t in tools
            ]
        resp = self.client.messages.create(**kwargs)

        prompt_tokens = resp.usage.input_tokens if resp.usage else 0
        completion_tokens = resp.usage.output_tokens if resp.usage else 0

        for block in resp.content:
            if getattr(block, "type", None) == "tool_use":
                return Completion(
                    tool_call=ToolCall(name=block.name, args_json=json.dumps(block.input)),
                    finish_reason="tool_call",
                    model=self.model,
                    usage_prompt_tokens=prompt_tokens,
                    usage_completion_tokens=completion_tokens,
                )
        text = "".join(getattr(b, "text", "") for b in resp.content)
        return Completion(
            text=text,
            finish_reason="stop" if resp.stop_reason == "end_turn" else "length",
            model=self.model,
            usage_prompt_tokens=prompt_tokens,
            usage_completion_tokens=completion_tokens,
        )

    def complete_structured(
        self,
        messages: list[Message],
        schema: dict[str, Any],
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        system, rest = self._split_messages(messages)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": rest,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "tools": [
                {
                    "name": "emit_route_query",
                    "description": (
                        "Emit a RouteQuery JSON object. This is the only thing you may do."
                    ),
                    "input_schema": schema,
                }
            ],
            "tool_choice": {"type": "tool", "name": "emit_route_query"},
        }
        if system:
            kwargs["system"] = system
        resp = self.client.messages.create(**kwargs)
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use":
                return dict(block.input)
        raise RuntimeError("Anthropic did not return a tool_use block for structured completion")


# ---------------------------------------------------------------------------
# Ollama (local)
# ---------------------------------------------------------------------------


class OllamaClient:
    """Local Gemma via ollama. Loopback only.

    Refuses to start if OLLAMA_HOST is not loopback -- defense in depth so a
    misconfiguration cannot turn this into an egressing client.

    Uses ollama's native `format=<schema>` parameter (added Dec 2024) for
    structured output -- no prompt-based JSON parsing needed.
    """

    name = "local"

    def __init__(self, model: str | None = None, host: str | None = None) -> None:
        self.host = host or os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
        if not (
            self.host.startswith("http://127.")
            or self.host.startswith("http://localhost")
            or self.host.startswith("http://[::1]")
        ):
            raise RuntimeError(
                f"OllamaClient host must be loopback, got: {self.host}. "
                "Refusing to start to prevent accidental network egress."
            )
        self.model = model or os.environ.get("OLLAMA_MODEL", "gemma3:4b")
        self.client = OllamaLib(host=self.host)

    def _to_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in messages]

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> Completion:
        ol_messages = self._to_messages(messages)
        if tools:
            tool_prompt = (
                "When you need to call a tool, respond with ONLY a JSON object "
                'of the form {"tool": "<name>", "args": {...}}. No prose, no '
                "markdown fences. Available tools: " + json.dumps([t.model_dump() for t in tools])
            )
            ol_messages.insert(0, {"role": "system", "content": tool_prompt})

        resp = self.client.chat(
            model=self.model,
            messages=ol_messages,
            options={"num_predict": max_tokens, "temperature": temperature},
        )
        text = resp["message"]["content"]

        if tools:
            stripped = text.strip()
            if stripped.startswith("```"):
                stripped = stripped.strip("`").lstrip("json").strip()
            try:
                parsed = json.loads(stripped)
                if (
                    isinstance(parsed, dict)
                    and "tool" in parsed
                    and "args" in parsed
                    and isinstance(parsed["args"], dict)
                ):
                    return Completion(
                        tool_call=ToolCall(
                            name=str(parsed["tool"]),
                            args_json=json.dumps(parsed["args"]),
                        ),
                        finish_reason="tool_call",
                        model=self.model,
                    )
            except json.JSONDecodeError:
                pass
        return Completion(text=text, finish_reason="stop", model=self.model)

    def complete_structured(
        self,
        messages: list[Message],
        schema: dict[str, Any],
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        resp = self.client.chat(
            model=self.model,
            messages=self._to_messages(messages),
            format=schema,
            options={"num_predict": max_tokens, "temperature": temperature},
        )
        content = resp["message"]["content"]
        parsed: dict[str, Any] = json.loads(content)
        return parsed


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def _select_frontier_class() -> type[LLMClient] | None:
    """Pick OpenAI or Anthropic based on env var + key presence.

    Returns the class to instantiate, or None if no frontier provider is
    configured (e.g. austere profile with no API keys).
    """
    pref = os.environ.get("TERA_FRONTIER_PROVIDER", "openai").lower()
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))

    if pref == "anthropic" and has_anthropic:
        return AnthropicClient
    if pref == "openai" and has_openai:
        return OpenAIClient
    # Fallback: whichever key is present
    if has_openai:
        return OpenAIClient
    if has_anthropic:
        return AnthropicClient
    return None


class LLMRegistry:
    """Holds available LLM clients gated by device profile.

    Initialization is best-effort: a missing API key or a non-running ollama
    daemon does NOT fail construction; it just means that mode is unavailable.
    Calls to `get(mode)` for an unavailable but allowed mode raise RuntimeError
    so the API layer can return 503.
    """

    def __init__(self, profile: Profile | None = None) -> None:
        self.profile: Profile = profile or self._load_profile()
        self._clients: dict[Mode, LLMClient] = {}

        try:
            self._clients["local"] = OllamaClient()
        except RuntimeError as e:
            log.warning("local_client_unavailable", error=str(e))

        if "frontier" in PROFILE_ALLOWED[self.profile]:
            frontier_cls = _select_frontier_class()
            if frontier_cls is not None:
                try:
                    self._clients["frontier"] = frontier_cls()
                except RuntimeError as e:
                    log.warning("frontier_client_unavailable", error=str(e))
            else:
                log.warning("frontier_no_api_key", note="set OPENAI_API_KEY or ANTHROPIC_API_KEY")

        log.info(
            "llm_registry_initialized",
            profile=self.profile,
            allowed_modes=sorted(PROFILE_ALLOWED[self.profile]),
            available={mode: c.name for mode, c in self._clients.items()},
            default=PROFILE_DEFAULT[self.profile],
        )

    @staticmethod
    def _load_profile() -> Profile:
        raw = os.environ.get("TERA_DEVICE_PROFILE", "austere")
        if raw not in PROFILE_ALLOWED:
            raise RuntimeError(
                f"Invalid TERA_DEVICE_PROFILE={raw!r}. Must be one of: {sorted(PROFILE_ALLOWED)}"
            )
        return raw

    @property
    def default_mode(self) -> Mode:
        return PROFILE_DEFAULT[self.profile]

    @property
    def allowed_modes(self) -> frozenset[Mode]:
        return PROFILE_ALLOWED[self.profile]

    def get(self, mode: ModeOrAuto = "auto") -> LLMClient:
        resolved: Mode = self.default_mode if mode == "auto" else mode
        if resolved not in self.allowed_modes:
            raise PermissionError(
                f"mode {resolved!r} not allowed in profile {self.profile!r}. "
                f"Allowed: {sorted(self.allowed_modes)}"
            )
        if resolved not in self._clients:
            raise RuntimeError(
                f"mode {resolved!r} is allowed but the client did not initialize. "
                "Check service availability "
                "(ollama running? OPENAI_API_KEY / ANTHROPIC_API_KEY set?)."
            )
        return self._clients[resolved]


_registry: LLMRegistry | None = None


def get_registry() -> LLMRegistry:
    """Module-level lazy singleton. Most callers should use this."""
    global _registry
    if _registry is None:
        _registry = LLMRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the singleton. For tests only."""
    global _registry
    _registry = None
