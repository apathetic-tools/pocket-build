# tests/test_cli.py
"""Tests for package.cli (package and standalone versions)."""

import json
import os
import re
from pathlib import Path

import pytest

import pocket_build.cli as mod_cli
import pocket_build.meta as mod_meta
import pocket_build.utils as mod_utils
import pocket_build.utils_using_runtime as mod_utils_runtime
from tests.utils import TRACE, patch_everywhere


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_main_no_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should print a warning and return exit code 1 when config is missing."""
    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    assert code == 1
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "No build config" in out


def test_main_with_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should detect config, run one build, and exit cleanly."""
    # --- setup ---
    config = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    out = capsys.readouterr().out
    assert code == 0
    assert "Build completed" in out


def test_help_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should print usage information and exit cleanly when --help is passed."""
    # --- execute ---
    # Capture SystemExit since argparse exits after printing help.
    with pytest.raises(SystemExit) as e:
        mod_cli.main(["--help"])

    # --- verify ---
    # Argparse exits with code 0 for --help (must be outside context)
    assert e.value.code == 0

    out = capsys.readouterr().out
    assert "usage:" in out.lower()
    assert mod_meta.PROGRAM_SCRIPT in out
    assert "--out" in out


def test_version_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should print version and commit info cleanly."""
    # --- execute ---
    code = mod_cli.main(["--version"])
    out = capsys.readouterr().out

    # --- verify ---
    TRACE(out)
    assert code == 0
    assert mod_meta.PROGRAM_DISPLAY in out
    assert re.search(r"\d+\.\d+\.\d+", out)

    if os.getenv("RUNTIME_MODE") in {"singlefile"}:
        # Standalone version — commit may be known or local
        if os.getenv("CI") or os.getenv("GIT_TAG") or os.getenv("GITHUB_REF"):
            assert re.search(r"\([0-9a-f]{4,}\)", out)
        else:
            assert "(unknown (local build))" in out
    else:
        # installed (source) version — should always have a live git commit hash
        assert re.search(r"\([0-9a-f]{4,}\)", out)


def test_dry_run_creates_no_files(tmp_path: Path) -> None:
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "foo.txt").write_text("data")

    config = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    config.write_text('{"builds": [{"include": ["src/**"], "out": "dist"}]}')

    # --- execute ---
    code = mod_cli.main(["--config", str(config), "--dry-run"])

    # --- verify ---
    assert code == 0
    assert not (tmp_path / "dist").exists()


def test_main_with_custom_config(tmp_path: Path) -> None:
    # --- setup ---
    config = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    config.write_text('{"builds": [{"include": ["src"], "out": "dist"}]}')

    # --- execute ---
    code = mod_cli.main(["--config", str(config)])

    # --- verify ---
    assert code == 0


def test_main_invalid_config(tmp_path: Path) -> None:
    # --- setup ---
    bad = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    bad.write_text("{not valid json}")

    # --- execute ---
    code = mod_cli.main(["--config", str(bad)])

    # --- verify ---
    assert code == 1


# --- exception catching -----------------------------------------


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
