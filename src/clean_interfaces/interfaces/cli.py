"""CLI interface implementation using Typer."""

from pathlib import Path
from typing import Annotated, Sequence

import typer
from rich.console import Console
from rich.table import Table

from clean_interfaces.core import (
    AgentConfigurationError,
    AgentExecutionError,
    run_coding_agent,
    run_repository_qa_agent,
    run_serena_coder_agent,
    run_tdd_workflow,
)
from clean_interfaces.config.mcp import (
    MCPConfigError,
    McpServerEntry,
    load_mcp_servers,
    remove_mcp_server,
    save_mcp_server,
)
from clean_interfaces.models.io import WelcomeMessage
from clean_interfaces.workflow import TestCommandExecutionError

from .base import BaseInterface

# Configure console for better test compatibility
# Force terminal mode even in non-TTY environments
console = Console(force_terminal=True, force_interactive=False)

_JSON_FLAG_DEFAULT = False


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

        # Model Context Protocol management commands
        mcp_app = typer.Typer(
            name="mcp",
            help="Manage Model Context Protocol server integrations.",
            add_completion=False,
        )
        mcp_app.command(name="add")(self.mcp_add)
        mcp_app.command(name="list")(self.mcp_list)
        mcp_app.command(name="get")(self.mcp_get)
        mcp_app.command(name="remove")(self.mcp_remove)
        self.app.add_typer(mcp_app, name="mcp")

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

    # ------------------------------------------------------------------
    # MCP management helpers
    # ------------------------------------------------------------------

    def _handle_mcp_error(self, action: str, exc: MCPConfigError) -> None:
        """Log an MCP configuration error and exit."""
        console.print(f"[red]{action}: {exc}[/red]")
        console.file.flush()
        self.logger.error("MCP configuration error", action=action, error=str(exc))
        raise typer.Exit(1) from exc

    def _parse_env_values(
        self, env_values: Sequence[str] | None
    ) -> dict[str, str] | None:
        """Convert repeated KEY=VALUE options into a mapping."""
        if not env_values:
            return None

        env_map: dict[str, str] = {}
        for raw in env_values:
            if "=" not in raw:
                msg = "Environment entries must be provided as KEY=VALUE pairs."
                raise typer.BadParameter(msg)
            key, value = raw.split("=", 1)
            key = key.strip()
            if not key:
                msg = "Environment variable names cannot be empty."
                raise typer.BadParameter(msg)
            env_map[key] = value
        return env_map

    def _validate_server_name(self, name: str) -> None:
        """Ensure the server name matches the expected pattern."""
        if not name or not all(
            char.isalnum() or char in {"-", "_"} for char in name
        ):
            msg = (
                "Server names must contain only letters, numbers, '-' or '_' "
                "characters."
            )
            raise typer.BadParameter(msg)

    def mcp_add(
        self,
        name: Annotated[
            str,
            typer.Argument(help="Identifier for the MCP server configuration."),
        ],
        command: Annotated[
            list[str],
            typer.Argument(
                help="Command used to launch the MCP server.",
                metavar="COMMAND...",
            ),
        ],
        env: Annotated[
            Sequence[str],
            typer.Option(
                (),
                "--env",
                help="Environment variables to set when launching the server.",
                metavar="KEY=VALUE",
                show_default=False,
            ),
        ],
        startup_timeout_sec: Annotated[
            float | None,
            typer.Option(
                None,
                "--startup-timeout-sec",
                help="Override how long to wait for the server to become ready.",
            ),
        ] = None,
        tool_timeout_sec: Annotated[
            float | None,
            typer.Option(
                None,
                "--tool-timeout-sec",
                help="Override how long individual MCP tool calls may run.",
            ),
        ] = None,
    ) -> None:
        """Add or update an MCP server entry in the config file."""
        self._validate_server_name(name)
        if not command:
            msg = "A command to launch the MCP server is required."
            raise typer.BadParameter(msg)

        env_map = self._parse_env_values(env)

        entry = McpServerEntry(
            command=command[0],
            args=command[1:],
            env=env_map,
            startup_timeout_sec=startup_timeout_sec,
            tool_timeout_sec=tool_timeout_sec,
        )

        try:
            save_mcp_server(name, entry)
        except MCPConfigError as exc:
            self._handle_mcp_error("Failed to save MCP server configuration", exc)
            return

        self.logger.info("Saved MCP server entry", name=name, command=command[0])
        console.print(f"[green]Added MCP server '{name}'.[/green]")
        console.file.flush()

    def mcp_list(
        self,
        json_output: Annotated[
            bool,
            typer.Option(
                _JSON_FLAG_DEFAULT,
                "--json",
                help="Render the configured servers as JSON instead of a table.",
                is_flag=True,
            ),
        ] = False,
    ) -> None:
        """List configured MCP servers."""
        try:
            servers = load_mcp_servers()
        except MCPConfigError as exc:
            self._handle_mcp_error("Failed to load MCP server configuration", exc)
            return

        if json_output:
            payload = [entry.to_json(name) for name, entry in sorted(servers.items())]
            console.print_json(data=payload)
            console.file.flush()
            return

        if not servers:
            message = (
                "[yellow]No MCP servers configured. Use 'clean-interfaces mcp add' "
                "to add one.[/yellow]"
            )
            console.print(message)
            console.file.flush()
            return

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Name", style="bold")
        table.add_column("Command")
        table.add_column("Args")
        table.add_column("Env")

        for name, entry in sorted(servers.items()):
            args_display = " ".join(entry.args) if entry.args else "-"
            if entry.env:
                env_parts = [
                    f"{key}={value}" for key, value in sorted(entry.env.items())
                ]
                env_display = ", ".join(env_parts)
            else:
                env_display = "-"
            table.add_row(name, entry.command, args_display, env_display)

        console.print(table)
        console.file.flush()

    def mcp_get(
        self,
        name: Annotated[
            str,
            typer.Argument(help="Name of the configured MCP server to display."),
        ],
        json_output: Annotated[
            bool,
            typer.Option(
                _JSON_FLAG_DEFAULT,
                "--json",
                help="Render the server configuration as JSON.",
                is_flag=True,
            ),
        ] = False,
    ) -> None:
        """Display a single MCP server configuration entry."""
        try:
            servers = load_mcp_servers()
        except MCPConfigError as exc:
            self._handle_mcp_error("Failed to load MCP server configuration", exc)
            return

        entry = servers.get(name)
        if entry is None:
            console.print(f"[red]No MCP server named '{name}' found.[/red]")
            console.file.flush()
            raise typer.Exit(1)

        if json_output:
            console.print_json(data=entry.to_json(name))
            console.file.flush()
            return

        console.print(f"[bold]{name}[/bold]")
        console.print(f"  command: {entry.command}")
        args_display = " ".join(entry.args) if entry.args else "-"
        console.print(f"  args: {args_display}")
        if entry.env:
            env_parts = [f"{key}={value}" for key, value in sorted(entry.env.items())]
            env_display = ", ".join(env_parts)
        else:
            env_display = "-"
        console.print(f"  env: {env_display}")
        if entry.startup_timeout_sec is not None:
            console.print(f"  startup_timeout_sec: {entry.startup_timeout_sec}")
        if entry.tool_timeout_sec is not None:
            console.print(f"  tool_timeout_sec: {entry.tool_timeout_sec}")
        console.print(f"  remove: clean-interfaces mcp remove {name}")
        console.file.flush()

    def mcp_remove(
        self,
        name: Annotated[
            str,
            typer.Argument(help="Name of the MCP server configuration to remove."),
        ],
    ) -> None:
        """Remove a configured MCP server."""
        try:
            removed = remove_mcp_server(name)
        except MCPConfigError as exc:
            self._handle_mcp_error("Failed to update MCP server configuration", exc)
            return

        if removed:
            self.logger.info("Removed MCP server entry", name=name)
            console.print(f"[green]Removed MCP server '{name}'.[/green]")
        else:
            console.print(f"[yellow]No MCP server named '{name}' found.[/yellow]")
        console.file.flush()

    def run(self) -> None:
        """Run the CLI interface."""
        # Let Typer handle the command parsing
        self.app()
