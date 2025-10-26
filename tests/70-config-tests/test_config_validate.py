# tests/test_config_validate.py
"""Tests for pocket_build.config_validate."""

from typing import Any

from pytest import MonkeyPatch, fixture

import pocket_build.config_validate as mod_validate

# --- fixtures ---------------------------------------------------------------


@fixture(autouse=True)
def mute_log(monkeypatch: MonkeyPatch) -> None:
    """Silence logging for clean test output."""

    def _silent_log(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(mod_validate, "log", _silent_log)


# fixture(autouse=True)
# def silent_logs(monkeypatch: MonkeyPatch) -> None:
#     """Silence all logs during tests via LOG_LEVEL=silent."""
#     monkeypatch.setenv("LOG_LEVEL", "silent")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Basic “known good” configurations
# ---------------------------------------------------------------------------


def test_valid_minimal_root_and_build() -> None:
    """A simple one-build config with list[str] include should validate True."""

    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [{"include": ["src"], "out": "dist"}],
    }

    # --- execute and validate ---
    assert mod_validate.validate_config(cfg) is True


def test_valid_multiple_builds() -> None:
    """Multiple valid builds should still pass."""

    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [
            {"include": ["src"], "out": "dist"},
            {"include": ["tests"], "out": "dist/tests"},
        ],
        "watch_interval": 1.0,
    }

    # --- execute and validate ---
    assert mod_validate.validate_config(cfg) is True


# ---------------------------------------------------------------------------
# Structural or type errors
# ---------------------------------------------------------------------------


def test_invalid_builds_not_a_list() -> None:
    # --- setup ---
    cfg: dict[str, Any] = {"builds": {"include": ["src"], "out": "dist"}}  # wrong type

    # --- execute and validate ---
    assert mod_validate.validate_config(cfg) is False


def test_invalid_inner_type_in_list() -> None:
    """Include should be list[str], but we insert an int."""
    # --- setup ---
    cfg: dict[str, Any] = {"builds": [{"include": ["src", 42], "out": "dist"}]}

    # --- execute and validate ---
    assert mod_validate.validate_config(cfg) is False


def test_invalid_top_level_key() -> None:
    """Unknown root key should invalidate config under strict=True."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [{"include": ["src"], "out": "dist"}],
        "bogus": 123,
    }

    # --- execute and validate ---
    assert mod_validate.validate_config(cfg, strict=True) is False


# ---------------------------------------------------------------------------
# Optional/edge handling
# ---------------------------------------------------------------------------


def test_empty_build_list() -> None:
    """Empty list should log warning but still count as valid."""
    # --- setup ---
    cfg: dict[str, Any] = {"builds": []}

    # --- execute and validate ---
    assert mod_validate.validate_config(cfg) is True


def test_handles_list_of_typed_dicts() -> None:
    """A list of build dicts should not be rejected as non-BuildConfigInput."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [
            {"include": ["src"], "out": "dist"},
        ],
        "strict_config": False,
    }

    # --- execute and validate ---
    # Should be True — verifies TypedDict lists aren’t misclassified
    assert mod_validate.validate_config(cfg) is True


def test_warn_keys_once_behavior(monkeypatch: MonkeyPatch) -> None:
    """Repeated dry-run keys should only trigger one warning."""
    # --- setup ---
    called: list[tuple[str, str]] = []
    cfg: dict[str, Any] = {
        "builds": [{"include": ["src"], "out": "dist", "dry_run": True}]
    }

    def _mock_log(lvl: str, msg: str) -> None:
        called.append((lvl, msg))

    # --- patch and execute ---
    monkeypatch.setattr(mod_validate, "log", _mock_log)
    mod_validate.validate_config(cfg)

    # --- validate ---
    # Only one log message mentioning dry-run should appear
    dry_msgs = [m for _lvl, m in called if "dry-run" in m]
    assert len(dry_msgs) == 1


def test_invalid_type_at_root() -> None:
    """Root-level key of wrong type should fail."""

    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [{"include": ["src"], "out": "dist"}],
        "strict_config": "yes",  # wrong type
    }

    # --- execute and validate ---
    assert mod_validate.validate_config(cfg) is False


def test_root_and_build_strict_config(monkeypatch: MonkeyPatch) -> None:
    """Build-level strict_config overrides root strictness."""
    # --- setup ---
    called: list[tuple[str, str]] = []
    cfg: dict[str, Any] = {
        "builds": [
            {"include": ["src"], "out": "dist", "strict_config": True, "extra": 123}
        ],
        "strict_config": False,
    }

    def _mock_log(lvl: str, msg: str) -> None:
        called.append((lvl, msg))

    # --- patch and execute ---
    monkeypatch.setattr(mod_validate, "log", _mock_log)
    valid = mod_validate.validate_config(cfg)

    # --- validate ---
    # Even with root strict=False, build strict=True should mark invalid
    assert valid is False
    assert any("unknown key" in msg for _lvl, msg in called)


def test_invalid_missing_builds_key():
    # --- setup ---
    cfg: dict[str, Any] = {"not_builds": []}

    # --- execute and validate ---
    assert mod_validate.validate_config(cfg) is False


def test_valid_with_optional_fields():
    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [{"include": ["src"], "out": "dist"}],
        "log_level": "debug",
        "respect_gitignore": True,
        "watch_interval": 2.5,
    }

    # --- execute and validate ---
    assert mod_validate.validate_config(cfg) is True


def test_empty_build_dict():
    # --- setup ---
    cfg: dict[str, Any] = {"builds": [{}]}

    # --- execute and validate ---
    assert mod_validate.validate_config(cfg) is True
