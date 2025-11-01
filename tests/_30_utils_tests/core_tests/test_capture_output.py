# tests/_30_utils_tests/test_utils.py
"""Tests for package.utils (package and standalone versions)."""

import sys
from io import StringIO
from typing import cast

import pytest

import pocket_build.utils as mod_utils


def test_capture_output_captures_stdout_and_stderr() -> None:
    """Stdout and stderr should be captured separately and merged together."""
    # --- setup ---
    assert sys.stdout is not None
    assert sys.stderr is not None
    old_out, old_err = sys.stdout, sys.stderr

    # --- execute ---
    with mod_utils.capture_output() as cap:
        print("hello stdout")
        print("oops stderr", file=sys.stderr)

    # --- verify ---
    out_text = cap.stdout.getvalue()
    err_text = cap.stderr.getvalue()
    merged_text = cap.merged.getvalue()

    assert "hello stdout" in out_text
    assert "oops stderr" in err_text
    # merged should contain both in order
    assert "hello stdout" in merged_text
    assert "oops stderr" in merged_text

    # Streams must have been restored
    assert sys.stdout is old_out
    assert sys.stderr is old_err


def test_capture_output_restores_streams_after_exception() -> None:
    """Even on exception, sys.stdout/stderr should be restored."""
    # --- setup ---
    old_out, old_err = sys.stdout, sys.stderr

    # --- execute and verify ---
    with mod_utils.capture_output():
        print("before boom")
        with pytest.raises(RuntimeError, match="boom"):
            raise RuntimeError("boom")  # noqa: EM101

    assert sys.stdout is old_out
    assert sys.stderr is old_err

    # --- captured output attachment ---
    with pytest.raises(ValueError, match="expected fail") as exc_info:  # noqa: SIM117
        with mod_utils.capture_output():
            raise ValueError("expected fail")  # noqa: EM101, TRY003

    e = exc_info.value
    assert hasattr(e, "captured_output")
    captured = cast("mod_utils.CapturedOutput", getattr(e, "captured_output"))  # noqa: B009
    assert isinstance(captured.stdout, StringIO)
    assert isinstance(captured.stderr, StringIO)
    assert isinstance(captured.merged, StringIO)


def test_capture_output_interleaved_writes_preserve_order() -> None:
    """Merged stream should record messages in chronological order."""
    # --- execute ---
    with mod_utils.capture_output() as cap:
        print("A1", end="")  # stdout
        print("B1", end="", file=sys.stderr)
        print("A2", end="")  # stdout
        print("B2", end="", file=sys.stderr)

    # --- verify ---
    merged = cap.merged.getvalue()
    # It should appear exactly in the order written
    order = (
        merged.index("A1")
        < merged.index("B1")
        < merged.index("A2")
        < merged.index("B2")
    )
    assert order


def test_capture_output_supports_str_method_and_as_dict() -> None:
    """CapturedOutput should stringify and export all buffers cleanly."""
    # --- execute ---
    with mod_utils.capture_output() as cap:
        print("hello")
        print("err", file=sys.stderr)

    # --- verify ---
    s = str(cap)
    d = cap.as_dict()

    assert isinstance(s, str)
    assert "hello" in s
    assert "err" in s
    assert all(k in d for k in ("stdout", "stderr", "merged"))
    assert d["stdout"].strip().startswith("hello")
