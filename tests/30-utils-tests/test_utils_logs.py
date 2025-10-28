# tests/test_utils_logs.py

# not doing tests for _is_error_level() and _should_log()

from __future__ import annotations

import io
import re
import sys
from typing import Any

import pytest
from pytest import MonkeyPatch

import pocket_build.runtime as mod_runtime
import pocket_build.utils_using_runtime as mod_utils_runtime
from pocket_build.meta import PROGRAM_ENV

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ANSI_PATTERN = re.compile(r"\033\[[0-9;]*m")


def strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences for color safety."""
    return ANSI_PATTERN.sub("", s)


def capture_log_output(
    monkeypatch: MonkeyPatch,
    msg_level: str,
    runtime_level: str = "debug",
    *,
    msg: str | None = None,
    **kwargs: Any,
) -> tuple[str, str]:
    """Set the runtime log level, call log() once, and capture stdout/stderr output."""
    # --- configure runtime ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", runtime_level)

    # record old buffers (respecting any existing redirection)
    old_out, old_err = sys.stdout, sys.stderr

    # --- capture output temporarily ---
    out_buf, err_buf = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "stdout", out_buf)
    monkeypatch.setattr(sys, "stderr", err_buf)

    # --- execute ---
    try:
        final_msg: str = msg if msg is not None else f"msg:{msg_level}"
        mod_utils_runtime.log(msg_level, final_msg, **kwargs)
    finally:
        # --- restore output capture mechanism ---
        monkeypatch.setattr(sys, "stdout", old_out)
        monkeypatch.setattr(sys, "stderr", old_err)

    # --- return captured text ---
    return out_buf.getvalue(), err_buf.getvalue()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_is_bypass_capture_env_vars(
    monkeypatch: MonkeyPatch,
) -> None:
    """is_bypass_capture() should return True
    when *_BYPASS_CAPTURE or BYPASS_CAPTURE is set."""
    # --- patch, execute, and verify ---
    # Clear all possibly conflicting env vars first
    monkeypatch.delenv(f"{PROGRAM_ENV}_BYPASS_CAPTURE", raising=False)
    monkeypatch.delenv("BYPASS_CAPTURE", raising=False)

    # Default → both unset → expect False
    assert mod_utils_runtime.is_bypass_capture() is False

    # Specific env var (PROGRAM_ENV_BYPASS_CAPTURE) wins
    monkeypatch.setenv(f"{PROGRAM_ENV}_BYPASS_CAPTURE", "1")
    assert mod_utils_runtime.is_bypass_capture() is True

    # Unset the specific one again
    monkeypatch.delenv(f"{PROGRAM_ENV}_BYPASS_CAPTURE", raising=False)

    # Generic BYPASS_CAPTURE also triggers
    monkeypatch.setenv("BYPASS_CAPTURE", "1")
    assert mod_utils_runtime.is_bypass_capture() is True

    # Non-“1” values should not trigger
    monkeypatch.setenv("BYPASS_CAPTURE", "0")
    assert mod_utils_runtime.is_bypass_capture() is False

    # Case: both set → still True
    monkeypatch.setenv(f"{PROGRAM_ENV}_BYPASS_CAPTURE", "1")
    monkeypatch.setenv("BYPASS_CAPTURE", "1")
    assert mod_utils_runtime.is_bypass_capture() is True


@pytest.mark.parametrize(
    "msg_level,expected_stream",
    [
        ("debug", "stdout"),
        ("info", "stdout"),
        ("warning", "stderr"),
        ("error", "stderr"),
        ("critical", "stderr"),
        ("trace", "stdout"),
    ],
)
def test_log_routes_correct_stream(
    monkeypatch: MonkeyPatch, msg_level: str, expected_stream: str
) -> None:
    """Ensure log() routes to the correct stream and message appears,
    ignoring prefixes/colors."""
    # --- setup, patch, and execute ---
    text = f"msg:{msg_level}"
    out, err = capture_log_output(monkeypatch, msg_level, "trace", msg=text)
    out, err = strip_ansi(out.strip()), strip_ansi(err.strip())

    # --- verify ---
    combined = out or err
    assert text in combined  # message always present

    if expected_stream == "stdout":
        assert out  # message goes to stdout
        assert not err
    else:
        assert err  # message goes to stderr
        assert not out


@pytest.mark.parametrize(
    "runtime_level,visible_levels",
    [
        ("critical", {"critical"}),
        ("error", {"critical", "error"}),
        ("warning", {"critical", "error", "warning"}),
        ("info", {"critical", "error", "warning", "info"}),
        ("debug", {"critical", "error", "warning", "info", "debug"}),
        ("trace", set(["critical", "error", "warning", "info", "debug", "trace"])),
    ],
)
def test_log_respects_current_log_level(
    monkeypatch: MonkeyPatch, runtime_level: str, visible_levels: set[str]
) -> None:
    """Messages below the current log level should not be printed."""
    # --- setup, patch, execute, and verify ---
    for msg_level in mod_utils_runtime.LEVEL_ORDER:
        text = f"msg:{msg_level}"
        out, err = capture_log_output(monkeypatch, msg_level, runtime_level, msg=text)
        combined = out + err
        if msg_level in visible_levels:
            assert text in combined
        else:
            assert text not in combined


def test_log_bypass_capture_env(
    monkeypatch: MonkeyPatch,
) -> None:
    """When *_BYPASS_CAPTURE=1, log() should write to __stdout__/__stderr__."""
    # --- setup, patch, and execute ---
    # Sneaky program tries to escape our capture,
    #   we are sneakier and capture it anyways!
    #   What are you going to do now program?
    fake_stdout, fake_stderr = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "__stdout__", fake_stdout)
    monkeypatch.setattr(sys, "__stderr__", fake_stderr)

    # Mock the environment variable so utils re-evaluates
    monkeypatch.setenv(f"{PROGRAM_ENV}_BYPASS_CAPTURE", "1")
    monkeypatch.setenv("BYPASS_CAPTURE", "1")

    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "debug")

    # Info should go to stdout
    mod_utils_runtime.log("info", "out-msg")
    # Error should go to stderr
    mod_utils_runtime.log("error", "err-msg")

    # --- verify ---
    assert "out-msg" in fake_stdout.getvalue()
    assert "err-msg" in fake_stderr.getvalue()


@pytest.mark.parametrize(
    "msg_level,expected_prefix",
    [
        ("info", ""),  # info has no prefix
        ("debug", "[DEBUG] "),  # debug has one
        ("trace", "[TRACE] "),  # trace has one
        ("warning", "⚠️ "),  # emoji prefix
        ("error", "❌ "),
        ("critical", "💥 "),
    ],
)
def test_log_includes_default_prefix(
    monkeypatch: MonkeyPatch, msg_level: str, expected_prefix: str
) -> None:
    """log() should include the correct default prefix based on level."""
    # --- setup, patch, and execute ---
    text = "hello"
    out, err = capture_log_output(monkeypatch, msg_level, "trace", msg=text)
    output = (out or err).strip()

    # Strip any ANSI codes before comparing
    clean = re.sub(r"\033\[[0-9;]*m", "", output)

    # --- verify ---
    assert clean.startswith(expected_prefix)
    assert text in clean


def test_log_allows_custom_prefix(monkeypatch: MonkeyPatch) -> None:
    """Explicit prefix argument should override default prefix entirely."""
    # --- patch and execute ---
    out, _ = capture_log_output(
        monkeypatch, "debug", "debug", msg="world", prefix="[CUSTOM] "
    )
    clean = strip_ansi(out.strip())

    # --- verify ---
    assert clean.startswith("[CUSTOM] ")
    assert "world" in clean
    # Ensure default prefix does not appear
    assert "[DEBUG]" not in clean


def test_log_includes_some_prefix_for_non_info(monkeypatch: MonkeyPatch) -> None:
    """Non-info levels should include some kind of prefix (emoji or tag)."""
    # --- patch and execute ---
    out, _ = capture_log_output(monkeypatch, "debug", "trace")

    # --- verify ---
    cleaned = strip_ansi(out.strip())
    # There should be something before "msg:debug"
    assert any(cleaned.startswith(p) for p in ("[", "⚠️", "❌", "💥"))


def test_log_below_threshold_suppressed(monkeypatch: MonkeyPatch) -> None:
    # --- patch and execute ---
    out, err = capture_log_output(monkeypatch, "info", "error", msg="hidden")

    # --- verify ---
    assert not out and not err


def test_log_includes_ansi_when_color_enabled(monkeypatch: MonkeyPatch) -> None:
    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "use_color", True)
    out, _ = capture_log_output(monkeypatch, "debug", "debug", msg="colored")

    # --- verify ---
    assert "\033[" in out
