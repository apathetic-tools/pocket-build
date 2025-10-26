# tests/test_utils_logs.py

# not doing tests for _is_error_level() and _should_log()

import io
import re
import sys
from typing import Generator

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


@pytest.fixture(autouse=True)
def reset_runtime() -> Generator[None, None, None]:
    """Reset runtime log level between tests."""
    import pocket_build.runtime as mod_runtime

    mod_runtime.current_runtime["log_level"] = "info"
    yield
    mod_runtime.current_runtime["log_level"] = "info"


def log_and_capture_output(level: str, current_level: str = "debug") -> tuple[str, str]:
    """Capture stdout/stderr when calling log()."""
    import pocket_build.runtime as mod_runtime
    import pocket_build.utils_using_runtime as mod_utils_runtime

    mod_runtime.current_runtime["log_level"] = current_level

    out_buf, err_buf = io.StringIO(), io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out_buf, err_buf
    try:
        mod_utils_runtime.log(level, f"msg:{level}")
    finally:
        sys.stdout, sys.stderr = old_out, old_err

    return out_buf.getvalue(), err_buf.getvalue()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_is_bypass_capture_env_vars(
    monkeypatch: MonkeyPatch,
) -> None:
    """is_bypass_capture() should return True
    when *_BYPASS_CAPTURE or BYPASS_CAPTURE is set."""
    # --- setup, execute, and verify ---
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
    "level,expected_stream",
    [
        ("debug", "stdout"),
        ("info", "stdout"),
        ("warning", "stderr"),
        ("error", "stderr"),
        ("critical", "stderr"),
        ("trace", "stdout"),
    ],
)
def test_log_routes_correct_stream(level: str, expected_stream: str) -> None:
    """Ensure log() routes to the correct stream and message appears,
    ignoring prefixes/colors."""
    # --- setup, execute ---
    out, err = log_and_capture_output(level, "trace")

    out, err = strip_ansi(out.strip()), strip_ansi(err.strip())

    # --- verify ---
    combined = out or err
    assert f"msg:{level}" in combined  # message always present

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
    runtime_level: str, visible_levels: set[str]
) -> None:
    """Messages below the current log level should not be printed."""
    # --- setup, execute, and verify ---
    for level in mod_utils_runtime.LEVEL_ORDER:
        out, err = log_and_capture_output(level, runtime_level)
        text = f"msg:{level}"
        combined = out + err
        if level in visible_levels:
            assert text in combined
        else:
            assert text not in combined


def test_log_bypass_capture_env(
    monkeypatch: MonkeyPatch,
) -> None:
    """When *_BYPASS_CAPTURE=1, log() should write to __stdout__/__stderr__."""
    # --- setup and execute ---
    # Sneaky program tries to escape our capture,
    #   we are sneakier and capture it anyways!
    #   What are you going to do now program?
    fake_stdout, fake_stderr = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "__stdout__", fake_stdout)
    monkeypatch.setattr(sys, "__stderr__", fake_stderr)

    # Mock the environment variable so utils re-evaluates
    monkeypatch.setenv(f"{PROGRAM_ENV}_BYPASS_CAPTURE", "1")
    monkeypatch.setenv("BYPASS_CAPTURE", "1")

    mod_runtime.current_runtime["log_level"] = "debug"

    # Info should go to stdout
    mod_utils_runtime.log("info", "out-msg")
    # Error should go to stderr
    mod_utils_runtime.log("error", "err-msg")

    # --- verify ---
    assert "out-msg" in fake_stdout.getvalue()
    assert "err-msg" in fake_stderr.getvalue()


@pytest.mark.parametrize(
    "level,expected_prefix",
    [
        ("info", ""),  # info has no prefix
        ("debug", "[DEBUG] "),  # debug has one
        ("trace", "[TRACE] "),  # trace has one
        ("warning", "⚠️ "),  # emoji prefix
        ("error", "❌ "),
        ("critical", "💥 "),
    ],
)
def test_log_includes_default_prefix(level: str, expected_prefix: str) -> None:
    """log() should include the correct default prefix based on level."""
    # --- setup and execute ---
    mod_runtime.current_runtime["log_level"] = "trace"

    out_buf, err_buf = io.StringIO(), io.StringIO()
    sys_stdout, sys_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out_buf, err_buf
    try:
        mod_utils_runtime.log(level, "hello")
    finally:
        sys.stdout, sys.stderr = sys_stdout, sys_stderr

    output = (out_buf.getvalue() or err_buf.getvalue()).strip()
    # Strip any ANSI codes before comparing
    clean = __import__("re").sub(r"\033\[[0-9;]*m", "", output)

    # --- verify ---
    assert clean.startswith(expected_prefix)
    assert "hello" in clean


def test_log_allows_custom_prefix() -> None:
    """Explicit prefix argument should override default prefix entirely."""
    # --- setup and execute ---
    mod_runtime.current_runtime["log_level"] = "debug"

    buf = io.StringIO()
    sys_stdout, sys.stderr = sys.stdout, sys.stderr
    sys.stdout = buf
    try:
        mod_utils_runtime.log("debug", "world", prefix="[CUSTOM] ")
    finally:
        sys.stdout = sys_stdout

    output = buf.getvalue().strip()
    clean = __import__("re").sub(r"\033\[[0-9;]*m", "", output)

    # --- verify ---
    assert clean.startswith("[CUSTOM] ")
    assert "world" in clean
    # Ensure default prefix does not appear
    assert "[DEBUG]" not in clean


def test_log_includes_some_prefix_for_non_info() -> None:
    """Non-info levels should include some kind of prefix (emoji or tag)."""
    # --- setup and execute ---
    mod_runtime.current_runtime["log_level"] = "trace"
    out, _ = log_and_capture_output("debug", "trace")
    cleaned = strip_ansi(out.strip())

    # --- verify ---
    # There should be something before "msg:debug"
    assert any(cleaned.startswith(p) for p in ("[", "⚠️", "❌", "💥"))


def test_log_below_threshold_suppressed(monkeypatch: MonkeyPatch):
    # --- setup and execute ---
    mod_runtime.current_runtime["log_level"] = "error"
    out, err = io.StringIO(), io.StringIO()
    sys_stdout, sys_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        mod_utils_runtime.log("info", "hidden")
    finally:
        sys.stdout, sys.stderr = sys_stdout, sys_stderr

        # --- verify ---
    assert not out.getvalue() and not err.getvalue()


def test_log_includes_ansi_when_color_enabled(monkeypatch: MonkeyPatch):
    # --- setup and execute ---
    mod_runtime.current_runtime.update({"log_level": "debug", "use_color": True})
    buf = io.StringIO()
    sys_stdout, sys.stdout = sys.stdout, buf
    try:
        mod_utils_runtime.log("debug", "colored")
    finally:
        sys.stdout = sys_stdout
    output = buf.getvalue()

    # --- verify ---
    assert "\033[" in output
