"""Tests for Serena-powered coding agent factory."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from clean_interfaces.agents.serena_coder import create_serena_coder_agent
from clean_interfaces.utils.settings import AgentSettings, MCPSettings

if TYPE_CHECKING:
    from pathlib import Path


def test_serena_coder_agent_attaches_serena_toolkit(tmp_path: Path) -> None:
    """The Serena coding agent should configure OpenAI and attach MCP tools."""
    settings = AgentSettings.model_validate(
        {"OPENAI_API_KEY": "sk-test", "openai_model": "gpt", "agent_name": "Serena"},
    )
    mcp_settings = MCPSettings()

    fake_tool = object()

    with (
        patch(
            "clean_interfaces.agents.serena_coder.create_lsp_walker",
        ) as mock_walker_factory,
        patch("clean_interfaces.agents.serena_coder.OpenAIResponses") as mock_openai_responses,
    ):
        walker_instance = MagicMock()
        walker_instance.create_toolkit.return_value = fake_tool
        mock_walker_factory.return_value = walker_instance

        model_instance = MagicMock()
        mock_openai_responses.return_value = model_instance

        agent = create_serena_coder_agent(
            settings=settings,
            mcp_settings=mcp_settings,
            instructions="Improve the codebase",
            project_path=tmp_path,
        )

    mock_walker_factory.assert_called_once_with(mcp_settings, project_path=tmp_path)
    walker_instance.create_toolkit.assert_called_once()
    mock_openai_responses.assert_called_once_with(id="gpt", api_key="sk-test")

    assert agent.model is model_instance
    assert agent.name == "Serena"
