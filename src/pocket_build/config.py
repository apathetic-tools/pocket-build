# src/pocket_build/config.py
from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path
from typing import Any, cast

from .config_validate import validate_config
from .constants import (
    DEFAULT_LOG_LEVEL,
)
from .meta import (
    PROGRAM_ENV,
    PROGRAM_SCRIPT,
)
from .runtime import current_runtime
from .types import (
    BuildConfigInput,
    RootConfigInput,
)
from .utils import load_jsonc, remove_path_in_error_message
from .utils_types import cast_hint, schema_from_typeddict
from .utils_using_runtime import log


def can_run_configless(args: argparse.Namespace) -> bool:
    """To run without config we need at least --include
    or --add-include or a positional include.

    Since this is pre-args normalization we need to still check
    positionals and not assume the positional out doesn't improperly
    greed grab the include."""
    return bool(
        getattr(args, "include", None)
        or getattr(args, "add_include", None)
        or getattr(args, "positional_include", None)
        or getattr(args, "positional_out", None)
    )


def determine_log_level(
    args: argparse.Namespace,
    root_log_level: str | None = None,
    build_log_level: str | None = None,
) -> str:
    """Resolve log level from CLI → env → build config → root config → default."""
    if getattr(args, "log_level", None):
        return cast_hint(str, args.log_level)

    env_log_level = os.getenv(f"{PROGRAM_ENV}_LOG_LEVEL") or os.getenv("LOG_LEVEL")
    if env_log_level:
        return env_log_level

    if build_log_level:
        return build_log_level

    if root_log_level:
        return root_log_level

    return DEFAULT_LOG_LEVEL


def find_config(
    args: argparse.Namespace,
    cwd: Path,
    *,
    missing_level: str = "error",
) -> Path | None:
    """
    Locate a configuration file.

    missing_level: log-level for failing to find a configuration file.

    Search order:
      1. Explicit path from CLI (--config)
      2. Default candidates in the current working directory:
         .{PROGRAM_SCRIPT}.py, .{PROGRAM_SCRIPT}.jsonc, .{PROGRAM_SCRIPT}.json

    Returns the first matching path, or None if no config was found.
    """

    # NOTE: We only have early no-config Log-Level

    # --- 1. Explicit config path ---
    if getattr(args, "config", None):
        config = Path(args.config).expanduser().resolve()
        if not config.exists():
            # Explicit path → hard failure
            raise FileNotFoundError(f"Specified config file not found: {config}")
        return config

    # --- 2. Default candidate files ---
    candidates: list[Path] = [
        cwd / f".{PROGRAM_SCRIPT}.py",
        cwd / f".{PROGRAM_SCRIPT}.jsonc",
        cwd / f".{PROGRAM_SCRIPT}.json",
    ]
    found = [p for p in candidates if p.exists()]

    if not found:
        # Expected absence — soft failure (continue)
        log(
            missing_level,
            f"No config file found in {cwd}",
        )
        return None

    # --- 3. Handle multiple matches ---
    if len(found) > 1:
        names = ", ".join(p.name for p in found)
        log(
            "warning",
            f"Multiple config files detected ({names}); using {found[0].name}.",
        )
    return found[0]


def load_config(config_path: Path) -> dict[str, Any] | list[Any] | None:
    """
    Load configuration data from a file.

    Supports:
      - Python configs: .py files exporting either `config`, `builds`, or `includes`
      - JSON/JSONC configs: .json, .jsonc files

    Returns:
        The raw object defined in the config (dict, list, or None).
        Returns None for intentionally empty configs
          (e.g. empty files or `config = None`).
    Raises:
        ValueError if a .py config defines none of the expected variables.
    """

    # NOTE: We only have early no-config Log-Level

    # --- Python config ---
    if config_path.suffix == ".py":
        config_globals: dict[str, Any] = {}

        # Allow local imports in Python configs (e.g. from ./helpers import foo)
        # This is safe because configs are trusted user code.
        parent_dir = str(config_path.parent)
        added_to_sys_path = parent_dir not in sys.path
        if added_to_sys_path:
            sys.path.insert(0, parent_dir)

        # Execute the python config file
        try:
            source = config_path.read_text(encoding="utf-8")
            exec(compile(source, str(config_path), "exec"), config_globals)
            log(
                "trace",
                f"[EXEC] globals after exec: {list(config_globals.keys())}",
            )
        except Exception as e:
            tb = traceback.format_exc()
            msg = f"Error while executing Python config: {config_path.name}\n{e}\n{tb}"
            # Raise a generic runtime error for main() to catch and print cleanly
            raise RuntimeError(msg) from e
        finally:
            # Only remove if we actually inserted it
            if added_to_sys_path and sys.path[0] == parent_dir:
                sys.path.pop(0)

        for key in ("config", "builds", "includes"):
            if key in config_globals:
                # Explicitly narrow the loaded config to its expected union type.
                return cast(dict[str, Any] | list[Any] | None, config_globals[key])

        raise ValueError(
            f"{config_path.name} did not define `config` or `builds` or `includes`"
        )

    # JSONC / JSON fallback
    try:
        return load_jsonc(config_path)
    except ValueError as e:
        clean_msg = remove_path_in_error_message(str(e), config_path)
        raise ValueError(
            f"Error while loading configuration file '{config_path.name}': {clean_msg}"
        ) from e


