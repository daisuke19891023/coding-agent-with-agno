# Scenario Sample Repository

This repository emulates a small Python project that agents can explore during
Scenario-based end-to-end tests. It intentionally contains a failing test and a
TODO implementation so that coding agents can practice code search, editing, and
test execution workflows.

## Project Overview

- The main package is `sample_package` inside the `src/` directory.
- The `calculator.py` module exposes simple arithmetic helpers and contains a
  `multiply` function with a known defect for agents to fix.
- Tests live under `tests/` and rely on `pytest` with the `src/` directory on the
  import path via `pyproject.toml` configuration.
- `docs/architecture.md` includes background information that repository QA
  agents can summarise.

Agents running against this repository are expected to:

1. Inspect project documentation to understand the requested change.
2. Search for relevant source files and edit them using the available tools.
3. Run the configured pytest suite (`pytest -q`) to verify their work.
4. Provide a clear summary of the modifications and remaining tasks, if any.
