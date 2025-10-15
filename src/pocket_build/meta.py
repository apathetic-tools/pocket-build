# src/pocket_build/meta.py

"""Centralized program identity constants for Pocket Build."""

_BASE = "pocket-build"

# CLI script name (the executable or `poetry run` entrypoint)
PROGRAM_SCRIPT = _BASE

# Human-readable name for banners, help text, etc.
PROGRAM_DISPLAY = _BASE.replace("-", " ").title()

# Python package / import name
PROGRAM_PACKAGE = _BASE.replace("-", "_")

# Environment variable prefix (used for POCKET_BUILD_LOG_LEVEL, etc.)
PROGRAM_ENV = _BASE.replace("-", "_").upper()

# Short tagline or description for help screens and metadata
DESCRIPTION = "A tiny build system that fits in your pocket."
