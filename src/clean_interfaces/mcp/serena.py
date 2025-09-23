"""Serena-specific MCP walker implementation."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agno.tools.mcp import MCPTools

from .base import BaseLSPWalker

if TYPE_CHECKING:
    from clean_interfaces.utils.settings import MCPSettings


class SerenaLSPWalker(BaseLSPWalker):
    """LSP walker that launches the Serena MCP server."""

    def __init__(
        self,
        settings: MCPSettings,
        *,
        project_path: Path | None = None,
    ) -> None:
        """Initialise the Serena walker with configuration and project path."""
        super().__init__(project_path=project_path)
        self._settings = settings

    def _has_flag(self, parts: list[str], flag: str) -> bool:
        """Return whether the command parts already include a given flag."""
        flag_prefix = f"{flag}="
        return any(part == flag or part.startswith(flag_prefix) for part in parts)

    def _resolve_project_path(self) -> Path:
        """Resolve the project path to use when launching the server."""
        if self.project_path is not None:
            return self.project_path
        return Path.cwd().resolve()

    def _build_command(self) -> str | None:
        base_command = self._settings.lsp_walker_command.strip()
        if not base_command:
            return None

        parts = shlex.split(base_command)

        if self._settings.lsp_walker_context and not self._has_flag(parts, "--context"):
            parts.extend(["--context", self._settings.lsp_walker_context])

        project_path = self._resolve_project_path()
        if not self._has_flag(parts, "--project"):
            parts.extend(["--project", str(project_path)])

        return shlex.join(parts)

    def create_toolkit(self) -> MCPTools:
        """Return a configured MCP toolkit for the Serena walker."""
        command = self._build_command()
        kwargs: dict[str, Any] = {
            "transport": self._settings.lsp_walker_transport,
            "timeout_seconds": self._settings.lsp_walker_timeout_seconds,
        }

        if self._settings.lsp_walker_url:
            kwargs["url"] = self._settings.lsp_walker_url

        if command:
            kwargs["command"] = command

        if self._settings.lsp_walker_transport == "stdio" and not command:
            msg = "Serena LSP walker requires a command when using stdio transport"
            raise ValueError(msg)

        return MCPTools(**kwargs)
