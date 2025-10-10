"""Tests for pocket_build.build"""

from pathlib import Path

import pytest

from pocket_build.build import copy_directory, copy_file, copy_item, run_build
from pocket_build.types import BuildConfig


def test_copy_file_creates_and_copies(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    src = tmp_path / "a.txt"
    src.write_text("hi")
    dest = tmp_path / "out" / "a.txt"

    copy_file(src, dest, tmp_path)
    out = dest.read_text()
    assert out == "hi"
    captured = capsys.readouterr().out
    assert "📄" in captured


def test_copy_directory_respects_excludes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "keep.txt").write_text("ok")
    (src_dir / "skip.txt").write_text("no")

    dest = tmp_path / "out"
    copy_directory(src_dir, dest, ["**/skip.txt"], tmp_path)

    assert (dest / "keep.txt").exists()
    assert not (dest / "skip.txt").exists()

    captured = capsys.readouterr().out
    assert "🚫" in captured or "📄" in captured


def test_copy_item_handles_file_and_dir(tmp_path: Path):
    src_dir = tmp_path / "dir"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("data")

    dest = tmp_path / "out"
    copy_item(src_dir, dest, [], tmp_path)
    assert (dest / "a.txt").exists()


def test_run_build_creates_output_dir_and_copies(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "foo.txt").write_text("foo")

    build_cfg: BuildConfig = {"include": ["src"], "exclude": [], "out": "dist"}

    run_build(build_cfg, tmp_path, None)

    dist = tmp_path / "dist"
    assert (dist / "src" / "foo.txt").exists()
    captured = capsys.readouterr().out
    assert "✅ Build completed" in captured


def test_run_build_handles_missing_match(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    cfg: BuildConfig = {"include": ["nonexistent"], "out": "dist"}
    run_build(cfg, tmp_path, None)
    captured = capsys.readouterr().out
    assert "⚠️" in captured
