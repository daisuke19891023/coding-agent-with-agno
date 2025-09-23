"""Agentic workflows for practising test-driven development."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from agno.workflow import Step, StepInput, Workflow

from .test_commands import TestCommandExecutor, TestCommandManager, TestCommandResult

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(slots=True)
class TDDWorkflowConfig:
    """Configuration for the TDD workflow pipeline."""

    exploration_prompt: str
    test_prompt: str
    implementation_prompt: str
    test_command: str
    project_path: Path | None = None


ExplorationRunner = Callable[[str, "Path | None"], str]
CodingRunner = Callable[[str], str]


@dataclass(slots=True)
class _TDDStepFactory:
    """Build step executors for the TDD workflow."""

    config: TDDWorkflowConfig
    executor: TestCommandExecutor
    exploration_runner: ExplorationRunner
    test_writer_runner: CodingRunner
    implementation_runner: CodingRunner
    test_results: list[TestCommandResult]

    exploration_step_name: str = "Explore codebase"
    test_step_name: str = "Design tests"
    initial_test_run_name: str = "Execute tests (expect failure)"
    implementation_step_name: str = "Implement feature"
    final_test_run_name: str = "Execute tests (expect success)"

    def exploration(self, _step_input: StepInput) -> Any:
        """Run the exploration agent."""
        return self.exploration_runner(
            self.config.exploration_prompt,
            self.config.project_path,
        )

    def write_tests(self, step_input: StepInput) -> Any:
        """Run the test authoring agent with exploration context."""
        exploration_output = step_input.get_step_content(self.exploration_step_name)
        prompt = self._append_context(
            self.config.test_prompt,
            "Context from exploration:",
            exploration_output,
        )
        return self.test_writer_runner(prompt)

    def initial_test_run(self, _step_input: StepInput) -> Any:
        """Execute the first test run and capture its summary."""
        result = self.executor.run(self.config.test_command)
        self.test_results.append(result)
        return self._format_test_summary(result, expect_success=False)

    def implement_feature(self, step_input: StepInput) -> Any:
        """Run the implementation agent with accumulated context."""
        exploration_output = step_input.get_step_content(self.exploration_step_name)
        tests_output = step_input.get_step_content(self.test_step_name)
        previous_result = self.test_results[-1] if self.test_results else None

        prompt = self._append_context(
            self.config.implementation_prompt,
            "Context from exploration:",
            exploration_output,
        )
        prompt = self._append_context(prompt, "Tests to satisfy:", tests_output)
        if previous_result:
            prompt = self._append_context(
                prompt,
                "Latest test run (expected failure):",
                previous_result.to_prompt_block(),
            )
        return self.implementation_runner(prompt)

    def final_test_run(self, _step_input: StepInput) -> Any:
        """Execute the final test run to confirm success."""
        result = self.executor.run(self.config.test_command)
        self.test_results.append(result)
        return self._format_test_summary(result, expect_success=True)

    def _append_context(
        self,
        prompt: str,
        heading: str,
        content: object | None,
    ) -> str:
        if not content:
            return prompt
        content_str = str(content).strip()
        if not content_str:
            return prompt
        return f"{prompt}\n\n{heading}\n{content_str}"

    @staticmethod
    def _format_test_summary(
        result: TestCommandResult,
        *,
        expect_success: bool,
    ) -> str:
        expectation_met = (result.succeeded and expect_success) or (
            not result.succeeded and not expect_success
        )
        status_line = (
            "✅ Tests behaved as expected."
            if expectation_met
            else "⚠️ Test outcome did not match the expectation."
        )
        return f"{result.format()}\n\n{status_line}"


def create_tdd_workflow(
    *,
    config: TDDWorkflowConfig,
    command_manager: TestCommandManager | None = None,
    exploration_runner: ExplorationRunner,
    test_writer_runner: CodingRunner,
    implementation_runner: CodingRunner | None = None,
) -> Workflow:
    """Create a workflow that automates a TDD development session."""
    manager = command_manager or TestCommandManager()
    executor = TestCommandExecutor(manager, cwd=config.project_path)
    factory = _TDDStepFactory(
        config=config,
        executor=executor,
        exploration_runner=exploration_runner,
        test_writer_runner=test_writer_runner,
        implementation_runner=implementation_runner or test_writer_runner,
        test_results=[],
    )

    steps: Sequence[Step] = (
        Step(name=factory.exploration_step_name, executor=factory.exploration),
        Step(name=factory.test_step_name, executor=factory.write_tests),
        Step(name=factory.initial_test_run_name, executor=factory.initial_test_run),
        Step(name=factory.implementation_step_name, executor=factory.implement_feature),
        Step(name=factory.final_test_run_name, executor=factory.final_test_run),
    )

    return Workflow(
        name="TDD Workflow",
        description="Run exploration, tests, and implementation in a TDD loop.",
        steps=list(steps),
    )
