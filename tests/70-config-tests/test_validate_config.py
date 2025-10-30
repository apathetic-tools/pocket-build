# tests/test_config_validate.py
"""Tests for pocket_build.config_validate."""

from typing import Any

import pocket_build.config_validate as mod_validate


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

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    assert summary.valid is True


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

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    assert summary.valid is True


# ---------------------------------------------------------------------------
# Structural or type errors
# ---------------------------------------------------------------------------


def test_invalid_builds_not_a_list() -> None:
    # --- setup ---
    cfg: dict[str, Any] = {"builds": {"include": ["src"], "out": "dist"}}  # wrong type

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    assert summary.valid is False


def test_invalid_inner_type_in_list() -> None:
    """Include should be list[str], but we insert an int."""
    # --- setup ---
    cfg: dict[str, Any] = {"builds": [{"include": ["src", 42], "out": "dist"}]}

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    assert summary.valid is False


def test_invalid_top_level_key() -> None:
    """Unknown root key should invalidate config under strict=True."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [{"include": ["src"], "out": "dist"}],
        "bogus": 123,
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg, strict=True)

    # --- validate ---
    assert summary.valid is False


# ---------------------------------------------------------------------------
# Optional/edge handling
# ---------------------------------------------------------------------------


def test_empty_build_list() -> None:
    """Empty list should log warning but still count as valid."""
    # --- setup ---
    cfg: dict[str, Any] = {"builds": []}

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    assert summary.valid is True
    assert summary.warnings


def test_handles_list_of_typed_dicts() -> None:
    """A list of build dicts should not be rejected as non-BuildConfig."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [
            {"include": ["src"], "out": "dist"},
        ],
        "strict_config": False,
    }

    # --- execute ---
    # Should be True — verifies TypedDict lists aren’t misclassified
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    assert summary.valid is True


def test_warn_keys_once_behavior() -> None:
    """Repeated dry-run keys should only trigger one warning."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [{"include": ["src"], "out": "dist", "dry_run": True}],
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    # Collect all messages that mention dry-run, across all warning categories
    pool = summary.errors + summary.strict_warnings + summary.warnings
    # Only one log message mentioning dry-run should appear
    dry_msgs = [m for m in pool if "dry-run" in m]
    assert len(dry_msgs) == 1


def test_invalid_type_at_root() -> None:
    """Root-level key of wrong type should fail."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [{"include": ["src"], "out": "dist"}],
        "strict_config": "yes",  # wrong type
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg, strict=True)

    # --- validate ---
    assert summary.valid is False


def test_root_and_build_strict_config() -> None:
    """Build-level strict_config overrides root strictness."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [
            {"include": ["src"], "out": "dist", "strict_config": True, "extra": 123},
        ],
        "strict_config": False,
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    # Collect all messages that mention dry-run, across all warning categories
    pool = summary.errors + summary.strict_warnings + summary.warnings
    # Even with root strict=False, build strict=True should mark invalid
    assert summary.valid is False
    assert any("unknown key" in msg.lower() for msg in pool)


def test_invalid_missing_builds_key() -> None:
    # --- setup ---
    cfg: dict[str, Any] = {"not_builds": []}

    # --- execute ---
    summary = mod_validate.validate_config(cfg, strict=True)

    # --- validate ---
    assert summary.valid is False


def test_valid_with_optional_fields() -> None:
    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [{"include": ["src"], "out": "dist"}],
        "log_level": "debug",
        "respect_gitignore": True,
        "watch_interval": 2.5,
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg, strict=True)

    # --- validate ---
    assert summary.valid is True


def test_empty_build_dict() -> None:
    # --- setup ---
    cfg: dict[str, Any] = {"builds": [{}]}

    # --- execute ---
    summary = mod_validate.validate_config(cfg, strict=True)

    # --- validate ---
    assert summary.valid is True


def test_validate_config_suggests_similar_keys() -> None:
    """Validator should suggest close matches for mistyped keys."""
    # --- setup ---
    # Build a minimal but valid config with two bad keys that look like
    # legitimate ones so fuzzy suggestions trigger.
    bad_cfg: dict[str, Any] = {
        "buils": [],  # close to "builds"
        "outt": "dist",  # close to "out"
    }

    # --- execute ---
    summary = mod_validate.validate_config(bad_cfg)

    # --- validate ---
    # we just care about the suggestions, not if the validation failed or passed
    assert isinstance(summary.valid, bool)

    # It should have reported unknown keys
    pool = summary.errors + summary.strict_warnings + summary.warnings
    joined = "\n".join(pool).lower()

    # Find all messages mentioning 'unknown key' and 'Hint:'
    assert "unknown key" in joined
    # Each bad key should appear with a suggestion line
    assert "'buils' → 'builds'" in joined
    assert "'outt' → 'out'" in joined


# ---------------------------------------------------------------------------
# Aggregation / combined warnings
# ---------------------------------------------------------------------------


def test_aggregates_multiple_builds_same_warning() -> None:
    """Multiple builds with dry-run keys should combine into one aggregated warning."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [
            {"include": ["src"], "out": "dist", "dry_run": True},
            {"include": ["src2"], "out": "dist2", "dry_run": True},
        ],
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    pool = summary.errors + summary.strict_warnings + summary.warnings
    dry_msgs = [m for m in pool if "dry-run" in m]
    # All dry-run keys across builds should aggregate into one combined warning
    assert len(dry_msgs) == 1
    msg = dry_msgs[0].lower()
    # Message should mention both builds
    assert "build #1" in msg
    assert "build #2" in msg
    assert "dry-run" in msg or "dry_run" in msg


