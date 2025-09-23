"""Unit tests for core agent orchestration."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from clean_interfaces.core import (
    AgentConfigurationError,
    AgentExecutionError,
    run_coding_agent,
    run_repository_qa_agent,
)


def test_run_coding_agent_requires_api_key() -> None:
    """The core workflow should validate configuration before running."""
    with patch("clean_interfaces.core.get_agent_settings") as mock_get_settings:
        settings = MagicMock()
        settings.openai_api_key = None
        mock_get_settings.return_value = settings

        with pytest.raises(AgentConfigurationError):
            run_coding_agent("hello")


def test_run_coding_agent_invokes_agent_successfully() -> None:
    """The core workflow should invoke the agent and return string content."""
    with (
        patch("clean_interfaces.core.get_agent_settings") as mock_get_settings,
        patch("clean_interfaces.core.load_prompt") as mock_load_prompt,
        patch("clean_interfaces.core.create_coding_agent") as mock_create_agent,
    ):
        settings = MagicMock()
        settings.openai_api_key = "sk-test"
        mock_get_settings.return_value = settings

        mock_load_prompt.return_value = "Prompt instructions"

        agent_instance = MagicMock()
        result = MagicMock()
        result.get_content_as_string.return_value = "Agent says hi"
        agent_instance.run.return_value = result
        mock_create_agent.return_value = agent_instance

        response = run_coding_agent("Write code")

        mock_load_prompt.assert_called_once_with("coding_agent")
        mock_create_agent.assert_called_once()
        agent_instance.run.assert_called_once_with("Write code")
        assert response == "Agent says hi"


def test_run_coding_agent_wraps_execution_errors() -> None:
    """Any agent execution failure should be wrapped in a domain error."""
    with (
        patch("clean_interfaces.core.get_agent_settings") as mock_get_settings,
        patch("clean_interfaces.core.load_prompt") as mock_load_prompt,
        patch("clean_interfaces.core.create_coding_agent") as mock_create_agent,
    ):
        settings = MagicMock()
        settings.openai_api_key = "sk-test"
        mock_get_settings.return_value = settings
        mock_load_prompt.return_value = "Prompt instructions"

        agent_instance = MagicMock()
        agent_instance.run.side_effect = RuntimeError("boom")
        mock_create_agent.return_value = agent_instance

        with pytest.raises(AgentExecutionError):
            run_coding_agent("Write code")


def test_run_repo_agent_requires_api_key() -> None:
    """The repository QA agent should validate configuration before running."""
    with patch("clean_interfaces.core.get_agent_settings") as mock_get_settings:
        settings = MagicMock()
        settings.openai_api_key = None
        mock_get_settings.return_value = settings

        with pytest.raises(AgentConfigurationError):
            run_repository_qa_agent("hello")


def test_run_repo_agent_invokes_agent_successfully(tmp_path: Path) -> None:
    """The repository QA agent should invoke the MCP-backed agent and return text."""
    with (
        patch("clean_interfaces.core.get_agent_settings") as mock_get_settings,
        patch("clean_interfaces.core.get_mcp_settings") as mock_get_mcp_settings,
        patch("clean_interfaces.core.load_prompt") as mock_load_prompt,
        patch("clean_interfaces.core.create_repository_qa_agent") as mock_create_agent,
    ):
        settings = MagicMock()
        settings.openai_api_key = "sk-test"
        mock_get_settings.return_value = settings
        mock_get_mcp_settings.return_value = MagicMock()
        mock_load_prompt.return_value = "Repo prompt"

        agent_instance = MagicMock()
        result = MagicMock()
        result.get_content_as_string.return_value = "Repo answer"
        agent_instance.run.return_value = result
        mock_create_agent.return_value = agent_instance

        response = run_repository_qa_agent("Where is config?", project_path=tmp_path)

        mock_load_prompt.assert_called_once_with("repository_qa_agent")
        mock_create_agent.assert_called_once()
        agent_instance.run.assert_called_once_with("Where is config?")
        assert response == "Repo answer"


def test_run_repo_agent_wraps_execution_errors(tmp_path: Path) -> None:
    """Execution failures should be wrapped in domain-specific errors."""
    with (
        patch("clean_interfaces.core.get_agent_settings") as mock_get_settings,
        patch("clean_interfaces.core.get_mcp_settings") as mock_get_mcp_settings,
        patch("clean_interfaces.core.load_prompt") as mock_load_prompt,
        patch("clean_interfaces.core.create_repository_qa_agent") as mock_create_agent,
    ):
        settings = MagicMock()
        settings.openai_api_key = "sk-test"
        mock_get_settings.return_value = settings
        mock_get_mcp_settings.return_value = MagicMock()
        mock_load_prompt.return_value = "Repo prompt"

        agent_instance = MagicMock()
        agent_instance.run.side_effect = RuntimeError("boom")
        mock_create_agent.return_value = agent_instance

        with pytest.raises(AgentExecutionError):
            run_repository_qa_agent("Where is config?", project_path=tmp_path)
