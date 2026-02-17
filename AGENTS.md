# Repository Guidelines

## Project Structure & Module Organization

The repository is a Python monorepo with multiple packages. Core package lives in
`pkgs/mahos/`, with additional packages in `pkgs/mahos-dq/` and `pkgs/mahos-dq-ext/`.
Each package uses the src-layout.
Tests are under `tests/` (e.g., `tests/mahos/test_*.py`), and example configs and usage
are in `examples/`. Sphinx documentation sources live in `docs-src/` and build to `docs/`.
Ignore following directories when inspecting or editing:
- `docs/`: generated documentation.
- `misc/`: miscellaneous files which are not directly related to codes or documents.

## Build, Test, and Development Commands

- `pip install -e './pkgs/mahos[dev]' -e ./pkgs/mahos-dq` (or `make install-dev`):
  install core packages for development and testing.
- `pip install -e ./pkgs/mahos-dq-ext`: install optional C extension package
  when extension features are needed.
  (`-e` option may be removed if necessary.)
- `make test` (or `pytest --timeout=10`): run the test suite with timeouts.
- `make lint`: run flake8 with configured excludes
  (`build`, `tests`, and generated UI code).
- `make format`: format Python code with Black.
- `make docs`: build Sphinx HTML docs from `docs-src/` into `docs/`.
- `make browse`: open the built docs in a browser.

## Coding Style & Naming Conventions

Python code follows Black with a line length of 99 and flake8 with the same
limit. Indentation is 4 spaces. Use PEP 8 naming: `snake_case` for functions and
variables, `PascalCase` for classes, and `UPPER_CASE` for constants. Generated UI
code in `pkgs/mahos/src/mahos/gui/ui` and `pkgs/mahos-dq/src/mahos_dq/gui/ui` is excluded
from formatting and linting.

## Docstring Guidelines

- Write all docstrings in reStructuredText (reST).
- Provide comprehensive top-level class docstrings for all `Instrument`, `Node`,
  `GUINode`, and `Message` classes.
- For measurement Nodes with exactly one Worker, the Worker docstring may be omitted if the
  Worker behavior is documented in the Node docstring.
- For measurement Nodes with multiple Workers, each Worker should have its own docstring, and
  the Node docstring should link to those Worker docstrings. Use
  `pkgs/mahos-dq/src/mahos_dq/meas/odmr.py` (ODMR Node) as a reference pattern.
- Structure top-level class docstrings in this order:
  - A one-line summary, followed by a blank line.
  - A few paragraphs with detailed behavior and important requirements (for example,
    required dependent libraries), when applicable.
  - For the `Instrument`, `Node`, and `GUINode` classes, a list of static configuration keys in
    `self.conf` (loaded from `conf.toml`), using `:param:` and `:type:` directives.
    - For nested configuration dictionaries, express nested keys with dot notation
      (for example, `first_level_key.second_level_key`).
  - For the `Message` classes, the list of attributes using `:ivar:` directive.
  - Optional minor notes may follow, but use them sparingly.

## Testing Guidelines

Tests use pytest and live in `tests/`. Name tests `test_*.py` and focus new unit
tests on the module you change. Run targeted tests with `pytest tests/mahos/test_x.py`
or the full suite with `make test`. An example configuration for tests is in
`tests/conf.toml`.

## Commit & Pull Request Guidelines

Use a short, imperative first line for commit subjects. Scope prefixes are
recommended when applicable:
- `docs:` for documentation-only patches.
- `ClassName:` when the patch primarily affects a specific class.
- `module_name:` when the patch is module-wide.

For large patches, add a commit body with a bullet list describing the key
changes. Keep the summary concise and lower case where natural. For pull
requests, include a clear summary, the testing you ran (commands and results),
and links to any related issues. Add screenshots or GIFs when UI changes are
involved, and note documentation updates when behavior or configuration changes.
Do not use backticks in commit subjects or commit bodies.

## Configuration & Examples

MAHOS is configuration-driven. Use the examples in `examples/` and the sample
`tests/conf.toml` as starting points for local experiments or new setups.
