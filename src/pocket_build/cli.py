# src/pocket_build/cli.py

import argparse
import platform
import sys
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path

from .actions import get_metadata, run_selftest, watch_for_changes
from .build import run_all_builds
from .config import (
    can_run_configless,
    load_and_validate_config,
)
from .config_resolve import resolve_config
from .config_types import (
    BuildConfigResolved,
    RootConfig,
    RootConfigResolved,
)
from .constants import (
    DEFAULT_DRY_RUN,
    DEFAULT_WATCH_INTERVAL,
)
from .logs import get_logger
from .meta import (
    PROGRAM_DISPLAY,
    PROGRAM_SCRIPT,
)
from .utils import get_sys_version_info
from .utils_logs import LEVEL_ORDER, safe_log
from .utils_types import cast_hint


# --------------------------------------------------------------------------- #
# CLI setup and helpers
# --------------------------------------------------------------------------- #


class HintingArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        # Build known option strings: ["-v", "--verbose", "--log-level", ...]
        known_opts: list[str] = []
        for action in self._actions:
            known_opts.extend([s for s in action.option_strings if s])

        hint_lines: list[str] = []
        # Argparse message for bad flags is typically
        # "unrecognized arguments: --inclde ..."
        if "unrecognized arguments:" in message:
            bad = message.split("unrecognized arguments:", 1)[1].strip()
            # Split conservatively on whitespace
            bad_args = [tok for tok in bad.split() if tok.startswith("-")]
            for arg in bad_args:
                close = get_close_matches(arg, known_opts, n=1, cutoff=0.6)
                if close:
                    hint_lines.append(f"Hint: did you mean {close[0]}?")

        # Print usage + the original error
        self.print_usage(sys.stderr)
        full = f"{self.prog}: error: {message}"
        if hint_lines:
            full += "\n" + "\n".join(hint_lines)
        self.exit(2, full + "\n")


def _setup_parser() -> argparse.ArgumentParser:
    """Define and return the CLI argument parser."""
    parser = HintingArgumentParser(prog=PROGRAM_SCRIPT)

    # --- Positional shorthand arguments ---
    parser.add_argument(
        "positional_include",
        nargs="*",
        metavar="INCLUDE",
        help="Positional include paths or patterns (shorthand for --include).",
    )
    parser.add_argument(
        "positional_out",
        nargs="?",
        metavar="OUT",
        help="Positional output directory (shorthand for --out).",
    )

    # --- Standard flags ---
    parser.add_argument(
        "--include",
        nargs="+",
        help="Override include patterns. Format: path or path:dest",
    )
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
        help=(
            "Additional include paths (relative to cwd). "
            "Format: path or path:dest. Extends config includes."
        ),
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

    # --- Gitignore behavior ---
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

    # --- Color ---
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

    # --- Version and verbosity ---
    parser.add_argument("--version", action="store_true", help="Show version info.")

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
        choices=LEVEL_ORDER,
        default=None,
        dest="log_level",
        help="Set log verbosity level.",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Run a built-in sanity test to verify tool correctness.",
    )
    return parser


