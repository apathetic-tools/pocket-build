"""Tests for pocket_build.cli (module and single-file versions)."""

from __future__ import annotations

import json
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
