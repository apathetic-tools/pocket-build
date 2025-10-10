# 🧩 Contributing Guide

Thanks for your interest in contributing to **pocket-build** — the tiny build system that fits in your pocket.  
This guide explains how to set up your environment, run checks, and safely contribute code.

---

## 🐍 Supported Python Versions

Pocket-build targets **Python 3.10+**.  
That keeps compatibility with Ubuntu 22.04 (the baseline CI OS) while staying modern.

| Platform | Default Python | Notes |
|-----------|----------------|-------|
| Ubuntu 22.04 LTS | 3.10 | Minimum supported baseline. |
| Ubuntu 24.04 LTS | 3.12 | Current CI default. |
| macOS (Homebrew / Python.org) | 3.12 | Must be user-installed. |
| Windows (Microsoft Store) | 3.12 | Microsoft’s LTS release. |
| GitHub Actions `ubuntu-latest` | 3.10 → 3.12 | Both available during transition. |

> The build itself has **no runtime dependencies** — only dev tools use Poetry.

---

## 🧰 Setting Up the Environment

We use **[Poetry](https://python-poetry.org/)** for dependency and task management.

### 1️⃣ Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
poetry --version
```

If Poetry isn’t on your `PATH`, add it to your shell configuration (usually `~/.bashrc` or `~/.zshrc`):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### 2️⃣ Install Dependencies

```bash
poetry install --with dev
```

This creates an isolated virtual environment with Ruff, Mypy, pytest, and Poe tasks.

---

## ⚙️ Development Commands

All key workflows are defined in **`[tool.poe.tasks]`** inside `pyproject.toml`.

| Command | Description |
|----------|-------------|
| `poetry run poe check.fix` | Auto-fix issues, re-format, type-check, and re-test. |
| `poetry run poe check` | Run linting (`ruff`), type checks (`mypy`), and tests (`pytest`). |
| `poetry run poe fix` | Run all auto-fixers (Ruff + formatter). |
| `poetry run poe build.single` | Bundle the project into a single portable script in `bin/`. |

Example workflow:

```bash
# Run full check
poetry run poe check

# Auto-fix & re-check
poetry run poe check.fix
```

---

## 🔗 Pre-commit Hook

Pre-commit is configured to run `poe check` before every commit.

Install the hook once:

```bash
poetry run pre-commit install
```

Manually trigger it on all files anytime:

```bash
poetry run pre-commit run --all-files
```

If any linter, type check, or test fails, the commit is blocked — fix with:

```bash
poetry run poe check.fix
```

### 🧩 Fixing the `setlocale` Warning

If your terminal or Git log shows:

```
bash: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)
```

it means your system doesn’t have the `en_US.UTF-8` locale generated.

Run the following commands in your terminal:

```bash
sudo locale-gen en_US.UTF-8
sudo update-locale LANG=en_US.UTF-8
```

Then restart your shell or VS Code terminal.

---

## 🧪 Testing

Run the test suite directly:

```bash
poetry run poe test
```

Pytest will discover all files in `tests/` automatically.

---

## 📦 Building and Publishing (for maintainers)

Pocket-build ships two forms:

| Target | Command | Output |
|---------|----------|--------|
| **Single-file script** | `poetry run poe build.single` | Creates `bin/pocket-build.py` |
| **PyPI package** | `poetry build && poetry publish` | Builds and uploads wheel & sdist |

To publish:

```bash
poetry build
poetry publish --username __token__ --password <your-pypi-token>
```

> Verify the package on [Test PyPI](https://test.pypi.org/) before publishing live.

---

## 🪶 Contribution Rules

- Follow [PEP 8](https://peps.python.org/pep-0008/) (enforced via Ruff).  
- Keep the **core script dependency-free** — dev tooling lives only in `pyproject.toml`’s `dev` group.  
- Run `poetry run poe check` before committing.  
- Open PRs against the **`main`** branch.  
- Be kind: small tools should have small egos.

---

**Thank you for helping keep pocket-build tiny, dependency-free, and delightful.**
