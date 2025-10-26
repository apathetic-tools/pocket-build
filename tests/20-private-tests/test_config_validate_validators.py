# tests/private/test_config_validate_validators.py
"""Smoke tests for pocket_build.config_validate internal validator helpers."""

# pyright: reportPrivateUsage=false

from typing import Any, TypedDict

from pytest import MonkeyPatch

import pocket_build.config_validate as mod_validate

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


def test_infer_type_label_basic_types():
    # --- execute and verify ---
    assert "str" in mod_validate._infer_type_label(str)
    assert "list" in mod_validate._infer_type_label(list[str])
    assert "MiniBuild" in mod_validate._infer_type_label(MiniBuild)


def test_infer_type_label_handles_unusual_types():
    """Covers edge cases like custom classes and typing.Any."""

    # --- setup ---
    class Custom: ...

    # --- execute, verify ---
    assert "Custom" in mod_validate._infer_type_label(Custom)
    assert "Any" in mod_validate._infer_type_label(list[Any])
    # Should fall back gracefully on unknown types
    assert isinstance(mod_validate._infer_type_label(Any), str)


# --- _validate_scalar_value -------------------------------------------------


def test_validate_scalar_value_returns_bool():
    # --- execute ---
    result = mod_validate._validate_scalar_value(
        strict=True,
        context="ctx",
        key="x",
        val="abc",
        expected_type=str,
    )

    # --- verify ---
    assert isinstance(result, bool)


def test_validate_scalar_value_accepts_correct_type(monkeypatch: MonkeyPatch):
    # --- setup ---
    called: list[str] = []

    def _fake_log_strict(strict_config: bool, msg: str) -> None:
        called.append(msg)

    # --- patch and execute ---
    monkeypatch.setattr(mod_validate, "_log_strict", _fake_log_strict)
    ok = mod_validate._validate_scalar_value(True, "ctx", "x", 42, int)

    # --- verify ---
    assert ok is True
    assert called == []


def test_validate_scalar_value_rejects_wrong_type(monkeypatch: MonkeyPatch):
    # --- setup ---
    called: list[str] = []

    def _fake_log_strict(strict_config: bool, msg: str) -> None:
        called.append(msg)

    # --- patch and execute ---
    monkeypatch.setattr(mod_validate, "_log_strict", _fake_log_strict)
    ok = mod_validate._validate_scalar_value(True, "ctx", "x", "abc", int)

    # --- verify ---
    assert ok is False
    assert any("expected int" in m for m in called)


def test_validate_scalar_value_handles_fallback_path(monkeypatch: MonkeyPatch):
    """If safe_isinstance raises, fallback isinstance check still works."""

    # --- setup ---
    def _fake_safe_isinstance(_value: Any, _expected_type: Any) -> bool:
        raise TypeError("simulated typing bug")

    # --- patch and execute ---
    monkeypatch.setattr(mod_validate, "safe_isinstance", _fake_safe_isinstance)
    ok = mod_validate._validate_scalar_value(True, "ctx", "x", 5, int)

    # --- verify ---
    assert ok is True  # fallback handled correctly


# --- _validate_list_value ---------------------------------------------------


def test_validate_list_value_accepts_list():
    # --- execute ---
    result = mod_validate._validate_list_value(
        strict=False,
        context="root",
        key="nums",
        val=[1, 2, 3],
        subtype=int,
    )

    # --- verify ---
    assert isinstance(result, bool)


def test_validate_list_value_rejects_nonlist(monkeypatch: MonkeyPatch):
    # --- setup ---
    called: list[str] = []

    def _fake_log_strict(strict_config: bool, msg: str) -> None:
        called.append(msg)

    # --- patch and execute ---
    monkeypatch.setattr(mod_validate, "_log_strict", _fake_log_strict)
    ok = mod_validate._validate_list_value(True, "ctx", "nums", "notalist", int)

    # --- verify ---
    assert ok is False
    assert any("expected list" in m for m in called)


def test_validate_list_value_rejects_wrong_element_type(monkeypatch: MonkeyPatch):
    # --- setup ---
    called: list[str] = []

    def _fake_log_strict(strict_config: bool, msg: str) -> None:
        called.append(msg)

    # --- patch and execute ---
    monkeypatch.setattr(mod_validate, "_log_strict", _fake_log_strict)
    ok = mod_validate._validate_list_value(True, "ctx", "nums", [1, "two", 3], int)

    # --- verify ---
    assert ok is False
    assert any("expected int" in m for m in called)


def test_validate_list_value_handles_typed_dict_elements(monkeypatch: MonkeyPatch):
    # --- setup ---
    called: list[str] = []

    def _fake_log_strict(strict_config: bool, msg: str) -> None:
        called.append(msg)

    val: list[dict[str, Any]] = [
        {"include": ["src"], "out": "dist"},
        {"include": [123], "out": "x"},
    ]

    # --- patch and execute ---
    monkeypatch.setattr(mod_validate, "_log_strict", _fake_log_strict)
    ok = mod_validate._validate_list_value(True, "ctx", "builds", val, MiniBuild)

    # --- verify ---
    assert isinstance(ok, bool)


def test_validate_list_value_accepts_empty_list():
    # --- execute and verify ---
    assert mod_validate._validate_list_value(True, "ctx", "empty", [], int) is True


