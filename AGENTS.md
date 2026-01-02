# Repository Guidelines

## Project Structure & Module Organization

The repository is a Python monorepo with multiple packages. Core package live in
`pkgs/mahos/`, with additional packages in `pkgs/mahos-dq/` and `pkgs/mahos-dq-ext/`.
Each package uses the src-layout.
Tests are under `tests/` (e.g., `tests/mahos/test_*.py`), and example configs and usage
are in `examples/`. Sphinx documentation sources live in `docs-src/` and build
to `docs/`. Non-code contents in `misc/` can be ignored safely.

## Build, Test, and Development Commands

- `pip install -e ./pkgs/mahos`, `pip install -e ./pkgs/mahos-dq`,
  and `pip install -e ./pkgs/mahos-dq-ext`: build and install all the packages.
  (`-e` option may be removed if necessary.)
- `make test` (or `pytest --timeout=10`): run the test suite with timeouts.
- `make lint`: run flake8 across the repo.
- `make format`: format Python code with Black.
- `make docs`: build Sphinx HTML docs from `docs-src/` into `docs/`.
- `make browse`: open the built docs in a browser.

## Coding Style & Naming Conventions

Python code follows Black with a line length of 99 and flake8 with the same
limit. Indentation is 4 spaces. Use PEP 8 naming: `snake_case` for functions and
variables, `PascalCase` for classes, and `UPPER_CASE` for constants. Generated UI
code in `pkgs/mahos/src/mahos/gui/ui` and `pkgs/mahos-dq/src/mahos_dq/gui/ui` is excluded
from formatting and linting.

## Testing Guidelines

Tests use pytest and live in `tests/`. Name tests `test_*.py` and focus new unit
tests on the module you change. Run targeted tests with `pytest tests/mahos/test_x.py`
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
