# tests/_30_utils_tests/schema/private/test_infer_type_label.py
"""Smoke tests for pocket_build.config_validate internal validator helpers."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

from typing import Any, TypedDict

import pocket_build.utils_schema as mod_utils_schema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# --- Fixtures / Sample TypedDicts -------------------------------------------


class MiniBuild(TypedDict):
    include: list[str]
    out: str


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
