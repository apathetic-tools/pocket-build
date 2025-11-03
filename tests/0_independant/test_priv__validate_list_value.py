# tests/_30_utils_tests/schema/private/test_validate_list_value.py
"""Smoke tests for pocket_build.config_validate internal validator helpers."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

from typing import Any, TypedDict

import pocket_build.utils_schema as mod_utils_schema
from tests.utils import make_summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# --- Fixtures / Sample TypedDicts -------------------------------------------


class MiniBuild(TypedDict):
    include: list[str]
    out: str


def test_validate_list_value_accepts_list() -> None:
    # --- execute ---
    result = mod_utils_schema._validate_list_value(
        context="root",
        key="nums",
        val=[1, 2, 3],
        subtype=int,
        strict=False,
        summary=make_summary(),
        prewarn=set(),
    )

    # --- verify ---
    assert isinstance(result, bool)


def test_validate_list_value_rejects_nonlist() -> None:
    # --- setup ---
    summary = make_summary()

    # --- patch and execute ---
    ok = mod_utils_schema._validate_list_value(
        "ctx",
        "nums",
        "notalist",
        int,
        strict=True,
        summary=summary,
        prewarn=set(),
    )

    # --- verify ---
    assert ok is False
    assert any("expected list" in m for m in summary.errors)


def test_validate_list_value_rejects_wrong_element_type() -> None:
    # --- setup ---
    summary = make_summary()

    # --- patch and execute ---
    ok = mod_utils_schema._validate_list_value(
        "ctx",
        "nums",
        [1, "two", 3],
        int,
        strict=True,
        summary=summary,
        prewarn=set(),
    )

    # --- verify ---
    assert ok is False
    assert any("expected int" in m for m in summary.errors)


def test_validate_list_value_handles_typed_dict_elements() -> None:
    # --- setup ---
    val: list[dict[str, Any]] = [
        {"include": ["src"], "out": "dist"},
        {"include": [123], "out": "x"},
    ]
    summary = make_summary()

    # --- patch and execute ---
    ok = mod_utils_schema._validate_list_value(
        "ctx",
        "builds",
        val,
        MiniBuild,
        strict=True,
        summary=summary,
        prewarn=set(),
    )

    # --- verify ---
    assert isinstance(ok, bool)
    # should record some message (error under strict)
    assert summary.errors or summary.strict_warnings or summary.warnings


def test_validate_list_value_accepts_empty_list() -> None:
    # --- execute and verify ---
    assert (
        mod_utils_schema._validate_list_value(
            "ctx",
            "empty",
            [],
            int,
            strict=True,
            summary=make_summary(),
            prewarn=set(),
        )
        is True
    )


def test_validate_list_value_rejects_nested_mixed_types() -> None:
    """Nested lists with wrong inner types should fail."""
    # --- setup ---
    summary = make_summary()

    # --- patch and execute ---
    ok = mod_utils_schema._validate_list_value(
        "ctx",
        "nums",
        [[1, 2], ["a"]],
        list[int],
        strict=True,
        summary=summary,
        prewarn=set(),
    )

    # --- verify ---
    assert not ok
    assert any(("expected list" in m) or ("expected int" in m) for m in summary.errors)


def test_validate_list_value_mixed_types_like_integration() -> None:
    """Ensure behavior matches validate_config scenario with list[str] violation."""
    # --- setup ---
    summary = make_summary()

    # --- patch and execute ---
    ok = mod_utils_schema._validate_list_value(
        "ctx",
        "include",
        ["src", 42],
        str,
        strict=True,
        summary=summary,
        prewarn=set(),
    )

    # --- verify ---
    assert ok is False
    assert summary.errors  # message was collected


def test_validate_list_value_respects_prewarn() -> None:
    """Elements prewarned at parent level should not trigger duplicate errors."""
    # --- setup ---
    summary = make_summary()
    prewarn = {"dry_run"}
    val: list[dict[str, Any]] = [
        {"include": ["src"], "out": "dist", "dry_run": True},
        {"include": ["src2"], "out": "dist2", "dry_run": True},
    ]

    # --- execute ---
    ok = mod_utils_schema._validate_list_value(
        "ctx",
        "builds",
        val,
        MiniBuild,
        strict=True,
        summary=summary,
        prewarn=prewarn,
    )

    # --- verify ---
    assert ok is True
    pool = summary.errors + summary.strict_warnings + summary.warnings
    assert not any("dry_run" in m and "unknown key" in m for m in pool)
