# tests/test_utils.py
"""Tests for package.utils (module and single-file versions)."""

# not doing tests for has_glob_chars()

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest


def test_load_jsonc_strips_comments_and_trailing_commas(
    tmp_path: Path,
) -> None:
    """Ensure JSONC loader removes comments and trailing commas."""
    import pocket_build.utils_core as mod_utils_core

    # --- setup ---
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

    # --- execute ---
    result: Dict[str, Any] = mod_utils_core.load_jsonc(cfg)

    # --- verify ---
    assert result == {"foo": 123}


def test_is_excluded_matches_patterns(
    tmp_path: Path,
) -> None:
    """Verify exclude pattern matching works correctly."""
    import pocket_build.utils_core as mod_utils_core

    # --- setup ---
    root = tmp_path
    file = root / "foo/bar.txt"
    file.parent.mkdir(parents=True)
    file.touch()

    # --- execute and verify ---
    assert mod_utils_core.is_excluded(file, ["foo/*"], root)
    assert not mod_utils_core.is_excluded(file, ["baz/*"], root)


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
    pattern: str,
    expected: Path,
) -> None:
    """get_glob_root() should return the non-glob portion of a path pattern."""
    import pocket_build.utils_core as mod_utils_core

    # --- execute ---
    result = mod_utils_core.get_glob_root(pattern)

    # --- verify ---
    assert result == expected, f"{pattern!r} → {result}, expected {expected}"
