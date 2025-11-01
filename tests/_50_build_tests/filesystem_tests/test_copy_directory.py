# tests/test_build_filesystem.py
"""Tests for package.build (package and standalone versions)."""

from pathlib import Path

import pytest

import pocket_build.build as mod_build
import pocket_build.runtime as mod_runtime


def test_copy_directory_respects_excludes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure copy_directory skips excluded files."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "keep.txt").write_text("ok")
    (src_dir / "skip.txt").write_text("no")
    dest = tmp_path / "out"

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "debug")
    mod_build.copy_directory(
        src_dir, dest, ["**/skip.txt"], src_root=tmp_path, dry_run=False
    )

    # --- verify ---
    assert (dest / "keep.txt").exists()
    assert not (dest / "skip.txt").exists()

    # still needed?
    out = capsys.readouterr().out
    assert "🚫" in out or "📄" in out


def test_copy_directory_empty_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """copy_directory should create the destination even for an empty folder."""
    # --- setup ---
    src_dir = tmp_path / "empty"
    src_dir.mkdir()
    dest = tmp_path / "out"

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "warning")
    mod_build.copy_directory(src_dir, dest, [], src_root=tmp_path, dry_run=False)

    # --- verify ---
    assert dest.exists()
    assert list(dest.iterdir()) == []
