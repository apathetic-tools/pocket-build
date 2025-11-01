# tests/test_cli.py
"""Tests for package.cli (package and standalone versions)."""

import pytest

import pocket_build.cli as mod_cli
import pocket_build.utils as mod_utils
import pocket_build.utils_using_runtime as mod_utils_runtime
from tests.utils import patch_everywhere


def test_main_handles_controlled_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate a controlled exception (e.g. ValueError) and verify clean handling."""
    # --- setup ---
    called: dict[str, bool] = {}

    # --- stubs ---
    def fake_parser() -> object:
        xmsg = "mocked config failure"
        raise ValueError(xmsg)

    def fake_log(*_a: object, **_k: object) -> None:
        called.setdefault("log", True)

    # --- patch and execute ---
    patch_everywhere(monkeypatch, mod_cli, "_setup_parser", fake_parser)
    patch_everywhere(monkeypatch, mod_utils_runtime, "log", fake_log)
    code = mod_cli.main([])

    # --- verify ---
    assert code == 1
    assert "log" in called  # ensure log() was called for controlled exception


def test_main_handles_unexpected_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate an unexpected internal error and ensure it logs as critical."""
    # --- setup ---
    called: dict[str, str] = {}

    # --- stubs ---
    def fake_parser() -> object:
        xmsg = "boom!"
        raise OSError(xmsg)  # not one of the controlled types

    def fake_log(level: str, msg: str, **_kw: object) -> None:
        called["level"] = level
        called["msg"] = msg

    # --- patch and execute ---
    patch_everywhere(monkeypatch, mod_cli, "_setup_parser", fake_parser)
    patch_everywhere(monkeypatch, mod_utils_runtime, "log", fake_log)
    code = mod_cli.main([])

    # --- verify ---
    assert code == 1
    assert called["level"] == "critical"
    assert "Unexpected internal error" in called["msg"]


def test_main_fallbacks_to_safe_log(monkeypatch: pytest.MonkeyPatch) -> None:
    """If log() itself fails, safe_log() should be called instead of recursion."""
    # --- setup ---
    called: dict[str, str] = {}

    # --- stubs ---
    def fake_parser() -> object:
        xmsg = "simulated fail"
        raise ValueError(xmsg)

    def bad_log(*_a: object, **_k: object) -> None:
        xmsg = "log fail"
        raise RuntimeError(xmsg)

    def fake_safe_log(msg: str) -> None:
        called["msg"] = msg

    # --- patch and execute ---
    patch_everywhere(monkeypatch, mod_cli, "_setup_parser", fake_parser)
    patch_everywhere(monkeypatch, mod_utils_runtime, "log", bad_log)
    patch_everywhere(monkeypatch, mod_utils, "safe_log", fake_safe_log)
    code = mod_cli.main([])

    # --- verify ---
    assert code == 1
    assert "Logging failed while reporting" in called["msg"]
