# src/pocket_build/types.py

from __future__ import annotations

from typing import List, TypedDict, Union

from typing_extensions import NotRequired


class IncludeEntry(TypedDict, total=False):
    src: str
    dest: NotRequired[str]


class MetaBuildConfig(TypedDict, total=False):
    include_base: str
    include_add_base: str
    exclude_base: str
    exclude_add_base: str
    out_base: str
    origin: str


class BuildConfig(TypedDict, total=False):
    include: List[Union[str, IncludeEntry]]
    exclude: List[str]
    __meta__: MetaBuildConfig

    # optional per-build override
    out: str
    respect_gitignore: bool

    # optional single-build convenience override
    log_level: str

    # runtime flag (CLI only, not persisted in normal configs)
    dry_run: bool


class RootConfig(TypedDict, total=False):
    builds: List[BuildConfig]

    # runtime behavior
    log_level: str

    # default for each build
    out: str
    respect_gitignore: bool


class Runtime(TypedDict):
    log_level: str
    use_color: bool
