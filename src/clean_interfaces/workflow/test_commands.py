"""Utilities for managing and executing test commands within workflows."""

from __future__ import annotations

import shlex
import subprocess
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, cast

from clean_interfaces.base import BaseComponent
from clean_interfaces.utils.file_handler import FileHandler

CommandInput = str | Iterable[str] | Iterable[Iterable[str]]
CommandSequence = tuple[tuple[str, ...], ...]

if TYPE_CHECKING:
    from pathlib import Path


class TestCommandExecutionError(RuntimeError):
    """Raised when a test command cannot be executed successfully."""

    def __init__(
        self,
        command: tuple[str, ...],
        message: str,
        *,
        stderr: str | None = None,
    ) -> None:
        """Initialise the execution error with command context."""
        command_display = " ".join(shlex.quote(part) for part in command)
        formatted_message = f"{message}\nCommand: {command_display}"
        if stderr:
            formatted_message = f"{formatted_message}\nStderr: {stderr.strip()}"
        super().__init__(formatted_message)
        self.command = tuple(command)
        self.stderr = stderr


@dataclass(slots=True)
class TestCommandResult:
    """Result of executing a test command."""

    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    duration: float

    @property
    def succeeded(self) -> bool:
        """Return whether the command exited successfully."""
        return self.returncode == 0

    def command_display(self) -> str:
        """Return the command as a shell-escaped string."""
        return " ".join(shlex.quote(part) for part in self.command)

    def format(self) -> str:
        """Return a human-readable representation of the command result."""
        lines = [
            f"Command: {self.command_display()}",
            f"Exit code: {self.returncode}",
            f"Duration: {self.duration:.2f}s",
        ]
        if self.stdout.strip():
            lines.append("Stdout:\n" + self.stdout.strip())
        if self.stderr.strip():
            lines.append("Stderr:\n" + self.stderr.strip())
        return "\n".join(lines)

    def to_prompt_block(self) -> str:
        """Return a compact summary suitable for inclusion in prompts."""
        summary = [
            f"Command: {self.command_display()}",
            f"Exit code: {self.returncode}",
        ]
        stdout = self.stdout.strip()
        stderr = self.stderr.strip()
        if stdout:
            summary.append("Stdout:\n" + stdout)
        if stderr:
            summary.append("Stderr:\n" + stderr)
        return "\n".join(summary)


class TestCommandManager(BaseComponent):
    """Manage named test commands and resolve aliases."""

    _EMPTY_COMMAND_MESSAGE = "Command must contain at least one element"

    def __init__(
        self,
        *,
        commands: Mapping[str, CommandInput] | None = None,
        include_defaults: bool = True,
    ) -> None:
        """Initialise the manager with optional command aliases."""
        super().__init__()
        self._commands: dict[str, CommandSequence] = {}
        if include_defaults:
            self.register("pytest", ("uv", "run", "pytest"))
        if commands:
            self.register_many(commands)

    @classmethod
    def normalise(cls, command: CommandInput) -> CommandSequence:
        """Normalise a command input into canonical tuple form."""
        if isinstance(command, str):
            return cls._normalise_from_string(command)

        iterable_command = cast("Iterable[Any]", command)
        return cls._normalise_from_iterable(iterable_command)

    @classmethod
    def _normalise_from_string(cls, command: str) -> CommandSequence:
        """Normalise a shell-style string command."""
        return (cls._ensure_parts(shlex.split(command)),)

    @classmethod
    def _normalise_from_iterable(cls, command: Iterable[Any]) -> CommandSequence:
        """Normalise an iterable of commands or arguments."""
        elements = list(command)
        if not elements:
            raise ValueError(cls._EMPTY_COMMAND_MESSAGE)

        if all(isinstance(element, str) for element in elements):
            return (cls._ensure_parts([str(element) for element in elements]),)

        sequences = [cls._normalise_nested_element(element) for element in elements]
        return tuple(sequences)

    @classmethod
    def _normalise_nested_element(cls, element: Any) -> tuple[str, ...]:
        """Normalise a nested command element."""
        if isinstance(element, str):
            return cls._ensure_parts(shlex.split(element))
        try:
            iterator = iter(cast("Iterable[Any]", element))
        except TypeError as exc:
            message = f"Unsupported command element type: {type(element)!r}"
            raise TypeError(message) from exc
        parts = [str(part) for part in iterator]
        return cls._ensure_parts(parts)

    @staticmethod
    def _ensure_parts(parts: Iterable[str]) -> tuple[str, ...]:
        """Convert command parts into a tuple, ensuring it is not empty."""
        parts_tuple = tuple(parts)
        if not parts_tuple:
            raise ValueError(TestCommandManager._EMPTY_COMMAND_MESSAGE)
        return parts_tuple

    def register(self, name: str, command: CommandInput) -> None:
        """Register a new named command alias."""
        sequences = self.normalise(command)
        self.logger.debug("Registering test command", name=name, command=sequences)
        self._commands[name] = sequences

    def register_many(self, commands: Mapping[str, CommandInput]) -> None:
        """Register multiple command aliases at once."""
        for name, command in commands.items():
            self.register(name, command)

    def resolve(self, spec: str) -> tuple[str, ...]:
        """Resolve a command specification into a single executable tuple."""
        commands = self.resolve_all(spec)
        return commands[0]

    def resolve_all(self, spec: str) -> CommandSequence:
        """Resolve a command specification into all configured commands."""
        if not spec:
            message = "Command specification cannot be empty"
            raise ValueError(message)

        if spec in self._commands:
            return self._commands[spec]

        parsed = shlex.split(spec)
        if not parsed:
            message = "Command specification cannot be empty"
            raise ValueError(message)
        return (tuple(parsed),)


