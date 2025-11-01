# tests/_30_utils_tests/test_utils.py
"""Tests for package.utils (package and standalone versions)."""

# not doing tests for has_glob_chars()

from pathlib import Path

import pytest

import pocket_build.utils as mod_utils


@pytest.mark.parametrize(
    ("inner_msg", "path", "expected"),
    [
        # ✅ Simple case — full path
        (
            "Invalid JSONC syntax in /abs/path/config.jsonc: Expecting value",
            Path("/abs/path/config.jsonc"),
            "Invalid JSONC syntax: Expecting value",
        ),
        # ✅ Quoted path
        (
            "Invalid JSONC syntax in '/abs/path/config.jsonc': Expecting value",
            Path("/abs/path/config.jsonc"),
            "Invalid JSONC syntax: Expecting value",
        ),
        # ✅ Double-quoted path
        (
            'Invalid JSONC syntax in "/abs/path/config.jsonc": Expecting value',
            Path("/abs/path/config.jsonc"),
            "Invalid JSONC syntax: Expecting value",
        ),
        # ✅ Filename-only mention
        (
            "Invalid JSONC syntax in config.jsonc: Expecting value",
            Path("/abs/path/config.jsonc"),
            "Invalid JSONC syntax: Expecting value",
        ),
        # ✅ Path without “in” keyword
        (
            "Invalid JSONC syntax /abs/path/config.jsonc: Expecting value",
            Path("/abs/path/config.jsonc"),
            "Invalid JSONC syntax: Expecting value",
        ),
        # ✅ No path mention → unchanged
        (
            "Invalid JSONC syntax: Expecting value",
            Path("/abs/path/config.jsonc"),
            "Invalid JSONC syntax: Expecting value",
        ),
        # ✅ Redundant filename without path
        (
            "Invalid JSONC syntax in 'config.jsonc'",
            Path("/abs/path/config.jsonc"),
            "Invalid JSONC syntax",
        ),
        # ✅ Multiple spaces and dangling colons cleaned
        (
            "Invalid JSONC syntax  in /abs/path/config.jsonc  :  Expecting value",
            Path("/abs/path/config.jsonc"),
            "Invalid JSONC syntax: Expecting value",
        ),
    ],
)
def test_remove_path_in_error_message_normalizes_output(
    inner_msg: str,
    path: Path,
    expected: str,
) -> None:
    """remove_path_in_error_message() should strip redundant path mentions
    and normalize punctuation and whitespace cleanly.
    """
    # --- execute ---
    result = mod_utils.remove_path_in_error_message(inner_msg, path)

    # --- verify ---
    assert result == expected, f"{inner_msg!r} → {result!r}, expected {expected!r}"
