# tests/_30_utils_tests/schema/private/test_validate_scalar_value.py
"""Smoke tests for pocket_build.config_validate internal validator helpers."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

from typing import Any

import pytest

import pocket_build.utils_schema as mod_utils_schema
import pocket_build.utils_types as mod_utils_types
from tests.utils import make_summary, patch_everywhere


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
