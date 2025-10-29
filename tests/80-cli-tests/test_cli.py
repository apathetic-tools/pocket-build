# tests/test_cli.py
"""Tests for package.cli (module and single-file versions)."""

import json
import os
import re
from pathlib import Path

import pytest
from pytest import MonkeyPatch

import pocket_build.cli as mod_cli
import pocket_build.meta as mod_meta
from tests.utils import TRACE

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_main_no_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
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
    monkeypatch: MonkeyPatch,
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
        # Bundled version — commit may be known or local
        if os.getenv("CI") or os.getenv("GIT_TAG") or os.getenv("GITHUB_REF"):
            assert re.search(r"\([0-9a-f]{4,}\)", out)
        else:
            assert "(unknown (local build))" in out
    else:
        # Module (source) version — should always have a live git commit hash
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
