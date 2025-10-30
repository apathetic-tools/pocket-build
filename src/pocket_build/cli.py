# src/pocket_build/cli.py

import argparse
import sys
import traceback
from pathlib import Path

from .actions import get_metadata, run_selftest, watch_for_changes
from .build import run_all_builds
from .config import (
    can_run_configless,
    load_and_validate_config,
)
from .config_resolve import resolve_config
from .constants import (
    DEFAULT_WATCH_INTERVAL,
)
from .meta import (
    PROGRAM_DISPLAY,
    PROGRAM_SCRIPT,
)
from .runtime import current_runtime
from .types import (
    RootConfig,
)
from .utils import safe_log, should_use_color
from .utils_types import cast_hint
from .utils_using_runtime import LEVEL_ORDER, log


# --------------------------------------------------------------------------- #
# CLI setup and helpers
# --------------------------------------------------------------------------- #


def _setup_parser() -> argparse.ArgumentParser:
    """Define and return the CLI argument parser."""
    parser = argparse.ArgumentParser(prog=PROGRAM_SCRIPT)

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
    includes: list[str] = getattr(args, "positional_include", [])
    out_pos: str | None = getattr(args, "positional_out", None)

    # If no --out, assume last positional is output if we have ≥2 positionals
    if not getattr(args, "out", None) and len(includes) >= 2 and not out_pos:  # noqa: PLR2004
        out_pos = includes.pop()

    # If --out provided, treat all positionals as includes
    elif getattr(args, "out", None) and out_pos:
        log(
            "trace",
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
# Main entry
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:  # noqa: C901, PLR0911, PLR0912, PLR0915
    try:
        parser = _setup_parser()
        args = parser.parse_args(argv)

        # --- Color detection ---
        use_color = getattr(args, "use_color", should_use_color())
        current_runtime["use_color"] = use_color

        # --- Version flag ---
        if getattr(args, "version", None):
            meta = get_metadata()
            standalone = (
                " [standalone]" if globals().get("__STANDALONE__", False) else ""
            )
            print(f"{PROGRAM_DISPLAY} {meta.version} ({meta.commit}){standalone}")  # noqa: T201
            return 0

        # --- Python version check ---
        if sys.version_info < (3, 10):  # noqa: UP036
            # error before log-level exists
            print(  # noqa: T201
                f"❌  {PROGRAM_DISPLAY} requires Python 3.10 or newer.",
                file=sys.stderr,
            )
            return 1

        # --- Load configuration ---
        config_path: Path | None = None
        root_cfg: RootConfig | None = None
        config_result = load_and_validate_config(args)
        if config_result is not None:
            config_path, root_cfg = config_result

        # NOTE: log() from now on, we have log-level

        # --- Self-test mode ---
        if getattr(args, "selftest", None):
            return 0 if run_selftest() else 1

        # --- Normalize shorthand arguments ---
        _normalize_positional_args(args, parser)
        cwd = Path.cwd().resolve()
        config_dir = config_path.parent if config_path else cwd

        # --- Configless early bailout ---
        if root_cfg is None and not can_run_configless(args):
            log(
                "error",
                f"No build config found (.{PROGRAM_SCRIPT}.json)"
                " and no includes provided.",
            )
            return 1

        # --- CLI-only mode fallback ---
        if root_cfg is None:
            log("info", "No config file found — using CLI-only mode.")
            # Create minimal pseudo-config when running without a file for args merging
            root_cfg = cast_hint(RootConfig, {"builds": [{}]})

        # --- Resolve config with args and feaults ---
        resolved_root = resolve_config(root_cfg, args, config_dir, cwd)
        resolved_builds = resolved_root["builds"]

        # --- Sanity: missing includes ---
        if (
            all(not b.get("include") for b in resolved_builds)
            and not getattr(args, "add_include", None)
            and not getattr(args, "include", None)
        ):
            log(
                "warning",
                "No include patterns found.\n"
                "   Use 'include' in your config or pass --include / --add-include.",
            )

        # --- Dry-run notice ---
        if getattr(args, "dry_run", None):
            log("info", "🧪 Dry-run mode: no files will be written or deleted.\n")

        # --- Config summary ---
        if config_path:
            log("info", f"🔧 Using config: {config_path.name}")
        else:
            log("info", "🔧 Running in CLI-only mode (no config file).")
        log("info", f"📁 Config root: {config_dir}")
        log("info", f"📂 Invoked from: {cwd}")
        log("info", f"🔧 Running {len(resolved_builds)} build(s)\n")

        # --- Watch or run ---
        watch_enabled = getattr(args, "watch", None) is not None or (
            "--watch" in (argv or [])
        )
        if watch_enabled:
            watch_interval = resolved_root["watch_interval"]
            watch_for_changes(
                lambda: run_all_builds(
                    resolved_builds,
                    dry_run=getattr(args, "dry_run", False),
                ),
                resolved_builds,
                interval=watch_interval,
            )

        else:
            run_all_builds(resolved_builds, dry_run=getattr(args, "dry_run", False))

        return 0

    except (FileNotFoundError, ValueError, TypeError, RuntimeError) as e:
        # controlled termination
        silent = getattr(e, "silent", False)
        if not silent:
            try:
                log("error", str(e))
            except Exception:  # noqa: BLE001
                safe_log(f"[FATAL] Logging failed while reporting: {e}")
        return getattr(e, "code", 1)

    except Exception as e:  # noqa: BLE001
        # unexpected internal error
        try:
            log("critical", f"Unexpected internal error: {e}")
        except Exception:  # noqa: BLE001
            safe_log(f"[FATAL] Logging failed while reporting: {e}")
        # optionally print traceback in debug/trace mode only
        if current_runtime.get("log_level") in {"debug", "trace"}:
            traceback.print_exc()
        return getattr(e, "code", 1)
