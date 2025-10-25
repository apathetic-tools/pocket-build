# tests/test_build_filesystem.py
"""Tests for package.build (module and single-file versions)."""

from pathlib import Path
from typing import cast

from pytest import CaptureFixture, MonkeyPatch

from pocket_build.types import (
    PathResolved,
)

# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------


def _resolved(path: Path | str, base: Path | str) -> PathResolved:
    """Return a fake PathResolved-style dict."""
    return cast(PathResolved, {"path": path, "base": Path(base), "origin": "test"})


# ---------------------------------------------------------------------------
# Unit tests for individual functions
# ---------------------------------------------------------------------------


def test_copy_file_creates_and_copies(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: MonkeyPatch,
) -> None:
    """Ensure copy_file creates directories and copies file content."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src = tmp_path / "a.txt"
    src.write_text("hi")
    dest = tmp_path / "out" / "a.txt"

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "debug")
    mod_build.copy_file(src, dest, tmp_path, False)

    # --- verify ---
    assert dest.read_text() == "hi"
    out = capsys.readouterr().out
    assert "📄" in out


def test_copy_directory_respects_excludes(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: MonkeyPatch,
) -> None:
    """Ensure copy_directory skips excluded files."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "keep.txt").write_text("ok")
    (src_dir / "skip.txt").write_text("no")
    dest = tmp_path / "out"

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "debug")
    mod_build.copy_directory(src_dir, dest, ["**/skip.txt"], tmp_path, False)

    # --- verify ---
    assert (dest / "keep.txt").exists()
    assert not (dest / "skip.txt").exists()

    # still needed?
    out = capsys.readouterr().out
    assert "🚫" in out or "📄" in out


def test_copy_item_copies_single_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """copy_item should copy a single file to the resolved destination."""

    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src_file = tmp_path / "file.txt"
    src_file.write_text("content")

    src_entry = _resolved(src_file, tmp_path)
    dest_entry = _resolved(tmp_path / "out" / "file.txt", tmp_path)

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    mod_build.copy_item(src_entry, dest_entry, [], False)

    # --- verify ---
    assert (tmp_path / "out" / "file.txt").exists()
    assert (tmp_path / "out" / "file.txt").read_text() == "content"


def test_copy_item_handles_directory(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """copy_item should recursively copy directories."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src_dir = tmp_path / "dir"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("data")

    src_entry = _resolved(src_dir, tmp_path)
    dest_entry = _resolved(tmp_path / "out", tmp_path)

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "critical")
    mod_build.copy_item(src_entry, dest_entry, [], False)

    # --- verify ---
    # copy_directory copies contents, not the folder itself
    assert (tmp_path / "out" / "a.txt").exists()
    assert (tmp_path / "out" / "a.txt").read_text() == "data"


def test_copy_item_respects_excludes(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """copy_item should honor exclusion patterns."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "keep.txt").write_text("keep")
    (src_dir / "skip.txt").write_text("nope")

    src_entry = _resolved(src_dir, tmp_path)
    dest_entry = _resolved(tmp_path / "out", tmp_path)

    excludes = [_resolved("**/skip.txt", tmp_path)]

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "critical")
    mod_build.copy_item(src_entry, dest_entry, excludes, False)

    # --- verify ---
    assert (tmp_path / "out" / "keep.txt").exists()
    assert not (tmp_path / "out" / "skip.txt").exists()


def test_copy_item_respects_nested_excludes(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Deeply nested exclude patterns like **/skip.txt should be respected."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    src = tmp_path / "src"
    nested = src / "deep"
    nested.mkdir(parents=True)
    (nested / "keep.txt").write_text("ok")
    (nested / "skip.txt").write_text("no")

    src_entry = _resolved(src, tmp_path)
    dest_entry = _resolved(tmp_path / "out" / "src", tmp_path)
    excludes = [_resolved("**/skip.txt", tmp_path)]

    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "critical")
    mod_build.copy_item(src_entry, dest_entry, excludes, False)

    # --- verify ---
    assert (tmp_path / "out" / "src" / "deep" / "keep.txt").exists()
    assert not (tmp_path / "out" / "src" / "deep" / "skip.txt").exists()


def test_copy_item_respects_directory_excludes(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Exclude pattern with trailing slash should skip entire directories."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    src = tmp_path / "src"
    tmpdir = src / "tmp"
    tmpdir.mkdir(parents=True)
    (tmpdir / "bad.txt").write_text("no")
    (src / "keep.txt").write_text("ok")

    src_entry = _resolved(src, tmp_path)
    dest_entry = _resolved(tmp_path / "out" / "src", tmp_path)
    excludes = [_resolved("tmp/", tmp_path)]

    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "critical")
    mod_build.copy_item(src_entry, dest_entry, excludes, False)

    # --- verify ---
    assert (tmp_path / "out" / "src" / "keep.txt").exists()
    assert not (tmp_path / "out" / "src" / "tmp").exists()


# ---------------------------------------------------------------------------
# Additional edge and semantic coverage
# ---------------------------------------------------------------------------


def test_copy_file_overwrites_existing(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """copy_file should overwrite existing destination content."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src = tmp_path / "a.txt"
    src.write_text("new")
    dest = tmp_path / "out" / "a.txt"
    dest.parent.mkdir(parents=True)
    dest.write_text("old")

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "error")
    mod_build.copy_file(src, dest, tmp_path, False)

    # --- verify ---
    assert dest.read_text() == "new"


def test_copy_directory_empty_source(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """copy_directory should create the destination even for an empty folder."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src_dir = tmp_path / "empty"
    src_dir.mkdir()
    dest = tmp_path / "out"

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "warning")
    mod_build.copy_directory(src_dir, dest, [], tmp_path, False)

    # --- verify ---
    assert dest.exists()
    assert list(dest.iterdir()) == []


def test_copy_item_dry_run_skips_writing(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """copy_item with dry_run=True should not write anything to disk."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src_file = tmp_path / "foo.txt"
    src_file.write_text("data")

    src_entry = _resolved(src_file, tmp_path)
    dest_entry = _resolved(tmp_path / "out" / "foo.txt", tmp_path)

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    mod_build.copy_item(src_entry, dest_entry, [], True)

    # --- verify ---
    assert not (tmp_path / "out").exists()


def test_copy_item_nested_relative_path(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """copy_item should handle nested relative paths and preserve structure."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    nested = tmp_path / "src" / "nested"
    nested.mkdir(parents=True)
    (nested / "deep.txt").write_text("x")

    src_entry = _resolved(tmp_path / "src", tmp_path)
    dest_entry = _resolved(tmp_path / "out", tmp_path)

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "warning")
    mod_build.copy_item(src_entry, dest_entry, [], False)

    # --- verify ---
    assert (tmp_path / "out" / "nested" / "deep.txt").exists()


def test_copy_file_symlink(tmp_path: Path, monkeypatch: MonkeyPatch):
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    target = tmp_path / "target.txt"
    target.write_text("hi")
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    dest = tmp_path / "out" / "link.txt"

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "debug")
    mod_build.copy_file(link, dest, tmp_path, False)

    # --- verify ---
    assert dest.read_text() == "hi"
