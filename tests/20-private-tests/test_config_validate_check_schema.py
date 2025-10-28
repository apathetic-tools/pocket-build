# tests/private/test_config_validate_check_schema.py
"""Focused tests for pocket_build.config_validate._check_schema_conformance."""

# pyright: reportPrivateUsage=false

from typing import Any, TypedDict

import pocket_build.config_validate as mod_validate
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

# --- core behavior ---------------------------------------------------------


def test_accepts_matching_simple_types() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"foo": str, "bar": int}
    cfg: dict[str, Any] = {"foo": "hi", "bar": 42}
    summary = make_summary()

    # --- execute and validate ---
    assert (
        mod_validate._check_schema_conformance(
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
        mod_validate._check_schema_conformance(
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
        mod_validate._check_schema_conformance(
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
        mod_validate._check_schema_conformance(
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
        mod_validate._check_schema_conformance(
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
        mod_validate._check_schema_conformance(
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
        mod_validate._check_schema_conformance(
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
        mod_validate._check_schema_conformance(
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
        mod_validate._check_schema_conformance(
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
        mod_validate._check_schema_conformance(
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
        mod_validate._check_schema_conformance(
            True, cfg, schema, "root", summary=summary
        )
        is False
    )


def test_empty_schema_and_config() -> None:
    # --- setup ---
    summary = make_summary()

    # --- execute and validate ---
    assert mod_validate._check_schema_conformance(
        False, {}, {}, "root", summary=summary
    )
