"""Mathematical helpers with an intentionally broken implementation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OperationSummary:
    """Structured summary returned by the calculator helpers."""

    name: str
    description: str


def add(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a + b


def multiply(a: int, b: int) -> int:
    """Return the product of two integers.

    The implementation intentionally returns an incorrect result so that coding
    agents need to edit this file during Scenario tests.
    """
    # Placeholder implementation replaced by coding agents during Scenario tests
    return a + b


def describe() -> OperationSummary:
    """Provide a human readable summary of the operations."""
    return OperationSummary(
        name="Basic arithmetic",
        description=(
            "Provides helpers for adding and multiplying integers. The multiply "
            "function intentionally contains a defect to support Scenario test cases."
        ),
    )
