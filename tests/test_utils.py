# tests/test_utils.py
"""Tests for pocket_build.utils (module and single-file versions)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from conftest import PocketBuildLike

GREEN = "\x1b[32m"


def test_load_jsonc_strips_comments_and_trailing_commas(
    tmp_path: Path,
    pocket_build_env: PocketBuildLike,
) -> None:
    """Ensure JSONC loader removes comments and trailing commas."""
    cfg = tmp_path / "config.jsonc"
    cfg.write_text(
        """
        // a line comment
        # another comment
        {
          /* block comment */
          "foo": 123, // trailing comma next
        }
        """
    )

    result: Dict[str, Any] = pocket_build_env.load_jsonc(cfg)
    assert result == {"foo": 123}


def test_is_excluded_matches_patterns(
    tmp_path: Path,
    pocket_build_env: PocketBuildLike,
) -> None:
    """Verify exclude pattern matching works correctly."""
    root = tmp_path
    file = root / "foo/bar.txt"
    file.parent.mkdir(parents=True)
    file.touch()

    assert pocket_build_env.is_excluded(file, ["foo/*"], root)
    assert not pocket_build_env.is_excluded(file, ["baz/*"], root)
