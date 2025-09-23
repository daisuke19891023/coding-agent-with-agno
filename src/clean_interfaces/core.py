"""Core orchestration logic for the Clean Interfaces application."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable, cast

from clean_interfaces.agents import create_coding_agent
from clean_interfaces.prompts import load_prompt
from clean_interfaces.utils.settings import get_agent_settings


class AgentConfigurationError(RuntimeError):
    """Raised when the agent cannot be configured correctly."""

    def __init__(self, message: str | None = None) -> None:
        """Initialise the configuration error with an optional message."""
        default_message = "OpenAI API key not configured."
        super().__init__(message or default_message)


class AgentExecutionError(RuntimeError):
    """Raised when the agent fails while generating a response."""


@runtime_checkable
class SupportsStringContent(Protocol):
    """Protocol representing agno responses that expose string content."""

    def get_content_as_string(self, **kwargs: Any) -> str:
        """Return the agent output as a plain string."""
        ...


class SupportsAgentRun(Protocol):
    """Protocol capturing the subset of the agno Agent interface we rely on."""

    def run(
        self,
        prompt: str,
        *,
        stream: bool | None = None,
    ) -> SupportsStringContent | str:
        """Execute the agent and return its response."""
        ...


def run_coding_agent(prompt: str) -> str:
    """Execute the agno coding agent and return its response text."""
    settings = get_agent_settings()
    if not settings.openai_api_key:
        raise AgentConfigurationError

    instructions = load_prompt("coding_agent")
    agent = cast(
        "SupportsAgentRun",
        create_coding_agent(settings=settings, instructions=instructions),
    )

    try:
        result = agent.run(prompt)
    except Exception as exc:  # pragma: no cover - agno handles specifics internally
        raise AgentExecutionError(str(exc)) from exc

    return _coerce_response_to_string(result)


def _coerce_response_to_string(result: SupportsStringContent | str | object) -> str:
    """Convert a variety of agno run outputs into plain text."""
    if isinstance(result, str):
        return result

    if isinstance(result, SupportsStringContent):
        return result.get_content_as_string()

    get_content: Any = getattr(result, "get_content_as_string", None)
    if callable(get_content):
        coerced = get_content()
        if isinstance(coerced, str):
            return coerced
        return str(coerced)

    return str(result)

