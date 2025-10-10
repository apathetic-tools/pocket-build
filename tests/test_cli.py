"""Tests for pocket_build.cli"""

import json
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from pocket_build.cli import main


def test_main_no_config(
    tmp_path: Path, monkeypatch: MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.chdir(tmp_path)
    code = main([])
    assert code == 1
    out = capsys.readouterr().out
    assert "No build config" in out


def test_main_with_config(
    tmp_path: Path, monkeypatch: MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    config = tmp_path / ".pocket-build.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))
    monkeypatch.chdir(tmp_path)

    code = main([])
    out = capsys.readouterr().out
    assert code == 0
    assert "Build completed" in out
