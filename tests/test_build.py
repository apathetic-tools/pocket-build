# tests/test_build.py
"""Tests for package.build (module and single-file versions)."""

from pathlib import Path

import pytest

from pocket_build.types import BuildConfig, MetaBuildConfig


def test_copy_file_creates_and_copies(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Ensure copy_file creates directories and copies file content."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src = tmp_path / "a.txt"
    src.write_text("hi")

    dest = tmp_path / "out" / "a.txt"

    # --- execute ---
    mod_runtime.current_runtime["log_level"] = "debug"  # verbose
    mod_build.copy_file(src, dest, tmp_path, False)

    # --- verify ---
    out = dest.read_text()
    assert out == "hi"

    captured = capsys.readouterr().out
    assert "📄" in captured


def test_copy_directory_respects_excludes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
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
    mod_runtime.current_runtime["log_level"] = "debug"  # verbose
    mod_build.copy_directory(src_dir, dest, ["**/skip.txt"], tmp_path, False)

    # --- verify ---
    assert (dest / "keep.txt").exists()
    assert not (dest / "skip.txt").exists()

    captured = capsys.readouterr().out
    assert "🚫" in captured or "📄" in captured


def test_copy_item_handles_file_and_dir(
    tmp_path: Path,
) -> None:
    """Ensure copy_item handles directories and individual files."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
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

    # --- execute ---
    mod_runtime.current_runtime["log_level"] = "critical"  # normal
    mod_build.copy_item(src_dir, dest, [], meta, False)

    # --- verify ---
    assert (dest / "a.txt").exists()


def test_run_build_creates_output_dir_and_copies(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Validate full build execution flow."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
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

    # --- execute ---
    mod_runtime.current_runtime["log_level"] = "info"  # normal
    mod_build.run_build(build_cfg)

    # --- verify ---
    dist = project_root / "dist"
    assert (dist / "src" / "foo.txt").exists()

    captured = capsys.readouterr().out
    assert "✅ Build completed" in captured


def test_run_build_handles_missing_match(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Ensure run_build gracefully handles missing sources."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
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

    # --- execute ---
    mod_runtime.current_runtime["log_level"] = "debug"  # verbose
    mod_build.run_build(cfg)

    # --- verify ---
    captured = capsys.readouterr().out
    assert "⚠️" in captured
