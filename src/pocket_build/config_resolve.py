# src/pocket_build/config_resolve.py


import argparse
import os
from pathlib import Path
from typing import Any

from .config import determine_log_level
from .constants import (
    DEFAULT_ENV_LOG_LEVEL,
    DEFAULT_ENV_WATCH_INTERVAL,
    DEFAULT_OUT_DIR,
    DEFAULT_RESPECT_GITIGNORE,
    DEFAULT_WATCH_INTERVAL,
)
from .runtime import current_runtime
from .types import (
    BuildConfig,
    BuildConfigResolved,
    IncludeResolved,
    MetaBuildConfigResolved,
    OriginType,
    PathResolved,
    RootConfig,
    RootConfigResolved,
)
from .utils_types import cast_hint, make_includeresolved, make_pathresolved
from .utils_using_runtime import has_glob_chars, log

# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _load_gitignore_patterns(path: Path) -> list[str]:
    """Read .gitignore and return non-comment patterns."""
    patterns: list[str] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def _normalize_path_with_root(
    raw: Path | str, context_root: Path | str
) -> tuple[Path, Path | str]:
    """
    Normalize a user-provided path (from CLI or config).

    - If absolute → treat that path as its own root.
      * `/abs/path/**` → root=/abs/path, rel="**"
      * `/abs/path/`   → root=/abs/path, rel="**"  (treat as contents)
      * `/abs/path`    → root=/abs/path, rel="."   (treat as literal)
    - If relative → root = context_root, path = raw (preserve string form)
    """
    raw_path = Path(raw)
    rel: Path | str

    # --- absolute path case ---
    if raw_path.is_absolute():
        # Split out glob or trailing slash intent
        raw_str = str(raw)
        if raw_str.endswith("/**"):
            root = Path(raw_str[:-3]).resolve()
            rel = "**"
        elif raw_str.endswith("/"):
            root = Path(raw_str[:-1]).resolve()
            rel = "**"  # treat directory as contents
        else:
            root = raw_path.resolve()
            rel = "."
    else:
        root = Path(context_root).resolve()
        # preserve literal string if user provided one
        rel = raw if isinstance(raw, str) else Path(raw)

    log("trace", f"Normalized: raw={raw!r} → root={root}, rel={rel}")
    return root, rel


# --------------------------------------------------------------------------- #
# main per-build resolver
# --------------------------------------------------------------------------- #


