# src/pocket_build/cli.py
import argparse
import glob
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, List, cast

from .build import run_build
from .config import parse_builds
from .constants import DEFAULT_WATCH_INTERVAL
from .meta import PROGRAM_DISPLAY, PROGRAM_ENV, PROGRAM_SCRIPT
from .runtime import current_runtime
from .types import BuildConfig, MetaBuildConfig, RootConfig
from .utils_core import load_jsonc, should_use_color
from .utils_runtime import GREEN, RED, YELLOW, colorize, log


def _collect_included_files(resolved_builds: list[BuildConfig]) -> list[Path]:
    """Flatten all include globs into a unique list of files."""
    log("trace", "real_collect_included_files", __name__, id(_collect_included_files))
    files: set[Path] = set()
    for b in resolved_builds:
        for pattern in b.get("include", []):
            if isinstance(pattern, str):
                for match in glob.glob(pattern, recursive=True):
                    p = Path(match)
                    if p.is_file():
                        files.add(p.resolve())
    return sorted(files)


def watch_for_changes(
    rebuild_func: Callable[[], None],
    resolved_builds: list[BuildConfig],
    interval: float = DEFAULT_WATCH_INTERVAL,
) -> None:
    """Poll file modification times and rebuild when changes are detected.

    Features:
    - Skips files inside each build’s output directory.
    - Re-expands include patterns every loop to detect newly created files.
    - Polling interval defaults to 1 second (tune 0.5–2.0 for balance).
    Stops on KeyboardInterrupt.
    """

    log("trace", "real_watch_for_changes", __name__, id(watch_for_changes))
    log(
        "info",
        f"👀 Watching for changes (interval={interval:.2f}s)... Press Ctrl+C to stop.",
    )

    # discover at start
    included_files = _collect_included_files(resolved_builds)
    log("trace", "watch_for_changes", "initial files", [str(f) for f in included_files])

    mtimes: dict[Path, float] = {
        f: f.stat().st_mtime for f in included_files if f.exists()
    }

    # Collect all output directories to ignore
    out_dirs = [Path(b["out"]).resolve() for b in resolved_builds if "out" in b]

    rebuild_func()  # initial build

    try:
        while True:
            log("trace", "watch_for_changes", "sleep")
            time.sleep(interval)
            log("trace", "watch_for_changes", "loop")

            # 🔁 re-expand every tick so new/removed files are tracked
            included_files = _collect_included_files(resolved_builds)

            changed: list[Path] = []
            for f in included_files:
                log("trace", "watch_for_changes", "could be out dir?", f)
                # skip anything inside any build's output directory
                if any(f.is_relative_to(out_dir) for out_dir in out_dirs):
                    continue  # ignore output folder
                old_m = mtimes.get(f)
                log("trace", "watch_for_changes", "check", f, old_m)
                if not f.exists():
                    if old_m is not None:
                        changed.append(f)
                        mtimes.pop(f, None)
                    continue
                new_m = f.stat().st_mtime
                if old_m is None or new_m > old_m:
                    changed.append(f)
                    mtimes[f] = new_m

            if changed:
                print(f"\n🔁 Detected {len(changed)} modified file(s). Rebuilding...")
                rebuild_func()
                # refresh timestamps after rebuild
                mtimes = {f: f.stat().st_mtime for f in included_files if f.exists()}
    except KeyboardInterrupt:
        print("\n🛑 Watch stopped.")


def _get_metadata_from_header(script_path: Path) -> tuple[str, str]:
    """Extract version and commit from bundled script.

    Prefers in-file constants (__version__, __commit__) if present;
    falls back to commented header tags.
    """
    version = "unknown"
    commit = "unknown"

    try:
        text = script_path.read_text(encoding="utf-8")

        # --- Prefer Python constants if defined ---
        const_version = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", text)
        const_commit = re.search(r"__commit__\s*=\s*['\"]([^'\"]+)['\"]", text)
        if const_version:
            version = const_version.group(1)
        if const_commit:
            commit = const_commit.group(1)

        # --- Fallback: header lines ---
        if version == "unknown" or commit == "unknown":
            for line in text.splitlines():
                if line.startswith("# Version:") and version == "unknown":
                    version = line.split(":", 1)[1].strip()
                elif line.startswith("# Commit:") and commit == "unknown":
                    commit = line.split(":", 1)[1].strip()

    except Exception:
        pass

    return version, commit


