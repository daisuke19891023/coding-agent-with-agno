"""Factories for Serena-powered coding agents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from clean_interfaces.mcp import create_lsp_walker

if TYPE_CHECKING:
    from pathlib import Path

    from clean_interfaces.utils.settings import AgentSettings, MCPSettings


def create_serena_coder_agent(
    *,
    settings: AgentSettings,
    mcp_settings: MCPSettings,
    instructions: str,
    project_path: Path | None = None,
) -> Agent:
    """Create an agent configured for Serena-assisted coding workflows."""
    model = OpenAIChat(id=settings.openai_model, api_key=settings.openai_api_key)

    walker = create_lsp_walker(mcp_settings, project_path=project_path)
    toolkit = walker.create_toolkit()

    return Agent(
        model=model,
        name=settings.agent_name,
        instructions=instructions,
        tools=[toolkit],
    )
