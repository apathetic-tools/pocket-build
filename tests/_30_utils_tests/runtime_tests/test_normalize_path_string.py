# tests/_30_utils_tests/test_utils.py
"""Tests for package.utils (package and standalone versions)."""

import pytest

import pocket_build.utils_using_runtime as mod_utils_runtime


@pytest.mark.parametrize(
    ("raw", "expected"),
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
    capsys: pytest.CaptureFixture[str],
) -> None:
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
