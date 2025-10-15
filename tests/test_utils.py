# tests/test_utils.py
"""Tests for pocket_build.utils (module and single-file versions)."""

# not doing tests for has_glob_chars()

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from tests.conftest import RuntimeLike

GREEN = "\x1b[32m"


def test_load_jsonc_strips_comments_and_trailing_commas(
    tmp_path: Path,
    runtime_env: RuntimeLike,
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

    result: Dict[str, Any] = runtime_env.load_jsonc(cfg)
    assert result == {"foo": 123}


def test_is_excluded_matches_patterns(
    tmp_path: Path,
    runtime_env: RuntimeLike,
) -> None:
    """Verify exclude pattern matching works correctly."""
    root = tmp_path
    file = root / "foo/bar.txt"
    file.parent.mkdir(parents=True)
    file.touch()

    assert runtime_env.is_excluded(file, ["foo/*"], root)
    assert not runtime_env.is_excluded(file, ["baz/*"], root)


@pytest.mark.parametrize(
    "pattern,expected",
    [
        ("src/**/*.py", Path("src")),  # nested glob
        ("foo/bar/*.txt", Path("foo/bar")),  # single-level glob
        ("assets/*", Path("assets")),  # trailing glob
        ("*.md", Path(".")),  # glob at start (no static prefix)
        ("**/*.js", Path(".")),  # pure glob pattern
        ("no/globs/here", Path("no/globs/here")),  # no globs at all
        ("./src/*/*.cfg", Path("src")),  # leading ./ ignored, stops at *
    ],
)
def test_get_glob_root_extracts_static_prefix(
    runtime_env: RuntimeLike, pattern: str, expected: Path
):
    """get_glob_root() should return the non-glob portion of a path pattern."""
    result = runtime_env.get_glob_root(pattern)
    assert result == expected, f"{pattern!r} → {result}, expected {expected}"
