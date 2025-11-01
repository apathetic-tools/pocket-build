# tests/30-utils-tests/_20_log_tests/test_safe_log.py


import sys
from io import StringIO

import pytest

import pocket_build.utils_using_runtime as mod_utils_runtime


def test_safe_log_writes_to_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    """safe_log() should write to __stderr__ without throwing."""
    # --- setup ---
    buf = StringIO()

    # --- patch and execute ---
    monkeypatch.setattr(sys, "__stderr__", buf)
    mod_utils_runtime.safe_log("hello safe")

    # --- verify ---
    assert "hello safe" in buf.getvalue()


def test_safe_log_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """safe_log() should survive even if sys.__stderr__ is None."""
    # --- patch and execute ---
    monkeypatch.setattr(sys, "__stderr__", None)
    # Should not raise
    mod_utils_runtime.safe_log("fallback works")


def test_safe_log_handles_print_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """If print() fails, safe_log() should fall back to .write()."""
    # --- setup ---
    buf = StringIO()

    # --- stubs ---
    def bad_print(*_args: object, **_kwargs: object) -> None:
        xmsg = "printer exploded"
        raise OSError(xmsg)

    # --- patch and execute ---
    monkeypatch.setattr(sys, "__stderr__", buf)
    monkeypatch.setattr("builtins.print", bad_print)
    mod_utils_runtime.safe_log("broken print test")

    # --- verify ---
    # Fallback write should prefix with [INTERNAL]
    assert "[INTERNAL]" in buf.getvalue()
