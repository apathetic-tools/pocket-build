# tests/30-utils-tests/_20_log_tests/test_log.py

import io
import re
import sys
from io import StringIO
from typing import Any, cast

import pytest

import pocket_build.runtime as mod_runtime
import pocket_build.utils_logs as mod_logs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ANSI_PATTERN = re.compile(r"\033\[[0-9;]*m")


def strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences for color safety."""
    return ANSI_PATTERN.sub("", s)


def capture_log_output(
    monkeypatch: pytest.MonkeyPatch,
    msg_level: str,
    runtime_level: str = "debug",
    *,
    msg: str | None = None,
    **kwargs: Any,
) -> tuple[str, str]:
    """Temporarily capture stdout/stderr during a log() call.

    Returns (stdout_text, stderr_text) as plain strings.
    Automatically restores sys.stdout/sys.stderr afterwards.
    """
    # --- configure runtime ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", runtime_level)

    # Preserve original streams for proper restoration
    old_out, old_err = sys.stdout, sys.stderr

    # --- capture output temporarily ---
    out_buf, err_buf = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "stdout", out_buf)
    monkeypatch.setattr(sys, "stderr", err_buf)

    # --- execute ---
    try:
        logger = mod_logs.get_logger()
        method = getattr(logger, msg_level.lower(), None)
        if callable(method):
            final_msg: str = msg if msg is not None else f"msg:{msg_level}"
            method(final_msg, **kwargs)
    finally:
        # Always restore, even if log() crashes
        monkeypatch.setattr(sys, "stdout", old_out)
        monkeypatch.setattr(sys, "stderr", old_err)

    # --- return captured text ---
    return out_buf.getvalue(), err_buf.getvalue()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("msg_level", "expected_stream"),
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
    monkeypatch: pytest.MonkeyPatch,
    msg_level: str,
    expected_stream: str,
) -> None:
    """Ensure log() routes to the correct stream and message appears,
    ignoring prefixes/colors.
    """
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


def test_log_includes_default_prefix(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """log() should include the correct default prefix based on level."""
    # --- patch, execute, and verify ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "trace")
    logger = mod_logs.get_logger()
    for level, (_, expected_tag) in mod_logs.TAG_STYLES.items():
        log_method = getattr(logger, level.lower(), None)
        if callable(log_method):
            log_method("sample")
            capture = capsys.readouterr()
            out = (capture.out + capture.err).lower()
            assert expected_tag.strip().lower() in out, f"{level} missing expected tag"


def test_formatter_adds_ansi_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "use_color", True)
    out, _ = capture_log_output(monkeypatch, "debug", "debug", msg="colored")

    # --- verify ---
    assert "\033[" in out


def test_log_dynamic_unknown_level(capsys: pytest.CaptureFixture[str]) -> None:
    # --- execute ---
    mod_logs.log_dynamic("nonsense", "This should not crash")

    # --- verify ---
    out = capsys.readouterr().err.lower()
    assert "Unknown log level".lower() in out


def test_log_missing_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    """If current_runtime has no 'log_level', logger should fallback safely."""
    # --- setup ---
    output = StringIO()

    # --- patch and execute ---
    monkeypatch.setattr(sys, "__stderr__", output)

    # Remove key temporarily
    backup = dict(mod_runtime.current_runtime)
    mod_runtime.current_runtime.pop("log_level", None)

    try:
        logger = mod_logs.get_logger()
        logger.info("no level key")
    finally:
        runtime_dict = cast("dict[str, object]", mod_runtime.current_runtime)  # pylance
        runtime_dict.update(backup)

    # --- verify ---
    msg = output.getvalue()
    assert "[LOGGER ERROR]" in msg
    assert "log_level" in msg
