# src/pocket_build/__init__.py

"""Pocket Build — a tiny build system that fits in your pocket.

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
from .config_types import (
    BuildConfig,
    BuildConfigResolved,
    IncludeResolved,
    MetaBuildConfigResolved,
    OriginType,
    PathResolved,
    RootConfig,
    RootConfigResolved,
)
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
from .runtime import Runtime, current_runtime
from .utils import (
    load_jsonc,
    should_use_color,
)
from .utils_logs import (
    LEVEL_ORDER,
    RESET,
    colorize,
    log,
)
from .utils_types import (
    make_includeresolved,
    make_pathresolved,
    safe_isinstance,
    schema_from_typeddict,
)
from .utils_using_runtime import (
    get_glob_root,
    has_glob_chars,
    is_excluded,
    is_excluded_raw,
)


__all__ = [  # noqa: RUF022
    # --- CLI / Actions ---
    "get_metadata",  # verison info
    "main",
    "run_selftest",
    "watch_for_changes",
    #
    # --- Build Engine ---
    "copy_directory",
    "copy_file",
    "copy_item",
    "run_all_builds",
    "run_build",
    #
    # --- Config Handling ---
    "find_config",
    "load_and_validate_config",
    "load_config",
    "parse_config",
    "resolve_build_config",
    "resolve_config",
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
    "Metadata",
    "PROGRAM_DISPLAY",
    "PROGRAM_ENV",
    "PROGRAM_PACKAGE",
    "PROGRAM_SCRIPT",
    "current_runtime",
    #
    # --- utils ---
    "LEVEL_ORDER",
    "RESET",
    "colorize",
    "get_glob_root",
    "has_glob_chars",
    "is_excluded_raw",
    "is_excluded",
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
    "BuildConfigResolved",
    "IncludeResolved",
    "MetaBuildConfigResolved",
    "OriginType",
    "PathResolved",
    "RootConfig",
    "RootConfigResolved",
    "Runtime",
]
