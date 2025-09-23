"""CLI interface implementation using Typer."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from clean_interfaces.core import (
    AgentConfigurationError,
    AgentExecutionError,
    run_coding_agent,
    run_repository_qa_agent,
)
from clean_interfaces.models.io import WelcomeMessage

from .base import BaseInterface

# Configure console for better test compatibility
# Force terminal mode even in non-TTY environments
console = Console(force_terminal=True, force_interactive=False)


class CLIInterface(BaseInterface):
    """Command Line Interface implementation."""

    def __init__(self) -> None:
        """Initialize the CLI interface."""
        super().__init__()  # Call BaseComponent's __init__ for logger initialization
        self.app = typer.Typer(
            name="clean-interfaces",
            help="Clean Interfaces CLI",
            add_completion=False,
        )
        self._setup_commands()

    @property
    def name(self) -> str:
        """Get the interface name.

        Returns:
            str: The interface name

        """
        return "CLI"

    def _setup_commands(self) -> None:
        """Set up CLI commands."""
        # Set the default command to welcome
        self.app.command(name="welcome")(self.welcome)
        self.app.command(name="agent")(self.agent)
        self.app.command(name="repo-agent")(self.repo_agent)

        # Add a callback that shows welcome when no command is specified
        self.app.callback(invoke_without_command=True)(self._main_callback)

    def _main_callback(self, ctx: typer.Context) -> None:  # pragma: no cover
        """Run when no subcommand is provided."""
        if ctx.invoked_subcommand is None:
            self.welcome()
            # Ensure we exit cleanly after showing welcome
            raise typer.Exit(0)

    def welcome(self) -> None:
        """Display welcome message."""
        msg = WelcomeMessage()
        # Use console for output (configured for E2E test compatibility)
        console.print(msg.message)
        console.print(msg.hint)
        # Force flush to ensure output is visible
        console.file.flush()

    def agent(
        self,
        prompt: Annotated[
            str,
            typer.Argument(help="Prompt to send to the coding agent."),
        ],
    ) -> None:
        """Generate a response using an agno-powered coding agent."""
        self.logger.info(
            "Running agno agent",
            prompt=prompt,
        )

        try:
            response_text = run_coding_agent(prompt)
        except AgentConfigurationError as exc:
            console.print(
                "[red]OpenAI API key not configured. "
                "Set the OPENAI_API_KEY environment variable.[/red]",
            )
            self.logger.error("Agent configuration error", error=str(exc))
            raise typer.Exit(1) from exc
        except AgentExecutionError as exc:  # pragma: no cover - agno handles specifics
            self.logger.error("Agent execution failed", error=str(exc))
            console.print(f"[red]Failed to generate response: {exc}[/red]")
            raise typer.Exit(1) from exc

        console.print(response_text)
        console.file.flush()

    def repo_agent(
        self,
        prompt: Annotated[
            str,
            typer.Argument(help="Prompt to send to the repository QA agent."),
        ],
        project_path: Annotated[
            Path | None,
            typer.Option(
                "--path",
                "-p",
                exists=True,
                file_okay=False,
                dir_okay=True,
                help="Optional project directory to explore during QA.",
            ),
        ] = None,
    ) -> None:
        """Generate a response using the repository QA agent."""
        self.logger.info(
            "Running repository QA agent",
            prompt=prompt,
            project_path=str(project_path) if project_path else None,
        )

        try:
            response_text = run_repository_qa_agent(prompt, project_path=project_path)
        except AgentConfigurationError as exc:
            console.print(
                "[red]OpenAI API key not configured. "
                "Set the OPENAI_API_KEY environment variable.[/red]",
            )
            self.logger.error("Agent configuration error", error=str(exc))
            raise typer.Exit(1) from exc
        except AgentExecutionError as exc:  # pragma: no cover - agno handles specifics
            self.logger.error("Agent execution failed", error=str(exc))
            console.print(f"[red]Failed to generate response: {exc}[/red]")
            raise typer.Exit(1) from exc

        console.print(response_text)
        console.file.flush()

    def run(self) -> None:
        """Run the CLI interface."""
        # Let Typer handle the command parsing
        self.app()