def parse_config(
    raw_config: dict[str, Any] | list[Any] | None,
) -> dict[str, Any] | None:
    """
    Normalize user config into canonical RootConfigInput shape (no filesystem work).

    Accepted forms:
      - #1 [] / {}                   → single build with `include` = []
      - #2 ["src/**", "assets/**"]   → single build with those includes
      - #3 [{...}, {...}]            → multi-build list
      - #4 {"builds": [...]}         → multi-build config (returned shape)
      - #5 {"build": {...}}          → single build config with root config
      - #6 {...}                     → single build config

     After normalization:
      - Always returns {"builds": [ ... ]} (at least one empty {} build).
      - Root-level defaults may be present:
          log_level, out, respect_gitignore, watch_interval.
      - Preserves all unknown keys for later validation.
    """

    # NOTE: This function only normalizes shape — it does NOT validate or restrict keys.
    #       Unknown keys are preserved for the validation phase.

    root: dict[str, Any]  # type it once

    # --- Case 1: empty config → one blank build ---
    # Includes None (empty file / config = None), [] (no builds), and {} (empty object)
    if not raw_config or raw_config == {}:  # handles None, [], {}
        return None

    # --- Case 2: naked list of strings → single build's include ---
    if isinstance(raw_config, list) and all(isinstance(x, str) for x in raw_config):
        return {"builds": [{"include": list(raw_config)}]}

    # --- Case 3: naked list of dicts (no root) → multi-build shorthand ---
    if isinstance(raw_config, list) and all(isinstance(x, dict) for x in raw_config):
        builds = [dict(b) for b in raw_config]

        # Lift watch_interval from the first build that defines it (convenience),
        # then remove it from ALL builds to avoid ambiguity.
        first_watch = next(
            (b.get("watch_interval") for b in builds if "watch_interval" in b), None
        )
        root = {"builds": builds}
        if first_watch is not None:
            root["watch_interval"] = first_watch
            for b in builds:
                b.pop("watch_interval", None)
        return root

    # --- From here on, must be a dict ---
    if not isinstance(raw_config, dict):
        raise TypeError(
            f"Invalid top-level value: {type(raw_config).__name__} "
            "(expected dict, list of dicts, or list of strings)"
        )

    builds_val = raw_config.get("builds")
    build_val = raw_config.get("build")

    # --- Case 4: dict with "build(s)" key → root with multi-builds ---
    if isinstance(builds_val, list) or (
        isinstance(build_val, list) and "builds" not in raw_config
    ):
        root = dict(raw_config)  # preserve all user keys

        # If user used "build" with a list → coerce, warn
        if isinstance(build_val, list) and "builds" not in raw_config:
            log("warning", "Config key 'build' was a list — treating as 'builds'.")
            root["builds"] = build_val
            root.pop("build", None)

        return root

    # --- Case 5: dict with "build(s)" key → root with single-build ---
    if isinstance(build_val, dict) or isinstance(builds_val, dict):
        root = dict(raw_config)  # preserve all user keys

        # If user used "builds" with a dict → coerce, warn
        if isinstance(builds_val, dict):
            log("warning", "Config key 'builds' was a dict — treating as 'build'.")
            root["builds"] = [builds_val]
            # keep the 'builds' key — it's now properly normalized
        else:
            root["builds"] = [dict(root.pop("build"))]

        # no hoisting since they specified a root
        return root

    # --- Case 6: single build fields (hoist only shared keys) ---
    # The user gave a flat single-build config.
    # We move only the overlapping fields (shared between Root and Build)
    # up to the root; all build-only fields stay inside the build entry.
    build = dict(raw_config)
    hoisted: dict[str, Any] = {}

    # Keys on both Root and Build are what we want to hoist up
    root_keys = set(schema_from_typeddict(RootConfigInput))
    build_keys = set(schema_from_typeddict(BuildConfigInput))
    hoist_keys = root_keys & build_keys

    # Move shared keys to the root
    for k in hoist_keys:
        if k in build:
            hoisted[k] = build.pop(k)

    # Preserve any extra unknown root-level fields from raw_config
    for k, v in raw_config.items():
        if k not in hoisted:
            build.setdefault(k, v)

    # Construct normalized root
    root = dict(hoisted)
    root["builds"] = [build]

    return root


def load_and_validate_config(
    args: argparse.Namespace,
) -> tuple[Path, RootConfigInput] | None:
    """
    Find, load, parse, and validate the user's configuration.

    Also determines the effective log level (from CLI/env/config/default)
    early, so logging can initialize as soon as possible.

    Returns:
        (config_path, root_cfg) if a config file was found and valid,
        or None if no config was found.
    """

    # --- initialize logging wihtout config ---
    current_runtime["log_level"] = determine_log_level(args)

    # --- Find config file ---
    cwd = Path.cwd().resolve()
    missing_level = "warning" if can_run_configless(args) else "error"
    config_path = find_config(args, cwd, missing_level=missing_level)
    if config_path is None:
        return None

    # --- Load the raw config (dict or list) ---
    raw_config = load_config(config_path)
    if raw_config is None:
        return None

    # --- Early peek for log_level before parsing ---
    # Handles:
    #   - Root configs with "log_level"
    #   - Single-build dicts with "log_level"
    # Skips empty, list, or multi-build roots.
    if isinstance(raw_config, dict):
        raw_log_level = raw_config.get("log_level")
        if isinstance(raw_log_level, str) and raw_log_level:
            current_runtime["log_level"] = determine_log_level(args, raw_log_level)

    # --- Parse structure into final form without types ---
    try:
        parsed_cfg = parse_config(raw_config)
    except TypeError as e:
        raise TypeError(f"Could not parse config {config_path.name}: {e}") from e
    if parsed_cfg is None:
        return None

    # --- Validate schema ---
    if not validate_config(parsed_cfg):
        # validate_config should already log the failure
        raise ValueError(
            f"Configuration file {config_path.name} contains validation errors."
        )

    # --- Upgrade to RootConfigInput type ---
    root_cfg: RootConfigInput = cast_hint(RootConfigInput, parsed_cfg)
    return config_path, root_cfg
