"""Prompt loading utilities for the Clean Interfaces agents."""

from importlib import resources


def load_prompt(name: str) -> str:
    """Load a prompt template bundled with the package."""
    prompt_path = resources.files(__package__).joinpath(f"{name}.md")
    with prompt_path.open("r", encoding="utf-8") as prompt_file:
        return prompt_file.read()


__all__ = ["load_prompt"]

