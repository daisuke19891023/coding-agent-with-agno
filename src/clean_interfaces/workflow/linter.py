"""Agentic workflow for running linters and proposing fixes.

This module defines a small workflow that:

1) Runs a user-specified linter command against provided targets
2) Summarises the results
3) Invokes a coding agent to propose fixes for any issues found

It mirrors the structure of the TDD workflow by accepting runner callables
from the orchestrator layer to avoid circular dependencies.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from agno.workflow import Step, StepInput, Workflow

from .test_commands import TestCommandExecutor, TestCommandManager, TestCommandResult

if TYPE_CHECKING:
    from pathlib import Path


CodingRunner = Callable[[str], str]


@dataclass(slots=True)
class LinterWorkflowConfig:
    """Configuration for the linter workflow pipeline."""

    linter_command: str
    targets: Sequence[str]
    project_path: Path | None = None
    fix_instructions: str | None = None


@dataclass(slots=True)
class _LinterStepFactory:
    """Build step executors for the linter workflow."""

    config: LinterWorkflowConfig
    executor: TestCommandExecutor
    fix_runner: CodingRunner
    results: list[TestCommandResult]

    lint_step_name: str = "Run linter"
    propose_fixes_step_name: str = "Propose fixes for linter issues"

    def run_linter(self, _step_input: StepInput) -> str:
        """Execute the linter command against configured targets."""
        # Build a command spec including targets; the executor resolves named aliases
        # and executes with the configured working directory.
        #
        # We join the targets into the command specification to preserve quoting rules
        # applied by the manager/executor.
        target_spec = " ".join(self._shell_escape_many(self.config.targets))
        command_spec = (
            f"{self.config.linter_command} {target_spec}" if target_spec else self.config.linter_command
        )

        result = self.executor.run(command_spec)
        self.results.append(result)
        return self._format_lint_summary(result)

    def propose_fixes(self, step_input: StepInput) -> str:
        """Invoke the coding agent to propose fixes based on linter output."""
        lint_output = step_input.get_step_content(self.lint_step_name)
        prompt_parts: list[str] = [
            self.config.fix_instructions
            or (
                "Review the linter findings and propose precise, actionable code edits "
                "to resolve all issues. Provide unified diffs for each file that should "
                "be changed, and explain the rationale briefly."
            ),
            "\n\nLinter summary (raw output included):\n",
            str(lint_output),
        ]
        prompt = "".join(prompt_parts)
        return self.fix_runner(prompt)

    @staticmethod
    def _shell_escape_many(values: Iterable[str]) -> list[str]:
        # Lightweight shell-escape that mirrors shlex.join behaviour for simple values
        # without introducing a hard dependency here. Targets typically are paths.
        escaped: list[str] = []
        for value in values:
            if not value:
                escaped.append("''")
                continue
            if any(ch.isspace() for ch in value) or any(ch in "'\"$`" for ch in value):
                escaped.append("'" + value.replace("'", "'\\''") + "'")
            else:
                escaped.append(value)
        return escaped

    @staticmethod
    def _format_lint_summary(result: TestCommandResult) -> str:
        expectation = "Issues found" if result.returncode != 0 else "No issues detected"
        return (
            f"Command: {result.command_display()}\n"
            f"Exit code: {result.returncode} ({expectation})\n"
            f"Duration: {result.duration:.2f}s\n\n"
            f"Stdout:\n{result.stdout.strip()}\n\nStderr:\n{result.stderr.strip()}"
        ).strip()


def create_linter_workflow(
    *,
    config: LinterWorkflowConfig,
    command_manager: TestCommandManager | None = None,
    fix_runner: CodingRunner,
) -> Workflow:
    """Create a workflow that runs a linter and proposes fixes.

    We reuse the generic command manager/executor utilities, as they already
    encapsulate command resolution, execution, and result formatting.
    """
    manager = command_manager or TestCommandManager()
    executor = TestCommandExecutor(manager, cwd=config.project_path)
    factory = _LinterStepFactory(
        config=config,
        executor=executor,
        fix_runner=fix_runner,
        results=[],
    )

    steps: Sequence[Step] = (
        Step(name=factory.lint_step_name, executor=factory.run_linter),
        Step(name=factory.propose_fixes_step_name, executor=factory.propose_fixes),
    )

    return Workflow(
        name="Linter Workflow",
        description=(
            "Run the configured linter against targets and ask a coding agent to "
            "propose fixes for issues."
        ),
        steps=list(steps),
    )