def get_metadata() -> tuple[str, str]:
    """
    Return (version, commit) tuple for this tool.
    - Bundled script → parse from header
    - Source package → read pyproject.toml + git
    """
    script_path = Path(__file__)

    # --- Heuristic: bundled script lives outside `src/` ---
    if "src" not in str(script_path):
        return _get_metadata_from_header(script_path)

    # --- Modular / source package case ---

    # Source package case
    version = "unknown"
    commit = "unknown"

    # Try pyproject.toml for version
    root = Path(__file__).resolve().parents[2]

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text()
        match = re.search(r'(?m)^\s*version\s*=\s*["\']([^"\']+)["\']', text)
        if match:
            version = match.group(1)

    # Try git for commit
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        commit = result.stdout.strip()
    except Exception:
        pass

    return version, commit


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


def run_selftest() -> int:
    """Run a lightweight functional test of the tool itself."""
    import shutil
    import tempfile

    log("info", "🧪 Running self-test...")

    tmp_dir = Path(tempfile.mkdtemp(prefix=f"{PROGRAM_SCRIPT}-selftest-"))
    src = tmp_dir / "src"
    out = tmp_dir / "out"
    src.mkdir()

    # Create a tiny file to copy
    file = src / "hello.txt"
    file.write_text(f"hello {PROGRAM_DISPLAY}!", encoding="utf-8")

    # Explicitly typed fake config for internal run
    config: dict[str, list[BuildConfig]] = {
        "builds": [
            {"include": [str(src / "**")], "out": str(out)},
        ]
    }

    try:
        log("debug", f"[SELFTEST] using temp dir: {tmp_dir}")
        builds = parse_builds(config)
        for b in builds:
            resolved = resolve_build_config(
                b,
                argparse.Namespace(
                    include=None,
                    exclude=None,
                    add_include=None,
                    add_exclude=None,
                    out=None,
                    dry_run=False,
                    respect_gitignore=None,
                    log_level="info",
                ),
                config_dir=tmp_dir,
                cwd=tmp_dir,
                root_cfg={"respect_gitignore": False},
            )
            run_build(resolved)

        # Verify file copy
        copied = out / "hello.txt"
        if (
            copied.exists()
            and copied.read_text().strip() == f"hello {PROGRAM_DISPLAY}!"
        ):
            log(
                "info", f"✅ Self-test passed — {PROGRAM_DISPLAY} is working correctly."
            )
            return 0
        log("error", "Self-test failed: output file not found or invalid.")
        return 1

    except Exception as e:
        log("error", f"Self-test failed: {e}")
        return 1
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def find_config(args: argparse.Namespace, cwd: Path) -> Path | None:
    if args.config:
        config = Path(args.config).expanduser().resolve()
        if not config.exists():
            # error before log-level exists
            print(
                colorize(f"⚠️  Config file not found: {config}", YELLOW),
                file=sys.stderr,
            )
            return None
        return config

    candidates: List[Path] = [
        cwd / f".{PROGRAM_SCRIPT}.py",
        cwd / f".{PROGRAM_SCRIPT}.jsonc",
        cwd / f".{PROGRAM_SCRIPT}.json",
    ]
    found = [p for p in candidates if p.exists()]

    if found:
        if len(found) > 1:
            names = ", ".join(p.name for p in found)
            # error before log-level exists
            print(
                colorize(
                    (
                        f"⚠️  Multiple config files detected ({names});"
                        f" using {found[0].name}."
                    ),
                    YELLOW,
                ),
                file=sys.stderr,
            )
        return found[0]

    return None


def load_config(config_path: Path) -> dict[str, Any] | list[Any]:
    if config_path.suffix == ".py":
        config_globals: dict[str, Any] = {}
        sys.path.insert(0, str(config_path.parent))
        try:
            exec(config_path.read_text(), config_globals)
            log(
                "trace",
                f"[EXEC] globals after exec: {list(config_globals.keys())}",
            )
            log("trace", f"[EXEC] builds: {config_globals.get('builds')}")
        finally:
            sys.path.pop(0)

        if "config" in config_globals:
            return cast(dict[str, Any], config_globals["config"])
        if "builds" in config_globals:
            return {"builds": config_globals["builds"]}

        raise ValueError(f"{config_path.name} did not define `config` or `builds`")
    else:
        return load_jsonc(config_path)