def test_validate_list_value_rejects_nested_mixed_types(monkeypatch: MonkeyPatch):
    """Nested lists with wrong inner types should fail."""
    # --- setup ---
    called: list[str] = []

    def _fake_log_strict(strict_config: bool, msg: str) -> None:
        called.append(msg)

    # --- patch and execute ---
    monkeypatch.setattr(mod_validate, "_log_strict", _fake_log_strict)
    ok = mod_validate._validate_list_value(
        True, "ctx", "nums", [[1, 2], ["a"]], list[int]
    )

    # --- verify ---
    assert not ok
    assert any("expected list" in msg or "expected int" in msg for msg in called)


def test_validate_list_value_mixed_types_like_integration(monkeypatch: MonkeyPatch):
    """Ensure behavior matches validate_config scenario with list[str] violation."""
    # --- setup ---
    called: list[str] = []

    def _fake_log_strict(strict_config: bool, msg: str) -> None:
        called.append("x")

    # --- patch and execute ---
    monkeypatch.setattr(mod_validate, "_log_strict", _fake_log_strict)
    ok = mod_validate._validate_list_value(True, "ctx", "include", ["src", 42], str)

    # --- verify ---
    assert ok is False
    assert called  # log was triggered


# --- _validate_typed_dict ---------------------------------------------------


def test_validate_typed_dict_accepts_dict():
    # --- execute ---
    result = mod_validate._validate_typed_dict(
        strict=True,
        context="root",
        val={"include": ["src"], "out": "dist"},
        typedict_cls=MiniBuild,
    )

    # --- verify ---
    assert isinstance(result, bool)


def test_validate_typed_dict_rejects_non_dict(monkeypatch: MonkeyPatch):
    # --- setup ---
    called: list[str] = []

    def _fake_log_strict(strict_config: bool, msg: str) -> None:
        called.append(msg)

    # --- patch and execute ---
    monkeypatch.setattr(mod_validate, "_log_strict", _fake_log_strict)
    ok = mod_validate._validate_typed_dict(True, "root", "notadict", MiniBuild)

    # --- verify ---
    assert ok is False
    assert any("expected dict" in m for m in called)


def test_validate_typed_dict_detects_unknown_keys(monkeypatch: MonkeyPatch):
    # --- setup ---
    called: list[str] = []

    def _fake_log_strict(strict_config: bool, msg: str) -> None:
        called.append(msg)

    # --- patch and execute ---
    monkeypatch.setattr(mod_validate, "_log_strict", _fake_log_strict)
    ok = mod_validate._validate_typed_dict(
        True, "root", {"include": ["x"], "out": "y", "weird": 1}, MiniBuild
    )

    # --- verify ---
    assert ok is False
    assert any("unknown key" in m for m in called)


def test_validate_typed_dict_allows_missing_field():
    """Missing field should not cause failure."""
    # --- setup ---
    val = {"out": "dist"}  # 'include' missing

    # --- execute ---
    ok = mod_validate._validate_typed_dict(True, "ctx", val, MiniBuild)

    # --- verify ---
    assert ok is True


def test_validate_typed_dict_nested_recursion(monkeypatch: MonkeyPatch):
    """Nested TypedDict structures should validate recursively."""
    # --- setup ---
    called: list[str] = []

    def _fake_log_strict(strict_config: bool, msg: str) -> None:
        called.append("bad")

    class Outer(TypedDict):
        inner: MiniBuild

    good: Outer = {"inner": {"include": ["src"], "out": "dist"}}
    bad: Outer = {"inner": {"include": [123], "out": "dist"}}  # type: ignore[assignment]

    # --- patch, execute and verify ---
    monkeypatch.setattr(mod_validate, "_log_strict", _fake_log_strict)
    assert mod_validate._validate_typed_dict(True, "root", good, Outer)
    assert not mod_validate._validate_typed_dict(True, "root", bad, Outer)


# --- _check_schema_conformance smoke ---------------------------------------


def test_check_schema_conformance_smoke():
    # --- setup ---
    schema: dict[str, Any] = {"include": list[str], "out": str}
    cfg: dict[str, Any] = {"include": ["src"], "out": "dist"}

    # --- execute ---
    result = mod_validate._check_schema_conformance(True, cfg, schema, "root")

    # --- verify ---
    assert isinstance(result, bool)


def test_check_schema_conformance_matches_list_validator(monkeypatch: MonkeyPatch):
    """Ensures _check_schema_conformance returns
    same validity as low-level list validator."""
    # --- setup ---
    called: list[str] = []

    def _fake_log_strict(strict_config: bool, msg: str) -> None:
        called.append("x")

    schema: dict[str, Any] = {"include": list[str], "out": str}
    cfg: dict[str, Any] = {"include": ["src", 42], "out": "dist"}

    # --- patch and execute ---
    monkeypatch.setattr(mod_validate, "_log_strict", _fake_log_strict)
    ok_list = mod_validate._validate_list_value(
        True, "ctx", "include", ["src", 42], str
    )
    ok_schema = mod_validate._check_schema_conformance(True, cfg, schema, "ctx")

    # --- verify ---
    assert not ok_list
    assert not ok_schema
