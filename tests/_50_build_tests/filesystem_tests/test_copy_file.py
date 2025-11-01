# tests/test_build_filesystem.py
"""Tests for package.build (package and standalone versions)."""

from pathlib import Path

import pytest

import pocket_build.build as mod_build
import pocket_build.runtime as mod_runtime


def test_copy_file_creates_and_copies(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure copy_file creates directories and copies file content."""
    # --- setup ---
    src = tmp_path / "a.txt"
    src.write_text("hi")
    dest = tmp_path / "out" / "a.txt"

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "debug")
    mod_build.copy_file(src, dest, src_root=tmp_path, dry_run=False)

    # --- verify ---
    assert dest.read_text() == "hi"
    out = capsys.readouterr().out
    assert "📄" in out


def test_copy_file_overwrites_existing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """copy_file should overwrite existing destination content."""
    # --- setup ---
    src = tmp_path / "a.txt"
    src.write_text("new")
    dest = tmp_path / "out" / "a.txt"
    dest.parent.mkdir(parents=True)
    dest.write_text("old")

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "error")
    mod_build.copy_file(src, dest, src_root=tmp_path, dry_run=False)

    # --- verify ---
    assert dest.read_text() == "new"


def test_copy_file_symlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # --- setup ---
    target = tmp_path / "target.txt"
    target.write_text("hi")
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    dest = tmp_path / "out" / "link.txt"

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "debug")
    mod_build.copy_file(link, dest, src_root=tmp_path, dry_run=False)

    # --- verify ---
    assert dest.read_text() == "hi"
