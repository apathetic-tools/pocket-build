# tests/test_build.py
"""Tests for pocket_build.build (module and single-file versions)."""

from pathlib import Path

import pytest
from conftest import PocketBuildLike

from pocket_build.types import BuildConfig


def test_copy_file_creates_and_copies(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """Ensure copy_file creates directories and copies file content."""
    src = tmp_path / "a.txt"
    src.write_text("hi")
    dest = tmp_path / "out" / "a.txt"
    verbose = True

    pocket_build_env.copy_file(src, dest, tmp_path, verbose)

    out = dest.read_text()
    assert out == "hi"
    captured = capsys.readouterr().out
    assert "📄" in captured


def test_copy_directory_respects_excludes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """Ensure copy_directory skips excluded files."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "keep.txt").write_text("ok")
    (src_dir / "skip.txt").write_text("no")

    dest = tmp_path / "out"
    verbose = True
    pocket_build_env.copy_directory(src_dir, dest, ["**/skip.txt"], tmp_path, verbose)

    assert (dest / "keep.txt").exists()
    assert not (dest / "skip.txt").exists()

    captured = capsys.readouterr().out
    assert "🚫" in captured or "📄" in captured


def test_copy_item_handles_file_and_dir(
    tmp_path: Path,
    pocket_build_env: PocketBuildLike,
) -> None:
    """Ensure copy_item handles directories and individual files."""
    src_dir = tmp_path / "dir"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("data")

    dest = tmp_path / "out"
    verbose = False
    pocket_build_env.copy_item(src_dir, dest, [], tmp_path, verbose)
    assert (dest / "a.txt").exists()


def test_run_build_creates_output_dir_and_copies(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """Validate full build execution flow."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "foo.txt").write_text("foo")

    build_cfg: BuildConfig = {"include": ["src"], "exclude": [], "out": "dist"}

    verbose = False
    pocket_build_env.run_build(build_cfg, tmp_path, None, verbose)

    dist = tmp_path / "dist"
    assert (dist / "src" / "foo.txt").exists()

    captured = capsys.readouterr().out
    assert "✅ Build completed" in captured


def test_run_build_handles_missing_match(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """Ensure run_build gracefully handles missing sources."""
    cfg: BuildConfig = {"include": ["nonexistent"], "out": "dist"}
    verbose = True
    pocket_build_env.run_build(cfg, tmp_path, None, verbose)
    captured = capsys.readouterr().out
    assert "⚠️" in captured