def _load_gitignore_patterns(path: Path) -> list[str]:
    patterns: list[str] = []
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def run_all_builds(resolved_builds: list[BuildConfig], dry_run: bool) -> None:
    for i, build_cfg in enumerate(resolved_builds, 1):
        build_log_level = build_cfg.get("log_level")
        prev_level = current_runtime["log_level"]

        build_cfg["dry_run"] = dry_run
        if build_log_level:
            current_runtime["log_level"] = build_log_level
            log("debug", f"Overriding log level → {build_log_level}")

        log("info", f"▶️  Build {i}/{len(resolved_builds)}")
        run_build(build_cfg)

        if build_log_level:
            current_runtime["log_level"] = prev_level

    log("info", "🎉 All builds complete.")


def resolve_build_config(
    build_cfg: BuildConfig,
    args: argparse.Namespace,
    config_dir: Path,
    cwd: Path,
    root_cfg: RootConfig | None = None,
) -> BuildConfig:
    """Merge CLI overrides and normalize paths."""
    # Make a mutable copy
    resolved: dict[str, Any] = dict(build_cfg)

    meta = cast(MetaBuildConfig, dict(resolved.get("__meta__", {})))
    meta["origin"] = str(config_dir)

    # Normalize includes
    includes: list[str] = []
    if args.include:
        # Full override → relative to cwd
        meta["include_base"] = str(cwd)
        for i in cast(list[str], args.include):
            includes.append(str((cwd / i).resolve()))
    elif "include" in build_cfg:
        # From config → relative to config_dir
        meta["include_base"] = str(config_dir)
        for i in cast(list[str], build_cfg.get("include")):
            includes.append(str((config_dir / i).resolve()))

    # Add-on includes (extend, not override)
    if args.add_include:
        meta["include_add_base"] = str(cwd)
        for i in cast(list[str], args.add_include):
            includes.append(str((cwd / i).resolve()))

    # deduplicate include
    resolved["include"] = list(dict.fromkeys(includes))

    # Normalize excludes
    excludes: list[str] = []
    if args.exclude:
        # Full override → relative to cwd
        meta["exclude_base"] = str(cwd)
        # Keep CLI-provided exclude patterns as-is (do not resolve),
        # since glob patterns like "*.tmp" should match relative paths
        # beneath the include base, not absolute paths.
        for e in cast(list[str], args.exclude):
            excludes.append(e)
    elif "exclude" in build_cfg:
        # From config → relative to config_dir
        meta["exclude_base"] = str(config_dir)
        for e in build_cfg.get("exclude", []):
            excludes.append(e)

    # Add-on excludes (extend, not override)
    if args.add_exclude:
        meta["exclude_add_base"] = str(cwd)
        for e in cast(list[str], args.add_exclude):
            excludes.append(e)

    resolved["exclude"] = excludes

    # --- Merge .gitignore patterns into excludes if enabled ---
    # Determine whether to respect .gitignore
    if getattr(args, "respect_gitignore", None) is not None:
        use_gitignore = args.respect_gitignore
    elif "respect_gitignore" in build_cfg:
        use_gitignore = build_cfg["respect_gitignore"]
    else:
        # fallback — true by default, overridden by root config if needed
        use_gitignore = (root_cfg or {}).get("respect_gitignore", True)
    resolved["respect_gitignore"] = use_gitignore

    if use_gitignore:
        gitignore_path = config_dir / ".gitignore"
        patterns = _load_gitignore_patterns(gitignore_path)
        log(
            "trace",
            f"Using .gitignore at {config_dir} ({len(patterns)} patterns)",
        )
        if patterns:
            resolved["exclude"].extend(patterns)

    # deduplicate exclude
    resolved["exclude"] = list(dict.fromkeys(resolved["exclude"]))

    # Normalize output path
    out_dir = args.out or resolved.get("out", "dist")
    if args.out:
        # Full override → relative to cwd
        meta["out_base"] = str(cwd)
        resolved["out"] = str((cwd / out_dir).resolve())
    else:
        # From config → relative to config_dir
        meta["out_base"] = str(config_dir)
        resolved["out"] = str((config_dir / out_dir).resolve())

    # --- Optional per-build log level override (for single-build convenience) ---
    if "log_level" in build_cfg:
        # Allow single-build convenience override
        resolved["log_level"] = build_cfg["log_level"]

    # Explicitly cast back to BuildConfig for return
    resolved["__meta__"] = meta
    return cast(BuildConfig, resolved)


def main(argv: List[str] | None = None) -> int:
    parser = _setup_parser()
    args = parser.parse_args(argv)

    use_color = args.use_color if args.use_color is not None else should_use_color()
    current_runtime["use_color"] = use_color

    # --- Version flag ---
    if args.version:
        version, commit = get_metadata()
        # always output
        print(f"{PROGRAM_DISPLAY} {version} ({commit})")
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
        return run_selftest()

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
