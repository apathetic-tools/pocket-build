# tests/test_cli.py
"""Tests for pocket_build.cli (module and single-file versions)."""

# we import `_` private for testing purposes only
# pyright: reportPrivateUsage=false
# ruff: noqa: F401

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from pocket_build.meta import PROGRAM_DISPLAY, PROGRAM_SCRIPT


def test_main_no_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should print a warning and return exit code 1 when config is missing."""
    import pocket_build.cli as mod_cli

    # --- patch and execute ---
    with monkeypatch.context() as mp:
        mp.chdir(tmp_path)
        code = mod_cli.main([])

    # --- verify ---
    assert code == 1
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "No build config" in out


def test_main_with_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should detect config, run one build, and exit cleanly."""
    import pocket_build.cli as mod_cli

    # --- setup ---
    config = tmp_path / f".{PROGRAM_SCRIPT}.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))

    # --- patch and execute ---
    with monkeypatch.context() as mp:
        mp.chdir(tmp_path)
        code = mod_cli.main([])

    # --- verify ---
    out = capsys.readouterr().out
    assert code == 0
    assert "Build completed" in out


def test_help_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should print usage information and exit cleanly when --help is passed."""
    import pocket_build.cli as mod_cli

    # --- execute and verify ---
    # Capture SystemExit since argparse exits after printing help.
    with pytest.raises(SystemExit) as e:
        mod_cli.main(["--help"])

        # Argparse exits with code 0 for --help
        assert e.value.code == 0

    out = capsys.readouterr().out
    assert "usage:" in out.lower()
    assert PROGRAM_SCRIPT in out
    assert "--out" in out


def test_version_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should print version and commit info cleanly."""
    import pocket_build.cli as mod_cli

    # --- execute ---
    code = mod_cli.main(["--version"])

    # --- verify ---
    out = capsys.readouterr().out
    assert code == 0
    assert PROGRAM_DISPLAY in out
    assert re.search(r"\d+\.\d+\.\d+", out)

    if os.getenv("RUNTIME_MODE") in {"singlefile"}:
        # Bundled version — commit may be known or local
        if os.getenv("CI") or os.getenv("GIT_TAG") or os.getenv("GITHUB_REF"):
            assert re.search(r"\([0-9a-f]{4,}\)", out)
        else:
            assert "(unknown (local build))" in out
    else:
        # Module (source) version — should always have a live git commit hash
        assert re.search(r"\([0-9a-f]{4,}\)", out)


def test_dry_run_creates_no_files(tmp_path: Path) -> None:
    import pocket_build.cli as mod_cli

    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "foo.txt").write_text("data")

    config = tmp_path / f".{PROGRAM_SCRIPT}.json"
    config.write_text('{"builds": [{"include": ["src/**"], "out": "dist"}]}')

    # --- execute ---
    code = mod_cli.main(["--config", str(config), "--dry-run"])

    # --- verify ---
    assert code == 0
    assert not (tmp_path / "dist").exists()