class TestCommandExecutor(BaseComponent):
    """Execute test commands resolved by :class:`TestCommandManager`."""

    def __init__(
        self,
        manager: TestCommandManager,
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        """Store configuration for executing test commands."""
        super().__init__()
        self._manager = manager
        self._cwd = cwd
        self._env = env

    def run(
        self,
        command_spec: str,
        *,
        timeout: float | None = None,
    ) -> TestCommandResult:
        """Execute the provided command specification and return the result."""
        command = self._manager.resolve(command_spec)
        return self._execute(command, timeout=timeout)

    def run_all(
        self,
        command_spec: str,
        *,
        timeout: float | None = None,
    ) -> tuple[TestCommandResult, ...]:
        """Execute all commands associated with the specification."""
        commands = self._manager.resolve_all(command_spec)
        results = [self._execute(command, timeout=timeout) for command in commands]
        return tuple(results)

    def _execute(
        self,
        command: tuple[str, ...],
        *,
        timeout: float | None,
    ) -> TestCommandResult:
        """Execute a single command sequence and capture the result."""
        self.logger.info(
            "Running test command",
            command=command,
            cwd=str(self._cwd) if self._cwd else None,
            timeout=timeout,
        )

        start = time.perf_counter()
        try:
            completed = subprocess.run(  # noqa: S603 - executed without shell, aliases are validated
                command,
                cwd=self._cwd,
                env=self._env,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:  # pragma: no cover - rare in tests
            stderr_output = (
                exc.stderr.decode() if isinstance(exc.stderr, bytes) else exc.stderr
            )
            raise TestCommandExecutionError(
                command,
                "Test command timed out",
                stderr=stderr_output,
            ) from exc
        except OSError as exc:  # pragma: no cover - environment-specific
            raise TestCommandExecutionError(command, str(exc)) from exc

        duration = time.perf_counter() - start
        result = TestCommandResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration=duration,
        )

        self.logger.info(
            "Test command finished",
            command=command,
            returncode=result.returncode,
            duration=result.duration,
        )
        return result


@dataclass(slots=True)
class WorkflowCommandConfig:
    """Command configuration for agent workflows."""

    tests: dict[str, CommandSequence]
    lint: dict[str, CommandSequence]

    def __post_init__(self) -> None:
        """Normalise provided command mappings into dictionaries."""
        self.tests = dict(self.tests)
        self.lint = dict(self.lint)

    @classmethod
    def empty(cls) -> WorkflowCommandConfig:
        """Return an empty configuration."""
        return cls(tests={}, lint={})

    def commands_for(
        self,
        category: Literal["tests", "lint"],
    ) -> dict[str, CommandSequence]:
        """Return a shallow copy of commands for the given category."""
        return dict(getattr(self, category))

    def register_tests(self, manager: TestCommandManager) -> None:
        """Register test commands with the provided manager."""
        for name, command in self.tests.items():
            manager.register(name, command)

    def register_lint(self, manager: TestCommandManager) -> None:
        """Register lint commands with the provided manager."""
        for name, command in self.lint.items():
            manager.register(name, command)


def load_workflow_command_config(
    path: str | Path,
    *,
    file_handler: FileHandler | None = None,
) -> WorkflowCommandConfig:
    """Load workflow command configuration from a YAML file."""
    handler = file_handler or FileHandler()
    data = handler.read_yaml(path)
    if data is None:
        return WorkflowCommandConfig.empty()
    if not isinstance(data, Mapping):
        message = "Workflow command configuration must be a mapping"
        raise TypeError(message)

    typed_data = cast("Mapping[str, object]", data)
    tests = _parse_command_section(typed_data.get("tests"), section="tests")
    lint = _parse_command_section(typed_data.get("lint"), section="lint")
    return WorkflowCommandConfig(tests=tests, lint=lint)


def create_manager_from_config(
    config: WorkflowCommandConfig,
    *,
    category: Literal["tests", "lint"],
    include_defaults: bool | None = None,
) -> TestCommandManager:
    """Create a :class:`TestCommandManager` populated from configuration."""
    include = include_defaults if include_defaults is not None else category == "tests"
    manager = TestCommandManager(include_defaults=include)
    commands = config.commands_for(category)
    if commands:
        manager.register_many(commands)
    return manager


def _parse_command_section(
    section_data: Any,
    *,
    section: str,
) -> dict[str, CommandSequence]:
    """Parse a command section from configuration data."""
    if section_data is None:
        return {}
    if not isinstance(section_data, Mapping):
        message = f"{section} section must be a mapping of command names to commands"
        raise TypeError(message)

    typed_section = cast("Mapping[object, object]", section_data)

    result: dict[str, CommandSequence] = {}
    for raw_name, raw_command in typed_section.items():
        if not isinstance(raw_name, str):
            message = "Command names must be strings"
            raise TypeError(message)
        try:
            command_input = cast("CommandInput", raw_command)
            result[raw_name] = TestCommandManager.normalise(command_input)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive guard
            message = (
                f"Invalid command definition for {section} command '{raw_name}': {exc}"
            )
            raise ValueError(message) from exc
    return result
