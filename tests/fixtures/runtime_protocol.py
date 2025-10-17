# /tests/package_protocol.py
# ruff: noqa: E501
import argparse
import pathlib
import typing
from typing import Any, Callable, Dict, List, Optional, Protocol, Union

import pocket_build.types


class RuntimeLike(Protocol):
    """Auto-generated interface of the pocket_build package."""

    BuildConfig: type
    IncludeEntry: type
    LEVEL_ORDER: Any
    MetaBuildConfig: type
    Metadata: type
    PROGRAM_DISPLAY: Any
    PROGRAM_ENV: Any
    PROGRAM_SCRIPT: Any
    RESET: Any
    RootConfig: type
    Runtime: type

    def _collect_included_files(
        self, resolved_builds: list[pocket_build.types.BuildConfig]
    ) -> list[pathlib.Path]: ...
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

    def find_config(
        self, args: argparse.Namespace, cwd: pathlib.Path
    ) -> pathlib.Path | None: ...
    def get_glob_root(self, pattern: str) -> pathlib.Path: ...
    def get_metadata(
        self,
    ) -> pocket_build.meta.Metadata: ...
    def has_glob_chars(self, s: str) -> bool: ...
    def is_bypass_capture(
        self,
    ) -> bool: ...
    def is_excluded(
        self, path: pathlib.Path, exclude_patterns: List[str], root: pathlib.Path
    ) -> bool: ...
    def load_config(
        self, config_path: pathlib.Path
    ) -> dict[str, typing.Any] | list[typing.Any]: ...
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
    def resolve_build_config(
        self,
        build_cfg: pocket_build.types.BuildConfig,
        args: argparse.Namespace,
        config_dir: pathlib.Path,
        cwd: pathlib.Path,
        root_cfg: pocket_build.types.RootConfig | None = None,
    ) -> pocket_build.types.BuildConfig: ...
    def run_all_builds(
        self, resolved_builds: list[pocket_build.types.BuildConfig], dry_run: bool
    ) -> None: ...
    def run_build(self, build_cfg: pocket_build.types.BuildConfig) -> None: ...
    def run_selftest(
        self,
    ) -> bool: ...
    def should_use_color(
        self,
    ) -> bool: ...
    def watch_for_changes(
        self,
        rebuild_func: Callable[[], None],
        resolved_builds: list[pocket_build.types.BuildConfig],
        interval: float = 1.0,
    ) -> None: ...
