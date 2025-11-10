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
  - `poetry run poe coverage` - Generate code coverage report (dual runtime coverage)
  - `poetry run poe check:fix` - Fix, type check, and test (run before committing)
  - `poetry run poe build:script` - Generate the single-file bin/pocket-build.py

- **Python execution:**
  - Always use `poetry run python3` (not bare `python3`) to ensure execution in the project's virtual environment

- **Code quality standards:**
  - Strict Ruff (linting) and Mypy (type checking) compliance required
  - **Maximum line length: 88 characters (enforced by Ruff)**
  - Code must pass both Pylance (IDE) and Mypy (CI) type checking
  - Target Python 3.10+ compatibility
  - All changes must pass `poetry run poe check:fix`

- **Git commit conventions:**
  - NEVER include Claude Code attribution or Co-Authored-By trailers in commit messages
  - Write clean, conventional commit messages without any AI tool attribution

- **Important files:**
  - `bin/pocket-build.py` is **generated** - never edit directly
  - Generate it using `poetry run poe build:script` (runs `python dev/make_script.py`)

## AI Model Strategy

When identifying tasks that require complex reasoning, planning, or analysis, ask for confirmation before proceeding:

> "This task appears to require significant planning and reasoning. Would you like me to use Claude Sonnet 4.5 to create a detailed execution plan first, then switch to Haiku 4.5 for implementation?"

If confirmed, follow this workflow:
1. **Planning phase**: Use the Task tool with `model: "sonnet"` and `subagent_type: "general-purpose"` to create a detailed execution plan and document the approach
2. **Execution phase**: After receiving the plan, use Claude Haiku 4.5 to implement the plan following the documented steps

This hybrid approach combines Sonnet's superior reasoning for complex problems with Haiku's speed for straightforward implementation.

## Project Structure

- `src/pocket_build/` - Main source code
- `bin/pocket-build.py` - Generated single-file executable (do not edit directly)
- `tests/` - Test suite
- `dev/` - Development scripts and build tools
  - `dev/make_script.py` - Script generator