def _normalize_positional_args(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> None:
    """Normalize positional arguments into explicit include/out flags."""
    logger = get_logger()
    includes: list[str] = getattr(args, "positional_include", [])
    out_pos: str | None = getattr(args, "positional_out", None)

    # If no --out, assume last positional is output if we have ≥2 positionals
    if not getattr(args, "out", None) and len(includes) >= 2 and not out_pos:  # noqa: PLR2004
        out_pos = includes.pop()

    # If --out provided, treat all positionals as includes
    elif getattr(args, "out", None) and out_pos:
        logger.trace(
            "Interpreting all positionals as includes since --out was provided.",
        )
        includes.append(out_pos)
        out_pos = None

    # Conflict: can't mix --include and positional includes
    if getattr(args, "include", None) and (includes or out_pos):
        parser.error(
            "Cannot mix positional include arguments with --include; "
            "use --out for destination or --add-include to extend."
        )

    # Internal sanity check
    assert not (getattr(args, "out", None) and out_pos), (  # only for dev # noqa: S101
        "out_pos not cleared after normalization"
    )

    # Assign normalized values
    if includes:
        args.include = includes
    if out_pos:
        args.out = out_pos


# --------------------------------------------------------------------------- #
# Main entry helpers
# --------------------------------------------------------------------------- #


@dataclass
class _LoadedConfig:
    """Container for loaded and resolved configuration data."""

    config_path: Path | None
    root_cfg: RootConfig
    resolved_root: RootConfigResolved
    resolved_builds: list[BuildConfigResolved]
    config_dir: Path
    cwd: Path


def _initialize_logger(args: argparse.Namespace) -> None:
    """Initialize logger with CLI args, env vars, and defaults."""
    logger = get_logger()
    logger.setLevel(logger.determine_log_level(args=args))
    logger.enable_color = getattr(
        args, "enable_color", logger.determine_color_enabled()
    )
    logger.trace("[BOOT] log-level initialized: %s", logger.level_name)

    logger.debug(
        "Runtime: Python %s (%s)\n    %s",
        platform.python_version(),
        platform.python_implementation(),
        sys.version.replace("\n", " "),
    )


def _validate_includes(
    root_cfg: RootConfig,
    resolved_builds: list[BuildConfigResolved],
    resolved_root: RootConfigResolved,
    args: argparse.Namespace,
) -> bool:
    """
    Validate that builds have include patterns.

    Returns True if validation passes, False if we should abort.
    Logs appropriate warnings/errors.
    """
    logger = get_logger()

    # Check for builds with missing includes. Respect per-build strict_config:
    # - If ANY build with no includes has strict_config=true → error (abort)
    # - If ALL builds with no includes have strict_config=false → warning (continue)
    # - If builds=[] and root strict_config=true → error
    # - If builds=[] and root strict_config=false → warning
    #
    # The presence of "include" key (even if empty) signals intentional choice:
    #   [] or includes=[]                  → include:[] in build → no check
    #   {"include": []}                    → include:[] in build → no check
    #   {"builds": [{"include": []}]}      → include:[] in build → no check
    #
    # Missing "include" key likely means forgotten:
    #   {} or ""                           → no include key → check
    #   {"builds": []}                     → no include key → check
    #   {"log_level": "debug"}             → no include key → check
    #   {"builds": [{"out": "dist"}]}      → no include key → check
    original_builds = root_cfg.get("builds", [])
    has_explicit_include_key = any(
        isinstance(b, dict) and "include" in b  # pyright: ignore[reportUnnecessaryIsInstance]
        for b in original_builds
    )

    # Check if any builds have missing includes (respecting CLI overrides)
    has_cli_includes = bool(
        getattr(args, "add_include", None) or getattr(args, "include", None)
    )

    # Builds with no includes
    builds_missing_includes = [b for b in resolved_builds if not b.get("include")]

    # Check if ALL builds have no includes (including zero builds)
    all_builds_missing = len(resolved_builds) == 0 or len(
        builds_missing_includes
    ) == len(resolved_builds)

    if not has_explicit_include_key and not has_cli_includes and all_builds_missing:
        # Determine if we should error or warn based on strict_config
        # If builds exist, check ANY build for strict_config=true
        # If no builds, use root-level strict_config
        if builds_missing_includes:
            any_strict = any(
                b.get("strict_config", True) for b in builds_missing_includes
            )
        else:
            # No builds at all - use root strict_config
            any_strict = resolved_root.get("strict_config", True)

        if any_strict:
            # Error: at least one build with missing includes is strict
            logger.error(
                "No include patterns found "
                "(strict_config=true prevents continuing).\n"
                "   Use 'include' in your config or pass "
                "--include / --add-include.",
            )
            return False

        # Warning: builds have no includes but all are non-strict
        logger.warning(
            "No include patterns found.\n"
            "   Use 'include' in your config or pass "
            "--include / --add-include.",
        )

    return True


def _handle_early_exits(args: argparse.Namespace) -> int | None:
    """
    Handle early exit conditions (version, selftest, Python version check).

    Returns exit code if we should exit early, None otherwise.
    """
    logger = get_logger()

    # --- Version flag ---
    if getattr(args, "version", None):
        meta = get_metadata()
        standalone = " [standalone]" if globals().get("__STANDALONE__", False) else ""
        logger.info(
            "%s %s (%s)%s", PROGRAM_DISPLAY, meta.version, meta.commit, standalone
        )
        return 0

    # --- Python version check ---
    if get_sys_version_info() < (3, 10):
        logger.error("%s requires Python 3.10 or newer.", {PROGRAM_DISPLAY})
        return 1

    # --- Self-test mode ---
    if getattr(args, "selftest", None):
        return 0 if run_selftest() else 1

    return None


def _load_and_resolve_config(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> _LoadedConfig:
    """Load config, normalize args, and resolve final configuration."""
    logger = get_logger()

    # --- Load configuration ---
    config_path: Path | None = None
    root_cfg: RootConfig | None = None
    config_result = load_and_validate_config(args)
    if config_result is not None:
        config_path, root_cfg, _validation_summary = config_result

    logger.trace("[CONFIG] log-level re-resolved from config: %s", logger.level_name)

    # --- Normalize shorthand arguments ---
    _normalize_positional_args(args, parser)
    cwd = Path.cwd().resolve()
    config_dir = config_path.parent if config_path else cwd

    # --- Configless early bailout ---
    if root_cfg is None and not can_run_configless(args):
        logger.error(
            "No build config found (.%s.json) and no includes provided.",
            PROGRAM_SCRIPT,
        )
        xmsg = "No config file or CLI includes provided"
        raise RuntimeError(xmsg)

    # --- CLI-only mode fallback ---
    if root_cfg is None:
        logger.info("No config file found — using CLI-only mode.")
        root_cfg = cast_hint(RootConfig, {"builds": [{}]})

    # --- Resolve config with args and defaults ---
    resolved_root = resolve_config(root_cfg, args, config_dir, cwd)
    resolved_builds = resolved_root["builds"]

    return _LoadedConfig(
        config_path=config_path,
        root_cfg=root_cfg,
        resolved_root=resolved_root,
        resolved_builds=resolved_builds,
        config_dir=config_dir,
        cwd=cwd,
    )


def _execute_builds(
    resolved_builds: list[BuildConfigResolved],
    resolved_root: RootConfigResolved,
    args: argparse.Namespace,
    argv: list[str] | None,
) -> None:
    """Execute builds either in watch mode or one-time mode."""
    watch_enabled = getattr(args, "watch", None) is not None or (
        "--watch" in (argv or [])
    )

    if watch_enabled:
        watch_interval = resolved_root["watch_interval"]
        watch_for_changes(
            lambda: run_all_builds(
                resolved_builds,
                dry_run=getattr(args, "dry_run", DEFAULT_DRY_RUN),
            ),
            resolved_builds,
            interval=watch_interval,
        )
    else:
        run_all_builds(
            resolved_builds, dry_run=getattr(args, "dry_run", DEFAULT_DRY_RUN)
        )


# --------------------------------------------------------------------------- #
# Main entry
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    logger = get_logger()  # init (use env + defaults)

    try:
        parser = _setup_parser()
        args = parser.parse_args(argv)

        # --- Early runtime init (use CLI + env + defaults) ---
        _initialize_logger(args)

        # --- Handle early exits (version, selftest, etc.) ---
        early_exit_code = _handle_early_exits(args)
        if early_exit_code is not None:
            return early_exit_code

        # --- Load and resolve configuration ---
        config = _load_and_resolve_config(args, parser)

        # --- Validate includes ---
        if not _validate_includes(
            config.root_cfg, config.resolved_builds, config.resolved_root, args
        ):
            return 1

        # --- Dry-run notice ---
        if getattr(args, "dry_run", None):
            logger.info("🧪 Dry-run mode: no files will be written or deleted.\n")

        # --- Config summary ---
        if config.config_path:
            logger.info("🔧 Using config: %s", config.config_path.name)
        else:
            logger.info("🔧 Running in CLI-only mode (no config file).")
        logger.info("📁 Config root: %s", config.config_dir)
        logger.info("📂 Invoked from: %s", config.cwd)
        logger.info("🔧 Running %d build(s)\n", len(config.resolved_builds))

        # --- Execute builds ---
        _execute_builds(config.resolved_builds, config.resolved_root, args, argv)

    except (FileNotFoundError, ValueError, TypeError, RuntimeError) as e:
        # controlled termination
        silent = getattr(e, "silent", False)
        if not silent:
            try:
                logger.error_if_not_debug(str(e))
            except Exception:  # noqa: BLE001
                safe_log(f"[FATAL] Logging failed while reporting: {e}")
        return getattr(e, "code", 1)

    except Exception as e:  # noqa: BLE001
        # unexpected internal error
        try:
            logger.critical_if_not_debug("Unexpected internal error: %s", e)
        except Exception:  # noqa: BLE001
            safe_log(f"[FATAL] Logging failed while reporting: {e}")

        return getattr(e, "code", 1)

    else:
        return 0
