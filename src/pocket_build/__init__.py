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
from .utils import is_excluded, load_jsonc

__all__ = [
    "copy_file",
    "copy_directory",
    "copy_item",
    "run_build",
    "main",
    "parse_builds",
    "is_excluded",
    "load_jsonc",
    "BuildConfig",
]
