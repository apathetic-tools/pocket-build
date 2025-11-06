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
        field_path="root.nums",
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
        field_path="root.nums",
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
        field_path="root.nums",
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
        field_path="root.builds",
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
            field_path="root.empty",
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
        field_path="root.nums",
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
        field_path="root.include",
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
        field_path="root.builds",
    )

    # --- verify ---
    assert ok is True
    pool = summary.errors + summary.strict_warnings + summary.warnings
    assert not any("dry_run" in m and "unknown key" in m for m in pool)


def test_validate_list_value_includes_examples_in_error() -> None:
    """Error messages for fields with examples should include the example."""
    # --- setup ---
    summary = make_summary()
    field_examples = {
        "root.builds.*.include": '["src/", "lib/"]',
    }

    # --- execute ---
    ok = mod_utils_schema._validate_list_value(
        "in build #1",
        "include",
        42,  # wrong type - should be list[str]
        str,
        strict=True,
        summary=summary,
        prewarn=set(),
        field_path="root.builds.*.include",
        field_examples=field_examples,
    )

    # --- verify ---
    assert ok is False
    assert summary.errors
    error_msg = summary.errors[0]
    # Should include the example for build.include
    assert "expected list[str]" in error_msg
    assert '["src/", "lib/"]' in error_msg
    assert "(e.g." in error_msg
