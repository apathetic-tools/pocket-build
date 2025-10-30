# tests/utils/buildconfig.py
"""Shared test helpers for constructing fake BuildConfigResolved and related types."""

from pathlib import Path
from typing import cast

import pocket_build.types as mod_types


# ---------------------------------------------------------------------------
# Factories for resolved and unresolved configs
# ---------------------------------------------------------------------------


def make_meta(root: Path) -> mod_types.MetaBuildConfigResolved:
    """Minimal fake meta object for resolved configs."""
    return {"cli_root": root, "config_root": root}


def make_resolved(path: Path | str, root: Path | str) -> mod_types.PathResolved:
    """Return a fake PathResolved-style dict."""
    raw_path = path if isinstance(path, str) else str(path)
    return cast(
        "mod_types.PathResolved",
        {
            "path": raw_path,
            "root": Path(root),
            "origin": "test",
        },
    )


def make_include_resolved(
    path: Path | str,
    root: Path | str,
    dest: Path | str | None = None,
) -> mod_types.IncludeResolved:
    """Return a fake IncludeResolved-style dict."""
    # Preserve raw string form to retain trailing slashes
    raw_path = path if isinstance(path, str) else str(path)
    d: dict[str, Path | str] = {
        "path": raw_path,
        "root": Path(root),
        "origin": "test",
    }
    if dest:
        d["dest"] = Path(dest)
    return cast("mod_types.IncludeResolved", d)


def make_build_cfg(
    tmp_path: Path,
    include: list[mod_types.IncludeResolved],
    exclude: list[mod_types.PathResolved] | None = None,
    *,
    respect_gitignore: bool = True,
    log_level: str = "info",
    dry_run: bool = False,
    out: mod_types.PathResolved | None = None,
) -> mod_types.BuildConfigResolved:
    """Return a fake, fully-populated BuildConfigResolved."""
    return {
        "include": include,
        "exclude": exclude or [],
        "out": out if out is not None else make_resolved(tmp_path / "dist", tmp_path),
        "__meta__": make_meta(tmp_path),
        "respect_gitignore": respect_gitignore,
        "log_level": log_level,
        "dry_run": dry_run,
    }


def make_build_input(
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    out: str | None = None,
    **extra: object,
) -> mod_types.BuildConfig:
    """Convenient shorthand for constructing raw (pre-resolve) build inputs."""
    cfg: dict[str, object] = {}
    if include is not None:
        cfg["include"] = include
    if exclude is not None:
        cfg["exclude"] = exclude
    if out is not None:
        cfg["out"] = out
    cfg.update(extra)
    return cast("mod_types.BuildConfig", cfg)
