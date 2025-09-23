"""Scenario-based end-to-end tests for agno agents and workflows."""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterable, Sequence
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

import pytest
from agno.agent import RunOutput  # noqa: TC002
from clean_interfaces.agents.repo_qa import create_repository_qa_agent
from clean_interfaces.agents.serena_coder import create_serena_coder_agent
from clean_interfaces.utils.settings import AgentSettings, MCPSettings
from clean_interfaces.workflow.tdd import TDDWorkflowConfig, create_tdd_workflow

if TYPE_CHECKING:  # pragma: no cover - imported for type checkers only
    from agno.agent import Message
    from agno.run.workflow import WorkflowRunOutput
    from agno.workflow.workflow import Workflow
    from scenario import AgentInput, AgentReturnTypes
else:  # pragma: no cover - runtime fallbacks for typing names
    AgentInput = AgentReturnTypes = Any


scenario = cast(
    "Any",
    pytest.importorskip(  # type: ignore[attr-defined]
        "scenario",
        reason="Scenario tests require the scenario package and external model access.",
    ),
)

pytest = cast("Any", pytest)

pytestmark: Any = pytest.mark.scenario


def _get_env(name: str) -> str | None:
    """Return the trimmed environment variable if present."""
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


@lru_cache(maxsize=1)
def _configure_scenario() -> None:
    """Configure the Scenario test harness with deterministic defaults."""
    scenario.configure(
        default_model=_get_env("SCENARIO_DEFAULT_MODEL") or "openai/gpt-4.1-mini",
        cache_key=_get_env("SCENARIO_CACHE_KEY") or "clean-interfaces-scenario-suite",
        max_turns=8,
    )


def _require_credentials() -> None:
    """Skip Scenario tests when the required credentials are missing."""
    provider = _get_env("AGNO_PROVIDER") or "openai"
    if provider == "openai" and not _get_env("OPENAI_API_KEY"):
        pytest.skip(  # type: ignore[attr-defined]
            "Scenario tests require OPENAI_API_KEY for the OpenAI provider.",
        )


def _format_agent_messages(messages: Sequence[Message] | None) -> list[dict[str, Any]]:
    """Convert agno messages into OpenAI-compatible dictionaries."""
    if not messages:
        return []
    return [message.to_dict() for message in messages]


class _AgentTextRunner:
    """Helper that exposes agno agents as callable text runners for workflows."""

    def __init__(
        self,
        agent: Any,
        *,
        project_path: Path | None,
        session_prefix: str,
    ) -> None:
        self._agent = agent
        self._project_path = project_path
        self._session_id = f"{session_prefix}-{uuid4()}"

    def __call__(self, prompt: str, project_path: Path | None = None) -> str:
        effective_path = project_path or self._project_path
        effective_prompt = prompt
        if effective_path:
            effective_prompt = f"{prompt}\n\nRepository root: {effective_path}"
        result = cast(
            "RunOutput",
            self._agent.run(  # type: ignore[reportUnknownMemberType]
                effective_prompt,
                session_id=self._session_id,
            ),
        )
        if result.content:
            return cast(
                "str",
                result.get_content_as_string(),  # type: ignore[reportUnknownMemberType]
            )
        responses = [msg["content"] for msg in _format_agent_messages(result.messages)]
        return "\n\n".join(str(part) for part in responses if part)


class SerenaCodingAdapter(scenario.AgentAdapter):  # type: ignore[misc]
    """Adapter that exposes the Serena coding agent to the Scenario framework."""

    def __init__(
        self,
        *,
        project_path: Path,
        agent_settings: AgentSettings,
        mcp_settings: MCPSettings,
        instructions: str,
    ) -> None:
        """Initialise the adapter with the project context and settings."""
        self._project_path = project_path
        self._agent = create_serena_coder_agent(
            settings=agent_settings,
            mcp_settings=mcp_settings,
            instructions=instructions,
            project_path=project_path,
        )

    async def call(self, agent_input: AgentInput) -> AgentReturnTypes:
        """Bridge Scenario input to the underlying Serena coding agent."""
        _configure_scenario()
        user_message = agent_input.last_new_user_message_str()
        prompt = f"{user_message}\n\nRepository root: {self._project_path}"
        result = cast(
            "RunOutput",
            self._agent.run(  # type: ignore[reportUnknownMemberType]
                prompt,
                session_id=agent_input.thread_id,
            ),
        )
        messages = _format_agent_messages(result.messages)
        if result.content:
            messages.append(
                {
                    "role": "assistant",
                    "content": cast(
                        "str",
                        result.get_content_as_string(),  # type: ignore[reportUnknownMemberType]
                    ),
                },
            )
        return messages or [
            {
                "role": "assistant",
                "content": "I have no updates.",
            },
        ]


