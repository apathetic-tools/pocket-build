# tests/test_utils_safe_isinstance.py
"""Focused tests for pocket_build.utils_core.safe_isinstance."""

import typing

import pocket_build.utils_types as mod_utils_types


def test_plain_types_work_normally() -> None:
    assert mod_utils_types.safe_isinstance("x", str)
    assert not mod_utils_types.safe_isinstance(123, str)
    assert mod_utils_types.safe_isinstance(123, int)


def test_union_types() -> None:
    U = typing.Union[str, int]
    assert mod_utils_types.safe_isinstance("abc", U)
    assert mod_utils_types.safe_isinstance(42, U)
    assert not mod_utils_types.safe_isinstance(3.14, U)


def test_optional_types() -> None:
    Opt = typing.Optional[int]  # Union[int, NoneType]
    assert mod_utils_types.safe_isinstance(5, Opt)
    assert mod_utils_types.safe_isinstance(None, Opt)
    assert not mod_utils_types.safe_isinstance("nope", Opt)


def test_any_type_always_true() -> None:
    assert mod_utils_types.safe_isinstance("anything", typing.Any)
    assert mod_utils_types.safe_isinstance(None, typing.Any)
    assert mod_utils_types.safe_isinstance(42, typing.Any)


def test_list_type_accepts_lists() -> None:
    assert mod_utils_types.safe_isinstance([], list)
    assert not mod_utils_types.safe_isinstance({}, list)


def test_list_of_str_type_accepts_strings_inside() -> None:
    ListStr = list[str]
    assert mod_utils_types.safe_isinstance(["a", "b"], ListStr)
    assert not mod_utils_types.safe_isinstance(["a", 2], ListStr)


def test_typed_dict_like_accepts_dicts() -> None:
    class DummyDict(typing.TypedDict):
        foo: str
        bar: int

    # should treat dicts as valid, not crash
    assert mod_utils_types.safe_isinstance({"foo": "x", "bar": 1}, DummyDict)
    assert not mod_utils_types.safe_isinstance("not a dict", DummyDict)


def test_union_with_list_and_dict() -> None:
    U = typing.Union[list[str], dict[str, int]]
    assert mod_utils_types.safe_isinstance(["a", "b"], U)
    assert mod_utils_types.safe_isinstance({"a": 1}, U)
    assert not mod_utils_types.safe_isinstance(42, U)


def test_does_not_raise_on_weird_types() -> None:
    """Exotic typing constructs should not raise exceptions."""

    class A: ...

    T = typing.TypeVar("T", bound=A)
    # just ensure it returns a boolean, not crash
    result = mod_utils_types.safe_isinstance(A(), T)
    assert isinstance(result, bool)


def test_nested_generics_work():
    L2 = list[list[int]]
    assert mod_utils_types.safe_isinstance([[1, 2], [3, 4]], L2)
    assert not mod_utils_types.safe_isinstance([[1, "a"]], L2)


def test_literal_values_match():
    Lit = typing.Literal["x", "y"]
    assert mod_utils_types.safe_isinstance("x", Lit)
    assert not mod_utils_types.safe_isinstance("z", Lit)


def test_tuple_generic_support():
    Tup = tuple[int, str]
    assert mod_utils_types.safe_isinstance((1, "a"), Tup)
    assert not mod_utils_types.safe_isinstance(("a", 1), Tup)
