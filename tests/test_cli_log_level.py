# tests/test_cli_log_level.py
"""Tests for pocket_build.cli (module and single-file versions)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from pocket_build.meta import PROGRAM_ENV
from tests.conftest import RuntimeLike


def test_quiet_flag(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """Should suppress most output but still succeed."""
    config = tmp_path / ".pocket-build.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))

    with monkeypatch.context() as mp:
        mp.chdir(tmp_path)
        code = runtime_env.main(["--quiet"])

        out = capsys.readouterr().out

        assert code == 0
        # should not contain normal messages
        assert "Build completed" not in out
        assert "All builds complete" not in out


def test_verbose_flag(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """Should print detailed file-level logs when --verbose is used."""
    # create a tiny input directory with a file to copy
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "foo.txt").write_text("hello")

    config = tmp_path / ".pocket-build.json"
    config.write_text(
        json.dumps({"builds": [{"include": ["src/**"], "exclude": [], "out": "dist"}]})
    )

    with monkeypatch.context() as mp:
        mp.chdir(tmp_path)
        code = runtime_env.main(["--verbose"])

        captured = capsys.readouterr()
        out = captured.out + captured.err

        assert code == 0
        # Verbose mode should show per-file details
        assert "📄" in out or "🚫" in out
        # It should still include summary
        assert "Build completed" in out
        assert "All builds complete" in out


def test_verbose_and_quiet_mutually_exclusive(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """Should fail when both --verbose and --quiet are provided."""
    config = tmp_path / ".pocket-build.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))

    with monkeypatch.context() as mp:
        mp.chdir(tmp_path)

        # argparse should exit with SystemExit(2)
        with pytest.raises(SystemExit) as e:
            runtime_env.main(["--quiet", "--verbose"])
            assert e.value.code == 2  # argparse error exit code

        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert (
            "not allowed with argument" in combined or "mutually exclusive" in combined
        )
        assert "--quiet" in combined and "--verbose" in combined


def test_log_level_flag_sets_runtime(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """--log-level should override config and environment."""
    config = tmp_path / ".pocket-build.json"
    config.write_text('{"builds": [{"include": [], "out": "dist"}]}')

    with monkeypatch.context() as mp:
        mp.chdir(tmp_path)
        code = runtime_env.main(["--log-level", "debug"])

        out = capsys.readouterr().out

        assert code == 0
        assert "Build completed" in out
        # Verify that runtime log level is set correctly
        assert runtime_env.current_runtime["log_level"] == "debug"


def test_log_level_from_env_var(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """LOG_LEVEL and {PROGRAM_ENV}_LOG_LEVEL should be respected when flag not given."""
    config = tmp_path / ".pocket-build.json"
    config.write_text('{"builds": [{"include": [], "out": "dist"}]}')

    with monkeypatch.context() as mp:
        mp.chdir(tmp_path)

        # 1️⃣ Specific env var wins
        mp.setenv(f"{PROGRAM_ENV}_LOG_LEVEL", "warning")
        code = runtime_env.main([])

        assert code == 0
        assert runtime_env.current_runtime["log_level"] == "warning"

        # 2️⃣ Generic LOG_LEVEL fallback works
        mp.delenv(f"{PROGRAM_ENV}_LOG_LEVEL")
        mp.setenv("LOG_LEVEL", "error")
        code = runtime_env.main([])

        assert code == 0
        assert runtime_env.current_runtime["log_level"] == "error"


def test_per_build_log_level_override(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """A build's own log_level should temporarily override the runtime level."""
    # Root config sets info, but the build overrides to debug
    config = tmp_path / ".pocket-build.json"
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

    with monkeypatch.context() as mp:
        mp.chdir(tmp_path)

        code = runtime_env.main([])
        captured = capsys.readouterr()
        out = captured.out + captured.err

        assert code == 0
        # It should have built both directories
        assert (tmp_path / "dist1").exists()
        assert (tmp_path / "dist2").exists()

        # During the second build, debug logs should have appeared
        assert "[DEBUG" in out or "Overriding log level" in out

        # After all builds complete, runtime should be restored to root level
        assert runtime_env.current_runtime["log_level"] == "info"
