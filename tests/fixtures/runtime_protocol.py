# /tests/package_protocol.py
# ruff: noqa: E501
import pathlib
from typing import Any, Dict, List, Optional, Protocol

import pocket_build.types


class RuntimeLike(Protocol):
    """Auto-generated interface of the pocket_build package."""

    BuildConfig: type
    RESET: Any

    def colorize(self, text: str, color: str, use_color: bool | None = None) -> str: ...
    def copy_directory(
        self,
        src: pathlib.Path,
        dest: pathlib.Path,
        exclude_patterns: List[str],
        root: pathlib.Path,
        verbose: bool = False,
    ) -> None: ...
    def copy_file(
        self,
        src: pathlib.Path,
        dest: pathlib.Path,
        root: pathlib.Path,
        verbose: bool = False,
    ) -> None: ...
    def copy_item(
        self,
        src: pathlib.Path,
        dest: pathlib.Path,
        exclude_patterns: List[str],
        meta: pocket_build.types.MetaBuildConfig,
        verbose: bool = False,
    ) -> None: ...
    def is_excluded(
        self, path: pathlib.Path, exclude_patterns: List[str], root: pathlib.Path
    ) -> bool: ...
    def load_jsonc(self, path: pathlib.Path) -> Dict[str, Any]: ...
    def main(self, argv: Optional[List[str]] = None) -> int: ...
    def parse_builds(
        self, raw_config: Dict[str, Any]
    ) -> List[pocket_build.types.BuildConfig]: ...
    def run_build(
        self, build_cfg: pocket_build.types.BuildConfig, verbose: bool = False
    ) -> None: ...
    def should_use_color(
        self,
    ) -> bool: ...
