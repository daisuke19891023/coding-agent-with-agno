"""Helpers for managing MCP server configuration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any, cast

import tomllib
import tomli_w

CONFIG_ENV_VAR = "CLEAN_INTERFACES_CONFIG_HOME"
_APP_SUBDIR = "clean-interfaces"
_CONFIG_FILENAME = "config.toml"
_MCP_SECTION = "mcp_servers"


class MCPConfigError(RuntimeError):
    """Raised when MCP configuration cannot be parsed or persisted."""


def _new_args_list() -> list[str]:
    """Return a new list for command arguments."""
    return []


def _new_extras_dict() -> dict[str, Any]:
    """Return a new dictionary for additional values."""
    return {}


def _parse_args_field(raw: Mapping[str, Any]) -> list[str]:
    """Extract the optional args field as a list of strings."""
    args_raw = raw.get("args")
    if args_raw is None:
        return []
    if not isinstance(args_raw, list):
        msg = "'args' must be provided as a list"
        raise MCPConfigError(msg)

    args_candidates = cast("list[object]", args_raw)
    args_list: list[str] = []
    for item in args_candidates:
        if not isinstance(item, str):
            msg = "'args' must be a list of strings in MCP server entries"
            raise MCPConfigError(msg)
        args_list.append(item)
    return args_list


def _parse_env_field(raw: Mapping[str, Any]) -> dict[str, str] | None:
    """Extract the optional env field as a mapping of strings."""
    env_value = raw.get("env")
    if env_value is None:
        return None
    if not isinstance(env_value, Mapping):
        msg = "'env' must be provided as a mapping of string pairs"
        raise MCPConfigError(msg)

    env_map: dict[str, str] = {}
    env_mapping = cast("Mapping[Any, Any]", env_value)
    for key_obj, value_obj in env_mapping.items():
        if not isinstance(key_obj, str) or not isinstance(value_obj, str):
            msg = "'env' must be a table of string key/value pairs"
            raise MCPConfigError(msg)
        env_map[key_obj] = value_obj
    return env_map


@dataclass(slots=True)
class McpServerEntry:
    """Representation of a configured MCP server."""

    command: str
    args: list[str] = field(default_factory=_new_args_list)
    env: dict[str, str] | None = None
    startup_timeout_sec: float | None = None
    tool_timeout_sec: float | None = None
    extras: dict[str, Any] = field(default_factory=_new_extras_dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> McpServerEntry:
        """Create an entry from a TOML mapping."""
        if "command" not in raw or not isinstance(raw["command"], str):
            msg = "MCP server entries must define a 'command' string"
            raise MCPConfigError(msg)

        args_list = _parse_args_field(raw)
        env_map = _parse_env_field(raw)

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
            args=args_list,
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
            data: dict[str, Any] = tomllib.load(fh)
            return data
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
    raw_servers_value = raw_config.get(_MCP_SECTION)

    if raw_servers_value in (None, {}):
        return {}

    if not isinstance(raw_servers_value, Mapping):
        msg = f"'{_MCP_SECTION}' section must be a table in the config file"
        raise MCPConfigError(msg)

    servers: dict[str, McpServerEntry] = {}
    raw_servers = cast("Mapping[Any, Any]", raw_servers_value)

    for name_obj, entry_obj in raw_servers.items():
        if not isinstance(name_obj, str):
            msg = "Server names must be strings"
            raise MCPConfigError(msg)
        name = name_obj
        if not isinstance(entry_obj, Mapping):
            msg = f"MCP server '{name}' must be a table"
            raise MCPConfigError(msg)
        entry_mapping = cast("Mapping[str, Any]", entry_obj)
        servers[name] = McpServerEntry.from_mapping(entry_mapping)

    return servers


def save_mcp_server(name: str, entry: McpServerEntry) -> None:
    """Insert or update an MCP server entry."""
    raw_config = _load_raw_config()
    raw_servers_value = raw_config.get(_MCP_SECTION)
    if raw_servers_value is None:
        raw_servers: dict[str, Any] = {}
    elif not isinstance(raw_servers_value, Mapping):
        msg = f"'{_MCP_SECTION}' section must be a table in the config file"
        raise MCPConfigError(msg)
    else:
        raw_servers = dict(cast("Mapping[str, Any]", raw_servers_value))

    raw_servers[name] = entry.to_mapping()

    updated_config = dict(raw_config)
    updated_config[_MCP_SECTION] = raw_servers

    _write_raw_config(updated_config)


def remove_mcp_server(name: str) -> bool:
    """Remove an MCP server entry by name."""
    raw_config = _load_raw_config()
    raw_servers_value = raw_config.get(_MCP_SECTION)
    if raw_servers_value is None:
        return False
    if not isinstance(raw_servers_value, Mapping):
        msg = f"'{_MCP_SECTION}' section must be a table in the config file"
        raise MCPConfigError(msg)

    mutable_servers = dict(cast("Mapping[str, Any]", raw_servers_value))
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
