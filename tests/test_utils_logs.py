# tests/test_utils_logs.py

# not doing tests for is_error_level() and should_log()

import io
import sys

import pytest
from _pytest.monkeypatch import MonkeyPatch

from tests.conftest import RuntimeLike


@pytest.fixture(autouse=True)
def reset_runtime(runtime_env: RuntimeLike):
    """Reset runtime log level between tests."""
    runtime_env.current_runtime["log_level"] = "info"
    yield
    runtime_env.current_runtime["log_level"] = "info"


def capture_output(runtime_env: RuntimeLike, level: str, current_level: str = "debug"):
    """Capture stdout/stderr when calling log()."""
    runtime_env.current_runtime["log_level"] = current_level

    out_buf, err_buf = io.StringIO(), io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out_buf, err_buf
    try:
        runtime_env.log(level, f"msg:{level}")
    finally:
        sys.stdout, sys.stderr = old_out, old_err

    return out_buf.getvalue(), err_buf.getvalue()


def test_is_bypass_capture_env_vars(
    monkeypatch: MonkeyPatch, runtime_env: RuntimeLike
) -> None:
    """is_bypass_capture() should return True
    when *_BYPASS_CAPTURE or BYPASS_CAPTURE is set."""

    # Clear all possibly conflicting env vars first
    monkeypatch.delenv(f"{runtime_env.PROGRAM_ENV}_BYPASS_CAPTURE", raising=False)
    monkeypatch.delenv("BYPASS_CAPTURE", raising=False)

    # Default → both unset → expect False
    assert runtime_env.is_bypass_capture() is False

    # Specific env var (PROGRAM_ENV_BYPASS_CAPTURE) wins
    monkeypatch.setenv(f"{runtime_env.PROGRAM_ENV}_BYPASS_CAPTURE", "1")
    assert runtime_env.is_bypass_capture() is True

    # Unset the specific one again
    monkeypatch.delenv(f"{runtime_env.PROGRAM_ENV}_BYPASS_CAPTURE", raising=False)

    # Generic BYPASS_CAPTURE also triggers
    monkeypatch.setenv("BYPASS_CAPTURE", "1")
    assert runtime_env.is_bypass_capture() is True

    # Non-“1” values should not trigger
    monkeypatch.setenv("BYPASS_CAPTURE", "0")
    assert runtime_env.is_bypass_capture() is False

    # Case: both set → still True
    monkeypatch.setenv(f"{runtime_env.PROGRAM_ENV}_BYPASS_CAPTURE", "1")
    monkeypatch.setenv("BYPASS_CAPTURE", "1")
    assert runtime_env.is_bypass_capture() is True


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
def test_log_routes_correct_stream(
    runtime_env: RuntimeLike, level: str, expected_stream: str
):
    """Log should route messages to stdout/stderr based on severity."""
    out, err = capture_output(runtime_env, level, "trace")

    if expected_stream == "stdout":
        assert out.strip() == f"msg:{level}"
        assert err == ""
    else:
        assert err.strip() == f"msg:{level}"
        assert out == ""


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
    runtime_env: RuntimeLike, runtime_level: str, visible_levels: set[str]
):
    """Messages below the current log level should not be printed."""
    for level in runtime_env.LEVEL_ORDER:
        out, err = capture_output(runtime_env, level, runtime_level)
        text = f"msg:{level}"
        combined = out + err
        if level in visible_levels:
            assert text in combined
        else:
            assert text not in combined


def test_log_bypass_capture_env(monkeypatch: MonkeyPatch, runtime_env: RuntimeLike):
    """When *_BYPASS_CAPTURE=1, log() should write to __stdout__/__stderr__."""

    # Sneaky program tries to escape our capture,
    #   we are sneakier and capture it anyways!
    #   What are you going to do now program?
    fake_stdout, fake_stderr = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "__stdout__", fake_stdout)
    monkeypatch.setattr(sys, "__stderr__", fake_stderr)

    # Mock the environment variable so utils re-evaluates
    monkeypatch.setenv(f"{runtime_env.PROGRAM_ENV}_BYPASS_CAPTURE", "1")
    monkeypatch.setenv("BYPASS_CAPTURE", "1")

    runtime_env.current_runtime["log_level"] = "debug"

    # Info should go to stdout
    runtime_env.log("info", "out-msg")
    # Error should go to stderr
    runtime_env.log("error", "err-msg")

    assert "out-msg" in fake_stdout.getvalue()
    assert "err-msg" in fake_stderr.getvalue()
