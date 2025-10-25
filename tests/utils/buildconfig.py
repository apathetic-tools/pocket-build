# tests/utils/buildconfig.py
"""Shared test helpers for constructing fake BuildConfig and related types."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from pocket_build.types import (
    BuildConfig,
    BuildConfigInput,
    IncludeResolved,
    MetaBuildConfig,
    PathResolved,
)

# ---------------------------------------------------------------------------
# Factories for resolved and unresolved configs
# ---------------------------------------------------------------------------


def make_meta(base: Path) -> MetaBuildConfig:
    """Minimal fake meta object for resolved configs."""
    return {"cli_base": base, "config_base": base}


def make_resolved(path: Path | str, base: Path | str) -> PathResolved:
    """Return a fake PathResolved-style dict."""
    raw_path = path if isinstance(path, str) else str(path)
    return cast(PathResolved, {"path": raw_path, "base": Path(base), "origin": "test"})


def make_include_resolved(
    path: Path | str, base: Path | str, dest: Path | str | None = None
) -> IncludeResolved:
    """Return a fake IncludeResolved-style dict."""
    # Preserve raw string form to retain trailing slashes
    raw_path = path if isinstance(path, str) else str(path)
    d: dict[str, Path | str] = {
        "path": raw_path,
        "base": Path(base),
        "origin": "test",
    }
    if dest:
        d["dest"] = Path(dest)
    return cast(IncludeResolved, d)


def make_build_cfg(
    tmp_path: Path,
    include: list[IncludeResolved],
    exclude: list[PathResolved] | None = None,
    *,
    respect_gitignore: bool = True,
    log_level: str = "info",
    dry_run: bool = False,
    out: PathResolved | None = None,
) -> BuildConfig:
    """Return a fake, fully-populated BuildConfig."""
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
) -> BuildConfigInput:
    """Convenient shorthand for constructing raw (pre-resolve) build inputs."""
    cfg: dict[str, object] = {}
    if include is not None:
        cfg["include"] = include
    if exclude is not None:
        cfg["exclude"] = exclude
    if out is not None:
        cfg["out"] = out
    cfg.update(extra)
    return cast(BuildConfigInput, cfg)
