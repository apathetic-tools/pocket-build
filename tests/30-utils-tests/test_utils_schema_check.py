# tests/30-utils-tests/test_utils_schema_check.py
"""Focused tests for pocket_build.config_validate._check_schema_conformance."""

# pyright: reportPrivateUsage=false

from typing import Any, TypedDict

import pocket_build.utils_schema as mod_utils_schema
from tests.utils import make_summary

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# --- fixtures --------------------------------------------------------------


class MiniBuild(TypedDict, total=False):
    include: list[str]
    out: str
    strict_config: bool


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


# --- smoke -----------------------------------------------------


def test_check_schema_conformance_matches_list_validator() -> None:
    """Ensures _check_schema_conformance returns
    same validity as low-level list validator."""
    # --- setup ---
    schema: dict[str, Any] = {"include": list[str], "out": str}
    cfg: dict[str, Any] = {"include": ["src", 42], "out": "dist"}

    # --- patch and execute ---
    summary1 = mod_utils_schema.ValidationSummary(True, [], [], [], True)
    ok_list = mod_utils_schema._validate_list_value(
        True,
        "ctx",
        "include",
        ["src", 42],
        str,
        summary=summary1,
        prewarn=set(),
    )

    summary2 = mod_utils_schema.ValidationSummary(True, [], [], [], True)
    ok_schema = mod_utils_schema.check_schema_conformance(
        True, cfg, schema, "ctx", summary=summary2
    )

    # --- verify ---
    assert not ok_list
    assert not ok_schema
    assert summary2.errors  # schema check should have recorded an error


def test_check_schema_conformance_smoke() -> None:
    # --- setup ---
    schema: dict[str, Any] = {"include": list[str], "out": str}
    cfg: dict[str, Any] = {"include": ["src"], "out": "dist"}

    # --- execute ---
    result = mod_utils_schema.check_schema_conformance(
        True, cfg, schema, "root", summary=make_summary()
    )

    # --- verify ---
    assert isinstance(result, bool)


def test_check_schema_conformance_respects_prewarn() -> None:
    """Prewarned keys should be skipped during schema checking."""
    # --- setup ---
    schema: dict[str, Any] = {"include": list[str], "out": str}
    cfg: dict[str, Any] = {"include": ["src"], "out": "dist", "dry_run": True}
    prewarn = {"dry_run"}

    # --- execute ---
    summary = make_summary()
    ok = mod_utils_schema.check_schema_conformance(
        True,
        cfg,
        schema,
        "ctx",
        summary=summary,
        prewarn=prewarn,
    )

    # --- verify ---
    assert ok is True
    pool = summary.errors + summary.strict_warnings + summary.warnings
    assert not any("dry_run" in m and "unknown key" in m for m in pool)


# --- core behavior ---------------------------------------------------------


def test_accepts_matching_simple_types() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"foo": str, "bar": int}
    cfg: dict[str, Any] = {"foo": "hi", "bar": 42}
    summary = make_summary()

    # --- execute and validate ---
    assert (
        mod_utils_schema.check_schema_conformance(
            False, cfg, schema, "root", summary=summary
        )
        is True
    )


def test_rejects_wrong_type() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"foo": str}
    cfg = {"foo": 123}
    summary = make_summary()

    # --- execute and validate ---
    assert (
        mod_utils_schema.check_schema_conformance(
            True, cfg, schema, "root", summary=summary
        )
        is False
    )


def test_list_of_str_ok() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"items": list[str]}
    cfg = {"items": ["a", "b", "c"]}
    summary = make_summary()

    # --- execute and validate ---
    assert (
        mod_utils_schema.check_schema_conformance(
            False, cfg, schema, "root", summary=summary
        )
        is True
    )


def test_list_with_bad_inner_type() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"items": list[str]}
    cfg: dict[str, Any] = {"items": ["a", 42]}
    summary = make_summary()

    # --- execute and validate ---
    assert (
        mod_utils_schema.check_schema_conformance(
            True, cfg, schema, "root", summary=summary
        )
        is False
    )


def test_list_of_typeddict_allows_dicts() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"builds": list[MiniBuild]}
    cfg: dict[str, Any] = {"builds": [{"include": ["src"], "out": "dist"}]}
    summary = make_summary()

    # --- execute and validate ---
    assert (
        mod_utils_schema.check_schema_conformance(
            False, cfg, schema, "root", summary=summary
        )
        is True
    )


def test_list_of_typeddict_rejects_non_dict() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"builds": list[MiniBuild]}
    cfg = {"builds": ["bad"]}
    summary = make_summary()

    # --- execute and validate ---
    assert (
        mod_utils_schema.check_schema_conformance(
            True, cfg, schema, "root", summary=summary
        )
        is False
    )


def test_unknown_keys_fail_in_strict() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"foo": str}
    cfg: dict[str, Any] = {"foo": "x", "unknown": 1}
    summary = make_summary()

    # --- execute and validate ---
    assert (
        mod_utils_schema.check_schema_conformance(
            True, cfg, schema, "ctx", summary=summary
        )
        is False
    )


def test_unknown_keys_warn_in_non_strict() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"foo": str}
    cfg: dict[str, Any] = {"foo": "x", "unknown": 1}
    summary = make_summary()

    # --- execute and validate ---
    assert (
        mod_utils_schema.check_schema_conformance(
            False, cfg, schema, "ctx", summary=summary
        )
        is True
    )


def test_prewarn_keys_ignored() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"foo": str, "bar": int}
    cfg: dict[str, Any] = {"foo": 1, "bar": "oops"}
    summary = make_summary()

    # --- execute and validate ---
    # prewarn tells it to skip foo
    assert (
        mod_utils_schema.check_schema_conformance(
            True, cfg, schema, "ctx", summary=summary, prewarn={"foo"}
        )
        is False
    )


def test_list_of_typeddict_with_invalid_inner_type() -> None:
    # --- setup ---
    schema = {"builds": list[MiniBuild]}
    cfg: dict[str, Any] = {"builds": [{"include": [123], "out": "dist"}]}
    summary = make_summary()

    # --- execute and validate ---
    assert (
        mod_utils_schema.check_schema_conformance(
            True, cfg, schema, "root", summary=summary
        )
        is False
    )


def test_extra_field_in_typeddict_strict() -> None:
    # --- setup ---
    schema = {"builds": list[MiniBuild]}
    cfg: dict[str, Any] = {
        "builds": [{"include": ["src"], "out": "dist", "weird": True}]
    }
    summary = make_summary()

    # --- execute and validate ---
    assert (
        mod_utils_schema.check_schema_conformance(
            True, cfg, schema, "root", summary=summary
        )
        is False
    )


def test_empty_schema_and_config() -> None:
    # --- setup ---
    summary = make_summary()

    # --- execute and validate ---
    assert mod_utils_schema.check_schema_conformance(
        False, {}, {}, "root", summary=summary
    )
