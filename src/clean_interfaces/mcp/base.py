"""Base interfaces for Model Context Protocol integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from agno.tools.mcp import MCPTools


class BaseLSPWalker(ABC):
    """Abstract base class for LSP-oriented MCP walkers."""

    def __init__(self, *, project_path: Path | None = None) -> None:
        """Store the optional project path to explore."""
        self._project_path = project_path.resolve() if project_path else None

    @property
    def project_path(self) -> Path | None:
        """Return the resolved project path if one was provided."""
        return self._project_path

    @abstractmethod
    def create_toolkit(self) -> MCPTools:
        """Return a configured MCP toolkit for the walker."""
