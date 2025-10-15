# tests/test_utils_color.py
"""Tests for color utility helpers in pocket_build.utils."""

# not doing tests for resolved_use_color()

from __future__ import annotations

import sys
import types
from typing import Generator

import pytest

from tests.conftest import RuntimeLike

GREEN = "\x1b[32m"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Reset environment variables and cached state before each test."""
    for var in ("NO_COLOR", "FORCE_COLOR"):
        monkeypatch.delenv(var, raising=False)
    yield


def test_should_use_color_no_color(
    runtime_env: RuntimeLike,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disables color if NO_COLOR is present in environment."""
    monkeypatch.setenv("NO_COLOR", "1")
    assert runtime_env.should_use_color() is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "Yes"])
def test_should_use_color_force_color(
    runtime_env: RuntimeLike,
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    """Enables color when FORCE_COLOR is set to truthy value."""
    monkeypatch.setenv("FORCE_COLOR", value)
    assert runtime_env.should_use_color() is True


def test_should_use_color_tty(
    runtime_env: RuntimeLike,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Falls back to TTY detection when no env vars set."""
    fake_stdout = types.SimpleNamespace(isatty=lambda: True)
    monkeypatch.setattr(sys, "stdout", fake_stdout)
    assert runtime_env.should_use_color() is True

    fake_stdout = types.SimpleNamespace(isatty=lambda: False)
    monkeypatch.setattr(sys, "stdout", fake_stdout)
    assert runtime_env.should_use_color() is False


def test_colorize_explicit_true_false(runtime_env: RuntimeLike) -> None:
    """Explicit use_color argument forces color on or off."""
    colorize = runtime_env.colorize
    RESET = runtime_env.RESET
    test_string = "test string"
    assert (
        colorize(test_string, GREEN, use_color=True) == f"{GREEN}{test_string}{RESET}"
    )
    assert colorize(test_string, GREEN, use_color=False) == test_string


def test_colorize_respects_reset(
    runtime_env: RuntimeLike,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recomputes cache if manually cleared."""
    colorize = runtime_env.colorize

    # Determine correct patch target
    if getattr(runtime_env, "__name__", "") == "pocket_build_single":
        target = "pocket_build_single.should_use_color"
    else:
        target = "pocket_build.utils_core.should_use_color"

    monkeypatch.setattr(target, lambda: False)
    if hasattr(colorize, "_system_default"):
        delattr(colorize, "_system_default")

    test_string = "test string"
    result = colorize(test_string, GREEN)
    assert result == test_string


def test_colorize_respects_runtime_flag(
    runtime_env: RuntimeLike, monkeypatch: pytest.MonkeyPatch
) -> None:
    """colorize() should follow current_runtime['use_color'] exactly."""
    colorize = runtime_env.colorize
    RESET = runtime_env.RESET
    text = "sample"

    # Force runtime to enable color
    runtime_env.current_runtime["use_color"] = True
    result = colorize(text, GREEN)
    assert result == f"{GREEN}{text}{RESET}"

    # Force runtime to disable color
    runtime_env.current_runtime["use_color"] = False
    result = colorize(text, GREEN)
    assert result == text
