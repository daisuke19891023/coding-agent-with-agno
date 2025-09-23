"""Tests for the prompt loading utilities."""

from pathlib import Path

import pytest

from clean_interfaces.prompts.loader import load_prompt
from clean_interfaces.utils.file_handler import FileHandler


class FakeFileHandler(FileHandler):
    """Minimal stub mimicking the FileHandler interface for tests."""

    def __init__(self) -> None:
        """Initialise the stub handler state."""
        super().__init__()
        self.last_path: Path | None = None
        self.calls: int = 0

    def read_text(self, path: Path | str, encoding: str | None = None) -> str:
        """Record the arguments provided to the handler and return fake content."""
        self.calls += 1
        self.last_path = Path(path)
        _ = encoding
        return "fake-content"


def test_load_prompt_reads_using_provided_handler() -> None:
    """The loader should delegate file access to the provided handler."""
    handler = FakeFileHandler()

    content = load_prompt("coding_agent", file_handler=handler)

    assert content == "fake-content"
    assert handler.calls == 1
    assert handler.last_path is not None
    assert handler.last_path.name == "coding_agent.md"


def test_load_prompt_reads_real_prompt() -> None:
    """Reading without a custom handler should return the packaged prompt contents."""
    content = load_prompt("coding_agent")

    assert "Clean Interfaces" in content


def test_load_prompt_missing_file() -> None:
    """Loading a prompt that does not exist should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_prompt("missing_prompt")

