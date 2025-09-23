# pyright: reportMissingImports=false, reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false
"""Tests for the intentionally flawed calculator module."""

from sample_package.calculator import OperationSummary, add, describe, multiply


def test_add_returns_sum() -> None:
    """Verify the addition helper works as expected."""
    assert add(2, 3) == 5


def test_multiply_returns_product() -> None:
    """Expose the known defect so coding agents must fix it."""
    assert multiply(6, 7) == 42


def test_describe_includes_context() -> None:
    """Ensure the description documents the known defect."""
    summary = describe()
    assert isinstance(summary, OperationSummary)
    assert "defect" in summary.description.lower()
