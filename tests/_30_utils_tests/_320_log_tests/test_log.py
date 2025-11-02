# tests/30-utils-tests/_20_log_tests/test_log.py

import io
import re
import sys
from typing import Any

import pytest

import pocket_build.logs as mod_logs
import pocket_build.utils_logs as mod_utils_logs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ANSI_PATTERN = re.compile(r"\033\[[0-9;]*m")


def strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences for color safety."""
    return ANSI_PATTERN.sub("", s)


def capture_log_output(
    monkeypatch: pytest.MonkeyPatch,
    logger: mod_logs.AppLogger,
    msg_level: str,
    *,
    msg: str | None = None,
    enable_color: bool = False,
    log_level: str = "TRACE",
    **kwargs: Any,
) -> tuple[str, str]:
    """Temporarily capture stdout/stderr during a log() call.

    Returns (stdout_text, stderr_text) as plain strings.
    Automatically restores sys.stdout/sys.stderr afterwards.
    """
    logger.enable_color = enable_color
    logger.setLevel(log_level.upper())

    # Preserve original streams for proper restoration
    old_out, old_err = sys.stdout, sys.stderr

    # --- capture output temporarily ---
    out_buf, err_buf = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "stdout", out_buf)
    monkeypatch.setattr(sys, "stderr", err_buf)

    # --- execute ---
    try:
        method = getattr(logger, msg_level.lower(), None)
        if callable(method):
            final_msg: str = msg or f"msg:{msg_level}"
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
    direct_logger: mod_logs.AppLogger,
) -> None:
    """Ensure messages go to the correct stream based on severity."""
    # --- setup, patch, and execute ---
    text = f"msg:{msg_level}"
    out, err = capture_log_output(monkeypatch, direct_logger, msg_level, msg=text)
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


def test_formatter_includes_expected_tags(
    capsys: pytest.CaptureFixture[str],
    direct_logger: mod_logs.AppLogger,
) -> None:
    """Each log level should include its corresponding prefix/tag."""
    # --- setup ---
    direct_logger.setLevel("trace")

    # --- execute, and verify ---
    for level_name, (_, expected_tag) in mod_utils_logs.TAG_STYLES.items():
        method = getattr(direct_logger, level_name.lower(), None)
        if callable(method):
            method("sample")
            capture = capsys.readouterr()
            out = (capture.out + capture.err).lower()
            assert expected_tag.strip().lower() in out, (
                f"{level_name} missing expected tag"
            )


def test_formatter_adds_ansi_when_color_enabled(
    monkeypatch: pytest.MonkeyPatch,
    direct_logger: mod_logs.AppLogger,
) -> None:
    """When color is enabled, ANSI codes should appear in output."""
    # --- patch and execute ---
    out, _ = capture_log_output(
        monkeypatch, direct_logger, "debug", enable_color=True, msg="colored"
    )

    # --- verify ---
    assert "\033[" in out


def test_log_dynamic_unknown_level(
    capsys: pytest.CaptureFixture[str],
    direct_logger: mod_logs.AppLogger,
) -> None:
    """Unknown string levels are handled gracefully."""
    # --- execute ---
    direct_logger.log_dynamic("nonsense", "This should not crash")

    # --- verify ---
    out = capsys.readouterr().err.lower()
    assert "Unknown log level".lower() in out


def test_use_level_context_manager_changes_temporarily(
    direct_logger: mod_logs.AppLogger,
) -> None:
    """use_level() should temporarily change the logger level."""
    # --- setup ---
    orig_level = direct_logger.level

    # --- execute and verify ---
    with direct_logger.use_level("error"):
        assert direct_logger.level_name == "ERROR"
    assert direct_logger.level == orig_level


def test_log_dynamic_accepts_numeric_level(
    capsys: pytest.CaptureFixture[str],
    direct_logger: mod_logs.AppLogger,
) -> None:
    """log_dynamic() should work with int levels too."""
    # --- execute ---
    direct_logger.log_dynamic(mod_utils_logs.TRACE_LEVEL, "Numeric trace log works")

    # --- verify ---
    captured = capsys.readouterr()
    combined = (captured.out + captured.err).lower()
    assert "Numeric trace log works".lower() in combined
