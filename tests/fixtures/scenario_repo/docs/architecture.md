# Architecture Overview

The project follows a simple `src/`-layout package with a single module. The
`sample_package.calculator` module exposes arithmetic helpers that Scenario
agents are expected to modify during tests.

Key expectations for Scenario runs:

- Repository QA agents should read this document and summarise the location of
  the intentionally broken `multiply` implementation and its associated tests.
- Coding agents should edit `src/sample_package/calculator.py` and run
  `pytest -q` to ensure the suite in `tests/test_calculator.py` passes.
- Workflow agents should orchestrate exploration, test authoring, and
  implementation steps using the provided instructions.
