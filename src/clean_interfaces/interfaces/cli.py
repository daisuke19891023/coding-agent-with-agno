"""CLI interface implementation using Typer."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from clean_interfaces.core import (
    AgentConfigurationError,
    AgentExecutionError,
    run_coding_agent,
    run_linter_workflow,
    run_repository_qa_agent,
    run_serena_coder_agent,
    run_tdd_workflow,
)
from clean_interfaces.models.io import WelcomeMessage
from clean_interfaces.workflow import TestCommandExecutionError

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
        self.app.command(name="serena-agent")(self.serena_agent)
        self.app.command(name="tdd")(self.tdd)
        self.app.command(name="lint")(self.lint)

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

    def serena_agent(
        self,
        prompt: Annotated[
            str,
            typer.Argument(help="Prompt to send to the Serena coding agent."),
        ],
        project_path: Annotated[
            Path | None,
            typer.Option(
                "--path",
                "-p",
                exists=True,
                file_okay=False,
                dir_okay=True,
                help="Optional project directory to modify using Serena.",
            ),
        ] = None,
    ) -> None:
        """Generate a response using the Serena-powered coding agent."""
        self.logger.info(
            "Running Serena coding agent",
            prompt=prompt,
            project_path=str(project_path) if project_path else None,
        )

        try:
            response_text = run_serena_coder_agent(prompt, project_path=project_path)
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

    def tdd(
        self,
        exploration_prompt: Annotated[
            str,
            typer.Argument(help="Prompt to drive the initial code exploration."),
        ],
        test_prompt: Annotated[
            str,
            typer.Argument(help="Prompt for the coding agent to design tests."),
        ],
        implementation_prompt: Annotated[
            str,
            typer.Argument(help="Prompt for implementing production code."),
        ],
        test_command: Annotated[
            str,
            typer.Option(
                "--test-command",
                "-t",
                help=(
                    "Test command to execute during the workflow. Use aliases like"
                    " 'pytest' or provide a full shell command."
                ),
            ),
        ] = "pytest",
        project_path: Annotated[
            Path | None,
            typer.Option(
                "--path",
                "-p",
                exists=True,
                file_okay=False,
                dir_okay=True,
                help="Optional project directory for the workflow to operate in.",
            ),
        ] = None,
    ) -> None:
        """Run the agentic TDD workflow."""
        self.logger.info(
            "Running TDD workflow",
            exploration_prompt=exploration_prompt,
            test_prompt=test_prompt,
            implementation_prompt=implementation_prompt,
            test_command=test_command,
            project_path=str(project_path) if project_path else None,
        )

        try:
            workflow_run = run_tdd_workflow(
                exploration_prompt=exploration_prompt,
                test_prompt=test_prompt,
                implementation_prompt=implementation_prompt,
                test_command=test_command,
                project_path=project_path,
            )
        except AgentConfigurationError as exc:
            console.print(
                "[red]OpenAI API key not configured. "
                "Set the OPENAI_API_KEY environment variable.[/red]",
            )
            self.logger.error("Agent configuration error", error=str(exc))
            raise typer.Exit(1) from exc
        except AgentExecutionError as exc:
            self.logger.error("Agent execution failed", error=str(exc))
            console.print(f"[red]Failed to run workflow: {exc}[/red]")
            raise typer.Exit(1) from exc
        except TestCommandExecutionError as exc:
            self.logger.error("Test command execution failed", error=str(exc))
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1) from exc

        step_results = list(workflow_run.step_results or [])
        for step in step_results:
            step_name = getattr(step, "step_name", None) or "Workflow step"
            console.rule(step_name)
            content = getattr(step, "content", None)
            if isinstance(content, str):
                console.print(content)
            elif content is not None:
                console.print(str(content))

        final_content = workflow_run.content
        if isinstance(final_content, str):
            last_content = (
                getattr(step_results[-1], "content", None) if step_results else None
            )
            if not step_results or final_content != last_content:
                console.rule("Workflow summary")
                console.print(final_content)
        elif final_content is not None and not step_results:
            console.rule("Workflow summary")
            console.print(str(final_content))

        console.file.flush()

    def lint(
        self,
        linter_command: Annotated[
            str,
            typer.Argument(help="Linter command or alias to execute (e.g. 'ruff')."),
        ],
        targets: Annotated[
            list[str],
            typer.Argument(help="Files or directories to lint."),
        ],
        project_path: Annotated[
            Path | None,
            typer.Option(
                "--path",
                "-p",
                exists=True,
                file_okay=False,
                dir_okay=True,
                help="Optional project directory for running the linter.",
            ),
        ] = None,
        fix_instructions: Annotated[
            str | None,
            typer.Option(
                "--fix-instructions",
                help=(
                    "Optional additional instructions for the agent when proposing fixes."
                ),
            ),
        ] = None,
    ) -> None:
        """Run the linter workflow and display results."""
        self.logger.info(
            "Running linter workflow",
            linter_command=linter_command,
            targets=targets,
            project_path=str(project_path) if project_path else None,
        )

        try:
            workflow_run = run_linter_workflow(
                linter_command=linter_command,
                targets=targets,
                project_path=project_path,
                fix_instructions=fix_instructions,
            )
        except AgentConfigurationError as exc:
            console.print(
                "[red]OpenAI API key not configured. "
                "Set the OPENAI_API_KEY environment variable.[/red]",
            )
            self.logger.error("Agent configuration error", error=str(exc))
            raise typer.Exit(1) from exc
        except AgentExecutionError as exc:
            self.logger.error("Agent execution failed", error=str(exc))
            console.print(f"[red]Failed to run linter workflow: {exc}[/red]")
            raise typer.Exit(1) from exc

        step_results = list(workflow_run.step_results or [])
        for step in step_results:
            step_name = getattr(step, "step_name", None) or "Workflow step"
            console.rule(step_name)
            content = getattr(step, "content", None)
            if isinstance(content, str):
                console.print(content)
            elif content is not None:
                console.print(str(content))

        final_content = workflow_run.content
        if isinstance(final_content, str):
            last_content = (
                getattr(step_results[-1], "content", None) if step_results else None
            )
            if not step_results or final_content != last_content:
                console.rule("Workflow summary")
                console.print(final_content)
        elif final_content is not None and not step_results:
            console.rule("Workflow summary")
            console.print(str(final_content))

        console.file.flush()

    def run(self) -> None:
        """Run the CLI interface."""
        # Let Typer handle the command parsing
        self.app()
