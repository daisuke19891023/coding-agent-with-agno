"""Core orchestration logic for the Clean Interfaces application."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable

from clean_interfaces.agents import (
    create_coding_agent,
    create_repository_qa_agent,
    create_serena_coder_agent,
)
from clean_interfaces.prompts import load_prompt
from clean_interfaces.utils.settings import get_agent_settings, get_mcp_settings
from clean_interfaces.workflow import create_linter_workflow, create_tdd_workflow
from clean_interfaces.workflow.linter import LinterWorkflowConfig
from clean_interfaces.workflow.tdd import TDDWorkflowConfig

if TYPE_CHECKING:
    from pathlib import Path

    from agno.run.workflow import WorkflowRunOutput


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


def run_repository_qa_agent(
    prompt: str,
    *,
    project_path: Path | None = None,
) -> str:
    """Execute the repository QA agent and return its response text."""
    settings = get_agent_settings()
    if not settings.openai_api_key:
        raise AgentConfigurationError

    instructions = load_prompt("repository_qa_agent")
    mcp_settings = get_mcp_settings()
    agent = cast(
        "SupportsAgentRun",
        create_repository_qa_agent(
            settings=settings,
            mcp_settings=mcp_settings,
            instructions=instructions,
            project_path=project_path,
        ),
    )

    try:
        result = agent.run(prompt)
    except Exception as exc:  # pragma: no cover - agno handles specifics internally
        raise AgentExecutionError(str(exc)) from exc

    return _coerce_response_to_string(result)


def run_serena_coder_agent(
    prompt: str,
    *,
    project_path: Path | None = None,
) -> str:
    """Execute the Serena-backed coding agent and return its response text."""
    settings = get_agent_settings()
    if not settings.openai_api_key:
        raise AgentConfigurationError

    instructions = load_prompt("serena_coder_agent")
    mcp_settings = get_mcp_settings()
    agent = cast(
        "SupportsAgentRun",
        create_serena_coder_agent(
            settings=settings,
            mcp_settings=mcp_settings,
            instructions=instructions,
            project_path=project_path,
        ),
    )

    try:
        result = agent.run(prompt)
    except Exception as exc:  # pragma: no cover - agno handles specifics internally
        raise AgentExecutionError(str(exc)) from exc

    return _coerce_response_to_string(result)


def run_tdd_workflow(
    *,
    exploration_prompt: str,
    test_prompt: str,
    implementation_prompt: str,
    test_command: str,
    project_path: Path | None = None,
) -> WorkflowRunOutput:
    """Execute the end-to-end TDD workflow."""
    settings = get_agent_settings()
    if not settings.openai_api_key:
        raise AgentConfigurationError

    workflow = create_tdd_workflow(
        config=TDDWorkflowConfig(
            exploration_prompt=exploration_prompt,
            test_prompt=test_prompt,
            implementation_prompt=implementation_prompt,
            test_command=test_command,
            project_path=project_path,
        ),
        exploration_runner=lambda prompt, path: run_serena_coder_agent(
            prompt,
            project_path=path,
        ),
        test_writer_runner=run_coding_agent,
        implementation_runner=run_coding_agent,
    )

    return workflow.run()


def run_linter_workflow(
    *,
    linter_command: str,
    targets: list[str],
    project_path: "Path | None" = None,
    fix_instructions: str | None = None,
) -> "WorkflowRunOutput":
    """Execute the linter workflow and return its results.

    Runs the specified linter against provided targets, then asks the coding
    agent to propose fixes for any issues discovered.
    """
    settings = get_agent_settings()
    if not settings.openai_api_key:
        raise AgentConfigurationError

    instructions = load_prompt("coding_agent")
    agent = cast(
        "SupportsAgentRun",
        create_coding_agent(settings=settings, instructions=instructions),
    )

    workflow = create_linter_workflow(
        config=LinterWorkflowConfig(
            linter_command=linter_command,
            targets=targets,
            project_path=project_path,
            fix_instructions=fix_instructions,
        ),
        fix_runner=lambda prompt: _coerce_response_to_string(agent.run(prompt)),
    )

    return workflow.run()


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
