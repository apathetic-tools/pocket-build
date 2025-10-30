# src/pocket_build/config.py


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
    BuildConfig,
    RootConfig,
)
from .utils import load_jsonc, plural, remove_path_in_error_message
from .utils_schema import ValidationSummary
from .utils_types import cast_hint, schema_from_typeddict
from .utils_using_runtime import log


def can_run_configless(args: argparse.Namespace) -> bool:
    """To run without config we need at least --include
    or --add-include or a positional include.

    Since this is pre-args normalization we need to still check
    positionals and not assume the positional out doesn't improperly
    greed grab the include.
    """
    return bool(
        getattr(args, "include", None)
        or getattr(args, "add_include", None)
        or getattr(args, "positional_include", None)
        or getattr(args, "positional_out", None),
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
    """Locate a configuration file.

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
            xmsg = f"Specified config file not found: {config}"
            raise FileNotFoundError(xmsg)
        if config.is_dir():
            xmsg = f"Specified config path is a directory, not a file: {config}"
            raise ValueError(xmsg)
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
        log(missing_level, f"No config file found in {cwd}")
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
    """Load configuration data from a file.

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
            exec(compile(source, str(config_path), "exec"), config_globals)  # noqa: S102
            log(
                "trace",
                f"[EXEC] globals after exec: {list(config_globals.keys())}",
            )
        except Exception as e:
            tb = traceback.format_exc()
            xmsg = (
                f"Error while executing Python config: {config_path.name}\n"
                f"{type(e).__name__}: {e}\n{tb}"
            )
            # Raise a generic runtime error for main() to catch and print cleanly
            raise RuntimeError(xmsg) from e
        finally:
            # Only remove if we actually inserted it
            if added_to_sys_path and sys.path[0] == parent_dir:
                sys.path.pop(0)

        for key in ("config", "builds", "includes"):
            if key in config_globals:
                result = config_globals[key]
                if not isinstance(result, (dict, list, type(None))):
                    xmsg = (
                        f"{key} in {config_path.name} must be a dict, list, or None"
                        f", not {type(result).__name__}"
                    )
                    raise TypeError(xmsg)

                # Explicitly narrow the loaded config to its expected union type.
                return cast("dict[str, Any] | list[Any] | None", result)

        xmsg = f"{config_path.name} did not define `config` or `builds` or `includes`"
        raise ValueError(xmsg)

    # JSONC / JSON fallback
    try:
        return load_jsonc(config_path)
    except ValueError as e:
        clean_msg = remove_path_in_error_message(str(e), config_path)
        xmsg = (
            f"Error while loading configuration file '{config_path.name}': {clean_msg}"
        )
        raise ValueError(xmsg) from e


def _parse_case_2_list_of_strings(
    raw_config: list[str],
) -> dict[str, Any]:
    # --- Case 2: naked list of strings → single build's include ---
    return {"builds": [{"include": list(raw_config)}]}


def _parse_case_3_list_of_dicts(
    raw_config: list[dict[str, Any]],
) -> dict[str, Any]:
    # --- Case 3: naked list of dicts (no root) → multi-build shorthand ---
    root: dict[str, Any]  # type it once
    builds = [dict(b) for b in raw_config]

    # Lift watch_interval from the first build that defines it (convenience),
    # then remove it from ALL builds to avoid ambiguity.
    first_watch = next(
        (b.get("watch_interval") for b in builds if "watch_interval" in b),
        None,
    )
    root = {"builds": builds}
    if first_watch is not None:
        root["watch_interval"] = first_watch
        for b in builds:
            b.pop("watch_interval", None)
    return root


def _parse_case_4_dict_multi_builds(
    raw_config: dict[str, Any],
    *,
    build_val: Any,
) -> dict[str, Any]:
    # --- Case 4: dict with "build(s)" key → root with multi-builds ---
    root = dict(raw_config)  # preserve all user keys

    # we might have a "builds" key that is a list, then nothing to do

    # If user used "build" with a list → coerce, warn
    if isinstance(build_val, list) and "builds" not in raw_config:
        log("warning", "Config key 'build' was a list — treating as 'builds'.")
        root["builds"] = build_val
        root.pop("build", None)

    return root


def _parse_case_5_dict_single_build(
    raw_config: dict[str, Any],
    *,
    builds_val: Any,
) -> dict[str, Any]:
    # --- Case 5: dict with "build(s)" key → root with single-build ---
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


def _parse_case_6_root_single_build(
    raw_config: dict[str, Any],
) -> dict[str, Any]:
    # --- Case 6: single build fields (hoist only shared keys) ---
    # The user gave a flat single-build config.
    # We move only the overlapping fields (shared between Root and Build)
    # up to the root; all build-only fields stay inside the build entry.
    build = dict(raw_config)
    hoisted: dict[str, Any] = {}

    # Keys on both Root and Build are what we want to hoist up
    root_keys = set(schema_from_typeddict(RootConfig))
    build_keys = set(schema_from_typeddict(BuildConfig))
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
    root: dict[str, Any] = dict(hoisted)
    root["builds"] = [build]

    return root


def parse_config(  # noqa: PLR0911
    raw_config: dict[str, Any] | list[Any] | None,
) -> dict[str, Any] | None:
    """Normalize user config into canonical RootConfig shape (no filesystem work).

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

    # --- Case 1: empty config → one blank build ---
    # Includes None (empty file / config = None), [] (no builds), and {} (empty object)
    if not raw_config or raw_config == {}:  # handles None, [], {}
        return None

    # --- Case 2: naked list of strings → single build's include ---
    if isinstance(raw_config, list) and all(isinstance(x, str) for x in raw_config):
        return _parse_case_2_list_of_strings(raw_config)

    # --- Case 3: naked list of dicts (no root) → multi-build shorthand ---
    if isinstance(raw_config, list) and all(isinstance(x, dict) for x in raw_config):
        return _parse_case_3_list_of_dicts(raw_config)

    # --- better error message for mixed lists ---
    if isinstance(raw_config, list):
        xmsg = (
            "Invalid mixed-type list: "
            "all elements must be strings or all must be objects."
        )
        raise TypeError(xmsg)

    # --- From here on, must be a dict ---
    # Defensive check: should be unreachable after list cases above,
    # but kept to guard against future changes or malformed input.
    if not isinstance(raw_config, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
        xmsg = (
            f"Invalid top-level value: {type(raw_config).__name__} "
            "(expected object, list of objects, or list of strings)",
        )
        raise TypeError(xmsg)

    builds_val = raw_config.get("builds")
    build_val = raw_config.get("build")

    # --- Case 4: dict with "build(s)" key → root with multi-builds ---
    if isinstance(builds_val, list) or (
        isinstance(build_val, list) and "builds" not in raw_config
    ):
        return _parse_case_4_dict_multi_builds(
            raw_config,
            build_val=build_val,
        )

    # --- Case 5: dict with "build(s)" key → root with single-build ---
    if isinstance(build_val, dict) or isinstance(builds_val, dict):
        return _parse_case_5_dict_single_build(
            raw_config,
            builds_val=builds_val,
        )

    # --- Case 6: single build fields (hoist only shared keys) ---
    return _parse_case_6_root_single_build(
        raw_config,
    )


def _validation_summary(
    summary: ValidationSummary,
    config_path: Path,
) -> None:
    """Pretty-print a validation summary using the standard log() interface."""
    mode = "strict mode" if summary.strict else "lenient mode"

    # --- Build concise counts line ---
    counts: list[str] = []
    if summary.errors:
        counts.append(f"{len(summary.errors)} error{plural(summary.errors)}")
    if summary.strict_warnings:
        counts.append(
            f"{len(summary.strict_warnings)} strict warning"
            f"{plural(summary.strict_warnings)}",
        )
    if summary.warnings:
        counts.append(
            f"{len(summary.warnings)} normal warning{plural(summary.warnings)}",
        )
    counts_msg = f"\nFound {', '.join(counts)}." if counts else ""

    # --- Header (single icon) ---
    if not summary.valid:
        log(
            "error",
            f"Failed to validate configuration file {config_path.name} ({mode})."
            + counts_msg,
        )
    elif counts:
        log(
            "warning",
            f"Validated configuration file {config_path.name} ({mode}) with warnings."
            + counts_msg,
        )
    else:
        log("debug", f"Validated {config_path.name} ({mode}) successfully.")

    # --- Detailed sections ---
    if summary.errors:
        log("error", "\nErrors:\n  • " + "\n  • ".join(summary.errors))
    if summary.strict_warnings:
        log(
            "error",
            "\nStrict warnings (treated as errors):\n"
            "  • " + "\n  • ".join(summary.strict_warnings),
        )
    if summary.warnings:
        log(
            "warning",
            "\nWarnings (non-fatal):\n  • " + "\n  • ".join(summary.warnings),
        )


def load_and_validate_config(
    args: argparse.Namespace,
) -> tuple[Path, RootConfig] | None:
    """Find, load, parse, and validate the user's configuration.

    Also determines the effective log level (from CLI/env/config/default)
    early, so logging can initialize as soon as possible.

    Returns:
        (config_path, root_cfg) if a config file was found and valid,
        or None if no config was found.

    """
    # --- initialize logging wihtout config ---
    current_runtime["log_level"] = determine_log_level(args)

    # warn if cwd doesn't exist, edge case. We might still be able to run
    cwd = Path.cwd().resolve()
    if not cwd.exists():
        log("warning", f"Working directory does not exist: {cwd}")

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
        xmsg = f"Could not parse config {config_path.name}: {e}"
        raise TypeError(xmsg) from e
    if parsed_cfg is None:
        return None

    # --- Validate schema ---
    validation_result = validate_config(parsed_cfg)
    _validation_summary(validation_result, config_path)
    if not validation_result.valid:
        xmsg = f"Configuration file {config_path.name} contains validation errors."
        exception = ValueError(xmsg)
        exception.silent = True  # type: ignore[attr-defined]
        exception.data = validation_result  # type: ignore[attr-defined]
        raise exception

    # --- Upgrade to RootConfig type ---
    root_cfg: RootConfig = cast_hint(RootConfig, parsed_cfg)
    return config_path, root_cfg
