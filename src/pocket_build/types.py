# src/pocket_build/types.py


from pathlib import Path
from typing import Literal, TypedDict

from typing_extensions import NotRequired

OriginType = Literal["cli", "config", "plugin", "default", "code", "gitignore", "test"]


class PathResolved(TypedDict):
    path: Path | str  # absolute or relative to `root`, or a pattern
    root: Path  # canonical origin directory for resolution
    pattern: NotRequired[str]  # the original pattern matching this path

    # meta only
    origin: OriginType  # provenance


class IncludeResolved(PathResolved):
    dest: NotRequired[Path]  # optional override for target name


class MetaBuildConfigResolved(TypedDict):
    # sources of parameters
    cli_root: Path
    config_root: Path


class BuildConfig(TypedDict, total=False):
    include: list[str]
    exclude: list[str]

    # optional per-build override
    strict_config: bool
    out: str
    respect_gitignore: bool
    log_level: str

    # Single-build convenience (propagated upward)
    watch_interval: float


class RootConfig(TypedDict, total=False):
    builds: list[BuildConfig]

    # Defaults that cascade into each build
    log_level: str
    out: str
    respect_gitignore: bool

    # runtime behavior
    strict_config: bool
    watch_interval: float


class BuildConfigResolved(TypedDict):
    include: list[IncludeResolved]
    exclude: list[PathResolved]

    # optional per-build override
    out: PathResolved
    respect_gitignore: bool
    log_level: str

    # runtime flag (CLI only, not persisted in normal configs)
    dry_run: bool

    # global provenance (optional, for audit/debug)
    __meta__: MetaBuildConfigResolved


class RootConfigResolved(TypedDict):
    builds: list[BuildConfigResolved]

    # runtime behavior
    log_level: str
    strict_config: bool
    watch_interval: float


class Runtime(TypedDict):
    log_level: str
    use_color: bool
