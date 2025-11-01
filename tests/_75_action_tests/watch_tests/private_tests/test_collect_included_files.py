# tests/test_cli_watch.py
"""Tests for package.cli (package and standalone versions)."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

from pathlib import Path

import pocket_build.actions as mod_actions
from tests.utils import (
    make_build_cfg,
    make_include_resolved,
)


def test_collect_included_files_expands_patterns(tmp_path: Path) -> None:
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("A")
    (src / "b.txt").write_text("B")

    build = make_build_cfg(
        tmp_path,
        [make_include_resolved("src/*.txt", tmp_path)],
    )

    # --- execute ---
    files = mod_actions._collect_included_files([build])

    # --- verify ---
    assert set(files) == {src / "a.txt", src / "b.txt"}


def test_collect_included_files_handles_nonexistent_paths(tmp_path: Path) -> None:
    # --- setup ---
    build = make_build_cfg(
        tmp_path,
        [make_include_resolved("missing/**", tmp_path)],
    )

    # --- execute ---
    files = mod_actions._collect_included_files([build])

    # --- verify ---
    assert files == []  # no crash, empty result
