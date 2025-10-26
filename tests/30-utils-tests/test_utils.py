# tests/test_utils.py
"""Tests for package.utils (module and single-file versions)."""

# not doing tests for has_glob_chars()

from pathlib import Path

import pytest
from pytest import CaptureFixture

import pocket_build.utils_using_runtime as mod_utils_runtime
from pocket_build.utils_types import make_includeresolved

# ---------------------------------------------------------------------------
# get_glob_root()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pattern,expected",
    [
        # Basic glob roots
        ("src/**/*.py", Path("src")),
        ("foo/bar/*.txt", Path("foo/bar")),
        ("assets/*", Path("assets")),
        ("*.md", Path(".")),
        ("**/*.js", Path(".")),
        ("no/globs/here", Path("no/globs/here")),
        ("./src/*/*.cfg", Path("src")),
        ("src\\**\\*.py", Path("src")),  # backslashes normalized
        ("a/b\\c/*", Path("a/b/c")),  # mixed separators normalized
        ("", Path(".")),
        (".", Path(".")),
        ("./", Path(".")),
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
):
    """get_glob_root() should return the non-glob portion of a path pattern."""
    # --- setup and execute --
    result = mod_utils_runtime.get_glob_root(pattern)

    # --- verify ---
    assert result == expected, f"{pattern!r} → {result}, expected {expected}"


# ---------------------------------------------------------------------------
# normalize_path_string()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        # ✅ Simple normalization
        ("src/**/*.py", "src/**/*.py"),
        ("foo/bar/*.txt", "foo/bar/*.txt"),
        ("a/b\\c/*", "a/b/c/*"),
        ("src\\**\\*.py", "src/**/*.py"),
        ("folder///subdir//file.txt", "folder/subdir/file.txt"),
        ("./src/file.txt", "./src/file.txt"),
        # ✅ Escaped spaces → normalize with warning
        ("dir\\ with\\ spaces/file.txt", "dir with spaces/file.txt"),
        ("folder\\ with\\ many\\ spaces/**", "folder with many spaces/**"),
        # ✅ Trailing whitespace trimmed
        ("  ./src/file.txt  ", "./src/file.txt"),
        # ✅ Empty / trivial
        ("", ""),
        (" ", ""),
        # ✅ Previously invalid literal backslashes → now normalize
        ("dir\\back/file.txt", "dir/back/file.txt"),
        ("foo\\bar.txt", "foo/bar.txt"),
        ("path\\to\\thing", "path/to/thing"),
        # ✅ URL-like paths (preserve protocol //)
        ("file://server//share", "file://server/share"),
        ("http://example.com//foo//bar", "http://example.com/foo/bar"),
    ],
)
def test_normalize_path_string_behavior(
    raw: str,
    expected: str,
    capsys: CaptureFixture[str],
):
    """normalize_path_string() should produce normalized cross-platform paths."""
    # --- execute ---
    result = mod_utils_runtime.normalize_path_string(raw)

    # --- verify ---
    # normalization
    assert result == expected, f"{raw!r} → {result!r}, expected {expected!r}"

    # --- if escaped spaces were present, ensure we warned once ---
    if "\\ " in raw:
        stderr = capsys.readouterr().err
        assert "Normalizing escaped spaces" in stderr
    else:
        stderr = capsys.readouterr().err
        assert stderr == ""


def test_make_includeresolved_preserves_trailing_slash():
    # --- setup and execute --
    entry = make_includeresolved("src/", base=".", origin="test")

    # --- verify ---
    assert isinstance(entry["path"], str)
    assert entry["path"].endswith("/"), (
        f"expected trailing slash, got {entry['path']!r}"
    )
