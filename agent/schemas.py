"""Pydantic models shared across the agent.

Provider-agnostic shapes for messages, tool definitions, tool calls, and completions.
Used by both FrontierClient (OpenAI) and OllamaClient (local Gemma) in agent.llm.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    """One message in an LLM conversation."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_call_id: str | None = None
    name: str | None = None


class ToolDef(BaseModel):
    """JSON-schema description of a callable tool. Passed to the LLM at request time."""

    name: str
    description: str
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema object for the tool's arguments.",
    )


class ToolCall(BaseModel):
    """A tool invocation emitted by the LLM. args_json is the raw string from the model;
    JSON-schema validation happens at the agent.tools dispatch layer."""

    name: str
    args_json: str


class Completion(BaseModel):
    """One LLM response. Either text (final answer) or tool_call (more work to do).

    Exactly one of `text` or `tool_call` is populated, indicated by `finish_reason`.
    """

    text: str | None = None
    tool_call: ToolCall | None = None
    finish_reason: Literal["stop", "length", "tool_call", "error"]
    model: str
    usage_prompt_tokens: int = 0
    usage_completion_tokens: int = 0
