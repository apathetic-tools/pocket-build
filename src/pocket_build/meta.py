# src/pocket_build/meta.py

"""Centralized program identity constants for Pocket Build."""

from dataclasses import dataclass


_BASE = "pocket-build"

# CLI script name (the executable or `poetry run` entrypoint)
PROGRAM_SCRIPT = _BASE

# config file name
PROGRAM_CONFIG = _BASE

# Human-readable name for banners, help text, etc.
PROGRAM_DISPLAY = _BASE.replace("-", " ").title()

# Python package / import name
PROGRAM_PACKAGE = _BASE.replace("-", "_")

# Environment variable prefix (used for POCKET_BUILD_LOG_LEVEL, etc.)
PROGRAM_ENV = _BASE.replace("-", "_").upper()

# Short tagline or __DESCRIPTION for help screens and metadata
DESCRIPTION = "A tiny build system that fits in your pocket."


@dataclass(frozen=True)
class Metadata:
    """Lightweight result from get_metadata(), containing version and commit info."""

    version: str
    commit: str

    def __str__(self) -> str:
        return f"{self.version} ({self.commit})"
