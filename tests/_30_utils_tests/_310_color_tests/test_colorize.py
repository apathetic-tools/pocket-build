# tests/test_utils_color.py
"""Tests for color utility helpers in module.utils."""

import pytest

import pocket_build.logs as mod_logs
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
# colorize() behavior
# ---------------------------------------------------------------------------


def test_colorize_explicit_true_false(direct_logger: mod_logs.AppLogger) -> None:
    """Explicit enable_color argument forces color on or off."""
    # --- setup ---
    text = "test"

    # --- execute and verify ---
    assert (
        direct_logger.colorize(text, mod_utils_logs.GREEN, enable_color=True)
    ) == f"{mod_utils_logs.GREEN}{text}{mod_utils_logs.RESET}"
    assert (
        direct_logger.colorize(
            text,
            mod_utils_logs.GREEN,
            enable_color=False,
        )
    ) == text


def test_colorize_respects_instance_flag(direct_logger: mod_logs.AppLogger) -> None:
    """colorize() should honor logger.enable_color."""
    # --- setup ---
    text = "abc"

    # --- execute and verify ---
    direct_logger.enable_color = True
    assert (
        direct_logger.colorize(text, mod_utils_logs.GREEN)
        == f"{mod_utils_logs.GREEN}{text}{mod_utils_logs.RESET}"
    )

    direct_logger.enable_color = False
    assert direct_logger.colorize(text, mod_utils_logs.GREEN) == text


def test_colorize_does_not_mutate_text(direct_logger: mod_logs.AppLogger) -> None:
    """colorize() should not alter text content aside from color codes."""
    text = "safe!"
    direct_logger.enable_color = True
    result = direct_logger.colorize(text, mod_utils_logs.GREEN)
    assert text in result
    assert result.startswith(mod_utils_logs.GREEN)
    assert result.endswith(mod_utils_logs.RESET)
    # ensure text object itself wasn't modified
    assert text == "safe!"


def test_colorize_empty_text(direct_logger: mod_logs.AppLogger) -> None:
    """Empty strings should still produce proper output."""
    direct_logger.enable_color = True
    assert (
        direct_logger.colorize("", mod_utils_logs.GREEN)
        == f"{mod_utils_logs.GREEN}{mod_utils_logs.RESET}"
    )
    direct_logger.enable_color = False
    assert direct_logger.colorize("", mod_utils_logs.GREEN) == ""
