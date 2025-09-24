"""Tests for the workflow test command utilities."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

from clean_interfaces.workflow.test_commands import (
    TestCommandExecutor,
    TestCommandManager,
    TestCommandResult,
)


def test_manager_register_and_resolve() -> None:
    """It registers a custom alias and resolves dynamic commands."""
    manager = TestCommandManager()
    manager.register("custom", ["python", "-c", "print('ok')"])

    assert manager.resolve("custom") == ("python", "-c", "print('ok')")

    resolved = manager.resolve("python -c 'print(\"dynamic\")'")
    assert resolved[0] == "python"
    assert "dynamic" in resolved[-1]


def test_executor_runs_registered_command() -> None:
    """It executes a registered command and captures output."""
    manager = TestCommandManager()
    manager.register("echo", [sys.executable, "-c", "print('hello')"])

    executor = TestCommandExecutor(manager)
    result = executor.run("echo")

    assert isinstance(result, TestCommandResult)
    assert result.succeeded
    assert "hello" in result.stdout
    assert result.command_display().startswith(sys.executable)


def test_manager_registers_multiple_sequences() -> None:
    """It accepts multiple commands for a single alias."""
    manager = TestCommandManager(include_defaults=False)
    manager.register(
        "lint",
        [
            ["uv", "run", "ruff", "format"],
            "uv run ruff check",
        ],
    )

    first_command = manager.resolve("lint")
    assert first_command == ("uv", "run", "ruff", "format")

    all_commands = manager.resolve_all("lint")
    assert all_commands == (
        ("uv", "run", "ruff", "format"),
        ("uv", "run", "ruff", "check"),
    )


def test_executor_run_all_executes_every_command(monkeypatch: Any) -> None:
    """It executes all commands in sequence and returns individual results."""
    manager = TestCommandManager(include_defaults=False)
    manager.register(
        "lint",
        [
            ["uv", "run", "ruff", "format"],
            ["uv", "run", "ruff", "check"],
        ],
    )

    executor = TestCommandExecutor(manager)
    recorded: list[tuple[str, ...]] = []

    def fake_run(command: tuple[str, ...], **_: object) -> SimpleNamespace:
        recorded.append(tuple(command))
        index = len(recorded)
        return SimpleNamespace(returncode=0, stdout=f"out-{index}", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    results = executor.run_all("lint")

    assert recorded == [
        ("uv", "run", "ruff", "format"),
        ("uv", "run", "ruff", "check"),
    ]
    assert len(results) == 2
    assert all(result.succeeded for result in results)
    assert {result.stdout for result in results} == {"out-1", "out-2"}


def test_result_format_includes_outputs() -> None:
    """It formats command results with stdout and stderr."""
    result = TestCommandResult(
        command=("pytest",),
        returncode=1,
        stdout="example output",
        stderr="example error",
        duration=0.5,
    )

    formatted = result.format()
    assert "Exit code: 1" in formatted
    assert "example output" in formatted
    assert "example error" in formatted
    assert "0.50s" in formatted

    prompt_block = result.to_prompt_block()
    assert "example output" in prompt_block
    assert "example error" in prompt_block
