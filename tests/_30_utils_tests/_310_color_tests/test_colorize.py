# tests/test_utils_color.py
"""Tests for color utility helpers in module.utils."""

import pytest

import pocket_build.runtime as mod_runtime
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
