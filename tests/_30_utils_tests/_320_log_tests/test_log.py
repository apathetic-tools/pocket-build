# tests/30-utils-tests/_20_log_tests/test_log.py

import io
import logging
import re
import sys
from io import StringIO
from typing import Any, TextIO, cast

import pytest

import pocket_build.meta as mod_meta
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
        final_msg: str = msg if msg is not None else f"msg:{msg_level}"
        mod_logs.log(msg_level, final_msg, **kwargs)
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


@pytest.mark.parametrize(
    ("runtime_level", "visible_levels"),
    [
        ("critical", {"critical"}),
        ("error", {"critical", "error"}),
        ("warning", {"critical", "error", "warning"}),
        ("info", {"critical", "error", "warning", "info"}),
        ("debug", {"critical", "error", "warning", "info", "debug"}),
        ("trace", {"critical", "error", "warning", "info", "debug", "trace"}),
    ],
)
def test_log_respects_current_log_level(
    monkeypatch: pytest.MonkeyPatch,
    runtime_level: str,
    visible_levels: set[str],
) -> None:
    """Messages below the current log level should not be printed."""
    # --- setup, patch, execute, and verify ---
    for msg_level in mod_logs.LEVEL_ORDER:
        text = f"msg:{msg_level}"
        out, err = capture_log_output(monkeypatch, msg_level, runtime_level, msg=text)
        combined = out + err
        if msg_level in visible_levels:
            assert text in combined
        else:
            assert text not in combined


@pytest.mark.parametrize(
    ("msg_level", "expected_prefix"),
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
    monkeypatch: pytest.MonkeyPatch,
    msg_level: str,
    expected_prefix: str,
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


def test_log_includes_some_prefix_for_non_info(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-info levels should include some kind of prefix (emoji or tag)."""
    # --- patch and execute ---
    out, _ = capture_log_output(monkeypatch, "debug", "trace")

    # --- verify ---
    cleaned = strip_ansi(out.strip())
    # There should be something before "msg:debug"
    assert any(cleaned.startswith(p) for p in ("[", "⚠️", "❌", "💥"))


def test_log_below_threshold_suppressed(monkeypatch: pytest.MonkeyPatch) -> None:
    # --- patch and execute ---
    out, err = capture_log_output(monkeypatch, "info", "error", msg="hidden")

    # --- verify ---
    assert not out
    assert not err


def test_log_includes_ansi_when_color_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "use_color", True)
    out, _ = capture_log_output(monkeypatch, "debug", "debug", msg="colored")

    # --- verify ---
    assert "\033[" in out


def test_log_recursion_guard() -> None:
    """Ensure recursive logging doesn't hang or crash."""

    # --- stubs ---
    class RecursiveHandler(logging.StreamHandler[TextIO]):
        def emit(
            self,
            record: logging.LogRecord,  # noqa: ARG002
        ) -> None:
            # This would recurse infinitely if not guarded internally
            mod_logs.log("error", "nested boom")

    # --- patch, execute and verify ---
    # Replace all handlers temporarily
    logger = logging.getLogger(mod_meta.PROGRAM_PACKAGE)
    old_handlers = list(logger.handlers)
    old_level = logger.level

    try:
        logger.handlers = [RecursiveHandler()]
        logger.setLevel(logging.ERROR)

        # The test: logging should *not* raise RecursionError
        try:
            mod_logs.log("error", "outer boom")
        except RecursionError:
            pytest.fail("RecursionError was not caught by stdlib logging")

    finally:
        # --- always restore logger state ---
        logger.handlers = old_handlers
        logger.setLevel(old_level)


def test_log_unknown_level(monkeypatch: pytest.MonkeyPatch) -> None:
    # --- setup ---
    buf = StringIO()

    # --- patch and execute ---
    monkeypatch.setattr(sys, "__stderr__", buf)
    mod_logs.log("nonsense", "This should not crash")

    # --- verify ---
    assert "Unknown log level" in buf.getvalue()


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
        mod_logs.log("error", "no level key")
    finally:
        runtime_dict = cast("dict[str, object]", mod_runtime.current_runtime)  # pylance
        runtime_dict.update(backup)

    # --- verify ---
    msg = output.getvalue()
    assert "[LOGGER ERROR]" in msg
    assert "log_level" in msg


def test_log_handles_internal_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """If print() raises, logger should fall back to safe_log."""
    # --- setup ---
    buf = StringIO()

    # --- stubs ---
    class BoomHandler(logging.Handler):
        def emit(
            self,
            record: logging.LogRecord,  # noqa: ARG002
        ) -> None:
            xmsg = "handler exploded"
            raise RuntimeError(xmsg)

    # --- patch and execute ---
    monkeypatch.setattr(sys, "__stderr__", buf)
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "debug")

    logger = logging.getLogger(mod_meta.PROGRAM_PACKAGE)
    old_handlers = list(logger.handlers)
    old_level = logger.level

    try:
        logger.handlers = [BoomHandler()]
        logger.setLevel(logging.DEBUG)

        mod_logs.log("info", "test failure handling")
    finally:
        # --- restore original logger state ---
        logger.handlers = old_handlers
        logger.setLevel(old_level)

    # --- verify ---
    out = buf.getvalue()
    assert "LOGGER FAILURE" in out
