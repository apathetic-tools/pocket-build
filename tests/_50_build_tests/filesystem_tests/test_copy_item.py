# tests/test_build_filesystem.py
"""Tests for package.build (package and standalone versions)."""

from pathlib import Path

import pytest

import pocket_build.build as mod_build
import pocket_build.runtime as mod_runtime
from tests.utils import make_resolved


def test_copy_item_copies_single_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """copy_item should copy a single file to the resolved destination."""
    # --- setup ---
    src_file = tmp_path / "file.txt"
    src_file.write_text("content")

    src_entry = make_resolved(src_file, tmp_path)
    dest_entry = make_resolved(tmp_path / "out" / "file.txt", tmp_path)

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    mod_build.copy_item(src_entry, dest_entry, [], dry_run=False)

    # --- verify ---
    assert (tmp_path / "out" / "file.txt").exists()
    assert (tmp_path / "out" / "file.txt").read_text() == "content"


def test_copy_item_handles_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """copy_item should recursively copy directories."""
    # --- setup ---
    src_dir = tmp_path / "dir"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("data")

    src_entry = make_resolved(src_dir, tmp_path)
    dest_entry = make_resolved(tmp_path / "out", tmp_path)

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "critical")
    mod_build.copy_item(src_entry, dest_entry, [], dry_run=False)

    # --- verify ---
    # copy_directory copies contents, not the folder itself
    assert (tmp_path / "out" / "a.txt").exists()
    assert (tmp_path / "out" / "a.txt").read_text() == "data"


def test_copy_item_respects_excludes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """copy_item should honor exclusion patterns."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "keep.txt").write_text("keep")
    (src_dir / "skip.txt").write_text("nope")

    src_entry = make_resolved(src_dir, tmp_path)
    dest_entry = make_resolved(tmp_path / "out", tmp_path)

    excludes = [make_resolved("**/skip.txt", tmp_path)]

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "critical")
    mod_build.copy_item(src_entry, dest_entry, excludes, dry_run=False)

    # --- verify ---
    assert (tmp_path / "out" / "keep.txt").exists()
    assert not (tmp_path / "out" / "skip.txt").exists()


def test_copy_item_respects_nested_excludes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deeply nested exclude patterns like **/skip.txt should be respected."""
    # --- setup ---
    src = tmp_path / "src"
    nested = src / "deep"
    nested.mkdir(parents=True)
    (nested / "keep.txt").write_text("ok")
    (nested / "skip.txt").write_text("no")

    src_entry = make_resolved(src, tmp_path)
    dest_entry = make_resolved(tmp_path / "out" / "src", tmp_path)
    excludes = [make_resolved("**/skip.txt", tmp_path)]

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "critical")
    mod_build.copy_item(src_entry, dest_entry, excludes, dry_run=False)

    # --- verify ---
    assert (tmp_path / "out" / "src" / "deep" / "keep.txt").exists()
    assert not (tmp_path / "out" / "src" / "deep" / "skip.txt").exists()


def test_copy_item_respects_directory_excludes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exclude pattern with trailing slash should skip entire directories."""
    # --- setup ---
    src = tmp_path / "src"
    tmpdir = src / "tmp"
    tmpdir.mkdir(parents=True)
    (tmpdir / "bad.txt").write_text("no")
    (src / "keep.txt").write_text("ok")

    src_entry = make_resolved(src, tmp_path)
    dest_entry = make_resolved(tmp_path / "out" / "src", tmp_path)
    excludes = [make_resolved("tmp/", tmp_path)]

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "critical")
    mod_build.copy_item(src_entry, dest_entry, excludes, dry_run=False)

    # --- verify ---
    assert (tmp_path / "out" / "src" / "keep.txt").exists()
    assert not (tmp_path / "out" / "src" / "tmp").exists()


def test_copy_item_dry_run_skips_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """copy_item with dry_run=True should not write anything to disk."""
    # --- setup ---
    src_file = tmp_path / "foo.txt"
    src_file.write_text("data")

    src_entry = make_resolved(src_file, tmp_path)
    dest_entry = make_resolved(tmp_path / "out" / "foo.txt", tmp_path)

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    mod_build.copy_item(src_entry, dest_entry, [], dry_run=True)

    # --- verify ---
    assert not (tmp_path / "out").exists()


def test_copy_item_nested_relative_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """copy_item should handle nested relative paths and preserve structure."""
    # --- setup ---
    nested = tmp_path / "src" / "nested"
    nested.mkdir(parents=True)
    (nested / "deep.txt").write_text("x")

    src_entry = make_resolved(tmp_path / "src", tmp_path)
    dest_entry = make_resolved(tmp_path / "out", tmp_path)

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "warning")
    mod_build.copy_item(src_entry, dest_entry, [], dry_run=False)

    # --- verify ---
    assert (tmp_path / "out" / "nested" / "deep.txt").exists()
