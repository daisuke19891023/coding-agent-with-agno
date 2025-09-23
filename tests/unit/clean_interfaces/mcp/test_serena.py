"""Tests for the Serena MCP walker."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import clean_interfaces.mcp.serena as serena_module
from clean_interfaces.mcp.serena import SerenaLSPWalker
from clean_interfaces.utils.settings import MCPSettings


class DummyMCPTools:
    """Simple stand-in for MCPTools to capture arguments."""

    def __init__(self, **kwargs: Any) -> None:
        """Record initialization keyword arguments for later assertions."""
        self.kwargs = kwargs


def test_serena_walker_appends_context_and_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The Serena walker should augment the command with context and project path."""
    settings = MCPSettings(
        lsp_walker_command="uvx serena start-mcp-server",
        lsp_walker_context="ide-assistant",
        lsp_walker_timeout_seconds=15,
    )

    captured: dict[str, Any] = {}

    def fake_mcp_tools(**kwargs: Any) -> DummyMCPTools:
        captured.update(kwargs)
        return DummyMCPTools(**kwargs)

    monkeypatch.setattr(serena_module, "MCPTools", fake_mcp_tools)

    walker = SerenaLSPWalker(settings=settings, project_path=tmp_path)
    toolkit = walker.create_toolkit()

    assert isinstance(toolkit, DummyMCPTools)
    assert captured["transport"] == "stdio"
    assert captured["timeout_seconds"] == 15

    command = captured["command"]
    assert isinstance(command, str)
    assert "--context ide-assistant" in command
    assert f"--project {tmp_path}" in command


def test_serena_requires_command_for_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    """When using stdio the walker must have a command configured."""
    settings = MCPSettings(
        lsp_walker_command="",  # Removed command
        lsp_walker_context=None,
        lsp_walker_transport="stdio",
    )

    monkeypatch.setattr(serena_module, "MCPTools", DummyMCPTools)

    walker = SerenaLSPWalker(settings=settings)

    with pytest.raises(ValueError, match="requires a command"):
        walker.create_toolkit()


def test_serena_defaults_project_to_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    """When no project path is provided the current directory is used."""
    settings = MCPSettings(
        lsp_walker_command="uvx serena start-mcp-server",
        lsp_walker_context="ide-assistant",
    )

    captured: dict[str, Any] = {}

    def fake_mcp_tools(**kwargs: Any) -> DummyMCPTools:
        captured.update(kwargs)
        return DummyMCPTools(**kwargs)

    monkeypatch.setattr(serena_module, "MCPTools", fake_mcp_tools)

    walker = SerenaLSPWalker(settings=settings)
    walker.create_toolkit()

    command = captured["command"]
    assert isinstance(command, str)
    cwd = str(Path.cwd().resolve())
    assert f"--project {cwd}" in command


def test_serena_does_not_duplicate_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    """Existing flag definitions in the command should not be duplicated."""
    settings = MCPSettings(
        lsp_walker_command=(
            "uvx serena start-mcp-server --context custom --project /tmp/repo"
        ),
        lsp_walker_context="ignored",
    )

    captured: dict[str, Any] = {}

    def fake_mcp_tools(**kwargs: Any) -> DummyMCPTools:
        captured.update(kwargs)
        return DummyMCPTools(**kwargs)

    monkeypatch.setattr(serena_module, "MCPTools", fake_mcp_tools)

    walker = SerenaLSPWalker(settings=settings)
    walker.create_toolkit()

    command_parts = captured["command"].split()
    assert command_parts.count("--context") == 1
    assert command_parts.count("--project") == 1
