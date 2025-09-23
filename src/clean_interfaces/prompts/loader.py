"""Utilities for loading bundled agent prompts."""

from importlib import resources
from pathlib import Path

from clean_interfaces.utils.file_handler import FileHandler


def load_prompt(name: str, *, file_handler: FileHandler | None = None) -> str:
    """Load a prompt template bundled with the package."""
    handler = file_handler or FileHandler()
    resource = resources.files(__package__).joinpath(f"{name}.md")

    if not resource.is_file():
        message = f"Prompt '{name}' was not found."
        raise FileNotFoundError(message)

    with resources.as_file(resource) as resolved_path:
        path = Path(resolved_path)
        return handler.read_text(path)


__all__ = ["load_prompt"]

