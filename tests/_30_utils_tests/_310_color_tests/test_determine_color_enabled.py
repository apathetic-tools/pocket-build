# tests/test_determine_color_enabled.py
"""Tests for ApatheticCLILogger.determine_color_enabled()."""

import sys
import types

import pytest

import pocket_build.utils_logs as mod_utils_logs


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


def test_no_color_disables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NO_COLOR disables color regardless of FORCE_COLOR or TTY."""
    # --- patch, execute, and verify ---
    monkeypatch.setenv("NO_COLOR", "1")
    assert mod_utils_logs.ApatheticCLILogger.determine_color_enabled() is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "Yes"])
def test_force_color_enables(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    """FORCE_COLOR enables color when set to a truthy value."""
    # --- patch, execute, and verify ---
    monkeypatch.setenv("FORCE_COLOR", value)
    assert mod_utils_logs.ApatheticCLILogger.determine_color_enabled() is True


def test_falls_back_to_tty_detection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without env vars, falls back to sys.stdout.isatty()."""
    # --- patch, execute, and verify ---

    # Simulate TTY
    fake_stdout = types.SimpleNamespace(isatty=lambda: True)
    monkeypatch.setattr(sys, "stdout", fake_stdout)
    assert mod_utils_logs.ApatheticCLILogger.determine_color_enabled() is True

    # Simulate non-TTY
    fake_stdout = types.SimpleNamespace(isatty=lambda: False)
    monkeypatch.setattr(sys, "stdout", fake_stdout)
    assert mod_utils_logs.ApatheticCLILogger.determine_color_enabled() is False


def test_no_color_overrides_force_color(monkeypatch: pytest.MonkeyPatch) -> None:
    # --- patch, execute and verify ---
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert mod_utils_logs.ApatheticCLILogger.determine_color_enabled() is False
