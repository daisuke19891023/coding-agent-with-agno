"""Utilities for managing and executing test commands within workflows."""

from __future__ import annotations

import shlex
import subprocess
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from clean_interfaces.base import BaseComponent

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path


class TestCommandExecutionError(RuntimeError):
    """Raised when a test command cannot be executed successfully."""

    def __init__(
        self,
        command: Sequence[str],
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

    def __init__(self) -> None:
        """Initialise the manager with default command aliases."""
        super().__init__()
        self._commands: dict[str, tuple[str, ...]] = {
            "pytest": ("uv", "run", "pytest"),
        }

    def register(self, name: str, command: Iterable[str]) -> None:
        """Register a new named command alias."""
        command_tuple = tuple(command)
        if not command_tuple:
            message = "Command must contain at least one element"
            raise ValueError(message)
        self.logger.debug("Registering test command", name=name, command=command_tuple)
        self._commands[name] = command_tuple

    def resolve(self, spec: str) -> tuple[str, ...]:
        """Resolve a command specification into an executable tuple."""
        if not spec:
            message = "Command specification cannot be empty"
            raise ValueError(message)

        if spec in self._commands:
            return self._commands[spec]

        return tuple(shlex.split(spec))


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
        if not command:
            raise TestCommandExecutionError(command, "Resolved command is empty")

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
