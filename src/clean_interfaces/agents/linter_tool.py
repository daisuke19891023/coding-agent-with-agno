"""An agno Tool for running arbitrary linter commands.

Designed to be reusable by agents while also usable directly by workflows.
It delegates execution to the workflow command executor utilities, but exposes
simple methods for convenience when used independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

try:  # agno 2.x may expose a base Tool type or simple protocol for tools
    from agno.tools import Tool as AgnoToolBase  # type: ignore
except Exception:  # pragma: no cover - fallback if import location differs
    AgnoToolBase = object  # type: ignore[misc,assignment]

from clean_interfaces.workflow.test_commands import (
    TestCommandExecutor,
    TestCommandManager,
    TestCommandResult,
)

if TYPE_CHECKING:
    from pathlib import Path
    from collections.abc import Sequence


@dataclass(slots=True)
class LinterTool(AgnoToolBase):
    """Tool wrapper that runs a linter command against targets."""

    linter_command: str
    manager: TestCommandManager
    cwd: Path | None = None

    def __init__(
        self,
        *,
        linter_command: str,
        cwd: Path | None = None,
        manager: TestCommandManager | None = None,
    ) -> None:
        # Avoid direct base class initialisation to keep compatibility across
        # potential agno releases where Tool may require different args.
        object.__setattr__(self, "linter_command", linter_command)
        object.__setattr__(self, "cwd", cwd)
        object.__setattr__(self, "manager", manager or TestCommandManager())

    def run(self, targets: Sequence[str]) -> TestCommandResult:
        """Execute the linter command against provided targets and return result."""
        executor = TestCommandExecutor(self.manager, cwd=self.cwd)
        target_spec = " ".join(targets)
        command_spec = (
            f"{self.linter_command} {target_spec}" if target_spec else self.linter_command
        )
        return executor.run(command_spec)

