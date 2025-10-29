# tests/test_cli_overrides.py
"""Tests for package.cli (package and standalone versions)."""

import json
from pathlib import Path

import pytest
from pytest import MonkeyPatch

import pocket_build.cli as mod_cli
import pocket_build.meta as mod_meta


def test_include_flag_overrides_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--include should override config include patterns."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "foo.txt").write_text("ok")

    other_dir = tmp_path / "other"
    other_dir.mkdir()
    (other_dir / "bar.txt").write_text("nope")

    # Config originally points to wrong folder
    config = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    config.write_text(
        json.dumps(
            {"builds": [{"include": ["other/**"], "exclude": [], "out": "dist"}]}
        )
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    # Override include at CLI level
    code = mod_cli.main(["--include", "src/**"])

    # --- verify ---
    out = capsys.readouterr().out

    assert code == 0
    dist_dir = tmp_path / "dist"
    # Should copy src contents (flattened), not 'other'
    assert (dist_dir / "foo.txt").exists()
    assert not (dist_dir / "other").exists()
    assert "Build completed" in out


def test_exclude_flag_overrides_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--exclude should override config exclude patterns."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "keep.txt").write_text("keep me")
    (src_dir / "ignore.tmp").write_text("ignore me")

    # Config has no exclude rules
    config = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    config.write_text(json.dumps({"builds": [{"include": ["src/**"], "out": "dist"}]}))

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    # Pass exclude override on CLI
    code = mod_cli.main(["--exclude", "*.tmp"])

    # --- verify ---
    out = capsys.readouterr().out

    assert code == 0
    dist_dir = tmp_path / "dist"
    # The .tmp file should be excluded now
    assert (dist_dir / "keep.txt").exists()
    assert not (dist_dir / "ignore.tmp").exists()
    assert "Build completed" in out


def test_add_include_extends_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--add-include should extend config include patterns, not override them."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("A")

    extra_dir = tmp_path / "extra"
    extra_dir.mkdir()
    (extra_dir / "b.txt").write_text("B")

    # Config includes only src/**
    config = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    config.write_text(
        json.dumps({"builds": [{"include": ["src/**"], "exclude": [], "out": "dist"}]})
    )

    # --- patch and execute ---
    # Run with --add-include extra/**
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--add-include", "extra/**"])

    # --- verify ---
    out = capsys.readouterr().out

    assert code == 0
    dist = tmp_path / "dist"

    # ✅ Both directories should be included
    assert (dist / "a.txt").exists()
    assert (dist / "b.txt").exists()

    # Output should confirm the build
    assert "Build completed" in out


def test_add_exclude_extends_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--add-exclude should extend config exclude patterns, not override them."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "keep.txt").write_text("keep")
    (src_dir / "ignore.tmp").write_text("ignore")
    (src_dir / "ignore.log").write_text("ignore2")

    # Config excludes *.log files
    config = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    config.write_text(
        json.dumps(
            {"builds": [{"include": ["src/**"], "exclude": ["*.log"], "out": "dist"}]}
        )
    )

    # --- patch and execute ---
    # Add an extra exclude via CLI
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--add-exclude", "*.tmp"])

    # --- verify ---
    out = capsys.readouterr().out

    assert code == 0
    dist = tmp_path / "dist"

    # ✅ keep.txt should survive
    assert (dist / "keep.txt").exists()
    # 🚫 both excluded files should be missing
    assert not (dist / "ignore.tmp").exists()
    assert not (dist / "ignore.log").exists()

    assert "Build completed" in out
