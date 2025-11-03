# tests/_30_utils_tests/is_excluded_raw.py
"""Tests for is_excluded_raw and its wrapper is_excluded.

Checklist:
- matches_patterns — simple include/exclude match using relative glob patterns.
- relative_path — confirms relative path resolution against root.
- outside_root — verifies paths outside root never match.
- absolute_pattern — ensures absolute patterns under the same root are matched.
- file_root_special_case — handles case where root itself is a file, not a directory.
- mixed_patterns — validates mixed matching and non-matching patterns.
- wrapper_delegates — checks that the wrapper forwards args correctly.
- gitignore_double_star_diff — '**' not recursive unlike gitignore in ≤Py3.10.
"""

from pathlib import Path

import pocket_build.utils as mod_utils
import pocket_build.utils_types as mod_utils_types


def test_is_excluded_wrapper_delegates(tmp_path: Path) -> None:
    """Integration test for is_excluded wrapper.

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
    entry = mod_utils_types.make_pathresolved("foo.txt", root, "cli")
    excludes = [mod_utils_types.make_pathresolved("*.txt", root, "config")]

    # --- execute + verify ---
    assert mod_utils.is_excluded(entry, excludes)
