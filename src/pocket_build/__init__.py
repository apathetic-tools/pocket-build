# src/pocket_build/__init__.py
"""
Pocket Build — modular entrypoint.
Exports the same surface as the single-file bundled version,
so that tests and users can use either interchangeably.
"""

from .build import copy_directory, copy_file, copy_item, run_build
from .cli import main
from .config import parse_builds
from .types import BuildConfig
from .utils import RESET, colorize, is_excluded, load_jsonc, should_use_color

__all__ = [
    # --- build ---
    "copy_directory",
    "copy_file",
    "copy_item",
    "run_build",
    # --- cli ---
    "main",
    # --- config ---
    "parse_builds",
    # --- types ---
    "BuildConfig",
    # --- utils ---
    "RESET",
    "colorize",
    "is_excluded",
    "load_jsonc",
    "should_use_color",
]
