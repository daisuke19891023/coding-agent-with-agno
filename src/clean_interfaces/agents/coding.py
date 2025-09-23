"""Factories for agno-based coding agents."""

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from clean_interfaces.llm import create_model

from clean_interfaces.utils.settings import AgentSettings


def create_coding_agent(*, settings: AgentSettings, instructions: str) -> Agent:
    """Create a configured agno coding agent instance."""
    if getattr(settings, "provider", "openai") == "openai":
        # Keep direct OpenAIChat usage so existing tests that patch this symbol
        # continue to work
        model = OpenAIChat(id=settings.openai_model, api_key=settings.openai_api_key)
    else:
        model = create_model(settings)
    return Agent(model=model, name=settings.agent_name, instructions=instructions)

