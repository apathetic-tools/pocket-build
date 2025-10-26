# tests/test_cli_log_level.py
"""Tests for package.cli (module and single-file versions)."""

import json
from pathlib import Path

import pytest
from pytest import MonkeyPatch

import pocket_build.cli as mod_cli
import pocket_build.runtime as mod_runtime
from pocket_build.meta import PROGRAM_ENV, PROGRAM_SCRIPT


def test_quiet_flag(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should suppress most output but still succeed."""
    # --- setup ---
    config = tmp_path / f".{PROGRAM_SCRIPT}.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--quiet"])

    # --- verify ---
    out = capsys.readouterr().out
    assert code == 0
    # should not contain normal messages
    assert "Build completed" not in out
    assert "All builds complete" not in out


def test_verbose_flag(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should print detailed file-level logs when --verbose is used."""
    # --- setup ---
    # create a tiny input directory with a file to copy
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "foo.txt").write_text("hello")

    config = tmp_path / f".{PROGRAM_SCRIPT}.json"
    config.write_text(
        json.dumps({"builds": [{"include": ["src/**"], "exclude": [], "out": "dist"}]})
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--verbose"])

    # --- verify ---
    captured = capsys.readouterr()
    out = captured.out + captured.err

    assert code == 0
    # Verbose mode should show per-file details
    assert "📄" in out or "🚫" in out
    # It should still include summary
    assert "Build completed" in out
    assert "All builds complete" in out

    assert mod_runtime.current_runtime["log_level"] == "debug"


def test_verbose_and_quiet_mutually_exclusive(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should fail when both --verbose and --quiet are provided."""
    # --- setup ---
    config = tmp_path / f".{PROGRAM_SCRIPT}.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))

    # --- patch and execute and verify ---
    monkeypatch.chdir(tmp_path)

    # argparse should exit with SystemExit(2)
    with pytest.raises(SystemExit) as e:
        mod_cli.main(["--quiet", "--verbose"])

    assert e.value.code == 2  # argparse error exit code # must be outside context

    # --- verify only ---
    captured = capsys.readouterr()
    combined = captured.out + captured.err

    assert "not allowed with argument" in combined or "mutually exclusive" in combined
    assert "--quiet" in combined and "--verbose" in combined


def test_log_level_flag_sets_runtime(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--log-level should override config and environment."""
    # --- setup ---
    config = tmp_path / f".{PROGRAM_SCRIPT}.json"
    config.write_text('{"builds": [{"include": [], "out": "dist"}]}')

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--log-level", "debug"])

    # --- verify ---
    out = capsys.readouterr().out

    assert code == 0
    assert "Build completed" in out
    # Verify that runtime log level is set correctly
    assert mod_runtime.current_runtime["log_level"] == "debug"


def test_log_level_from_env_var(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """LOG_LEVEL and {PROGRAM_ENV}_LOG_LEVEL should be respected when flag not given."""
    # --- setup ---
    config = tmp_path / f".{PROGRAM_SCRIPT}.json"
    config.write_text('{"builds": [{"include": [], "out": "dist"}]}')

    # --- patch and execute and verify ---
    monkeypatch.chdir(tmp_path)

    # 1️⃣ Specific env var wins
    monkeypatch.setenv(f"{PROGRAM_ENV}_LOG_LEVEL", "warning")
    code = mod_cli.main([])

    assert code == 0
    assert mod_runtime.current_runtime["log_level"] == "warning"

    # 2️⃣ Generic LOG_LEVEL fallback works
    monkeypatch.delenv(f"{PROGRAM_ENV}_LOG_LEVEL")
    monkeypatch.setenv("LOG_LEVEL", "error")
    code = mod_cli.main([])

    assert code == 0
    assert mod_runtime.current_runtime["log_level"] == "error"

    monkeypatch.delenv("LOG_LEVEL", raising=False)


def test_per_build_log_level_override(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A build's own log_level should temporarily override the runtime level."""
    # --- setup ---
    # Root config sets info, but the build overrides to debug
    config = tmp_path / f".{PROGRAM_SCRIPT}.json"
    config.write_text(
        json.dumps(
            {
                "log_level": "info",
                "builds": [
                    {"include": [], "out": "dist1"},
                    {"include": [], "out": "dist2", "log_level": "debug"},
                ],
            }
        )
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    captured = capsys.readouterr()
    out = captured.out + captured.err

    assert code == 0
    # It should have built both directories
    assert (tmp_path / "dist1").exists()
    assert (tmp_path / "dist2").exists()

    # During the second build, debug logs should have appeared
    assert "[DEBUG" in out or "Overriding log level" in out

    # After all builds complete, runtime should be restored to root level
    assert mod_runtime.current_runtime["log_level"] == "info"
