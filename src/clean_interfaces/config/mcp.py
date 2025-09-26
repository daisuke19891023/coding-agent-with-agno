"""Helpers for managing MCP server configuration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any

try:  # pragma: no cover - tomllib is present on Python >=3.11
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

import tomli_w

CONFIG_ENV_VAR = "CLEAN_INTERFACES_CONFIG_HOME"
_APP_SUBDIR = "clean-interfaces"
_CONFIG_FILENAME = "config.toml"
_MCP_SECTION = "mcp_servers"


class MCPConfigError(RuntimeError):
    """Raised when MCP configuration cannot be parsed or persisted."""


@dataclass(slots=True)
class McpServerEntry:
    """Representation of a configured MCP server."""

    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None
    startup_timeout_sec: float | None = None
    tool_timeout_sec: float | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> McpServerEntry:
        """Create an entry from a TOML mapping."""
        if "command" not in raw or not isinstance(raw["command"], str):
            msg = "MCP server entries must define a 'command' string"
            raise MCPConfigError(msg)

        args_value = raw.get("args", [])
        if not isinstance(args_value, list) or not all(
            isinstance(item, str) for item in args_value
        ):
            msg = "'args' must be a list of strings in MCP server entries"
            raise MCPConfigError(msg)

        env_value = raw.get("env")
        if env_value is not None:
            if not isinstance(env_value, Mapping) or not all(
                isinstance(key, str) and isinstance(value, str)
                for key, value in env_value.items()
            ):
                msg = "'env' must be a table of string key/value pairs"
                raise MCPConfigError(msg)
            env_map = {str(key): str(value) for key, value in env_value.items()}
        else:
            env_map = None

        extras: dict[str, Any] = {}
        for extra_key in raw.keys() - {
            "command",
            "args",
            "env",
            "startup_timeout_sec",
            "tool_timeout_sec",
        }:
            extras[extra_key] = raw[extra_key]

        return cls(
            command=str(raw["command"]),
            args=[str(item) for item in args_value],
            env=env_map,
            startup_timeout_sec=_optional_float(raw.get("startup_timeout_sec")),
            tool_timeout_sec=_optional_float(raw.get("tool_timeout_sec")),
            extras=extras,
        )

    def to_mapping(self) -> dict[str, Any]:
        """Convert the entry into a TOML-serialisable mapping."""
        data: dict[str, Any] = {"command": self.command, "args": list(self.args)}

        if self.env is not None:
            data["env"] = dict(self.env)

        if self.startup_timeout_sec is not None:
            data["startup_timeout_sec"] = self.startup_timeout_sec

        if self.tool_timeout_sec is not None:
            data["tool_timeout_sec"] = self.tool_timeout_sec

        if self.extras:
            data.update(self.extras)

        return data

    def to_json(self, name: str) -> dict[str, Any]:
        """Return a JSON-serialisable representation of the entry."""
        json_env = self.env if self.env is not None else None
        return {
            "name": name,
            "command": self.command,
            "args": list(self.args),
            "env": json_env,
            "startup_timeout_sec": self.startup_timeout_sec,
            "tool_timeout_sec": self.tool_timeout_sec,
        }


def _optional_float(value: Any) -> float | None:
    """Return value as float if provided, otherwise None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    msg = "timeout values must be numeric"
    raise MCPConfigError(msg)


def _resolve_base_dir() -> Path:
    """Return the base configuration directory."""
    env_dir = os.environ.get(CONFIG_ENV_VAR)
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return (Path.home() / "config").resolve()


def _resolve_config_dir() -> Path:
    """Return the application configuration directory."""
    return _resolve_base_dir() / _APP_SUBDIR


def _resolve_config_file() -> Path:
    """Return the path to the configuration file."""
    return _resolve_config_dir() / _CONFIG_FILENAME


def _load_raw_config() -> dict[str, Any]:
    """Load the raw configuration mapping from disk."""
    config_path = _resolve_config_file()
    if not config_path.exists():
        return {}

    try:
        with config_path.open("rb") as fh:
            return tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:  # pragma: no cover - I/O safety
        msg = f"Failed to read MCP configuration from {config_path}: {exc}"
        raise MCPConfigError(msg) from exc


def _write_raw_config(config: Mapping[str, Any]) -> None:
    """Write the provided configuration mapping to disk."""
    config_dir = _resolve_config_dir()
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # pragma: no cover - I/O safety
        msg = f"Failed to create config directory {config_dir}: {exc}"
        raise MCPConfigError(msg) from exc

    config_path = config_dir / _CONFIG_FILENAME
    try:
        with config_path.open("wb") as fh:
            tomli_w.dump(dict(config), fh)
    except OSError as exc:  # pragma: no cover - I/O safety
        msg = f"Failed to write config file {config_path}: {exc}"
        raise MCPConfigError(msg) from exc


def load_mcp_servers() -> dict[str, McpServerEntry]:
    """Return all configured MCP servers keyed by name."""
    raw_config = _load_raw_config()
    raw_servers = raw_config.get(_MCP_SECTION, {})

    if raw_servers in (None, {}):
        return {}

    if not isinstance(raw_servers, Mapping):
        msg = f"'{_MCP_SECTION}' section must be a table in the config file"
        raise MCPConfigError(msg)

    servers: dict[str, McpServerEntry] = {}
    for name, entry in raw_servers.items():
        if not isinstance(name, str):
            msg = "Server names must be strings"
            raise MCPConfigError(msg)
        if not isinstance(entry, Mapping):
            msg = f"MCP server '{name}' must be a table"
            raise MCPConfigError(msg)
        servers[name] = McpServerEntry.from_mapping(entry)

    return servers


def save_mcp_server(name: str, entry: McpServerEntry) -> None:
    """Insert or update an MCP server entry."""
    raw_config = _load_raw_config()
    raw_servers = raw_config.get(_MCP_SECTION)
    if raw_servers is None:
        raw_servers = {}
    elif not isinstance(raw_servers, Mapping):
        msg = f"'{_MCP_SECTION}' section must be a table in the config file"
        raise MCPConfigError(msg)

    raw_servers = dict(raw_servers)
    raw_servers[name] = entry.to_mapping()

    updated_config = dict(raw_config)
    updated_config[_MCP_SECTION] = raw_servers

    _write_raw_config(updated_config)


def remove_mcp_server(name: str) -> bool:
    """Remove an MCP server entry by name."""
    raw_config = _load_raw_config()
    raw_servers = raw_config.get(_MCP_SECTION)
    if raw_servers is None:
        return False
    if not isinstance(raw_servers, Mapping):
        msg = f"'{_MCP_SECTION}' section must be a table in the config file"
        raise MCPConfigError(msg)

    mutable_servers = dict(raw_servers)
    removed = mutable_servers.pop(name, None) is not None

    if not removed:
        return False

    updated_config = dict(raw_config)
    if mutable_servers:
        updated_config[_MCP_SECTION] = mutable_servers
    else:
        updated_config.pop(_MCP_SECTION, None)

    _write_raw_config(updated_config)
    return True


def dump_mcp_servers_json() -> str:
    """Return a JSON representation of the configured MCP servers."""
    servers = load_mcp_servers()
    payload = [entry.to_json(name) for name, entry in sorted(servers.items())]
    return json.dumps(payload, indent=2, ensure_ascii=False)
