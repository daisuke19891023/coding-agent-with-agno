"""Tests for repository QA agent factory."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from clean_interfaces.agents.repo_qa import create_repository_qa_agent
from clean_interfaces.utils.settings import AgentSettings, MCPSettings

if TYPE_CHECKING:
    from pathlib import Path


def test_repository_qa_agent_configures_model_and_tools(tmp_path: Path) -> None:
    """Repository QA agent should use OpenAI settings and attach MCP tools."""
    settings = AgentSettings.model_validate(
        {"OPENAI_API_KEY": "sk-test", "openai_model": "gpt", "agent_name": "Repo QA"},
    )
    mcp_settings = MCPSettings()

    fake_tool = object()

    with (
        patch(
            "clean_interfaces.agents.repo_qa.create_lsp_walker",
        ) as mock_walker_factory,
        patch("clean_interfaces.agents.repo_qa.OpenAIChat") as mock_openai_chat,
    ):
        walker_instance = MagicMock()
        walker_instance.create_toolkit.return_value = fake_tool
        mock_walker_factory.return_value = walker_instance

        model_instance = MagicMock()
        mock_openai_chat.return_value = model_instance

        agent = create_repository_qa_agent(
            settings=settings,
            mcp_settings=mcp_settings,
            instructions="Answer questions",
            project_path=tmp_path,
        )

    mock_walker_factory.assert_called_once_with(mcp_settings, project_path=tmp_path)
    walker_instance.create_toolkit.assert_called_once()
    mock_openai_chat.assert_called_once_with(id="gpt", api_key="sk-test")

    assert agent.model is model_instance
    assert agent.name == "Repo QA"
