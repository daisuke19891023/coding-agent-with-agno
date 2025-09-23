"""Tests for CLI interface implementation."""

from unittest.mock import MagicMock, patch

import pytest
import typer

from clean_interfaces.interfaces.base import BaseInterface
from clean_interfaces.interfaces.cli import CLIInterface
from clean_interfaces.core import AgentConfigurationError


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

        with patch("clean_interfaces.interfaces.cli.console") as mock_console, patch(
            "clean_interfaces.interfaces.cli.run_coding_agent",
        ) as mock_run:
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
