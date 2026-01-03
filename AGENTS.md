# Repository Guidelines

## Project Structure & Module Organization

The repository is a Python monorepo with multiple packages. Core sources live in
`mahos-core/`, with additional packages in `mahos-dq/` and `mahos-dq-ext/`.
Tests are under `tests/` (e.g., `tests/core/test_*.py`), and example configs and usage
are in `examples/`. Sphinx documentation sources live in `docs-src/` and build
to `docs/`. Miscellaneous tooling and scripts live in `misc/`.

## Build, Test, and Development Commands

- `pip install -e ./mahos-core`, `pip install -e ./mahos-dq`, and `pip install -e ./mahos-dq-ext`: install the all the packages.
- `make test` (or `pytest --timeout=10`): run the test suite with timeouts.
- `make lint`: run flake8 across the repo.
- `make format`: format Python code with Black.
- `make docs`: build Sphinx HTML docs from `docs-src/` into `docs/`.
- `make browse`: open the built docs in a browser.

## Coding Style & Naming Conventions

Python code follows Black with a line length of 99 and flake8 with the same
limit. Indentation is 4 spaces. Use PEP 8 naming: `snake_case` for functions and
variables, `PascalCase` for classes, and `UPPER_CASE` for constants. Generated UI
code in `mahos-core/mahos/core/gui/ui` and `mahos-dq/mahos/dq/gui/ui` is excluded
from formatting and linting.

## Testing Guidelines

Tests use pytest and live in `tests/`. Name tests `test_*.py` and focus new unit
tests on the module you change. Run targeted tests with `pytest tests/test_x.py`
or the full suite with `make test`. An example configuration for tests is in
`tests/conf.toml`.

## Commit & Pull Request Guidelines

Recent history uses short, imperative subjects, sometimes with a scope prefix,
for example `docs: update docs with subpackages` or `workflow/build: fix
installation`. Keep subjects concise and lower case. For pull requests, include
a clear summary, the testing you ran (commands and results), and links to any
related issues. Add screenshots or GIFs when UI changes are involved, and note
documentation updates when behavior or configuration changes.

## Configuration & Examples

MAHOS is configuration-driven. Use the examples in `examples/` and the sample
`tests/conf.toml` as starting points for local experiments or new setups.
