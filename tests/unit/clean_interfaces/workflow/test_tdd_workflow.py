"""Tests for the TDD workflow orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agno.run.workflow import WorkflowRunOutput

from clean_interfaces.workflow.tdd import TDDWorkflowConfig, create_tdd_workflow
from clean_interfaces.workflow.test_commands import TestCommandResult


def test_create_tdd_workflow_runs_sequential_steps(
    monkeypatch: Any,
) -> None:
    """It orchestrates exploration, testing, and implementation steps."""
    config = TDDWorkflowConfig(
        exploration_prompt="Explore the repository",
        test_prompt="Write tests for the feature",
        implementation_prompt="Implement the feature",
        test_command="pytest",
        project_path=Path.cwd(),
    )

    prompts: list[str] = []

    def fake_exploration(prompt: str, _project_path: Path | None) -> str:
        assert prompt == config.exploration_prompt
        return "exploration summary"

    def fake_coding(prompt: str) -> str:
        prompts.append(prompt)
        return "coding output"

    test_results = [
        TestCommandResult(
            command=("pytest",),
            returncode=1,
            stdout="failing tests",
            stderr="",
            duration=0.1,
        ),
        TestCommandResult(
            command=("pytest",),
            returncode=0,
            stdout="passing tests",
            stderr="",
            duration=0.1,
        ),
    ]

    def fake_run(
        _self: object,
        command_spec: str,
        *,
        timeout: float | None = None,
    ) -> TestCommandResult:
        assert timeout is None
        assert command_spec == config.test_command
        return test_results.pop(0)

    monkeypatch.setattr(
        "clean_interfaces.workflow.test_commands.TestCommandExecutor.run",
        fake_run,
    )

    workflow = create_tdd_workflow(
        config=config,
        exploration_runner=fake_exploration,
        test_writer_runner=fake_coding,
        implementation_runner=fake_coding,
    )

    result = workflow.run()
    assert isinstance(result, WorkflowRunOutput)
    step_results = list(result.step_results or [])
    step_names = [getattr(step, "step_name", None) for step in step_results]
    assert step_names == [
        "Explore codebase",
        "Design tests",
        "Execute tests (expect failure)",
        "Implement feature",
        "Execute tests (expect success)",
    ]

    assert "exploration summary" in prompts[0]
    assert "Tests to satisfy:" in prompts[1]
    assert "Exit code: 1" in prompts[1]

    final_content = getattr(step_results[-1], "content", None)
    assert isinstance(final_content, str)
    assert "Tests behaved as expected" in final_content