class RepositoryQAAdapter(scenario.AgentAdapter):  # type: ignore[misc]
    """Adapter that routes Scenario prompts to the repository QA agent."""

    def __init__(
        self,
        *,
        project_path: Path,
        agent_settings: AgentSettings,
        mcp_settings: MCPSettings,
        instructions: str,
    ) -> None:
        """Initialise the adapter with repository configuration."""
        self._project_path = project_path
        self._agent = create_repository_qa_agent(
            settings=agent_settings,
            mcp_settings=mcp_settings,
            instructions=instructions,
            project_path=project_path,
        )

    async def call(self, agent_input: AgentInput) -> AgentReturnTypes:
        """Handle a Scenario request by consulting the repository QA agent."""
        _configure_scenario()
        user_message = agent_input.last_new_user_message_str()
        prompt = f"{user_message}\n\nRepository root: {self._project_path}"
        result = cast(
            "RunOutput",
            self._agent.run(  # type: ignore[reportUnknownMemberType]
                prompt,
                session_id=agent_input.thread_id,
            ),
        )
        messages = _format_agent_messages(result.messages)
        if result.content:
            messages.append(
                {
                    "role": "assistant",
                    "content": cast(
                        "str",
                        result.get_content_as_string(),  # type: ignore[reportUnknownMemberType]
                    ),
                },
            )
        return messages or [
            {
                "role": "assistant",
                "content": "Repository exploration completed.",
            },
        ]


class TDDWorkflowAdapter(scenario.AgentAdapter):  # type: ignore[misc]
    """Adapter that executes the TDD workflow and returns a textual summary."""

    def __init__(self, workflow: Workflow) -> None:
        """Store the workflow instance that will process Scenario prompts."""
        self._workflow = workflow

    async def call(self, agent_input: AgentInput) -> AgentReturnTypes:
        """Execute the workflow and provide a summary for Scenario consumers."""
        request = agent_input.last_new_user_message_str()
        run: WorkflowRunOutput = self._workflow.run(
            request,
            session_id=agent_input.thread_id,
        )
        summary_lines = [
            "TDD workflow execution summary:",
            f"Status: {getattr(run.status, 'value', run.status)}",
        ]
        for entry in run.step_results or []:
            steps: Iterable[Any]
            is_iterable = isinstance(entry, Iterable) and not isinstance(
                entry,
                (dict, str, bytes),
            )
            steps = cast("Iterable[Any]", entry) if is_iterable else (entry,)
            for step in steps:
                name = getattr(step, "step_name", None) or "Unnamed step"
                content = getattr(step, "content", "")
                summary_lines.append(f"- {name}: {content}")
        if run.content and run.content not in summary_lines:
            summary_lines.append(str(run.content))
        return [{"role": "assistant", "content": "\n".join(summary_lines)}]


@pytest.fixture
def scenario_project(tmp_path: Path) -> Path:
    """Copy the virtual repository used by Scenario tests into a temp directory."""
    template = Path(__file__).parent.parent / "fixtures" / "scenario_repo"
    destination = tmp_path / "scenario-repo"
    shutil.copytree(template, destination)
    return destination


def _build_agent_settings(name: str) -> AgentSettings:
    """Return agent settings with an explicit display name."""
    return AgentSettings(agent_name=name)


def _build_mcp_settings() -> MCPSettings:
    """Return MCP settings with optional overrides from the environment."""
    overrides: dict[str, Any] = {}
    command_override = _get_env("SCENARIO_SERENA_COMMAND")
    if command_override:
        overrides["lsp_walker_command"] = command_override
    transport_override = _get_env("SCENARIO_SERENA_TRANSPORT")
    if transport_override:
        overrides["lsp_walker_transport"] = transport_override
    url_override = _get_env("SCENARIO_SERENA_URL")
    if url_override:
        overrides["lsp_walker_url"] = url_override
    if overrides:
        return MCPSettings(**overrides)
    return MCPSettings()


