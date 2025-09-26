"""Tests for MCP configuration helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from clean_interfaces.config.mcp import (
    McpServerEntry,
    load_mcp_servers,
    remove_mcp_server,
    save_mcp_server,
)

try:  # pragma: no cover - fallback for older Python versions
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def config_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide an isolated configuration home for tests."""
    base = tmp_path / "config_home"
    monkeypatch.setenv("CLEAN_INTERFACES_CONFIG_HOME", str(base))
    return base


def test_load_empty_when_config_missing(config_home: Path) -> None:
    """Loading configuration without a file should return an empty mapping."""
    _ = config_home
    assert load_mcp_servers() == {}


def test_save_and_reload_round_trip(config_home: Path) -> None:
    """Saving an entry should persist it to TOML and allow reloading."""
    entry = McpServerEntry(
        command="docs-server",
        args=["--port", "4000"],
        env={"API_KEY": "value"},
        startup_timeout_sec=12.5,
    )

    save_mcp_server("docs", entry)

    servers = load_mcp_servers()
    assert "docs" in servers
    stored = servers["docs"]
    assert stored.command == "docs-server"
    assert stored.args == ["--port", "4000"]
    assert stored.env == {"API_KEY": "value"}
    assert stored.startup_timeout_sec == pytest.approx(12.5)

    config_path = config_home / "clean-interfaces" / "config.toml"
    with config_path.open("rb") as fh:
        data = tomllib.load(fh)

    assert data["mcp_servers"]["docs"]["command"] == "docs-server"
    assert data["mcp_servers"]["docs"]["args"] == ["--port", "4000"]
    assert data["mcp_servers"]["docs"]["env"] == {"API_KEY": "value"}


def test_remove_missing_entry_returns_false(config_home: Path) -> None:
    """Removing a missing server should return False and keep the file untouched."""
    assert remove_mcp_server("unknown") is False

    config_path = config_home / "clean-interfaces" / "config.toml"
    assert not config_path.exists()
