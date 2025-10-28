# src/pocket_build/__init__.py

"""
Pocket Build — a tiny build system that fits in your pocket.

Full developer API
==================
This package re-exports all non-private symbols from its submodules,
making it suitable for programmatic use, custom integrations, or plugins.
Anything prefixed with "_" is considered internal and may change.

Highlights:
    - main()              → CLI entrypoint
    - run_build()         → Execute a build configuration
    - resolve_config()    → Merge CLI args with config files
    - get_metadata()      → Retrieve version / commit info
"""

from .actions import (
    get_metadata,
    run_selftest,
    watch_for_changes,
)
from .build import (
    copy_directory,
    copy_file,
    copy_item,
    run_all_builds,
    run_build,
)
from .cli import (
    main,
)
from .config import (
    find_config,
    load_and_validate_config,
    load_config,
    parse_config,
)
from .config_resolve import resolve_build_config, resolve_config
from .config_validate import validate_config
from .constants import (
    DEFAULT_ENV_LOG_LEVEL,
    DEFAULT_ENV_RESPECT_GITIGNORE,
    DEFAULT_ENV_WATCH_INTERVAL,
    DEFAULT_LOG_LEVEL,
    DEFAULT_OUT_DIR,
    DEFAULT_RESPECT_GITIGNORE,
    DEFAULT_STRICT_CONFIG,
    DEFAULT_WATCH_INTERVAL,
)
from .meta import (
    PROGRAM_DISPLAY,
    PROGRAM_ENV,
    PROGRAM_PACKAGE,
    PROGRAM_SCRIPT,
    Metadata,
)
from .runtime import current_runtime
from .types import (
    BuildConfig,
    BuildConfigInput,
    IncludeResolved,
    MetaBuildConfig,
    OriginType,
    PathResolved,
    RootConfig,
    RootConfigInput,
    Runtime,
)
from .utils import (
    load_jsonc,
    should_use_color,
)
from .utils_types import (
    make_includeresolved,
    make_pathresolved,
    safe_isinstance,
    schema_from_typeddict,
)
from .utils_using_runtime import (
    LEVEL_ORDER,
    RESET,
    colorize,
    get_glob_root,
    has_glob_chars,
    is_bypass_capture,
    is_excluded,
    is_excluded_raw,
    log,
)

__all__ = [
    # --- CLI / Actions ---
    "main",
    "get_metadata",  # verison info
    "run_selftest",
    "watch_for_changes",
    #
    # --- Build Engine ---
    "run_all_builds",
    "run_build",
    "copy_item",
    "copy_directory",
    "copy_file",
    #
    # --- Config Handling ---
    "resolve_config",
    "resolve_build_config",
    "load_and_validate_config",
    "find_config",
    "load_config",
    "parse_config",
    "validate_config",
    #
    # --- Constants / Metadata / Runtime ---
    "DEFAULT_ENV_LOG_LEVEL",
    "DEFAULT_ENV_RESPECT_GITIGNORE",
    "DEFAULT_ENV_WATCH_INTERVAL",
    "DEFAULT_LOG_LEVEL",
    "DEFAULT_OUT_DIR",
    "DEFAULT_RESPECT_GITIGNORE",
    "DEFAULT_STRICT_CONFIG",
    "DEFAULT_WATCH_INTERVAL",
    "PROGRAM_DISPLAY",
    "PROGRAM_ENV",
    "PROGRAM_PACKAGE",
    "PROGRAM_SCRIPT",
    "Metadata",
    "current_runtime",
    #
    # --- utils ---
    "LEVEL_ORDER",
    "RESET",
    "colorize",
    "get_glob_root",
    "has_glob_chars",
    "is_bypass_capture",
    "is_excluded",
    "is_excluded_raw",
    "load_jsonc",
    "log",
    "make_includeresolved",
    "make_pathresolved",
    "safe_isinstance",
    "schema_from_typeddict",
    "should_use_color",
    #
    # --- Types ---
    "BuildConfig",
    "BuildConfigInput",
    "IncludeResolved",
    "MetaBuildConfig",
    "OriginType",
    "PathResolved",
    "RootConfig",
    "RootConfigInput",
    "Runtime",
]
