# tests/test_utils_is_exclude.py
"""
Tests for is_excluded_raw and its wrapper is_excluded.

Checklist:
- matches_patterns — simple include/exclude match using relative glob patterns.
- relative_path — confirms relative path resolution against root.
- outside_root — verifies paths outside root never match.
- absolute_pattern — ensures absolute patterns under the same root are matched.
- file_base_special_case — handles case where base itself is a file, not a directory.
- mixed_patterns — validates mixed matching and non-matching patterns.
- wrapper_delegates — checks that the wrapper forwards args correctly.
- gitignore_double_star_diff — '**' not recursive unlike gitignore in ≤Py3.10.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pocket_build.utils_using_runtime as mod_utils_runtime
from pocket_build.utils_types import make_pathresolved


def test_is_excluded_raw_matches_patterns(tmp_path: Path) -> None:
    """
    Verify exclude pattern matching works correctly.

    Example:
      path:     /tmp/.../foo/bar.txt
      root:     /tmp/...
      pattern:  ["foo/*"]
      Result: True
      Explanation: pattern 'foo/*' matches 'foo/bar.txt' relative to root.
    """
    # --- setup ---
    root = tmp_path
    file = root / "foo/bar.txt"
    file.parent.mkdir(parents=True)
    file.touch()

    # --- execute + verify ---
    assert mod_utils_runtime.is_excluded_raw(file, ["foo/*"], root)
    assert not mod_utils_runtime.is_excluded_raw(file, ["baz/*"], root)


def test_is_excluded_raw_relative_path(tmp_path: Path) -> None:
    """
    Handles relative file path relative to given root.

    Example:
      path:     "src/file.txt"
      root:     /tmp/.../
      pattern:  ["src/*"]
      Result: True
      Explanation: path is relative; pattern matches within the same root.
    """
    # --- setup ---
    root = tmp_path
    (root / "src").mkdir()
    (root / "src/file.txt").touch()

    rel_path = Path("src/file.txt")

    # --- execute + verify ---
    assert mod_utils_runtime.is_excluded_raw(rel_path, ["src/*"], root)
    assert not mod_utils_runtime.is_excluded_raw(rel_path, ["dist/*"], root)


def test_is_excluded_raw_outside_root(tmp_path: Path) -> None:
    """
    Paths outside the root should never match.

    Example:
      path:     /tmp/outside.txt
      root:     /tmp/root/
      pattern:  ["*.txt"]
      Result: False
      Explanation: file is not under root; function skips comparison.
    """
    # --- setup ---
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.touch()

    # --- execute + verify ---
    assert not mod_utils_runtime.is_excluded_raw(outside, ["*.txt"], root)


def test_is_excluded_raw_absolute_pattern(tmp_path: Path) -> None:
    """
    Absolute patterns matching under the same root should match.

    Example:
      path:     /tmp/.../a/b/c.txt
      root:     /tmp/.../
      pattern:  ["/tmp/.../a/b/*.txt"]
      Result: True
      Explanation: pattern is absolute but lies within root;
                   converted to relative 'a/b/*.txt'.
    """
    # --- setup ---
    root = tmp_path
    file = root / "a/b/c.txt"
    file.parent.mkdir(parents=True)
    file.touch()

    abs_pattern = str(root / "a/b/*.txt")

    # --- execute + verify ---
    assert mod_utils_runtime.is_excluded_raw(file, [abs_pattern], root)
    assert not mod_utils_runtime.is_excluded_raw(file, [str(root / "x/*.txt")], root)


def test_is_excluded_raw_file_base_special_case(tmp_path: Path) -> None:
    """
    If the base itself is a file, match it directly.

    Example:
      path:     data.csv
      root:     /tmp/.../data.csv
      pattern:  []
      Result: True
      Explanation: root is a file; function returns True
                   when path resolves to that file.
    """
    # --- setup ---
    base_file = tmp_path / "data.csv"
    base_file.touch()

    # path argument can be either relative or absolute
    rel_same = Path("data.csv")
    abs_same = base_file

    # --- execute + verify ---
    assert mod_utils_runtime.is_excluded_raw(rel_same, [], base_file)
    assert mod_utils_runtime.is_excluded_raw(abs_same, [], base_file)

    # unrelated file should not match
    other = tmp_path / "other.csv"
    other.touch()
    assert not mod_utils_runtime.is_excluded_raw(other, [], base_file)


def test_is_excluded_raw_mixed_patterns(tmp_path: Path) -> None:
    """
    Mix of matching and non-matching patterns should behave predictably.

    Example:
      path:     /tmp/.../dir/sample.tmp
      root:     /tmp/.../
      pattern:  ["*.py", "dir/*.tmp", "ignore/*"]
      Result: True
      Explanation: second pattern matches; earlier and later do not.
    """
    # --- setup ---
    root = tmp_path
    file = root / "dir/sample.tmp"
    file.parent.mkdir(parents=True)
    file.touch()

    patterns = ["*.py", "dir/*.tmp", "ignore/*"]

    # --- execute + verify ---
    assert mod_utils_runtime.is_excluded_raw(file, patterns, root)


def test_is_excluded_wrapper_delegates(tmp_path: Path) -> None:
    """
    Integration test for is_excluded wrapper.

    Example:
      path:     foo.txt (relative)
      root:     /tmp/.../
      pattern:  ["*.txt"]
      Result: True
      Explanation: wrapper passes resolved args correctly to is_excluded_raw.
    """
    # --- setup ---
    root = tmp_path
    f = root / "foo.txt"
    f.touch()
    entry = make_pathresolved("foo.txt", root, "cli")
    excludes = [make_pathresolved("*.txt", root, "config")]

    # --- execute + verify ---
    assert mod_utils_runtime.is_excluded(entry, excludes)


def test_is_excluded_raw_gitignore_double_star_diff(tmp_path: Path) -> None:
    """
    Document that gitignore's '**' recursion is NOT emulated.

    Example:
      path:     /tmp/.../dir/sub/file.py
      root:     /tmp/.../
      pattern:  ["dir/**/*.py"]
      Result:   True  (Python ≥3.11)
                False (Python ≤3.10)
      Explanation:
        - In Python ≤3.10, fnmatch treats '**' as simple '*', matching only one level.
        - In Python ≥3.11, fnmatch matches recursively across directories.
        - Our code uses fnmatch directly, so it inherits the platform behavior.
          This test exists to document that difference, not to enforce one side.
    """
    # --- setup ---
    root = tmp_path
    nested = root / "dir/sub/file.py"
    nested.parent.mkdir(parents=True)
    nested.touch()

    # --- execute ---
    result = mod_utils_runtime.is_excluded_raw(nested, ["dir/**/*.py"], root)

    # --- verify ---
    if sys.version_info >= (3, 11):
        # Python 3.11+ uses recursive '**'
        assert result, "Expected True on Python ≥3.11 where '**' is recursive"
    else:
        # Python 3.10 and earlier use single-level '*'
        assert not result, "Expected False on Python ≤3.10 where '**' is shallow"
