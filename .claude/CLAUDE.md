# pocket-build Project Context

A tiny build system that fits in your pocket.

This project can be deployed in two ways:
1. As a standard Python package (installed via pip/poetry)
2. As a single-file executable script (bin/pocket-build.py)

## Key Conventions

- **Use poe tasks** for all common operations:
  - `poetry run poe check` - Run linting, type checking, and tests
  - `poetry run poe fix` - Auto-format and fix linting issues
  - `poetry run poe test` - Run test suite
  - `poetry run poe check:fix` - Fix, type check, and test (run before committing)
  - `poetry run poe build:script` - Generate the single-file bin/pocket-build.py

- **Code quality standards:**
  - Strict Ruff (linting) and Mypy (type checking) compliance required
  - Code must pass both Pylance (IDE) and Mypy (CI) type checking
  - Target Python 3.10+ compatibility
  - All changes must pass `poetry run poe check:fix`

- **Important files:**
  - `bin/pocket-build.py` is **generated** - never edit directly
  - Generate it using `poetry run poe build:script` (runs `python dev/make_script.py`)

## Project Structure

- `src/pocket_build/` - Main source code
- `bin/pocket-build.py` - Generated single-file executable (do not edit directly)
- `tests/` - Test suite
- `dev/` - Development scripts and build tools
  - `dev/make_script.py` - Script generator
