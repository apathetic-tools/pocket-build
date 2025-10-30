# tests/test_utils_color.py
"""Tests for color utility helpers in module.utils."""

# not doing tests for resolved_use_color()

import sys
import types

import pytest

import pocket_build.runtime as mod_runtime
import pocket_build.utils as mod_utils_core
import pocket_build.utils_using_runtime as mod_utils_runtime


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


def test_colorize_explicit_true_false() -> None:
    """Explicit use_color argument forces color on or off."""
    # --- setup ---
    test_string = "test string"

    # --- execute and verify ---
    assert (
        mod_utils_runtime.colorize(test_string, mod_utils_runtime.GREEN, use_color=True)
    ) == f"{mod_utils_runtime.GREEN}{test_string}{mod_utils_runtime.RESET}"
    assert (
        mod_utils_runtime.colorize(
            test_string,
            mod_utils_runtime.GREEN,
            use_color=False,
        )
    ) == test_string


def test_colorize_respects_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recomputes cache if manually cleared."""
    # --- setup ---
    test_string = "test string"

    # --- patch, execute and verify ---

    # Force color disabled at runtime
    monkeypatch.setitem(mod_runtime.current_runtime, "use_color", False)
    result = mod_utils_runtime.colorize(test_string, mod_utils_runtime.GREEN)

    # --- verify ---
    assert result == test_string


def test_colorize_respects_runtime_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """colorize() should follow current_runtime['use_color'] exactly."""
    # --- setup ---
    text = "sample"

    # --- patch, execute and verify ---
    # Force runtime to enable color
    monkeypatch.setitem(mod_runtime.current_runtime, "use_color", True)
    result = mod_utils_runtime.colorize(text, mod_utils_runtime.GREEN)
    assert result == f"{mod_utils_runtime.GREEN}{text}{mod_utils_runtime.RESET}"

    # Force runtime to disable color
    monkeypatch.setitem(mod_runtime.current_runtime, "use_color", False)
    result = mod_utils_runtime.colorize(text, mod_utils_runtime.GREEN)
    assert result == text


def test_no_color_overrides_force_color(monkeypatch: pytest.MonkeyPatch) -> None:
    # --- patch, execute and verify ---
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert mod_utils_core.should_use_color() is False
