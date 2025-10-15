# tests/test_cli.py
"""Tests for pocket_build.cli (module and single-file versions)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest
from _pytest.monkeypatch import MonkeyPatch

from tests.conftest import RuntimeLike


def test_main_no_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """Should print a warning and return exit code 1 when config is missing."""
    monkeypatch.chdir(tmp_path)

    code = runtime_env.main([])
    assert code == 1

    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "No build config" in out


def test_main_with_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """Should detect config, run one build, and exit cleanly."""
    config = tmp_path / f".{runtime_env.PROGRAM_SCRIPT}.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))
    monkeypatch.chdir(tmp_path)

    code = runtime_env.main([])
    out = capsys.readouterr().out

    assert code == 0
    assert "Build completed" in out


def test_help_flag(
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """Should print usage information and exit cleanly when --help is passed."""
    # Capture SystemExit since argparse exits after printing help.
    with pytest.raises(SystemExit) as e:
        runtime_env.main(["--help"])

    # Argparse exits with code 0 for --help
    assert e.value.code == 0

    out = capsys.readouterr().out
    assert "usage:" in out.lower()
    assert runtime_env.PROGRAM_SCRIPT in out
    assert "--out" in out


def test_version_flag(
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """Should print version and commit info cleanly."""
    code = runtime_env.main(["--version"])
    out = capsys.readouterr().out

    assert code == 0
    assert runtime_env.PROGRAM_DISPLAY in out

    assert re.search(r"\d+\.\d+\.\d+", out)

    env_mod = cast(ModuleType, runtime_env)
    if "pocket_build_single" in env_mod.__name__:
        # Single-file build case
        if os.getenv("CI") or os.getenv("GIT_TAG") or os.getenv("GITHUB_REF"):
            assert re.search(r"\([0-9a-f]{4,}\)", out)
        else:
            assert "(unknown (local build))" in out
    else:
        # Modular source version — uses live Git
        assert re.search(r"\([0-9a-f]{4,}\)", out)


def test_dry_run_creates_no_files(tmp_path: Path, runtime_env: RuntimeLike):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "foo.txt").write_text("data")

    config = tmp_path / f".{runtime_env.PROGRAM_SCRIPT}.json"
    config.write_text('{"builds": [{"include": ["src/**"], "out": "dist"}]}')

    code = runtime_env.main(["--config", str(config), "--dry-run"])
    assert code == 0
    assert not (tmp_path / "dist").exists()
