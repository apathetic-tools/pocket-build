# tests/test_utils_color.py
"""Tests for color utility helpers in module.utils."""

import sys
import types

import pytest

import pocket_build.utils as mod_utils_core


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset environment variables and cached state before each test."""
    # fixture itself deals with context teardown, don't need to explicitly set
    for var in ("NO_COLOR", "FORCE_COLOR"):
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_should_use_color_no_color(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disables color if NO_COLOR is present in environment."""
    # --- patch, execute, and verify ---
    monkeypatch.setenv("NO_COLOR", "1")
    assert mod_utils_core.should_use_color() is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "Yes"])
def test_should_use_color_force_color(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    """Enables color when FORCE_COLOR is set to truthy value."""
    # --- patch, execute, and verify ---
    monkeypatch.setenv("FORCE_COLOR", value)
    assert mod_utils_core.should_use_color() is True


def test_should_use_color_tty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Falls back to TTY detection when no env vars set."""
    # --- patch, execute, and verify ---
    fake_stdout = types.SimpleNamespace(isatty=lambda: True)
    monkeypatch.setattr(sys, "stdout", fake_stdout)
    assert mod_utils_core.should_use_color() is True

    fake_stdout = types.SimpleNamespace(isatty=lambda: False)
    monkeypatch.setattr(sys, "stdout", fake_stdout)
    assert mod_utils_core.should_use_color() is False


def test_no_color_overrides_force_color(monkeypatch: pytest.MonkeyPatch) -> None:
    # --- patch, execute and verify ---
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert mod_utils_core.should_use_color() is False
