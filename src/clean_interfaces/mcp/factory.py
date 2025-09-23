"""Factory helpers for creating MCP walker implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .serena import SerenaLSPWalker

if TYPE_CHECKING:
    from pathlib import Path

    from clean_interfaces.utils.settings import MCPSettings

    from .base import BaseLSPWalker


def create_lsp_walker(
    settings: MCPSettings,
    *,
    project_path: Path | None = None,
) -> BaseLSPWalker:
    """Create an LSP walker implementation based on configuration."""
    provider = settings.lsp_walker_provider.lower()

    if provider == "serena":
        return SerenaLSPWalker(settings=settings, project_path=project_path)

    msg = f"Unsupported LSP walker provider: {settings.lsp_walker_provider}"
    raise ValueError(msg)
