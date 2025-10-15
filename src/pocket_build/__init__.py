# src/pocket_build/__init__.py
"""
Pocket Build — modular entrypoint.
Exports the same surface as the single-file bundled version,
so that tests and users can use either interchangeably.
"""

from .build import copy_directory, copy_file, copy_item, run_build
from .cli import main
from .config import parse_builds
from .meta import PROGRAM_DISPLAY, PROGRAM_ENV, PROGRAM_SCRIPT
from .runtime import current_runtime
from .types import BuildConfig
from .utils_core import (
    get_glob_root,
    is_excluded,
    load_jsonc,
    should_use_color,
)
from .utils_runtime import (  # is_error_level,; should_log,
    LEVEL_ORDER,
    RESET,
    colorize,
    is_bypass_capture,
    log,
)

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
    # --- meta ---
    "PROGRAM_ENV",
    "PROGRAM_DISPLAY",
    "PROGRAM_SCRIPT",
    # --- types ---
    "BuildConfig",
    # --- utils ---
    "LEVEL_ORDER",
    "RESET",
    "is_bypass_capture",
    # "should_log", # covered by other tests
    # "is_error_level", # covered by other tests
    "log",
    "colorize",
    "is_excluded",
    "load_jsonc",
    "should_use_color",
    "get_glob_root",
    # --- runtime ---
    "current_runtime",
]
