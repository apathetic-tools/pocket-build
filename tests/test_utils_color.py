# tests/test_utils_color.py
"""Tests for color utility helpers in pocket_build.utils."""

# not doing tests for resolved_use_color()

from __future__ import annotations

import sys
import types
from typing import Generator

import pytest

from pocket_build.utils_runtime import GREEN, RESET
from tests.utils import patch_everywhere


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Reset environment variables and cached state before each test."""
    # fixture itself deals with context teardown, don't need to explicitly set
    for var in ("NO_COLOR", "FORCE_COLOR"):
        monkeypatch.delenv(var, raising=False)
    yield


def test_should_use_color_no_color(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disables color if NO_COLOR is present in environment."""
    import pocket_build.utils_core as mod_utils_core

    # --- patch and execute and verify ---
    with monkeypatch.context() as mp:
        mp.setenv("NO_COLOR", "1")
        assert mod_utils_core.should_use_color() is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "Yes"])
def test_should_use_color_force_color(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    """Enables color when FORCE_COLOR is set to truthy value."""
    import pocket_build.utils_core as mod_utils_core

    # --- patch and execute and verify ---
    with monkeypatch.context() as mp:
        mp.setenv("FORCE_COLOR", value)
        assert mod_utils_core.should_use_color() is True


def test_should_use_color_tty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Falls back to TTY detection when no env vars set."""
    import pocket_build.utils_core as mod_utils_core

    # --- patch and execute and verify ---
    with monkeypatch.context() as mp:
        fake_stdout = types.SimpleNamespace(isatty=lambda: True)
        mp.setattr(sys, "stdout", fake_stdout)
        assert mod_utils_core.should_use_color() is True

        fake_stdout = types.SimpleNamespace(isatty=lambda: False)
        mp.setattr(sys, "stdout", fake_stdout)
        assert mod_utils_core.should_use_color() is False


def test_colorize_explicit_true_false() -> None:
    """Explicit use_color argument forces color on or off."""
    import pocket_build.utils_runtime as mod_utils_runtime

    # --- setup ---
    test_string = "test string"

    # --- execute and verify ---
    assert (
        mod_utils_runtime.colorize(test_string, GREEN, use_color=True)
    ) == f"{GREEN}{test_string}{RESET}"
    assert (
        mod_utils_runtime.colorize(test_string, GREEN, use_color=False)
    ) == test_string


def test_colorize_respects_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recomputes cache if manually cleared."""
    import pocket_build.utils_core as mod_utils_core
    import pocket_build.utils_runtime as mod_utils_runtime

    # --- setup ---
    test_string = "test string"

    # --- patch and execute and verify ---
    with monkeypatch.context() as mp:
        patch_everywhere(mp, mod_utils_core, "should_use_color", lambda: False)
        result = mod_utils_runtime.colorize(test_string, GREEN)

    # --- verify ---
    assert result == test_string


def test_colorize_respects_runtime_flag() -> None:
    """colorize() should follow current_runtime['use_color'] exactly."""
    import pocket_build.runtime as mod_runtime
    import pocket_build.utils_runtime as mod_utils_runtime

    # --- setup ---
    text = "sample"

    # --- execute and verify ---
    # Force runtime to enable color
    mod_runtime.current_runtime["use_color"] = True
    result = mod_utils_runtime.colorize(text, GREEN)
    assert result == f"{GREEN}{text}{RESET}"

    # Force runtime to disable color
    mod_runtime.current_runtime["use_color"] = False
    result = mod_utils_runtime.colorize(text, GREEN)
    assert result == text
