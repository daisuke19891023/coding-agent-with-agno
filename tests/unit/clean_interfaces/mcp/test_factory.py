"""Tests for MCP walker factory."""

from __future__ import annotations

import pytest

from clean_interfaces.mcp.factory import create_lsp_walker
from clean_interfaces.mcp.serena import SerenaLSPWalker
from clean_interfaces.utils.settings import MCPSettings


def test_factory_returns_serena_walker() -> None:
    """Factory should return Serena implementation by default."""
    settings = MCPSettings()
    walker = create_lsp_walker(settings)
    assert isinstance(walker, SerenaLSPWalker)


def test_factory_rejects_unknown_provider() -> None:
    """Factory should raise on unsupported providers."""
    settings = MCPSettings(lsp_walker_provider="serena")
    # type ignore to circumvent Literal check during instantiation for test
    settings.lsp_walker_provider = "unknown"  # type: ignore[assignment]

    with pytest.raises(ValueError, match="Unsupported LSP walker provider"):
        create_lsp_walker(settings)
