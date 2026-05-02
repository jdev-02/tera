"""LLM client abstraction with device-profile gating.

Two concrete clients (`FrontierClient` for OpenAI; `OllamaClient` for local Gemma)
sit behind a single `LLMClient` Protocol. An `LLMRegistry` decides which clients
are available for the current device, based on the `TERA_DEVICE_PROFILE` env var.

Why profiles, not just an env var picking one provider:
A frontier API call from a comms-denied environment is an OPSEC failure -- it
emits RF (HTTPS request to OpenAI) that an adversary can geolocate. The
`austere` profile makes this mechanically impossible by never even constructing
the FrontierClient. The OPENAI_API_KEY never enters memory.

Profiles:
    austere   default; local-only. FrontierClient never constructed.
    garrison  local default; frontier allowed if operator explicitly chooses.
    sar       frontier default (satellite assumed); can fall back to local.

The orchestrator (#5) calls `get_registry().get(mode)` per request. `mode` is
"auto" (uses profile default), "frontier", or "local". Mode validation against
the profile's allowed set raises `PermissionError` -- a 403 at the API layer.
"""

from __future__ import annotations

import json
import os
from typing import Any, Literal, Protocol, runtime_checkable

import structlog
from ollama import Client as OllamaLib
from openai import OpenAI

from agent.schemas import Completion, Message, ToolCall, ToolDef

log = structlog.get_logger(__name__)

Profile = Literal["austere", "garrison", "sar"]
Mode = Literal["frontier", "local"]
ModeOrAuto = Literal["frontier", "local", "auto"]

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
    """Provider-agnostic LLM interface.

    Implementations must be deterministic for the same `(messages, tools, temperature)`
    when temperature=0, and must raise standard exceptions on transport failure
    (no silent retries -- the orchestrator decides retry policy).
    """

    name: str

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> Completion: ...


class FrontierClient:
    """OpenAI-compatible frontier model.

    Phase 1 / 2 only. Network-egressing -- must NEVER be instantiated in austere
    profile. The `LLMRegistry` enforces this; do not bypass.
    """

    name = "frontier"

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY required for FrontierClient")
        self.client = OpenAI(api_key=key)
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> Completion:
        oa_messages = [m.model_dump(exclude_none=True) for m in messages]
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": oa_messages,
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


class OllamaClient:
    """Local Gemma via ollama. Phase 3. Loopback only.

    Refuses to start if OLLAMA_HOST is not loopback -- defense in depth so a
    misconfiguration cannot turn this into an egressing client.
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
        self.model = model or os.environ.get("OLLAMA_MODEL", "gemma2:2b")
        self.client = OllamaLib(host=self.host)

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> Completion:
        ol_messages: list[dict[str, str]] = [
            {"role": m.role, "content": m.content} for m in messages
        ]
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
            try:
                self._clients["frontier"] = FrontierClient()
            except RuntimeError as e:
                log.warning("frontier_client_unavailable", error=str(e))

        log.info(
            "llm_registry_initialized",
            profile=self.profile,
            allowed_modes=sorted(PROFILE_ALLOWED[self.profile]),
            available=sorted(self._clients.keys()),
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
        """Return an LLM client for the requested mode.

        Raises:
            PermissionError: mode is not allowed by the current device profile.
            RuntimeError: mode is allowed but the client failed to initialize.
        """
        resolved: Mode = self.default_mode if mode == "auto" else mode
        if resolved not in self.allowed_modes:
            raise PermissionError(
                f"mode {resolved!r} not allowed in profile {self.profile!r}. "
                f"Allowed: {sorted(self.allowed_modes)}"
            )
        if resolved not in self._clients:
            raise RuntimeError(
                f"mode {resolved!r} is allowed but the client did not initialize. "
                "Check service availability (ollama running? OPENAI_API_KEY set?)."
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
