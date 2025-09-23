"""Core orchestration logic for the Clean Interfaces application."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

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

    def get_content_as_string(self) -> str:
        """Return the agent output as a plain string."""


def run_coding_agent(prompt: str) -> str:
    """Execute the agno coding agent and return its response text."""
    settings = get_agent_settings()
    if not settings.openai_api_key:
        raise AgentConfigurationError

    instructions = load_prompt("coding_agent")
    agent = create_coding_agent(settings=settings, instructions=instructions)

    try:
        result = agent.run(prompt)
    except Exception as exc:  # pragma: no cover - agno handles specifics internally
        raise AgentExecutionError(str(exc)) from exc

    if isinstance(result, SupportsStringContent):
        return result.get_content_as_string()

    if hasattr(result, "get_content_as_string"):
        return result.get_content_as_string()

    return str(result)

