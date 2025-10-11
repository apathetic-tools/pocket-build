# tests/test_cli.py
"""Tests for pocket_build.cli (module and single-file versions)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch
from conftest import PocketBuildLike


def test_main_no_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """Should print a warning and return exit code 1 when config is missing."""
    monkeypatch.chdir(tmp_path)

    code = pocket_build_env.main([])
    assert code == 1

    out = capsys.readouterr().out
    assert "No build config" in out


def test_main_with_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """Should detect config, run one build, and exit cleanly."""
    config = tmp_path / ".pocket-build.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))
    monkeypatch.chdir(tmp_path)

    code = pocket_build_env.main([])
    out = capsys.readouterr().out

    assert code == 0
    assert "Build completed" in out


def test_help_flag(
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """Should print usage information and exit cleanly when --help is passed."""
    # Capture SystemExit since argparse exits after printing help.
    with pytest.raises(SystemExit) as e:
        pocket_build_env.main(["--help"])

    # Argparse exits with code 0 for --help
    assert e.value.code == 0

    out = capsys.readouterr().out
    assert "usage:" in out.lower()
    assert "pocket-build" in out
    assert "--out" in out


def test_version_flag(
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """Should print version and commit info cleanly."""
    code = pocket_build_env.main(["--version"])
    out = capsys.readouterr().out

    assert code == 0
    assert "Pocket Build" in out
    assert re.search(r"\d+\.\d+\.\d+", out) or "unknown" in out
    assert re.search(r"\([0-9a-f]{4,}\)", out) or "(unknown)" in out


def test_quiet_flag(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """Should suppress most output but still succeed."""
    config = tmp_path / ".pocket-build.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))
    monkeypatch.chdir(tmp_path)

    code = pocket_build_env.main(["--quiet"])
    out = capsys.readouterr().out

    assert code == 0
    # should not contain normal messages
    assert "Build completed" not in out
    assert "All builds complete" not in out