@pytest.mark.asyncio
async def test_serena_coder_resolves_todo(scenario_project: Path) -> None:
    """Ensure the Serena coding agent can fix the known defect via Scenario."""
    _require_credentials()
    _configure_scenario()
    agent = SerenaCodingAdapter(
        project_path=scenario_project,
        agent_settings=_build_agent_settings("Scenario Serena Coder"),
        mcp_settings=_build_mcp_settings(),
        instructions=(
            "You are an autonomous engineer working in "
            f"{scenario_project}. "
            "Use the Serena MCP tools to inspect files, apply edits, and run pytest "
            "before providing a final report."
        ),
    )
    result = await scenario.run(
        name="Implement multiply helper",
        description=(
            "The assistant must implement the multiply helper in "
            "src/sample_package/calculator.py so that the pytest suite in "
            "tests/test_calculator.py passes."
        ),
        agents=[
            agent,
            scenario.UserSimulatorAgent(
                system_prompt=(
                    "You are a product owner requesting the multiply helper be fixed. "
                    "Ask the assistant to describe its plan, perform the change, "
                    "run pytest -q, and summarise the results."
                ),
            ),
            scenario.JudgeAgent(
                criteria=[
                    "Assistant fixes multiply in src/sample_package/calculator.py.",
                    "Assistant runs pytest and confirms the suite passes.",
                ],
            ),
        ],
    )
    assert result.success


@pytest.mark.asyncio
async def test_repo_qa_summarises_architecture(scenario_project: Path) -> None:
    """Validate that the repository QA agent can answer structural questions."""
    _require_credentials()
    _configure_scenario()
    agent = RepositoryQAAdapter(
        project_path=scenario_project,
        agent_settings=_build_agent_settings("Scenario Repo QA"),
        mcp_settings=_build_mcp_settings(),
        instructions=(
            "You answer architecture questions about the repository at "
            f"{scenario_project}. "
            "Cite file paths and summarise the purpose of key modules and tests."
        ),
    )
    result = await scenario.run(
        name="Repository architecture overview",
        description=(
            "The user needs an explanation of where arithmetic helpers live, how they "
            "are tested, and which documentation highlights the known multiply defect."
        ),
        agents=[
            agent,
            scenario.UserSimulatorAgent(
                system_prompt=(
                    "Ask targeted questions about project structure."
                    " Reference file paths from docs/ and src/."
                ),
            ),
            scenario.JudgeAgent(
                criteria=[
                    "Assistant cites docs/architecture.md in the summary.",
                    "Assistant highlights calculator module and pytest suite.",
                ],
            ),
        ],
        max_turns=6,
    )
    assert result.success


@pytest.mark.asyncio
async def test_tdd_workflow_full_cycle(scenario_project: Path) -> None:
    """Check that the TDD workflow integrates with Scenario conversations."""
    _require_credentials()
    _configure_scenario()

    exploration_agent = create_repository_qa_agent(
        settings=_build_agent_settings("Scenario Explorer"),
        mcp_settings=_build_mcp_settings(),
        instructions=(
            "Inspect the repository at "
            f"{scenario_project}, "
            "focusing on the multiply defect and related tests. Summarise findings in "
            "a structured way for downstream agents."
        ),
        project_path=scenario_project,
    )
    coding_agent = create_serena_coder_agent(
        settings=_build_agent_settings("Scenario Implementer"),
        mcp_settings=_build_mcp_settings(),
        instructions=(
            "Implement missing functionality in "
            f"{scenario_project}. "
            "Use Serena tools to edit files and run pytest -q."
        ),
        project_path=scenario_project,
    )

    workflow_config = TDDWorkflowConfig(
        exploration_prompt=(
            "Review the repository and confirm the multiply helper defect."
        ),
        test_prompt=(
            "Write a precise pytest that captures the expected behaviour for multiply."
        ),
        implementation_prompt=(
            "Implement the feature so all tests pass, then summarise the diff."
        ),
        test_command="pytest -q",
        project_path=scenario_project,
    )

    workflow = create_tdd_workflow(
        config=workflow_config,
        exploration_runner=_AgentTextRunner(
            exploration_agent,
            project_path=scenario_project,
            session_prefix="exploration",
        ),
        test_writer_runner=_AgentTextRunner(
            coding_agent,
            project_path=scenario_project,
            session_prefix="test-writer",
        ),
        implementation_runner=_AgentTextRunner(
            coding_agent,
            project_path=scenario_project,
            session_prefix="implementation",
        ),
    )

    agent = TDDWorkflowAdapter(workflow)

    result = await scenario.run(
        name="TDD workflow for multiply helper",
        description=(
            "Coordinate exploration, test writing, and implementation so that the "
            "multiply helper is fixed and tests pass."
        ),
        agents=[
            agent,
            scenario.UserSimulatorAgent(
                system_prompt=(
                    "Request the assistant to run the full TDD workflow and share "
                    "status updates after each step."
                ),
            ),
            scenario.JudgeAgent(
                criteria=[
                    "Workflow summary mentions both failing and passing pytest runs.",
                    "Workflow summary references exploration and implementation steps.",
                ],
            ),
        ],
        max_turns=6,
    )
    assert result.success