def resolve_build_config(
    build_cfg: BuildConfig,
    args: argparse.Namespace,
    config_dir: Path,
    cwd: Path,
    root_cfg: RootConfig | None = None,
) -> BuildConfigResolved:
    """Resolve a single BuildConfig into a BuildConfigResolved.

    Applies CLI overrides, normalizes paths, merges gitignore behavior,
    and attaches provenance metadata.
    """
    # Make a mutable copy
    resolved_cfg: dict[str, Any] = dict(build_cfg)

    # root provenance for all resolutions
    meta: MetaBuildConfigResolved = {
        "cli_root": cwd,
        "config_root": config_dir,
    }

    # ------------------------------
    # Includes
    # ------------------------------
    includes: list[IncludeResolved] = []

    if getattr(args, "include", None):
        # Full override → relative to cwd
        for raw in args.include:
            root, rel = _normalize_path_with_root(raw, cwd)
            includes.append(make_includeresolved(rel, root, "cli"))

    elif "include" in resolved_cfg:
        # From config → relative to config_dir
        for raw in resolved_cfg["include"]:
            root, rel = _normalize_path_with_root(raw, config_dir)
            includes.append(make_includeresolved(rel, root, "config"))

    # Add-on includes (extend, not override)
    if getattr(args, "add_include", None):
        for raw in args.add_include:
            root, rel = _normalize_path_with_root(raw, cwd)
            includes.append(make_includeresolved(rel, root, "cli"))

    # unique path+root
    seen_inc: set[tuple[Path | str, Path]] = set()
    unique_inc: list[IncludeResolved] = []
    for i in includes:
        key = (i["path"], i["root"])
        if key not in seen_inc:
            seen_inc.add(key)
            unique_inc.append(i)

            # Check root existence
            if not i["root"].exists():
                log(
                    "warning",
                    f"Include root does not exist: {i['root']} (origin: {i['origin']})",
                )

            # Check path existence
            if not has_glob_chars(str(i["path"])):
                full_path = i["root"] / i["path"]  # absolute paths override root
                if not full_path.exists():
                    log(
                        "warning",
                        f"Include path does not exist: {full_path}"
                        f" (origin: {i['origin']})",
                    )
    includes = unique_inc
    resolved_cfg["include"] = includes

    # ------------------------------
    # Excludes
    # ------------------------------
    excludes: list[PathResolved] = []

    def _add_excludes(paths: list[str], context: Path, origin: OriginType) -> None:
        for raw in paths:
            # Exclude patterns (from CLI, config, or gitignore) should stay literal
            excludes.append(make_pathresolved(raw, context, origin))

    if getattr(args, "exclude", None):
        # Full override → relative to cwd
        # Keep CLI-provided exclude patterns as-is (do not resolve),
        # since glob patterns like "*.tmp" should match relative paths
        # beneath the include root, not absolute paths.
        _add_excludes(args.exclude, cwd, "cli")
    elif "exclude" in resolved_cfg:
        # From config → relative to config_dir
        _add_excludes(resolved_cfg["exclude"], config_dir, "config")

    # Add-on excludes (extend, not override)
    if getattr(args, "add_exclude", None):
        _add_excludes(args.add_exclude, cwd, "cli")

    # --- Merge .gitignore patterns into excludes if enabled ---
    # Determine whether to respect .gitignore
    if getattr(args, "respect_gitignore", None) is not None:
        respect_gitignore = args.respect_gitignore
    elif "respect_gitignore" in resolved_cfg:
        respect_gitignore = resolved_cfg["respect_gitignore"]
    else:
        # fallback — true by default, overridden by root config if needed
        respect_gitignore = (root_cfg or {}).get(
            "respect_gitignore",
            DEFAULT_RESPECT_GITIGNORE,
        )

    if respect_gitignore:
        gitignore_path = config_dir / ".gitignore"
        patterns = _load_gitignore_patterns(gitignore_path)
        if patterns:
            log(
                "trace",
                f"Adding {len(patterns)} .gitignore patterns from {gitignore_path}",
            )
        _add_excludes(patterns, config_dir, "gitignore")

    resolved_cfg["respect_gitignore"] = respect_gitignore

    # unique path+root
    seen_exc: set[tuple[Path | str, Path]] = set()
    unique_exc: list[PathResolved] = []
    for ex in excludes:
        key = (ex["path"], ex["root"])
        if key not in seen_exc:
            seen_exc.add(key)
            unique_exc.append(ex)
    excludes = unique_exc
    resolved_cfg["exclude"] = excludes

    # ------------------------------
    # Output directory
    # ------------------------------
    if getattr(args, "out", None):
        # Full override → relative to cwd
        root, rel = _normalize_path_with_root(args.out, cwd)
        out_wrapped = make_pathresolved(rel, root, "cli")
    elif "out" in resolved_cfg:
        # From config → relative to config_dir
        root, rel = _normalize_path_with_root(resolved_cfg["out"], config_dir)
        out_wrapped = make_pathresolved(rel, root, "config")
    else:
        root, rel = _normalize_path_with_root(DEFAULT_OUT_DIR, cwd)
        out_wrapped = make_pathresolved(rel, root, "default")

    resolved_cfg["out"] = out_wrapped

    # ------------------------------
    # Log level
    # ------------------------------
    build_log = resolved_cfg.get("log_level")
    root_log = (root_cfg or {}).get("log_level")
    resolved_cfg["log_level"] = determine_log_level(args, root_log, build_log)

    # ------------------------------
    # Attach provenance
    # ------------------------------
    resolved_cfg["__meta__"] = meta
    return cast_hint(BuildConfigResolved, resolved_cfg)


# --------------------------------------------------------------------------- #
# root-level resolver
# --------------------------------------------------------------------------- #


def resolve_config(
    root_input: RootConfig,
    args: argparse.Namespace,
    config_dir: Path,
    cwd: Path,
) -> RootConfigResolved:
    """Fully resolve a loaded RootConfig into a ready-to-run RootConfigResolved."""
    root_cfg = cast_hint(RootConfig, dict(root_input))

    # ------------------------------
    # Watch interval
    # ------------------------------
    env_watch = os.getenv(DEFAULT_ENV_WATCH_INTERVAL)
    if getattr(args, "watch", None) is not None:
        watch_interval = args.watch
    elif env_watch is not None:
        try:
            watch_interval = float(env_watch)
        except ValueError:
            log(
                "warning",
                f"Invalid {DEFAULT_ENV_WATCH_INTERVAL}={env_watch!r}, using default.",
            )
            watch_interval = DEFAULT_WATCH_INTERVAL
    else:
        watch_interval = root_cfg.get("watch_interval", DEFAULT_WATCH_INTERVAL)

    # ------------------------------
    # Log level
    # ------------------------------
    #  log_level: arg -> env -> build -> root -> default
    env_log = os.getenv(DEFAULT_ENV_LOG_LEVEL)
    root_log = root_cfg.get("log_level")
    log_level = determine_log_level(args, root_log, None)
    if env_log:
        log_level = env_log  # environment wins over config if CLI missing

    # --- sync runtime ---
    current_runtime["log_level"] = log_level

    # ------------------------------
    # Resolve builds
    # ------------------------------
    builds_input = root_cfg.get("builds", [])
    resolved_builds = [
        resolve_build_config(b, args, config_dir, cwd, root_cfg) for b in builds_input
    ]

    resolved_root: RootConfigResolved = {
        "builds": resolved_builds,
        "strict_config": root_cfg.get("strict_config", False),
        "watch_interval": watch_interval,
        "log_level": log_level,
    }

    return resolved_root
