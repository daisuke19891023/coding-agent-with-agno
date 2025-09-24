"""Tests for workflow command configuration utilities."""

from __future__ import annotations

import pytest
from typing import TYPE_CHECKING

from clean_interfaces.workflow.test_commands import (
    WorkflowCommandConfig,
    create_manager_from_config,
    load_workflow_command_config,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_load_workflow_command_config_parses_yaml(tmp_path: Path) -> None:
    """It loads lint and test commands with multiple entries."""
    config_path = tmp_path / "commands.yaml"
    config_path.write_text(
        """
        tests:
          pytest:
            - uv run pytest
            - [uv, run, pytest, -k, smoke]
        lint:
          default:
            - [uv, run, ruff, format]
            - uv run ruff check
        """,
        encoding="utf-8",
    )

    config = load_workflow_command_config(config_path)
    assert config.tests["pytest"] == (
        ("uv", "run", "pytest"),
        ("uv", "run", "pytest", "-k", "smoke"),
    )
    assert config.lint["default"] == (
        ("uv", "run", "ruff", "format"),
        ("uv", "run", "ruff", "check"),
    )


def test_create_manager_from_config_respects_category_defaults() -> None:
    """It creates managers with and without default commands appropriately."""
    config = WorkflowCommandConfig(
        tests={"pytest": (("uv", "run", "pytest"),)},
        lint={
            "quality": (
                ("uv", "run", "ruff", "format"),
                ("uv", "run", "ruff", "check"),
            ),
        },
    )

    test_manager = create_manager_from_config(config, category="tests")
    assert test_manager.resolve("pytest") == ("uv", "run", "pytest")

    lint_manager = create_manager_from_config(config, category="lint")
    assert lint_manager.resolve_all("quality") == (
        ("uv", "run", "ruff", "format"),
        ("uv", "run", "ruff", "check"),
    )
    # Ensure the default pytest alias is not automatically added for lint managers.
    assert lint_manager.resolve_all("pytest") == (("pytest",),)


def test_load_workflow_command_config_rejects_invalid_structure(tmp_path: Path) -> None:
    """It raises an error when the YAML structure is not a mapping."""
    config_path = tmp_path / "commands.yaml"
    config_path.write_text("[]", encoding="utf-8")

    with pytest.raises(TypeError, match="configuration must be a mapping"):
        load_workflow_command_config(config_path)

    config_path.write_text(
        """
        tests:
          - not-a-mapping
        """,
        encoding="utf-8",
    )
    with pytest.raises(TypeError, match="tests section must be a mapping"):
        load_workflow_command_config(config_path)
