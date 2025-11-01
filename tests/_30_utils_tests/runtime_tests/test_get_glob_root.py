# tests/_30_utils_tests/test_utils.py
"""Tests for package.utils (package and standalone versions)."""

# not doing tests for has_glob_chars()

from pathlib import Path

import pytest

import pocket_build.utils_using_runtime as mod_utils_runtime


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        # Basic glob roots
        ("src/**/*.py", Path("src")),
        ("foo/bar/*.txt", Path("foo/bar")),
        ("assets/*", Path("assets")),
        ("*.md", Path()),
        ("**/*.js", Path()),
        ("no/globs/here", Path("no/globs/here")),
        ("./src/*/*.cfg", Path("src")),
        ("src\\**\\*.py", Path("src")),  # backslashes normalized
        ("a/b\\c/*", Path("a/b/c")),  # mixed separators normalized
        ("", Path()),
        (".", Path()),
        ("./", Path()),
        ("src/*/sub/*.py", Path("src")),
        # Escaped spaces should normalize gracefully
        ("dir\\ with\\ spaces/file.txt", Path("dir with spaces/file.txt")),
        # Multiple escaped spaces
        ("folder\\ with\\ many\\ spaces/**", Path("folder with many spaces")),
        # Escaped spaces at root (no subdirs)
        ("file\\ with\\ space.txt", Path("file with space.txt")),
        # Redundant slashes collapsed
        ("folder///deep//file.txt", Path("folder/deep/file.txt")),
    ],
)
def test_get_glob_root_extracts_static_prefix(
    pattern: str,
    expected: Path,
) -> None:
    """get_glob_root() should return the non-glob portion of a path pattern."""
    # --- execute --
    result = mod_utils_runtime.get_glob_root(pattern)

    # --- verify ---
    assert result == expected, f"{pattern!r} → {result}, expected {expected}"
