# src/pocket_build/config.py
import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Union, cast

from .meta import PROGRAM_SCRIPT
from .types import BuildConfig, MetaBuildConfig, RootConfig
from .utils_core import load_jsonc
from .utils_runtime import YELLOW, colorize, log


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


def parse_builds(raw_config: Union[Dict[str, Any], List[Any]]) -> List[BuildConfig]:
    """
    Normalize any supported config shape into a list of BuildConfig objects.

    Accepted forms:
      - []                        → treated as single build with `include` = []
      - ["src/**", "assets/**"]   → treated as single build with those includes
      - {...}                     → treated as single build config
      - {"builds": [...]}         → treated as multi-build config
    """
    # Case 1: naked list (includes or empty)
    if isinstance(raw_config, list):
        return [cast(BuildConfig, {"include": raw_config})]

    # Case 2: dict with "builds" key (multi-build)
    builds = raw_config.get("builds")
    if isinstance(builds, list):
        return cast(List[BuildConfig], builds)

    # Defensive: if someone accidentally set builds=None, ignore it
    if builds is not None and not isinstance(builds, list):
        raise TypeError(f"Expected 'builds' to be a list, got {type(builds).__name__}")

    # Case 3: single build object
    return [cast(BuildConfig, raw_config)]


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
