"""Tests for the workflow test command utilities."""

from __future__ import annotations

import sys

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
