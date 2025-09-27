"""Tests for CLI interface implementation."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import typer

from clean_interfaces.core import AgentConfigurationError
from clean_interfaces.config.mcp import McpServerEntry, save_mcp_server
from clean_interfaces.interfaces.base import BaseInterface
from clean_interfaces.interfaces.cli import CLIInterface

import tomllib


class TestCLIInterface:
    """Test CLI interface functionality."""

    def test_cli_interface_inherits_base(self) -> None:
        """Test that CLIInterface inherits from BaseInterface."""
        assert issubclass(CLIInterface, BaseInterface)

    def test_cli_interface_has_name(self) -> None:
        """Test that CLIInterface has correct name."""
        cli = CLIInterface()
        assert cli.name == "CLI"

    def test_cli_interface_has_typer_app(self) -> None:
        """Test that CLIInterface has Typer app."""
        cli = CLIInterface()
        assert hasattr(cli, "app")
        assert isinstance(cli.app, typer.Typer)

    def test_cli_welcome_command(self) -> None:
        """Test CLI welcome command functionality."""
        cli = CLIInterface()

        # Mock the console output
        with patch("clean_interfaces.interfaces.cli.console") as mock_console:
            cli.welcome()

            # Check that welcome message was printed (should be called twice)
            assert mock_console.print.call_count == 2
            # First call is the welcome message
            first_call = mock_console.print.call_args_list[0][0]
            assert "Welcome to Clean Interfaces!" in str(first_call)
            # Second call is the hint
            second_call = mock_console.print.call_args_list[1][0]
            assert "Type --help for more information" in str(second_call)

    def test_cli_run_method(self) -> None:
        """Test CLI run method executes typer app."""
        cli = CLIInterface()

        # Mock the typer app
        cli.app = MagicMock()

        cli.run()

        cli.app.assert_called_once()

    def test_cli_agent_requires_api_key(self) -> None:
        """The agent command should exit when the API key is missing."""
        cli = CLIInterface()

        with (
            patch("clean_interfaces.interfaces.cli.console") as mock_console,
            patch(
                "clean_interfaces.interfaces.cli.run_coding_agent",
            ) as mock_run,
        ):
            mock_run.side_effect = AgentConfigurationError("missing key")

            with pytest.raises(typer.Exit):
                cli.agent("hello")

            mock_console.print.assert_called_once()

    def test_cli_agent_generates_response(self) -> None:
        """The agent command should call agno and print the response."""
        cli = CLIInterface()

        with (
            patch("clean_interfaces.interfaces.cli.console") as mock_console,
            patch("clean_interfaces.interfaces.cli.run_coding_agent") as mock_run,
        ):
            mock_run.return_value = "Agent response"

            mock_console.file = MagicMock()

            cli.agent("Write code")

            mock_run.assert_called_once_with("Write code")
            mock_console.print.assert_any_call("Agent response")
            mock_console.file.flush.assert_called_once()

    def test_cli_repo_agent_requires_api_key(self) -> None:
        """The repo-agent command should exit when the API key is missing."""
        cli = CLIInterface()

        with (
            patch("clean_interfaces.interfaces.cli.console") as mock_console,
            patch(
                "clean_interfaces.interfaces.cli.run_repository_qa_agent",
            ) as mock_run,
        ):
            mock_run.side_effect = AgentConfigurationError("missing key")

            with pytest.raises(typer.Exit):
                cli.repo_agent("hello")

            mock_console.print.assert_called_once()

    def test_cli_repo_agent_generates_response(self, tmp_path: Path) -> None:
        """The repo-agent command should call the QA agent and print the response."""
        cli = CLIInterface()

        with (
            patch("clean_interfaces.interfaces.cli.console") as mock_console,
            patch(
                "clean_interfaces.interfaces.cli.run_repository_qa_agent",
            ) as mock_run,
        ):
            mock_run.return_value = "QA response"

            mock_console.file = MagicMock()

            cli.repo_agent("Where is the config?", project_path=tmp_path)

            mock_run.assert_called_once_with(
                "Where is the config?",
                project_path=tmp_path,
            )
            mock_console.print.assert_any_call("QA response")
            mock_console.file.flush.assert_called_once()

    def test_cli_serena_agent_requires_api_key(self) -> None:
        """The serena-agent command should exit when the API key is missing."""
        cli = CLIInterface()

        with (
            patch("clean_interfaces.interfaces.cli.console") as mock_console,
            patch(
                "clean_interfaces.interfaces.cli.run_serena_coder_agent",
            ) as mock_run,
        ):
            mock_run.side_effect = AgentConfigurationError("missing key")

            with pytest.raises(typer.Exit):
                cli.serena_agent("hello")

            mock_console.print.assert_called_once()

    def test_cli_serena_agent_generates_response(self, tmp_path: Path) -> None:
        """The serena-agent command should print the coding agent response."""
        cli = CLIInterface()

        with (
            patch("clean_interfaces.interfaces.cli.console") as mock_console,
            patch(
                "clean_interfaces.interfaces.cli.run_serena_coder_agent",
            ) as mock_run,
        ):
            mock_run.return_value = "Serena response"

            mock_console.file = MagicMock()

            cli.serena_agent("Implement feature", project_path=tmp_path)

            mock_run.assert_called_once_with(
                "Implement feature",
                project_path=tmp_path,
            )
            mock_console.print.assert_any_call("Serena response")
            mock_console.file.flush.assert_called_once()

    def test_cli_mcp_add_creates_entry(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The mcp add command should persist configuration to TOML."""
        config_root = tmp_path / "config"
        monkeypatch.setenv("CLEAN_INTERFACES_CONFIG_HOME", str(config_root))

        cli = CLIInterface()

        with patch("clean_interfaces.interfaces.cli.console") as mock_console:
            mock_console.file = MagicMock()

            cli.mcp_add(
                "docs",
                ["docs-server", "--port", "4000"],
                env=["API_KEY=value"],
            )

        config_path = config_root / "clean-interfaces" / "config.toml"
        with config_path.open("rb") as fh:
            data: dict[str, Any] = tomllib.load(fh)

        assert data["mcp_servers"]["docs"]["command"] == "docs-server"
        assert data["mcp_servers"]["docs"]["args"] == ["--port", "4000"]
        assert data["mcp_servers"]["docs"]["env"] == {"API_KEY": "value"}

    def test_cli_mcp_list_json_outputs_entries(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The mcp list command should emit JSON when requested."""
        config_root = tmp_path / "config"
        monkeypatch.setenv("CLEAN_INTERFACES_CONFIG_HOME", str(config_root))

        save_mcp_server("docs", McpServerEntry(command="docs-server"))

        cli = CLIInterface()

        with patch("clean_interfaces.interfaces.cli.console") as mock_console:
            mock_console.file = MagicMock()
            mock_console.print_json = MagicMock()

            cli.mcp_list(json_output=True)

            mock_console.print_json.assert_called_once()
            payload = mock_console.print_json.call_args.kwargs["data"]
            assert payload == [
                {
                    "name": "docs",
                    "command": "docs-server",
                    "args": [],
                    "env": None,
                    "startup_timeout_sec": None,
                    "tool_timeout_sec": None,
                },
            ]

    def test_cli_mcp_remove_missing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Removing a non-existent MCP server should warn the user."""
        config_root = tmp_path / "config"
        monkeypatch.setenv("CLEAN_INTERFACES_CONFIG_HOME", str(config_root))

        cli = CLIInterface()

        with patch("clean_interfaces.interfaces.cli.console") as mock_console:
            mock_console.file = MagicMock()

            cli.mcp_remove("missing")

            mock_console.print.assert_called_with(
                "[yellow]No MCP server named 'missing' found.[/yellow]",
            )
            mock_console.file.flush.assert_called_once()
