# tests/20-private/test_utils_schema_validators.py
"""Smoke tests for pocket_build.config_validate internal validator helpers."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

from typing import Any, TypedDict

import pytest

import pocket_build.utils_schema as mod_utils_schema
import pocket_build.utils_types as mod_utils_types
from tests.utils import make_summary, patch_everywhere


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# --- Fixtures / Sample TypedDicts -------------------------------------------


class MiniBuild(TypedDict):
    include: list[str]
    out: str


class Nested(TypedDict):
    meta: dict[str, Any]
    name: str


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


# --- _infer_type_label ------------------------------------------------------


def test_infer_type_label_basic_types() -> None:
    # --- execute and verify ---
    assert "str" in mod_utils_schema._infer_type_label(str)
    assert "list" in mod_utils_schema._infer_type_label(list[str])
    assert "MiniBuild" in mod_utils_schema._infer_type_label(MiniBuild)


def test_infer_type_label_handles_unusual_types() -> None:
    """Covers edge cases like custom classes and typing.Any."""

    # --- setup ---
    class Custom: ...

    # --- execute, verify ---
    assert "Custom" in mod_utils_schema._infer_type_label(Custom)
    assert "Any" in mod_utils_schema._infer_type_label(list[Any])
    # Should fall back gracefully on unknown types
    assert isinstance(mod_utils_schema._infer_type_label(Any), str)


# --- _validate_scalar_value -------------------------------------------------


def test_validate_scalar_value_returns_bool() -> None:
    # --- execute ---
    result = mod_utils_schema._validate_scalar_value(
        strict=True,
        context="ctx",
        key="x",
        val="abc",
        expected_type=str,
        summary=make_summary(),
    )

    # --- verify ---
    assert isinstance(result, bool)


def test_validate_scalar_value_accepts_correct_type() -> None:
    # --- setup ---
    summary = make_summary()
    print(summary)

    # --- patch and execute ---
    ok = mod_utils_schema._validate_scalar_value(
        "ctx",
        "x",
        42,
        int,
        strict=True,
        summary=summary,
    )

    # --- verify ---
    assert ok is True
    assert not summary.errors
    assert not summary.warnings
    assert not summary.strict_warnings


def test_validate_scalar_value_rejects_wrong_type() -> None:
    # --- setup ---
    summary = make_summary()

    # --- patch and execute ---
    ok = mod_utils_schema._validate_scalar_value(
        "ctx",
        "x",
        "abc",
        int,
        strict=True,
        summary=summary,
    )

    # --- verify ---
    assert ok is False
    assert any("expected int" in m for m in summary.errors)


def test_validate_scalar_value_handles_fallback_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If safe_isinstance raises, fallback isinstance check still works."""

    # --- setup ---
    def _fake_safe_isinstance(_value: Any, _expected_type: Any) -> bool:
        xmsg = "simulated typing bug"
        raise TypeError(xmsg)

    # --- patch and execute ---
    patch_everywhere(
        monkeypatch,
        mod_utils_types,
        "safe_isinstance",
        _fake_safe_isinstance,
    )
    ok = mod_utils_schema._validate_scalar_value(
        "ctx",
        "x",
        5,
        int,
        strict=True,
        summary=make_summary(),
    )

    # --- verify ---
    assert ok is True  # fallback handled correctly


# --- _validate_list_value ---------------------------------------------------


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


# --- _validate_typed_dict ---------------------------------------------------


def test_validate_typed_dict_accepts_dict() -> None:
    # --- execute ---
    result = mod_utils_schema._validate_typed_dict(
        context="root",
        val={"include": ["src"], "out": "dist"},
        typedict_cls=MiniBuild,
        strict=True,
        summary=make_summary(),
        prewarn=set(),
    )

    # --- verify ---
    assert isinstance(result, bool)


def test_validate_typed_dict_rejects_non_dict() -> None:
    # --- setup ---
    summary = make_summary()

    # --- patch and execute ---
    ok = mod_utils_schema._validate_typed_dict(
        "root",
        "notadict",
        MiniBuild,
        strict=True,
        summary=summary,
        prewarn=set(),
    )

    # --- verify ---
    assert ok is False
    assert any("expected an object" in m for m in summary.errors)


def test_validate_typed_dict_detects_unknown_keys() -> None:
    # --- setup ---
    summary = make_summary()

    # --- patch and execute ---
    ok = mod_utils_schema._validate_typed_dict(
        "root",
        {"include": ["x"], "out": "y", "weird": 1},
        MiniBuild,
        strict=True,
        summary=summary,
        prewarn=set(),
    )

    # --- verify ---
    assert ok is False
    # unknown keys appear as warnings (or strict_warnings if strict=True)
    pool = summary.warnings + summary.strict_warnings + summary.errors
    assert any("unknown key" in m.lower() for m in pool)


def test_validate_typed_dict_allows_missing_field() -> None:
    """Missing field should not cause failure."""
    # --- setup ---
    val = {"out": "dist"}  # 'include' missing

    # --- execute ---
    ok = mod_utils_schema._validate_typed_dict(
        "ctx",
        val,
        MiniBuild,
        strict=True,
        summary=make_summary(),
        prewarn=set(),
    )

    # --- verify ---
    assert ok is True


def test_validate_typed_dict_nested_recursion() -> None:
    """Nested TypedDict structures should validate recursively."""

    # --- setup ---
    class Outer(TypedDict):
        inner: MiniBuild

    good: Outer = {"inner": {"include": ["src"], "out": "dist"}}
    bad: Outer = {"inner": {"include": [123], "out": "dist"}}  # type: ignore[assignment]

    # --- patch, execute and verify ---
    summary1 = mod_utils_schema.ValidationSummary(True, [], [], [], True)
    assert mod_utils_schema._validate_typed_dict(
        "root",
        good,
        Outer,
        strict=True,
        summary=summary1,
        prewarn=set(),
    )

    summary2 = mod_utils_schema.ValidationSummary(True, [], [], [], True)
    assert not mod_utils_schema._validate_typed_dict(
        "root",
        bad,
        Outer,
        strict=True,
        summary=summary2,
        prewarn=set(),
    )
    assert summary2.errors  # collected from inner validation


def test_validate_typed_dict_respects_prewarn() -> None:
    """Keys in prewarn set should be skipped and not trigger unknown-key messages."""
    # --- setup ---
    cfg: dict[str, Any] = {"include": ["src"], "out": "dist", "dry_run": True}
    prewarn = {"dry_run"}
    summary = make_summary()

    # --- execute ---
    ok = mod_utils_schema._validate_typed_dict(
        "ctx",
        cfg,
        MiniBuild,
        strict=True,
        summary=summary,
        prewarn=prewarn,
    )

    # --- verify ---
    assert ok is True
    pool = summary.errors + summary.strict_warnings + summary.warnings
    assert not any("dry_run" in m and "unknown key" in m for m in pool)
