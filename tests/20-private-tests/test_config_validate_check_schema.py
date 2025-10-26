# tests/private/test_config_validate_check_schema.py
"""Focused tests for pocket_build.config_validate._check_schema_conformance."""

# pyright: reportPrivateUsage=false

from typing import Any, TypedDict

from pytest import MonkeyPatch, fixture

import pocket_build.config_validate as mod_validate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# --- fixtures --------------------------------------------------------------


class MiniBuild(TypedDict, total=False):
    include: list[str]
    out: str
    strict_config: bool


@fixture(autouse=True)
def mute_log(monkeypatch: MonkeyPatch) -> None:
    """Silence logging for clean test output."""

    def _silent_log(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(mod_validate, "log", _silent_log)


# @fixture(autouse=True)
# def silent_logs(monkeypatch: MonkeyPatch) -> None:
#     """Silence all logs during tests via LOG_LEVEL=silent."""
#     monkeypatch.setenv("LOG_LEVEL", "silent")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

# --- core behavior ---------------------------------------------------------


def test_accepts_matching_simple_types() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"foo": str, "bar": int}
    cfg: dict[str, Any] = {"foo": "hi", "bar": 42}

    # --- execute and validate ---
    assert mod_validate._check_schema_conformance(False, cfg, schema, "root") is True


def test_rejects_wrong_type() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"foo": str}
    cfg = {"foo": 123}

    # --- execute and validate ---
    assert mod_validate._check_schema_conformance(True, cfg, schema, "root") is False


def test_list_of_str_ok() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"items": list[str]}
    cfg = {"items": ["a", "b", "c"]}

    # --- execute and validate ---
    assert mod_validate._check_schema_conformance(False, cfg, schema, "root") is True


def test_list_with_bad_inner_type() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"items": list[str]}
    cfg: dict[str, Any] = {"items": ["a", 42]}

    # --- execute and validate ---
    assert mod_validate._check_schema_conformance(True, cfg, schema, "root") is False


def test_list_of_typeddict_allows_dicts() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"builds": list[MiniBuild]}
    cfg: dict[str, Any] = {"builds": [{"include": ["src"], "out": "dist"}]}

    # --- execute and validate ---
    assert mod_validate._check_schema_conformance(False, cfg, schema, "root") is True


def test_list_of_typeddict_rejects_non_dict() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"builds": list[MiniBuild]}
    cfg = {"builds": ["bad"]}

    # --- execute and validate ---
    assert mod_validate._check_schema_conformance(True, cfg, schema, "root") is False


def test_unknown_keys_fail_in_strict() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"foo": str}
    cfg: dict[str, Any] = {"foo": "x", "unknown": 1}

    # --- execute and validate ---
    assert mod_validate._check_schema_conformance(True, cfg, schema, "ctx") is False


def test_unknown_keys_warn_in_non_strict() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"foo": str}
    cfg: dict[str, Any] = {"foo": "x", "unknown": 1}

    # --- execute and validate ---
    assert mod_validate._check_schema_conformance(False, cfg, schema, "ctx") is True


def test_prewarn_keys_ignored() -> None:
    # --- setup ---
    schema: dict[str, type[Any]] = {"foo": str, "bar": int}
    cfg: dict[str, Any] = {"foo": 1, "bar": "oops"}

    # --- execute and validate ---
    # prewarn tells it to skip foo
    assert (
        mod_validate._check_schema_conformance(
            True, cfg, schema, "ctx", prewarn={"foo"}
        )
        is False
    )


def test_list_of_typeddict_with_invalid_inner_type():
    # --- setup ---
    schema = {"builds": list[MiniBuild]}
    cfg: dict[str, Any] = {"builds": [{"include": [123], "out": "dist"}]}
    # --- execute and validate ---
    assert mod_validate._check_schema_conformance(True, cfg, schema, "root") is False


def test_extra_field_in_typeddict_strict():
    # --- setup ---
    schema = {"builds": list[MiniBuild]}
    cfg: dict[str, Any] = {
        "builds": [{"include": ["src"], "out": "dist", "weird": True}]
    }
    # --- execute and validate ---
    assert mod_validate._check_schema_conformance(True, cfg, schema, "root") is False


def test_empty_schema_and_config():
    # --- execute and validate ---
    assert mod_validate._check_schema_conformance(False, {}, {}, "root")
