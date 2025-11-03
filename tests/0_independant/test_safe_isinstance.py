# tests/test_utils_safe_isinstance.py
"""Focused tests for pocket_build.utils_core.safe_isinstance."""

from typing import Any, Literal, TypedDict, TypeVar

import pocket_build.utils_types as mod_utils_types


def test_plain_types_work_normally() -> None:
    # --- execute, and verify ---
    assert mod_utils_types.safe_isinstance("x", str)
    assert not mod_utils_types.safe_isinstance(123, str)
    assert mod_utils_types.safe_isinstance(123, int)


def test_union_types() -> None:
    # --- setup ---
    u = str | int

    # --- execute and verify ---
    assert mod_utils_types.safe_isinstance("abc", u)
    assert mod_utils_types.safe_isinstance(42, u)
    assert not mod_utils_types.safe_isinstance(3.14, u)


def test_optional_types() -> None:
    # --- setup ---
    opt = int | None

    # --- execute and verify ---
    assert mod_utils_types.safe_isinstance(5, opt)
    assert mod_utils_types.safe_isinstance(None, opt)
    assert not mod_utils_types.safe_isinstance("nope", opt)


def test_any_type_always_true() -> None:
    # --- execute and verify ---
    assert mod_utils_types.safe_isinstance("anything", Any)
    assert mod_utils_types.safe_isinstance(None, Any)
    assert mod_utils_types.safe_isinstance(42, Any)


def test_list_type_accepts_lists() -> None:
    # --- execute and verify ---
    assert mod_utils_types.safe_isinstance([], list)
    assert not mod_utils_types.safe_isinstance({}, list)


def test_list_of_str_type_accepts_strings_inside() -> None:
    # --- setup ---
    list_str = list[str]

    # --- execute and verify ---
    assert mod_utils_types.safe_isinstance(["a", "b"], list_str)
    assert not mod_utils_types.safe_isinstance(["a", 2], list_str)


def test_typed_dict_like_accepts_dicts() -> None:
    # --- setup ---
    class DummyDict(TypedDict):
        foo: str
        bar: int

    # --- execute and verify ---
    # should treat dicts as valid, not crash
    assert mod_utils_types.safe_isinstance({"foo": "x", "bar": 1}, DummyDict)
    assert not mod_utils_types.safe_isinstance("not a dict", DummyDict)


def test_union_with_list_and_dict() -> None:
    # --- setup ---
    u = list[str] | dict[str, int]

    # --- execute and verify ---
    assert mod_utils_types.safe_isinstance(["a", "b"], u)
    assert mod_utils_types.safe_isinstance({"a": 1}, u)
    assert not mod_utils_types.safe_isinstance(42, u)


def test_does_not_raise_on_weird_types() -> None:
    """Exotic typing constructs should not raise exceptions."""

    # --- setup ---
    class A: ...

    T = TypeVar("T", bound=A)

    # --- execute ---
    # just ensure it returns a boolean, not crash
    result = mod_utils_types.safe_isinstance(A(), T)

    # --- verify ---
    assert isinstance(result, bool)


def test_nested_generics_work() -> None:
    # --- setup ---
    l2 = list[list[int]]

    # --- execute and verify ---
    assert mod_utils_types.safe_isinstance([[1, 2], [3, 4]], l2)
    assert not mod_utils_types.safe_isinstance([[1, "a"]], l2)


def test_literal_values_match() -> None:
    # --- setup ---
    lit = Literal["x", "y"]

    # --- execute and verify ---
    assert mod_utils_types.safe_isinstance("x", lit)
    assert not mod_utils_types.safe_isinstance("z", lit)


def test_tuple_generic_support() -> None:
    # --- setup ---
    tup = tuple[int, str]

    # --- execute and verify ---
    assert mod_utils_types.safe_isinstance((1, "a"), tup)
    assert not mod_utils_types.safe_isinstance(("a", 1), tup)
