# tests/30-utils-tests/_20_log_tests/test_is_bypass_capture.py

import pytest

import pocket_build.meta as mod_meta
import pocket_build.utils_logs as mod_logs


def test_is_bypass_capture_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """is_bypass_capture() should return True
    when *_BYPASS_CAPTURE or BYPASS_CAPTURE is set.
    """
    # --- patch, execute, and verify ---
    # Clear all possibly conflicting env vars first
    monkeypatch.delenv(f"{mod_meta.PROGRAM_ENV}_BYPASS_CAPTURE", raising=False)
    monkeypatch.delenv("BYPASS_CAPTURE", raising=False)

    # Default → both unset → expect False
    assert mod_logs.is_bypass_capture() is False

    # Specific env var (PROGRAM_ENV_BYPASS_CAPTURE) wins
    monkeypatch.setenv(f"{mod_meta.PROGRAM_ENV}_BYPASS_CAPTURE", "1")
    assert mod_logs.is_bypass_capture() is True

    # Unset the specific one again
    monkeypatch.delenv(f"{mod_meta.PROGRAM_ENV}_BYPASS_CAPTURE", raising=False)

    # Generic BYPASS_CAPTURE also triggers
    monkeypatch.setenv("BYPASS_CAPTURE", "1")
    assert mod_logs.is_bypass_capture() is True

    # Non-“1” values should not trigger
    monkeypatch.setenv("BYPASS_CAPTURE", "0")
    assert mod_logs.is_bypass_capture() is False

    # Case: both set → still True
    monkeypatch.setenv(f"{mod_meta.PROGRAM_ENV}_BYPASS_CAPTURE", "1")
    monkeypatch.setenv("BYPASS_CAPTURE", "1")
    assert mod_logs.is_bypass_capture() is True
