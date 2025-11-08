# pocket-build Project Context

A tiny build system that fits in your pocket.

This project can be deployed in two ways:
1. As a standard Python package (installed via pip/poetry)
2. As a single-file executable script (bin/pocket-build.py)

## Key Conventions

- **Use poe tasks** for all common operations:
  - `poe check` - Run linting, type checking, and tests
  - `poe fix` - Auto-format and fix linting issues
  - `poe test` - Run test suite
  - `poe check:fix` - Fix, type check, and test (run before committing)
  - `poe build:script` - Generate the single-file bin/pocket-build.py

- **Code quality standards:**
  - Strict Ruff (linting) and Mypy (type checking) compliance required
  - Code must pass both Pylance (IDE) and Mypy (CI) type checking
  - Target Python 3.10+ compatibility
  - All changes must pass `poe check:fix`

- **Important files:**
  - `bin/pocket-build.py` is **generated** - never edit directly
  - Generate it using `poe build:script` (runs `python dev/make_script.py`)

## Project Structure

- `src/pocket_build/` - Main source code
- `bin/pocket-build.py` - Generated single-file executable (do not edit directly)
- `tests/` - Test suite
- `dev/` - Development scripts and build tools
  - `dev/make_script.py` - Script generator
