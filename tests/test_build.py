# tests/test_build.py
"""Tests for pocket_build.build (module and single-file versions)."""

from pathlib import Path

import pytest

from pocket_build.types import BuildConfig, MetaBuildConfig
from tests.conftest import RuntimeLike


def test_copy_file_creates_and_copies(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """Ensure copy_file creates directories and copies file content."""
    src = tmp_path / "a.txt"
    src.write_text("hi")
    dest = tmp_path / "out" / "a.txt"

    runtime_env.current_runtime["log_level"] = "debug"  # verbose
    runtime_env.copy_file(src, dest, tmp_path)

    out = dest.read_text()
    assert out == "hi"
    captured = capsys.readouterr().out
    assert "📄" in captured


def test_copy_directory_respects_excludes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """Ensure copy_directory skips excluded files."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "keep.txt").write_text("ok")
    (src_dir / "skip.txt").write_text("no")

    dest = tmp_path / "out"
    runtime_env.current_runtime["log_level"] = "debug"  # verbose
    runtime_env.copy_directory(src_dir, dest, ["**/skip.txt"], tmp_path)

    assert (dest / "keep.txt").exists()
    assert not (dest / "skip.txt").exists()

    captured = capsys.readouterr().out
    assert "🚫" in captured or "📄" in captured


def test_copy_item_handles_file_and_dir(
    tmp_path: Path,
    runtime_env: RuntimeLike,
) -> None:
    """Ensure copy_item handles directories and individual files."""
    src_dir = tmp_path / "dir"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("data")

    dest = tmp_path / "out"

    meta: MetaBuildConfig = {
        "include_base": str(tmp_path),
        "exclude_base": str(tmp_path),
        "out_base": str(tmp_path),
        "origin": str(tmp_path),
    }

    runtime_env.current_runtime["log_level"] = "critical"  # normal
    runtime_env.copy_item(src_dir, dest, [], meta)
    assert (dest / "a.txt").exists()


def test_run_build_creates_output_dir_and_copies(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """Validate full build execution flow."""
    project_root = tmp_path
    src_dir = project_root / "src"
    src_dir.mkdir()
    (src_dir / "foo.txt").write_text("foo")

    # Create meta info similar to what resolve_build_config() would produce
    meta: MetaBuildConfig = {
        "include_base": str(project_root),
        "exclude_base": str(project_root),
        "out_base": str(project_root),
        "origin": str(project_root),
    }

    build_cfg: BuildConfig = {
        "include": [str(src_dir)],
        "exclude": [],
        "out": str(project_root / "dist"),
        "__meta__": meta,
    }
    runtime_env.current_runtime["log_level"] = "critical"  # normal
    runtime_env.run_build(build_cfg)

    dist = project_root / "dist"
    assert (dist / "src" / "foo.txt").exists()

    captured = capsys.readouterr().out
    assert "✅ Build completed" in captured


def test_run_build_handles_missing_match(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """Ensure run_build gracefully handles missing sources."""
    project_root = tmp_path
    meta: MetaBuildConfig = {
        "include_base": str(project_root),
        "exclude_base": str(project_root),
        "out_base": str(project_root),
        "origin": str(project_root),
    }

    nonexistent_path = project_root / "nonexistent"

    cfg: BuildConfig = {
        "include": [str(nonexistent_path)],
        "exclude": [],
        "out": str(project_root / "dist"),
        "__meta__": meta,
    }
    runtime_env.current_runtime["log_level"] = "debug"  # verbose
    runtime_env.run_build(cfg)
    captured = capsys.readouterr().out
    assert "⚠️" in captured


def test_parse_builds_handles_single_and_multiple(runtime_env: RuntimeLike):
    assert runtime_env.parse_builds({"builds": [{"include": []}]}) == [{"include": []}]
    assert runtime_env.parse_builds({"include": []}) == [{"include": []}]
