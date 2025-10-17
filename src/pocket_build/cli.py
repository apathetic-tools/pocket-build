# src/pocket_build/cli.py
import argparse
import os
import sys
from pathlib import Path
from typing import Any, List, cast

from .actions import get_metadata, run_selftest, watch_for_changes
from .build import run_all_builds
from .config import find_config, load_config, parse_builds, resolve_build_config
from .constants import DEFAULT_WATCH_INTERVAL
from .meta import PROGRAM_DISPLAY, PROGRAM_ENV, PROGRAM_SCRIPT
from .runtime import current_runtime
from .types import RootConfig
from .utils_core import should_use_color
from .utils_runtime import GREEN, RED, colorize, log


def _setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=PROGRAM_SCRIPT)
    parser.add_argument("--include", nargs="+", help="Override include patterns.")
    parser.add_argument("--exclude", nargs="+", help="Override exclude patterns.")
    parser.add_argument("-o", "--out", help="Override output directory.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate build actions without copying or deleting files.",
    )
    parser.add_argument("-c", "--config", help="Path to build config file.")

    parser.add_argument(
        "--add-include",
        nargs="+",
        help="Additional include paths (relative to cwd). Extends config includes.",
    )
    parser.add_argument(
        "--add-exclude",
        nargs="+",
        help="Additional exclude patterns (relative to cwd). Extends config excludes.",
    )

    parser.add_argument(
        "--watch",
        nargs="?",
        type=float,
        metavar="SECONDS",
        default=None,
        help=(
            "Rebuild automatically on changes. "
            "Optionally specify interval in seconds"
            f" (default config or: {DEFAULT_WATCH_INTERVAL}). "
        ),
    )

    gitignore = parser.add_mutually_exclusive_group()
    gitignore.add_argument(
        "--gitignore",
        dest="respect_gitignore",
        action="store_true",
        help="Respect .gitignore when selecting files (default).",
    )
    gitignore.add_argument(
        "--no-gitignore",
        dest="respect_gitignore",
        action="store_false",
        help="Ignore .gitignore and include all files.",
    )
    gitignore.set_defaults(respect_gitignore=None)

    parser.add_argument("--version", action="store_true", help="Show version info.")

    color = parser.add_mutually_exclusive_group()
    color.add_argument(
        "--no-color",
        dest="use_color",
        action="store_const",
        const=False,
        help="Disable ANSI color output.",
    )
    color.add_argument(
        "--color",
        dest="use_color",
        action="store_const",
        const=True,
        help="Force-enable ANSI color output (overrides auto-detect).",
    )
    color.set_defaults(use_color=None)

    log_level = parser.add_mutually_exclusive_group()
    log_level.add_argument(
        "-q",
        "--quiet",
        action="store_const",
        const="warning",
        dest="log_level",
        help="Suppress non-critical output (same as --log-level warning).",
    )
    log_level.add_argument(
        "-v",
        "--verbose",
        action="store_const",
        const="debug",
        dest="log_level",
        help="Verbose output (same as --log-level debug).",
    )
    log_level.add_argument(
        "--log-level",
        choices=["critical", "error", "warning", "info", "debug"],
        default=None,
        dest="log_level",
        help="Set log verbosity level.",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Run a built-in sanity test to verify that the tool works correctly.",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = _setup_parser()
    args = parser.parse_args(argv)

    use_color = args.use_color if args.use_color is not None else should_use_color()
    current_runtime["use_color"] = use_color

    # --- Version flag ---
    if args.version:
        meta = get_metadata()
        # always output
        print(f"{PROGRAM_DISPLAY} {meta.version} ({meta.commit})")
        return 0

    # --- Python version check ---
    if sys.version_info < (3, 10):
        # error before log-level exists
        print(
            colorize(f"❌  {PROGRAM_DISPLAY} requires Python 3.10 or newer.", RED),
            file=sys.stderr,
        )
        return 1

    if args.selftest:
        return 0 if run_selftest() else 1

    # --- Config path handling ---
    cwd = Path.cwd().resolve()
    config_path = find_config(args, cwd)
    if not config_path:
        if args.include or args.add_include:
            # debug before log-level exists
            print(
                colorize("[DEBUG]", GREEN),
                " No config file found — using CLI-only mode.",
                file=sys.stderr,
            )
            raw_config: dict[str, Any] | list[Any] = {}
            config_dir = cwd
        else:
            # error before log-level exists
            print(
                f"❌  No build config found (.{PROGRAM_SCRIPT}.json)"
                " and no includes provided.",
                file=sys.stderr,
            )
            return 1
    else:
        config_dir = config_path.parent.resolve()
        raw_config = load_config(config_path)

    # Narrow the type early so .get() and .items() are valid
    if isinstance(raw_config, list):
        # parse_builds() can handle lists directly; no global fields to inspect
        log("trace", "Config is a list — treating as single build (no root fields).")
        root_cfg: dict[str, Any] = {}
    else:
        root_cfg = raw_config

    # Determine effective log level, from now on use log()
    env_log_level = os.getenv(f"{PROGRAM_ENV}_LOG_LEVEL") or os.getenv("LOG_LEVEL")
    log_level: str
    if args.log_level:
        log_level = args.log_level
    elif env_log_level:
        log_level = env_log_level
    else:
        log_level = root_cfg.get("log_level", "info")
    current_runtime["log_level"] = log_level

    log("trace", f"[RAW CONFIG] {raw_config}")
    builds = parse_builds(raw_config)
    for b in builds:
        if "dry_run" in b:
            log("warning", "Ignoring dry_run field from config (CLI-only).")
            b.pop("dry_run", None)
    log("trace", f"[BUILDS AFTER PARSE] {builds}")

    root_respect_gitignore = root_cfg.get("respect_gitignore", True)

    root_cfg = {k: v for k, v in root_cfg.items() if k != "builds"}
    resolved_builds = [
        resolve_build_config(
            b,
            args,
            config_dir,
            cwd,
            cast(RootConfig, root_cfg),
        )
        for b in builds
    ]

    if (
        all(not b.get("include") for b in resolved_builds)
        and not args.add_include
        and not args.include
    ):
        log(
            "warning",
            "No include patterns found.\n"
            "   Use 'include' in your config or pass --include / --add-include.",
        )

    # Apply the root default to any build that didn't specify or override it
    for b in resolved_builds:
        if "respect_gitignore" not in b:
            b["respect_gitignore"] = root_respect_gitignore

    if args.dry_run:
        log("info", "🧪 Dry-run mode: no files will be written or deleted.\n")

    if config_path:
        log("info", f"🔧 Using config: {config_path.name}")
        log("info", f"📁 Config base: {config_dir}")
        log("info", f"📂 Invoked from: {cwd}\n")
    else:
        log("info", "🔧 Running in CLI-only mode (no config file).")
        log("info", f"📁 Working base: {config_dir}")
    log("info", f"🔧 Running {len(resolved_builds)} build(s)\n")

    # --- Watch mode ---
    watch_enabled = (args.watch is not None) or ("--watch" in (argv or []))
    if watch_enabled:
        if args.watch is not None:
            # explicit interval from CLI
            watch_interval = args.watch
        else:
            # no explicit interval — use config or fallback
            build_interval = next(
                (
                    b.get("watch_interval")
                    for b in resolved_builds
                    if b.get("watch_interval") is not None
                ),
                None,
            )
            root_interval = root_cfg.get("watch_interval")
            watch_interval = float(
                build_interval or root_interval or DEFAULT_WATCH_INTERVAL
            )

        watch_for_changes(
            lambda: run_all_builds(resolved_builds, args.dry_run),
            resolved_builds,
            interval=watch_interval,
        )

    # --- Regular Run builds ---
    else:
        run_all_builds(resolved_builds, args.dry_run)

    return 0
