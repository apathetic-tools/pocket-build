# tests/_30_utils_tests/test_utils.py
"""Tests for package.utils (package and standalone versions)."""

# not doing tests for has_glob_chars()

import math

import pytest

import pocket_build.utils as mod_utils


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # ✅ Integers
        (0, "s"),
        (1, ""),
        (2, "s"),
        (999, "s"),
        (-1, "s"),  # negative counts still pluralized
        # ✅ Floats
        (0.0, "s"),
        (1.0, ""),
        (1.1, "s"),
        (math.inf, "s"),
        # ✅ Sequences and containers
        ([], "s"),
        ([1], ""),
        ([1, 2], "s"),
        ("", "s"),
        ("a", ""),
        ("abc", "s"),
        ({}, "s"),
        ({"a": 1}, ""),
        ({"a": 1, "b": 2}, "s"),
        # ✅ Custom objects with __len__()
        (type("Fake", (), {"__len__": lambda self: 1})(), ""),  # noqa: ARG005 # type: ignore[reportUnknownLambdaType]
        (type("Fake", (), {"__len__": lambda self: 2})(), "s"),  # noqa: ARG005 # type: ignore[reportUnknownLambdaType]
        # ✅ Non-countable objects
        (object(), "s"),
        (None, "s"),
    ],
)
def test_plural_behavior(value: object, expected: str) -> None:
    """plural() should append 's' for pluralizable values,
    and '' for singular ones (1 or length == 1).
    """
    # --- execute ---
    result = mod_utils.plural(value)

    # --- verify ---
    assert result == expected, f"{value!r} → {result!r}, expected {expected!r}"


def test_plural_custom_len_error_fallback() -> None:
    """Objects defining __len__ that raise errors should fall back gracefully."""

    # --- setup ---
    class Weird:
        def __len__(self) -> int:
            xmsg = "unusable len()"
            raise TypeError(xmsg)

    # --- execute ---
    result = mod_utils.plural(Weird())

    # --- verify ---
    assert result == "s", "Expected fallback to plural form on len() failure"
