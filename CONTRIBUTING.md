# 🧩 Contributing Guide

Thanks for your interest in contributing to **pocket-build** — a tiny build system that fits in your pocket.  
This document explains how to set up your environment, run checks, and contribute safely.

---

## 🐍 Python Version

We currently target **Python 3.10** as the minimum supported version.

As of **2025-10-10**, here’s the Python landscape across common systems:

| Platform | Default Python | Notes |
|-----------|----------------|-------|
| **Ubuntu 20.04 LTS** (EOL April 2025) | **3.8** | Now out of standard support. |
| **Ubuntu 22.04 LTS** (widely used, esp. CI) | **3.10** | Default interpreter; supported until 2027. |
| **Ubuntu 24.04 LTS** (current default) | **3.12** | Default on new installations. |
| **macOS** (Homebrew / Python.org / CLT) | **3.12** | Must be user-installed — not preinstalled. |
| **Windows (Microsoft Store)** | **3.12** | Microsoft’s officially recommended LTS line. |
| **GitHub Actions `ubuntu-latest`** | **3.10 → 3.12** | Currently transitioning; both available. |
| **Python.org LTS** | **3.12** | Mainstream support → 2028  ·  Security → 2030 |

> ℹ️ Note: `pytest` and most modern tools now require Python 3.9 or newer.

---

## 🧰 Poetry Setup

We use **[Poetry](https://python-poetry.org/)** to manage the development environment and dependencies.  
The *production script itself has zero runtime dependencies.*

### Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
poetry --version
```

If you get `poetry: command not found`, ensure it’s on your `PATH`.  
Append this to your shell config (`~/.bashrc` or `~/.bash_profile`):

```bash
# poetry
export POETRY_HOME="$HOME/.local/bin"
case ":$PATH:" in
  *":$POETRY_HOME:"*) ;;
  *) export PATH="$POETRY_HOME:$PATH" ;;
esac
# poetry end
```

---

## ⚙️ Development Dependencies

All development tools are isolated in the **dev group**.  
To install them:

```bash
poetry install --with dev
```

No dependencies are required for users of the final `pocket-build.py` script — only for maintainers.

---

## 🧪 Development Workflow

Run static checks, type checking, and formatting:

```bash
poetry run poe check
```

Attempt to fix errors and format code automatically:

```bash
poetry run poe fix
```

Bundle:

```bash
poetry run poe bundle
```

---

## 🪶 Contribution Notes

- Follow [PEP 8](https://peps.python.org/pep-0008/) style (enforced by Ruff).  
- Keep the **main script dependency-free** — dev tools only in Poetry’s `dev` group.  
- Run `poetry run poe check` before committing.  
- Open pull requests against the **`main`** branch.

---

**Thank you for helping keep `pocket-build` tiny, portable, and delightful.**


## to-add

we want both a PyPI and a bin/ executable script using `poetry run po bundle`

```
poetry build
poetry publish
```