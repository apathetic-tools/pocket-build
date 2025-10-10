from __future__ import annotations

from typing import List, TypedDict, Union

from typing_extensions import NotRequired


class IncludeEntry(TypedDict, total=False):
    src: str
    dest: NotRequired[str]


class BuildConfig(TypedDict, total=False):
    include: List[Union[str, IncludeEntry]]
    exclude: List[str]
    out: str


class RootConfig(TypedDict, total=False):
    builds: List[BuildConfig]
