# /tests/package_protocol.py
# ruff: noqa: E501
import pathlib
import typing
from typing import Any, Dict, List, Optional, Protocol, Union

import pocket_build.types


class RuntimeLike(Protocol):
    """Auto-generated interface of the pocket_build package."""

    BuildConfig: type
    LEVEL_ORDER: Any
    PROGRAM_ENV: Any
    RESET: Any

    def colorize(self, text: str, color: str, use_color: bool | None = None) -> str: ...
    def copy_directory(
        self,
        src: pathlib.Path,
        dest: pathlib.Path,
        exclude_patterns: List[str],
        root: pathlib.Path,
        dry_run: bool,
    ) -> None: ...
    def copy_file(
        self, src: pathlib.Path, dest: pathlib.Path, root: pathlib.Path, dry_run: bool
    ) -> None: ...
    def copy_item(
        self,
        src: pathlib.Path,
        dest: pathlib.Path,
        exclude_patterns: List[str],
        meta: pocket_build.types.MetaBuildConfig,
        dry_run: bool,
    ) -> None: ...

    current_runtime: Any

    def get_glob_root(self, pattern: str) -> pathlib.Path: ...
    def is_bypass_capture(
        self,
    ) -> bool: ...
    def is_excluded(
        self, path: pathlib.Path, exclude_patterns: List[str], root: pathlib.Path
    ) -> bool: ...
    def load_jsonc(self, path: pathlib.Path) -> Dict[str, Any]: ...
    def log(
        self,
        level: str,
        *values: object,
        sep: str = " ",
        end: str = "\n",
        file: typing.TextIO | None = None,
        flush: bool = False,
        prefix: str | None = None,
    ) -> None: ...
    def main(self, argv: Optional[List[str]] = None) -> int: ...
    def parse_builds(
        self, raw_config: Union[Dict[str, Any], List[Any]]
    ) -> List[pocket_build.types.BuildConfig]: ...
    def run_build(self, build_cfg: pocket_build.types.BuildConfig) -> None: ...
    def should_use_color(
        self,
    ) -> bool: ...
