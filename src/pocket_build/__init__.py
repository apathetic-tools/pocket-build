# src/pocket_build/__init__.py

# we expose `_` private for testing purposes only
# pyright: reportPrivateUsage=false
# ruff: noqa: F401

"""
Pocket Build — modular entrypoint.
Exports the same surface as the single-file bundled version,
so that tests and users can use either interchangeably.
"""

from .build import copy_directory, copy_file, copy_item, run_build  # Engine
from .cli import (  # CLI; Engine; Tests
    _collect_included_files,
    find_config,
    get_metadata,
    load_config,
    main,
    resolve_build_config,
    run_all_builds,
    run_selftest,
    watch_for_changes,
)
from .config import parse_builds  # CLI
from .meta import PROGRAM_DISPLAY, PROGRAM_ENV, PROGRAM_SCRIPT, Metadata  # CLI; Utils
from .runtime import current_runtime  # Utils
from .types import (  # Utils
    BuildConfig,
    IncludeEntry,
    MetaBuildConfig,
    RootConfig,
    Runtime,
)
from .utils_core import (  # Utils; Engine
    get_glob_root,
    has_glob_chars,
    is_excluded,
    load_jsonc,
    should_use_color,
)
from .utils_runtime import (  # Utils; Tests
    LEVEL_ORDER,
    RESET,
    colorize,
    is_bypass_capture,
    log,
)

__all__ = [
    # === CLI Layer API ===
    # --- cli ---
    "main",
    "get_metadata",  # verison info
    "find_config",  # which config will we use?
    "load_config",  # into a generic structure
    "resolve_build_config",  # cli overrides and normalize paths of a build config
    "watch_for_changes",  # watch mode
    "run_all_builds",  # execute
    # --- config ---
    "parse_builds",  # takes generic structure and molds it into our type
    # === Misc / Util ===
    # --- meta ---
    "PROGRAM_SCRIPT",
    "PROGRAM_DISPLAY",
    "PROGRAM_ENV",
    "Metadata",
    # --- runtime ---
    "current_runtime",
    # --- utils_core ---
    "should_use_color",  # respects tty, env -- but not args
    # --- utils_runtime ---
    "RESET",
    "log",
    "colorize",
    # -- types ---
    #   watch_for_changes, run_all_builds, parse_builds, resolve_build_config
    "BuildConfig",
    "IncludeEntry",  # part of BuildConfig
    "MetaBuildConfig",  # part of BuildConfig
    "Runtime",  # current_runtime
    "RootConfig",  # resolve_build_config
    # === Engine Layer API ===
    # --- cli ---
    "run_selftest",
    # --- build ---
    "copy_directory",  # Recursively copy directory contents, skipping excluded files.
    "copy_file",
    "copy_item",  # Copy a file or directory, respecting excludes and meta base paths.
    "run_build",  # Execute a single build task using a fully resolved config.
    # --- utils_core ---
    "load_jsonc",
    "is_excluded",
    "get_glob_root",  # glob helper
    "has_glob_chars",  # glob helper
    # --- utils_runtime ---
    "LEVEL_ORDER",
    "is_bypass_capture",
    # -- types ---
    # "MetaBuildConfig", # already above # copy_item
    # "BuildConfig", # already above # run_build
    # === Test Layer API ===
    # --- cli ---
    "_collect_included_files",
    # --- types ---
    # "BuildConfig", # already above # _collect_included_files
]