def test_aggregates_multiple_root_and_builds() -> None:
    """Multiple builds with dry-run keys should combine into one aggregated warning."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "dry_run": True,
        "builds": [
            {"include": ["src"], "out": "dist", "dry_run": True},
            {"include": ["src2"], "out": "dist2", "dry_run": True},
        ],
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    pool = summary.errors + summary.strict_warnings + summary.warnings
    dry_msgs = [m for m in pool if "dry-run" in m]
    # All dry-run keys across builds should aggregate into one combined warning
    assert len(dry_msgs) == 1
    msg = dry_msgs[0].lower()
    # Message should mention both builds
    assert "top-level" in msg
    assert "build #1" in msg
    assert "build #2" in msg
    assert "dry-run" in msg or "dry_run" in msg


def test_aggregates_strict_and_non_strict_separately() -> None:
    """Strict builds aggregate separately from non-strict builds."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [
            {
                "include": ["src"],
                "out": "dist",
                "dry_run": True,
                "strict_config": True,
            },
            {
                "include": ["src2"],
                "out": "dist2",
                "dry_run": True,
                "strict_config": False,
            },
        ],
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    # Strict build should produce a strict-warning (fatal), non-strict a normal warning
    assert summary.valid is False  # strict warning should mark invalid
    strict_msgs = [m for m in summary.strict_warnings if "dry-run" in m.lower()]
    warn_msgs = [m for m in summary.warnings if "dry-run" in m.lower()]
    # One of each should appear
    assert len(strict_msgs) == 1
    assert len(warn_msgs) == 1
    # Each message should only reference its matching build
    assert "build #1" in strict_msgs[0]
    assert "build #2" in warn_msgs[0]


def test_aggregator_clears_after_flush() -> None:
    """Running validation twice should not leak previous aggregation state."""
    # --- setup ---
    cfg1: dict[str, Any] = {
        "builds": [{"include": ["src"], "out": "dist", "dry_run": True}],
    }
    cfg2: dict[str, Any] = {"builds": [{"include": ["src"], "out": "dist"}]}

    # --- execute ---
    summary1 = mod_validate.validate_config(cfg1)
    summary2 = mod_validate.validate_config(cfg2)

    # --- validate ---
    pool1 = summary1.errors + summary1.strict_warnings + summary1.warnings
    pool2 = summary2.errors + summary2.strict_warnings + summary2.warnings
    # First run should have one dry-run warning
    assert any("dry-run" in m for m in pool1)
    # Second run should not repeat or leak messages
    assert not any("dry-run" in m for m in pool2)


def test_validate_config_prewarn_suppresses_unknown_keys() -> None:
    """Keys handled by warn_keys_once should not appear again as unknown."""
    # --- setup ---
    cfg: dict[str, Any] = {
        "builds": [
            {"include": ["src"], "out": "dist", "dry_run": True},
            {"include": ["src2"], "out": "dist2"},
        ],
    }

    # --- execute ---
    summary = mod_validate.validate_config(cfg)

    # --- validate ---
    pool = summary.errors + summary.strict_warnings + summary.warnings
    joined = "\n".join(pool)
    # It should warn about dry-run once, but not call it "unknown"
    assert "dry-run" in joined or "dry_run" in joined
    assert "unknown key" not in joined
