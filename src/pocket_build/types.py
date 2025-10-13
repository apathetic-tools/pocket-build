# src/pocket_build/types.py

from __future__ import annotations

from typing import List, TypedDict, Union

from typing_extensions import NotRequired


class IncludeEntry(TypedDict, total=False):
    src: str
    dest: NotRequired[str]


class MetaBuildConfig(TypedDict, total=False):
    include_base: str
    exclude_base: str
    out_base: str
    origin: str


class BuildConfig(TypedDict, total=False):
    include: List[Union[str, IncludeEntry]]
    exclude: List[str]
    out: str
    __meta__: MetaBuildConfig


class RootConfig(TypedDict, total=False):
    builds: List[BuildConfig]
