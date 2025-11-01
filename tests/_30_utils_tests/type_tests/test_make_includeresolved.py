# tests/_30_utils_tests/test_utils.py
"""Tests for package.utils (package and standalone versions)."""

import pocket_build.utils_types as mod_utils_types


def test_make_includeresolved_preserves_trailing_slash() -> None:
    # --- execute --
    entry = mod_utils_types.make_includeresolved("src/", root=".", origin="test")

    # --- verify ---
    assert isinstance(entry["path"], str)
    assert entry["path"].endswith("/"), (
        f"expected trailing slash, got {entry['path']!r}"
    )
