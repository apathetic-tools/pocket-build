# src/pocket_build/cli.py
import argparse
import contextlib
import io
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, List, Optional, cast

from .build import run_build
from .config import parse_builds
from .meta import PROGRAM_ENV, PROGRAM_NAME
from .runtime import current_runtime
from .types import BuildConfig, MetaBuildConfig, RootConfig
from .utils import RED, YELLOW, colorize, is_error_level, load_jsonc, log


def get_metadata_from_header(script_path: Path) -> tuple[str, str]:
    """Extract version and commit from bundled header if present."""
    version = "unknown"
    commit = "unknown"

    try:
        text = script_path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("# Version:"):
                version = line.split(":", 1)[1].strip()
            elif line.startswith("# Commit:"):
                commit = line.split(":", 1)[1].strip()
    except Exception:
        pass

    return version, commit


def get_metadata() -> tuple[str, str]:
    """
    Return (version, commit) tuple for Pocket Build.
    - Bundled script → parse from header
    - Source package → read pyproject.toml + git
    """
    script_path = Path(__file__)

    # --- Heuristic: bundled script lives outside `src/` ---
    if "src" not in str(script_path):
        return get_metadata_from_header(script_path)

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


def setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=PROGRAM_NAME)
    parser.add_argument("--include", nargs="+", help="Override include patterns.")
    parser.add_argument("--exclude", nargs="+", help="Override exclude patterns.")
    parser.add_argument("-o", "--out", help="Override output directory.")
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
    return parser


def find_config(args: argparse.Namespace, cwd: Path) -> Optional[Path]:
    if args.config:
        config = Path(args.config).expanduser().resolve()
        if not config.exists():
            print(colorize(f"⚠️  Config file not found: {config}", YELLOW))
            return None
        return config

    candidates: List[Path] = [
        cwd / f".{PROGRAM_NAME}.py",
        cwd / f".{PROGRAM_NAME}.jsonc",
        cwd / f".{PROGRAM_NAME}.json",
    ]
    found = [p for p in candidates if p.exists()]

    if found:
        if len(found) > 1:
            names = ", ".join(p.name for p in found)
            print(
                colorize(
                    (
                        f"⚠️  Multiple config files detected ({names});"
                        f" using {found[0].name}."
                    ),
                    YELLOW,
                )
            )
        return found[0]

    return None


def load_config(config_path: Path) -> dict[str, Any]:
    if config_path.suffix == ".py":
        config_globals: dict[str, Any] = {}
        sys.path.insert(0, str(config_path.parent))
        try:
            exec(config_path.read_text(), config_globals)
            log(
                "trace",
                f"[DEBUG EXEC] globals after exec: {list(config_globals.keys())}",
            )
            log("trace", f"[DEBUG EXEC] builds: {config_globals.get('builds')}")
        finally:
            sys.path.pop(0)

        if "config" in config_globals:
            return cast(dict[str, Any], config_globals["config"])
        if "builds" in config_globals:
            return {"builds": config_globals["builds"]}

        raise ValueError(f"{config_path.name} did not define `config` or `builds`")
    else:
        return load_jsonc(config_path)


def load_gitignore_patterns(path: Path) -> list[str]:
    patterns: list[str] = []
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def resolve_build_config(
    build_cfg: BuildConfig,
    args: argparse.Namespace,
    config_dir: Path,
    cwd: Path,
    root_cfg: Optional[RootConfig] = None,
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
        patterns = load_gitignore_patterns(gitignore_path)
        log(
            "trace",
            f"[DEBUG] Using .gitignore at {config_dir} ({len(patterns)} patterns)",
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

    # Explicitly cast back to BuildConfig for return
    resolved["__meta__"] = meta
    return cast(BuildConfig, resolved)


def main(argv: Optional[List[str]] = None) -> int:
    parser = setup_parser()
    args = parser.parse_args(argv)

    # --- Version flag ---
    if args.version:
        version, commit = get_metadata()
        print(f"Pocket Build {version} ({commit})")
        return 0

    # --- Python version check ---
    if sys.version_info < (3, 10):
        print(colorize(f"❌ {PROGRAM_NAME} requires Python 3.10 or newer.", RED))
        return 1

    # --- Config path handling ---
    cwd = Path.cwd().resolve()
    config_path = find_config(args, cwd)
    if not config_path:
        print(colorize(f"⚠️  No build config found (.{PROGRAM_NAME}.json).", YELLOW))
        return 1

    # --- Config + Build handling ---
    config_dir = config_path.parent.resolve()
    raw_config = load_config(config_path)

    # Determine effective log level, from now on use log_print()
    env_log_level = os.getenv(f"{PROGRAM_ENV}_LOG_LEVEL") or os.getenv("LOG_LEVEL")
    log_level: str
    if args.log_level:
        log_level = args.log_level
    elif env_log_level:
        log_level = env_log_level
    else:
        log_level = raw_config.get("log_level", "info")
    current_runtime["log_level"] = log_level

    log("trace", f"[DEBUG RAW CONFIG] {raw_config}")
    builds = parse_builds(raw_config)
    log("trace", f"[DEBUG BUILDS AFTER PARSE] {builds}")

    root_respect_gitignore = raw_config.get("respect_gitignore", True)

    root_cfg = {k: v for k, v in raw_config.items() if k != "builds"}
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

    # Apply the root default to any build that didn't specify or override it
    for b in resolved_builds:
        if "respect_gitignore" not in b:
            b["respect_gitignore"] = root_respect_gitignore

    # --- Quiet mode: temporarily suppress stdout ---
    if is_error_level(args.log_level):
        # everything printed inside this block is discarded
        with contextlib.redirect_stdout(io.StringIO()):
            for build_cfg in resolved_builds:
                run_build(build_cfg)
        return 0

    # --- Normal / verbose mode ---
    print(f"🔧 Using config: {config_path.name}")
    print(f"📁 Config base: {config_dir}")
    print(f"📂 Invoked from: {cwd}\n")
    print(f"🔧 Running {len(resolved_builds)} build(s)\n")

    for i, build_cfg in enumerate(resolved_builds, 1):
        print(f"▶️  Build {i}/{len(resolved_builds)}")
        run_build(build_cfg)

    print("🎉 All builds complete.")
    return 0
